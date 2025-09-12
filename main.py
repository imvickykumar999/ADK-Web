'''bash
>>> tree -la
.
├── .env
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

3 directories, 10 files

>>> python main.py
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

# Arbitrary user and session IDs for the terminal chat
USER_ID = "terminal_user"
SESSION_ID = "terminal_session"

# Create the session asynchronously
async def create_session():
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

async def chat_terminal():
    # Create session first
    await create_session()
    
    print("Welcome to Bol7 Agent Terminal Chat!")
    print("Type your message and press Enter. Type 'exit' to quit.")
    
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        # Check for exit command
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        
        # Prepare the message
        message = Content(role="user", parts=[Part(text=user_input)])
        
        try:
            # Get response from the agent asynchronously
            response_text = ""
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=message
            ):
                if hasattr(event, "is_final_response") and event.is_final_response():
                    if hasattr(event, "content") and event.content.parts:
                        response_text = event.content.parts[0].text
                    break
            
            print(f"\nBol7 Agent: {response_text}")
        except Exception as e:
            print(f"\nError: {str(e)}")

if __name__ == "__main__":
    asyncio.run(chat_terminal())
