from google.adk.agents import Agent
from .Portfolio import (
    get_home,
    get_about,
    get_skilled,
    get_skills,
    get_work,
)

root_agent = Agent(
    name="portfolio_agent",
    model="gemini-2.0-flash",
    description="Portfolio agent",
    instruction="""
    You are a helpful assistant who fetch information about Vicky's Portfolio.
    """,
    tools=[
        get_home,
        get_about,
        get_skilled,
        get_skills,
        get_work,
    ],
)

# from google.adk.sessions import DatabaseSessionService 
# DB_URL = os.getenv("SESSION_DB_URL", "sqlite:///./sessions.db")
# session_service = DatabaseSessionService(db_url=DB_URL)
