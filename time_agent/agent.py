from google.adk.agents import Agent
from datetime import datetime

def get_current_time() -> dict:
    """
    Get the current time in the format YYYY-MM-DD HH:MM:SS
    """
    return {
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

root_agent = Agent(
    name="time_agent",
    model="gemini-2.0-flash",
    description="Time agent",
    instruction="""
    You are a helpful assistant that can use the following tools:
    - get_current_time
    """,
    tools=[get_current_time],
)

