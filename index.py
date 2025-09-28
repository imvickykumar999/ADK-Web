import os
import asyncio
import json
import sqlite3
from dotenv import load_dotenv
from flask import Flask, request, jsonify, g
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

# --- Database Configuration ---
DATABASE = 'history.db'

# Initialize Flask App EARLY to ensure it's available for decorators
app = Flask(__name__)

def get_db():
    """Returns a database connection, creating one if not present in flask.g."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # Allows accessing columns by name
    return g.db

@app.teardown_appcontext # FIXED: Changed from @Flask.teardown_appcontext to @app.teardown_appcontext
def close_db(e=None):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database and creates the messages table."""
    with app.app_context():
        db = get_db()
        # Create a table to store chat messages
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL, -- 'user' or 'agent'
                text TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

def save_message(session_id: str, role: str, text: str):
    """Saves a single message to the database."""
    try:
        db = get_db()
        db.execute(
            "INSERT INTO messages (session_id, role, text) VALUES (?, ?, ?)",
            (session_id, role, text)
        )
        db.commit()
    except Exception as e:
        app.logger.error(f"Database Save Error: {e}")

def load_history(session_id: str) -> list[dict]:
    """Loads all messages for a given session ID."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT role, text FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        ).fetchall()
        # Convert sqlite3.Row objects to standard Python dictionaries
        return [{"role": row['role'], "text": row['text']} for row in rows]
    except Exception as e:
        app.logger.error(f"Database Load Error: {e}")
        return []


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
                # Note: This runs within Flask's single-threaded context for simplicity.
                asyncio.run(initialize_adk_session())
             except Exception as e:
                app.logger.error(f"ADK Session Initialization Error: {e}")

# --- API Endpoints ---

@app.route('/history', methods=['GET'])
def get_history():
    """Returns the chat history for the current session ID."""
    history = load_history(SESSION_ID)
    return jsonify(history)

@app.route('/chat', methods=['POST'])
def chat():
    """Handles incoming user messages, runs the ADK agent, and returns the response."""
    if not runner:
        return jsonify({"response": "Error: Agent runner is not initialized. Check server logs."}), 500

    data = request.get_json()
    user_input = data.get('message', '').strip()

    if not user_input:
        return jsonify({"response": "Please provide a message."}), 400

    # 1. Save user message to history
    save_message(SESSION_ID, "user", user_input)

    # Prepare the message for the runner
    message = Content(role="user", parts=[Part(text=user_input)])

    response_text = "Sorry, I encountered an internal error."

    async def get_agent_response(msg):
        """Asynchronously runs the agent and extracts the final text response."""
        response = ""
        try:
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=msg
            ):
                if hasattr(event, "is_final_response") and event.is_final_response():
                    if hasattr(event, "content") and event.content.parts:
                        response = event.content.parts[0].text
                        break
        except Exception as e:
            return f"An agent error occurred: {str(e)}"
        
        return response

    try:
        final_response = asyncio.run(get_agent_response(message))
        
        if final_response.startswith("An agent error occurred"):
            response_text = final_response
            status_code = 500
        else:
            response_text = final_response
            status_code = 200
            
            # 2. Save agent message to history on success
            save_message(SESSION_ID, "agent", response_text)

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

            <!-- Chat Window (Content will be filled by JavaScript on load) -->
            <div id="chat-window" class="chat-window flex-grow overflow-y-auto p-4 space-y-4">
                <!-- Chat messages go here -->
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
                // Takes text and role ('user' or 'agent')
                function addMessage(text, role) {{
                    const isUser = role === 'user';
                    const messageElement = document.createElement('div');
                    
                    if (isUser) {{
                        messageElement.className = 'flex justify-end';
                        messageElement.innerHTML = `
                            <div class="bg-indigo-600 text-white p-4 rounded-xl rounded-br-sm max-w-[80%] shadow-lg break-words">
                                ${'{text}'}
                            </div>
                        `;
                    }} else {{ // agent
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
                
                // Function to load and display chat history
                async function loadChatHistory() {{
                    try {{
                        const response = await fetch('/history');
                        const history = await response.json();

                        if (history.length === 0) {{
                            // Display initial welcome message if history is empty
                            addMessage("Welcome! I am your ADK Agent, ready to assist you. Ask me anything!", 'agent');
                            return;
                        }}
                        
                        history.forEach(msg => {{
                            if (msg.role && msg.text) {{
                                addMessage(msg.text, msg.role);
                            }}
                        }});

                    }} catch (error) {{
                        console.error('Failed to load chat history:', error);
                        // Fallback welcome message
                        addMessage("Welcome! I am your ADK Agent, ready to assist you. Ask me anything!", 'agent');
                    }}
                }}

                // Load chat history when the page loads
                loadChatHistory();

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
                    addMessage(message, 'user');
                    
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
                            addMessage(data.response, 'agent');
                        }} else {{
                            addMessage(`Error: ${'{data.response}'}`, 'agent');
                            console.error('Agent API Error:', data.response);
                        }}

                    }} catch (error) {{
                        // 5. Hide loading indicator on error
                        hideLoading();
                        // 6. Display network error
                        addMessage('Network Error: Could not reach the server.', 'agent');
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
    # Initialize database when the application starts
    init_db()
    # To run this file, you'll need:
    # 1. 'instance/agent.py' file with 'root_agent' defined
    # 2. 'dotenv' installed and a '.env' file
    # 3. 'flask' installed
    # Run from the terminal: python app.py
    app.run(debug=True, host='0.0.0.0', port=5000)
