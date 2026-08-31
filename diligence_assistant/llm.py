"""LangChain ChatGroq LLM wrapper (Step 2: swaps raw groq client)."""
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm():
    return ChatGroq(model="openai/gpt-oss-120b", temperature=0)
