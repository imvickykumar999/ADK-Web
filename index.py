import os
import asyncio
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part

# NOTE: The 'instance.agent' module is assumed to be available in the execution environment.
# Ensure 'instance/agent.py' exists and exports a 'root_agent' instance for this to work.
try:
    from instance.agent import root_agent
except ImportError:
    # Placeholder for root_agent if not available, to allow the script to run/display
    print("WARNING: 'instance.agent' could not be imported. Agent functionality will be disabled.")
    root_agent = None

# Load environment variables from .env file
load_dotenv()

# --- ADK Initialization & Global State ---
APP_NAME = "agent_flask"
USER_ID = "web_user"
SESSION_ID = "web_session" # A simple fixed session for this single-user web demo

# Initialize Flask App
app = Flask(__name__)

# Initialize in-memory session service
session_service = InMemorySessionService()

# Create the runner with the agent only if root_agent was successfully imported
runner = None
session_created = False

if root_agent:
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    async def initialize_adk_session():
        """Creates the ADK session if it doesn't exist."""
        global session_created
        if not session_created:
            app.logger.info(f"Creating ADK session for {USER_ID}/{SESSION_ID}")
            await session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            session_created = True

    @app.before_request
    def run_adk_init():
        """Synchronously calls the async session creator before the first request if needed."""
        global session_created
        if runner and not session_created:
             try:
                # Use asyncio.run to block until the session is created
                asyncio.run(initialize_adk_session())
             except Exception as e:
                app.logger.error(f"ADK Session Initialization Error: {e}")

# --- Chat API Endpoint ---

@app.route('/chat', methods=['POST'])
def chat():
    """Handles incoming user messages, runs the ADK agent, and returns the response."""
    if not runner:
        return jsonify({"response": "Error: Agent runner is not initialized. Check server logs."}), 500

    data = request.get_json()
    user_input = data.get('message', '').strip()

    if not user_input:
        return jsonify({"response": "Please provide a message."}), 400

    # Prepare the message for the runner
    message = Content(role="user", parts=[Part(text=user_input)])

    response_text = "Sorry, I encountered an internal error."

    async def get_agent_response(msg):
        """Asynchronously runs the agent and extracts the final text response."""
        response = ""
        try:
            # Run the agent using the fixed session IDs
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=msg
            ):
                # The ADK runner streams events; we are only interested in the final response
                if hasattr(event, "is_final_response") and event.is_final_response():
                    if hasattr(event, "content") and event.content.parts:
                        # Extract the primary response text
                        response = event.content.parts[0].text
                        break
        except Exception as e:
            # Return error message to be handled outside the async context
            return f"An agent error occurred: {str(e)}"
        
        return response

    try:
        # NOTE: Using asyncio.run() blocks the current thread until the async call completes. 
        # For production applications, consider using an ASGI server (like Gunicorn with Uvicorn) 
        # and defining this route as 'async def chat()' for non-blocking I/O.
        final_response = asyncio.run(get_agent_response(message))
        
        if final_response.startswith("An agent error occurred"):
            response_text = final_response
            status_code = 500
        else:
            response_text = final_response
            status_code = 200

    except Exception as e:
        response_text = f"Flask runtime error: {str(e)}"
        status_code = 500
        
    return jsonify({"response": response_text}), status_code


# --- Frontend HTML/JS/CSS (Inlined for single-file deployment) ---

def get_html_content():
    """Generates the single HTML page with inline CSS and JavaScript for the chat UI."""
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ADK Agent Web Chat</title>
        <!-- Load Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            /* Custom Scrollbar for Chat Window */
            .chat-window::-webkit-scrollbar {{
                width: 8px;
            }}
            .chat-window::-webkit-scrollbar-thumb {{
                background-color: #a3a3a3; /* gray-400 */
                border-radius: 4px;
            }}
            .chat-window::-webkit-scrollbar-track {{
                background-color: #f3f4f6; /* gray-100 */
            }}
            /* Use Inter font */
            body {{
                font-family: 'Inter', sans-serif;
            }}
        </style>
        <script>
            // Set up Tailwind configuration for the Inter font
            tailwind.config = {{
                theme: {{
                    extend: {{
                        fontFamily: {{
                            sans: ['Inter', 'sans-serif'],
                        }}
                    }}
                }}
            }}
        </script>
    </head>
    <body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
        <div class="w-full max-w-lg bg-white shadow-2xl ring-1 ring-gray-200 rounded-xl overflow-hidden flex flex-col h-[90vh] md:h-[80vh]">
            <!-- Header -->
            <header class="p-4 bg-indigo-600 text-white shadow-lg rounded-t-xl">
                <h1 class="text-2xl font-extrabold tracking-tight">ADK Agent Chat</h1>
                <p class="text-xs opacity-80 mt-1">Chatting with ADK Agent (Session: {SESSION_ID})</p>
            </header>

            <!-- Chat Window -->
            <div id="chat-window" class="chat-window flex-grow overflow-y-auto p-4 space-y-4">
                <!-- Initial Welcome Message -->
                <div class="flex justify-start">
                    <div class="bg-indigo-100 text-indigo-800 p-4 rounded-xl rounded-tl-sm max-w-[80%] shadow-md border-b-2 border-indigo-200">
                        <p class="font-medium">Welcome!</p>
                        <p class="mt-1">I am your ADK Agent, ready to assist you. Ask me anything!</p>
                    </div>
                </div>
            </div>

            <!-- Input Form -->
            <div class="p-4 border-t border-gray-200 bg-white">
                <form id="chat-form" class="flex space-x-3">
                    <input 
                        type="text" 
                        id="user-input" 
                        placeholder="Type your message here..." 
                        required
                        autocomplete="off"
                        class="flex-grow p-3 border-2 border-gray-300 rounded-xl focus:ring-indigo-500 focus:border-indigo-500 transition duration-200"
                    />
                    <button 
                        type="submit" 
                        id="send-button"
                        class="bg-indigo-600 text-white p-3 rounded-xl font-bold shadow-lg hover:bg-indigo-700 transition duration-200 active:scale-[0.98] disabled:bg-gray-400"
                    >
                        Send
                    </button>
                </form>
            </div>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', () => {{
                const form = document.getElementById('chat-form');
                const userInput = document.getElementById('user-input');
                const chatWindow = document.getElementById('chat-window');
                const sendButton = document.getElementById('send-button');

                // Function to add a message to the chat window
                function addMessage(text, isUser = true) {{
                    const messageElement = document.createElement('div');
                    
                    if (isUser) {{
                        messageElement.className = 'flex justify-end';
                        messageElement.innerHTML = `
                            <div class="bg-indigo-600 text-white p-4 rounded-xl rounded-br-sm max-w-[80%] shadow-lg break-words">
                                ${'{text}'}
                            </div>
                        `;
                    }} else {{
                        messageElement.className = 'flex justify-start';
                        messageElement.innerHTML = `
                            <div class="bg-gray-200 text-gray-800 p-4 rounded-xl rounded-tl-sm max-w-[80%] shadow-lg break-words">
                                ${'{text}'}
                            </div>
                        `;
                    }}
                    
                    chatWindow.appendChild(messageElement);
                    // Scroll to the latest message
                    chatWindow.scrollTop = chatWindow.scrollHeight;
                }}

                // Function to show a loading state
                function showLoading() {{
                    let loadingDiv = document.getElementById('loading-message');
                    if (!loadingDiv) {{
                        loadingDiv = document.createElement('div');
                        loadingDiv.id = 'loading-message';
                        loadingDiv.className = 'flex justify-start';
                        loadingDiv.innerHTML = `
                            <div class="bg-gray-200 text-gray-600 p-4 rounded-xl rounded-tl-sm max-w-[80%] shadow-md">
                                <span class="animate-pulse">Agent is thinking...</span>
                            </div>
                        `;
                        chatWindow.appendChild(loadingDiv);
                        chatWindow.scrollTop = chatWindow.scrollHeight;
                    }}
                    return loadingDiv;
                }}

                // Function to hide the loading state
                function hideLoading() {{
                    const loadingDiv = document.getElementById('loading-message');
                    if (loadingDiv) {{
                        loadingDiv.remove();
                    }}
                }}

                // Handle form submission
                form.addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    
                    const message = userInput.value.trim();
                    if (!message) return;

                    // 1. Display user message
                    addMessage(message, true);
                    
                    // 2. Clear input and disable input/button
                    userInput.value = '';
                    sendButton.disabled = true;
                    userInput.disabled = true;

                    // 3. Show loading indicator
                    showLoading();

                    try {{
                        // 4. Send message to Flask backend
                        const response = await fetch('/chat', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{ message: message }})
                        }});

                        const data = await response.json();

                        // 5. Hide loading indicator
                        hideLoading();

                        // 6. Display agent response
                        if (response.ok) {{
                            addMessage(data.response, false);
                        }} else {{
                            addMessage(`Error: ${'{data.response}'}`, false);
                            console.error('Agent API Error:', data.response);
                        }}

                    }} catch (error) {{
                        // 5. Hide loading indicator on error
                        hideLoading();
                        // 6. Display network error
                        addMessage('Network Error: Could not reach the server.', false);
                        console.error('Fetch Error:', error);
                    }} finally {{
                        // 7. Re-enable input/button
                        sendButton.disabled = false;
                        userInput.disabled = false;
                        userInput.focus();
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """
    return html_template

@app.route('/')
def index():
    """Serves the main chat application page."""
    return get_html_content()

# --- Run the Flask App ---
if __name__ == "__main__":
    # To run this file, you'll need:
    # 1. 'instance/agent.py' file with 'root_agent' defined
    # 2. 'dotenv' installed and a '.env' file
    # 3. 'flask' installed
    # Run from the terminal: python app.py
    app.run(debug=True, host='0.0.0.0', port=5000)
