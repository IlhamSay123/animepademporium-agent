import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from shopify_tools import get_order_status, check_stock

import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

load_dotenv()

groq_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
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
        "and honestly, and never substitute a guess or a made-up example instead."
    ),
    tools=[get_order_status, check_stock],
    llm=groq_llm,
    verbose=True,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://animepademporium.myshopify.com"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatRequest):
    task = Task(
        description=(
            f"A customer asked: '{req.message}'. Use your tools to answer accurately. "
            "If a tool returns 'No product found' or 'No order found', you MUST tell the "
            "customer that exact information, do NOT invent product names, order details, "
            "or stock levels under any circumstances. Only state facts returned by your tools. "
            "When listing multiple products or items, format each one on its own new line "
            "using a markdown-style bullet ('- '), never as one run-on paragraph. Keep each "
            "line short: product name, then size/variant in parentheses, then stock count. "
            "Do not use numbered lists. Keep the whole reply concise."
        ),
        expected_output="A clear, accurate answer using only tool output, or an honest 'not found' message.",
        agent=support_agent,
    )
    crew = Crew(agents=[support_agent], tasks=[task], process=Process.sequential, verbose=True)
    result = crew.kickoff()
    return {"reply": str(result)}