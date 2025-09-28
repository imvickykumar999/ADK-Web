from google.adk.agents import Agent
from google.adk.tools import google_search
# from .Bol7API import get_info

root_agent = Agent(
    name="tool_agent",
    model="gemini-2.0-flash",
    description="Tool agent",
    instruction="""
    You are a helpful assistant that can use the following tools:
    - google_search
    """,
    tools=[google_search],
)
