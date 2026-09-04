import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
import shopify_tools
from shopify_tools import get_order_status, check_stock

import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

load_dotenv()

groq_llm = LLM(
    model="groq/openai/gpt-oss-120b",
    api_key=os.environ["GROQ_API_KEY"],
)

support_agent = Agent(
    role="Customer Support Specialist",
    goal="Answer customer questions about their orders accurately and concisely.",
    backstory=(
        "You work for AnimePadEmporium, an online store selling anime and gaming desk mats "
        "and mousepads, fulfilled via Printify print-on-demand. You are friendly and concise. "
        "You NEVER invent product names, order details, or stock numbers. If a tool returns "
        "'No product found' or 'No order found', you tell the customer exactly that, plainly "
        "and honestly, and never substitute a guess or a made-up example instead. "
        "When check_stock finds matching products, the customer will see clickable size "
        "options displayed separately below your message, so keep your text reply brief: "
        "name the product(s) found and how many sizes are in stock, then tell the customer "
        "to pick a size below. Do not list every individual variant in your text."
	"If a customer asks about an order but does not provide an order number, do NOT call "
        "the order status tool. Instead, politely ask them for their order number first."
    ),
    tools=[get_order_status, check_stock],
    llm=groq_llm,
    verbose=True,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://animepademporium.myshopify.com",
        "https://animepademporium.co.uk",
        "https://www.animepademporium.co.uk",
    ],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatRequest):
    shopify_tools.last_stock_products = []

    task = Task(
        description=(
            f"A customer asked: '{req.message}'. Use your tools to answer accurately. "
            "If a tool returns 'No product found' or 'No order found', you MUST tell the "
            "customer that exact information, do NOT invent product names, order details, "
            "or stock levels under any circumstances. Only state facts returned by your tools. "
            "When check_stock finds matches, keep your reply to one short sentence per product "
            "(name + how many sizes in stock), and tell the customer to pick a size below. "
            "Do not list every variant individually in text."
        ),
        expected_output="A short, accurate answer using only tool output, or an honest 'not found' message.",
        agent=support_agent,
    )

    last_error = None
    for attempt in range(2):
        try:
            crew = Crew(agents=[support_agent], tasks=[task], process=Process.sequential, verbose=True)
            result = crew.kickoff()
            return {
                "reply": str(result),
                "products": shopify_tools.last_stock_products,
            }
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt + 1} failed: {e}")

    print(f"Both attempts failed, last error: {last_error}")
    return {
        "reply": "Sorry, I had a little trouble processing that, could you try rephrasing your question?",
        "products": [],
    }