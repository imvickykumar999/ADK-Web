from google.adk.agents import Agent
from .WeatherAPI import get_weather

root_agent = Agent(
    name="weather_agent",
    model="gemini-2.0-flash",
    description="Weather agent",
    instruction="""
    You are a helpful assistant that can use the following tools:
    - get_weather
    """,
    tools=[get_weather],
)
