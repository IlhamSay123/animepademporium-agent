import os
import requests
from dotenv import load_dotenv

load_dotenv()

SHOP = os.environ["SHOPIFY_STORE"]
CLIENT_ID = os.environ["SHOPIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SHOPIFY_CLIENT_SECRET"]

def get_access_token():
    resp = requests.post(
        f"https://{SHOP}.myshopify.com/admin/oauth/access_token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

token = get_access_token()
print("Got token:", token[:10] + "...")

resp = requests.post(
    f"https://{SHOP}.myshopify.com/admin/api/2026-07/graphql.json",
    headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
    json={"query": "{ shop { name } orders(first: 3) { edges { node { name displayFulfillmentStatus } } } }"},
)
print(resp.json())