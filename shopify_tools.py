import os
import time
import requests
from dotenv import load_dotenv
from crewai.tools import tool

load_dotenv()

SHOP = os.environ["SHOPIFY_STORE"]
CLIENT_ID = os.environ["SHOPIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SHOPIFY_CLIENT_SECRET"]
API_VERSION = "2026-07"

_token_cache = {"token": None, "expires_at": 0}

# Side-channel: the last structured product results, read by server.py after each call
last_stock_products = []

def _get_access_token():
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    resp = requests.post(
        f"https://{SHOP}.myshopify.com/admin/oauth/access_token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    return _token_cache["token"]

def _graphql(query: str, variables: dict = None):
    token = _get_access_token()
    resp = requests.post(
        f"https://{SHOP}.myshopify.com/admin/api/{API_VERSION}/graphql.json",
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
    )
    resp.raise_for_status()
    return resp.json()

@tool("Get Order Status")
def get_order_status(order_number: str) -> str:
    """Look up a Shopify order's fulfillment status and tracking info by order number, e.g. '#1002' or '1002'."""
    name = order_number if order_number.startswith("#") else f"#{order_number}"
    query = """
    query getOrder($query: String!) {
      orders(first: 1, query: $query) {
        edges {
          node {
            name
            displayFulfillmentStatus
            displayFinancialStatus
            createdAt
            fulfillments(first: 5) {
              trackingInfo { number url company }
            }
          }
        }
      }
    }
    """
    result = _graphql(query, {"query": f"name:{name}"})
    edges = result.get("data", {}).get("orders", {}).get("edges", [])
    if not edges:
        return f"No order found matching {name}."
    order = edges[0]["node"]
    tracking = order["fulfillments"][0]["trackingInfo"] if order["fulfillments"] else []
    tracking_str = ", ".join(f"{t['company']} #{t['number']}" for t in tracking) if tracking else "no tracking yet"
    return (
        f"Order {order['name']}: fulfillment status is {order['displayFulfillmentStatus']}, "
        f"payment status is {order['displayFinancialStatus']}, placed on {order['createdAt']}. "
        f"Tracking: {tracking_str}."
    )

CONNECTOR_STOPWORDS = {"in", "stock", "any", "of", "the", "a", "an", "do", "you",
                        "have", "are", "there", "what", "show", "me", "list",
                        "all", "please", "some"}
PRODUCT_STOPWORD_STEMS = {"mousepad", "mouse", "pad", "mat", "desk"}

def _extract_keywords(text):
    words = []
    for w in text.lower().split():
        stem = w.rstrip("s")
        if w in CONNECTOR_STOPWORDS:
            continue
        if w in PRODUCT_STOPWORD_STEMS or stem in PRODUCT_STOPWORD_STEMS:
            continue
        words.append(w)
    return words

@tool("Check Product Stock")
def check_stock(product_title: str) -> str:
    """Check inventory levels for a product by (partial) title match. Also matches broad category terms like 'anime' or 'video game' to list multiple relevant products."""
    global last_stock_products
    last_stock_products = []

    words = _extract_keywords(product_title)
    if not words:
        words = product_title.lower().split()

    query_str = " AND ".join(f"title:*{w}*" for w in words)

    query = """
    query getProduct($query: String!) {
      products(first: 8, query: $query) {
        edges {
          node {
            title
            handle
            variants(first: 10) {
              edges {
                node {
                  id
                  title
                  inventoryQuantity
                }
              }
            }
          }
        }
      }
    }
    """
    result = _graphql(query, {"query": query_str})
    edges = result.get("data", {}).get("products", {}).get("edges", [])
    if not edges:
        return f"No product found matching '{product_title}'."

    lines = []
    for edge in edges:
        p = edge["node"]
        product_url = f"https://{SHOP}.myshopify.com/products/{p['handle']}"
        variants_out = []
        for v in p["variants"]["edges"]:
            variant = v["node"]
            variant_numeric_id = variant["id"].split("/")[-1]
            qty = variant["inventoryQuantity"]
            variants_out.append({
                "label": variant["title"],
                "stock": qty,
                "url": f"{product_url}?variant={variant_numeric_id}",
            })
            lines.append(f"{p['title']} ({variant['title']}): {qty} in stock")
        last_stock_products.append({
            "name": p["title"],
            "url": product_url,
            "variants": variants_out,
        })

    return "\n".join(lines)