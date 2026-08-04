# AnimePadEmporium Agent

An AI customer support agent for [AnimePadEmporium](https://animepademporium.myshopify.com), a Shopify store selling anime and gaming desk mats/mousepads. It answers customer questions about order status and product stock in real time, grounded entirely in live Shopify data, and ships as an embeddable chat widget on the storefront.

## Why this exists

Most "where's my order" and "is this in stock" messages are repetitive and don't need a human — but they still need to be *correct*, not a generic chatbot guess. This project automates that first line of support directly against the store's real Shopify data, so customers get an instant, accurate answer and only the genuinely tricky queries need a person.

It was also a chance to build an LLM agent against a real production API rather than a toy dataset: designing prompts and tool contracts that keep the agent from ever inventing an order number or stock count, handling a third-party API's auth/rate-limit realities, and shipping the result somewhere an actual customer could hit it.

## Features

- **Conversational order & stock lookups** — customers can ask things like *"where's my order #1002?"* or *"do you have any Berserk mousepads?"* and get accurate, real-time answers.
- **Grounded, hallucination-resistant responses** — the agent is instructed to only state facts returned by its tools and to say plainly when an order or product isn't found, never inventing details.
- **Live Shopify Admin API integration** — order fulfillment/tracking status and per-variant inventory levels are pulled directly from Shopify via GraphQL, not cached or guessed.
- **Smart product search** — natural-language queries are reduced to meaningful keywords (stripping filler words and generic terms like "mousepad" or "mat") so category-style questions ("any anime ones in stock?") still return relevant matches.
- **Clickable product/size results** — when stock is found, the API returns structured product + variant data (with direct storefront links) alongside the chat reply, so the widget can render pickable size options instead of a wall of text.
- **Resilient LLM calls** — failed or malformed tool-call responses from the LLM are automatically retried, with a friendly fallback message if both attempts fail.
- **Drop-in embeddable widget** — a self-contained HTML/CSS/JS chat widget that can be pasted directly into a Shopify theme, talking to the backend over a CORS-restricted REST endpoint.

## Tech Stack

| Layer | Technology |
|---|---|
| API server | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Agent orchestration | [CrewAI](https://www.crewai.com/) (Agent / Task / Crew) |
| LLM | Groq-hosted Llama 3.3 70B (via LiteLLM) |
| Store data | Shopify Admin GraphQL API (2026-07), OAuth2 client-credentials flow with token caching |
| Frontend | Vanilla HTML/CSS/JS embeddable widget |
| Config | python-dotenv |
| Deployment | Render (backend), Shopify theme (widget) |

## Architecture

```
Storefront (chat-widget.html)
        │  POST /chat { message }
        ▼
FastAPI server (server.py)
        │
        ▼
CrewAI Agent  ──tools──▶  shopify_tools.py
  (Groq LLM)                 │
        │                    ├─ get_order_status → Shopify GraphQL (orders)
        │                    └─ check_stock      → Shopify GraphQL (products/variants)
        ▼
{ reply, products[] }  →  rendered as text + clickable size links in the widget
```

## Project Structure

```
agent.py           CLI entrypoint for local testing of the agent loop
server.py          FastAPI app exposing the /chat endpoint
shopify_tools.py   Shopify Admin API auth + GraphQL tools (order status, stock check)
chat-widget.html   Embeddable storefront chat widget
shopify.app.toml   Shopify app configuration & API scopes
test_connection.py Standalone script to verify Shopify API credentials
test_chat.py       Quick manual test against a running /chat endpoint
requirements.txt   Python dependencies
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file with:
   ```
   GROQ_API_KEY=your_groq_key
   SHOPIFY_STORE=your-store-subdomain
   SHOPIFY_CLIENT_ID=your_app_client_id
   SHOPIFY_CLIENT_SECRET=your_app_client_secret
   ```
3. Run the API server:
   ```bash
   uvicorn server:app --reload
   ```
4. Embed `chat-widget.html` in your Shopify theme, pointing `API_URL` at your deployed backend.

## API

### `POST /chat`

**Request**
```json
{ "message": "do you have any Berserk mousepads?" }
```

**Response**
```json
{
  "reply": "We have 2 Berserk mousepads in stock — pick a size below.",
  "products": [
    { "name": "Berserk Mousepad", "url": "...", "variants": [ { "label": "XL", "stock": 4, "url": "..." } ] }
  ]
}
```

## Required Shopify Scopes

`read_customers`, `read_fulfillments`, `read_inventory`, `read_orders`, `read_products`
