'''bash
>>> tree -la
.
├── .env
├── app.py
├── bol7_agent
│   ├── Bol7API.py
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── Bol7API.cpython-312.pyc
│   │   ├── __init__.cpython-312.pyc
│   │   └── agent.cpython-312.pyc
│   └── agent.py
├── bol7_agent.zip
├── main.py
└── session-26bd4c1f-860f-4ba3-9d65-23ddf71246a7.json

3 directories, 11 files
'''

import os
import asyncio
from dotenv import load_dotenv
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part
from bol7_agent.agent import root_agent

# Load environment variables from .env file
load_dotenv()

# Initialize in-memory session service
session_service = InMemorySessionService()

# Create the runner with the agent
APP_NAME = "bol7_agent"
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

async def get_agent_response(user_input: str, user_id: str = "terminal_user", session_id: str = "terminal_session") -> str:
    """
    Sends a single user input to the Bol7 agent and returns the response.
    
    Args:
        user_input (str): The user's text input.
        user_id (str): Identifier for the user (default: 'terminal_user').
        session_id (str): Identifier for the session (default: 'terminal_session').
    
    Returns:
        str: The agent's response or an error message.
    """
    # Always create session (idempotent; handles duplicates safely)
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id
    )
    
    # Prepare the message
    message = Content(role="user", parts=[Part(text=user_input)])
    
    try:
        response_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
            if hasattr(event, "is_final_response") and event.is_final_response():
                if hasattr(event, "content") and event.content.parts:
                    response_text = event.content.parts[0].text
                break
        return response_text or "No response generated."
    except Exception as e:
        return f"Error: {str(e)}"

# Example usage
if __name__ == "__main__":
    response = asyncio.run(get_agent_response("Hello, what can you do?"))
    print(f"Bol7 Agent: {response}")
