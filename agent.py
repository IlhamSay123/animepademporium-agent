import os
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

def ask_agent(question: str) -> str:
    task = Task(
        description=(
            f"A customer asked: '{question}'. Use your tools to answer accurately. "
            "If a tool returns 'No product found' or 'No order found', you MUST tell the "
            "customer that exact information, do NOT invent product names, order details, "
            "or stock levels under any circumstances. Only state facts returned by your tools."
        ),
        expected_output="A clear, accurate answer using only tool output, or an honest 'not found' message.",
        agent=support_agent,
    )
    crew = Crew(agents=[support_agent], tasks=[task], process=Process.sequential, verbose=True)
    return crew.kickoff()

if __name__ == "__main__":
    while True:
        q = input("\nCustomer question (or 'quit'): ")
        if q.lower() == "quit":
            break
        print("\n", ask_agent(q))