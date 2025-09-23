## Configuring Persistent Sessions for `adk web`

Run the command with the flag to use SQLite for storage:
```
adk web --agent <your_agent_name> --session_service_uri sqlite://sessions.db
```
- This creates (or uses) a local SQLite file named `sessions.db` in the current directory.
- All new chats/sessions will now be persisted to this DB automatically.
- The web UI (at http://localhost:8000 by default) will load existing sessions from the DB on startup, allowing you to resume them seamlessly after a restart.
- For other persistence options:
  - **Vertex AI (cloud-based)**: Use `--session_service_uri agentengine://<your-agent-engine-id>` (requires a deployed Agent Engine in Google Cloud; see [docs](https://google.github.io/adk-docs/deploy/agent-engine/)).
  - Sessions are tied to the `appName` and `userId` from your JSON (e.g., "instance" and "user"), so they'll appear under the appropriate chat list in the UI.

If you want to customize further (e.g., a different DB path), the URI format is standard SQLAlchemy-style: `sqlite:///./path/to/your/sessions.db`.

### Importing Your Existing JSON Session into the Persistent DB
Since the JSON file is a serialized `Session` object (exported via CLI's `--save_session` or similar), `adk web` doesn't have a built-in CLI flag to directly import it. However, you can load and save it programmatically using the ADK Python SDK. This inserts it into your SQLite DB, making it available in the web UI after restart.

Here's a self-contained Python script to do this (run it once before starting `adk web`):

```python
import json
import asyncio
from google.adk.sessions import DatabaseSessionService, Session

# Load your JSON file
json_file_path = 'session-e0fa57a1-8de1-4886-a4ac-729fb8887a64.json'
with open(json_file_path, 'r') as f:
    session_data = json.load(f)

# Create the persistent session service (matches your adk web config)
db_uri = "sqlite://sessions.db"  # Same as --session_service_uri
session_service = DatabaseSessionService(db_url=db_uri)

# Reconstruct the Session object from JSON
resumed_session = Session(
    id=session_data['id'],
    app_name=session_data['appName'],
    user_id=session_data['userId'],
    state=session_data['state'],
    events=session_data['events'],
    last_update_time=session_data['lastUpdateTime']
)

# Save it to the DB (async, so use asyncio)
async def import_session():
    await session_service.save_session(resumed_session)
    print(f"Session '{session_data['id']}' imported to DB successfully!")

# Run the import
asyncio.run(import_session())
```

- **Steps to use**:
  1. Ensure ADK is installed (`pip install google-adk`).
  2. Run the script: `python import_session.py` (save the code to a file).
  3. Start `adk web` with the persistence flag as above.
  4. In the web UI, your imported session should now appear in the chat list (filter by user ID or app name if needed). You can continue chatting from where it left off.

This approach works because `DatabaseSessionService` handles serialization/deserialization under the hood. If you're using Vertex AI instead, swap to `VertexAiSessionService` in the code (requires GCP auth and project setup).

If you encounter errors (e.g., DB schema issues), drop the DB file and re-run the import—it'll recreate the tables. For more advanced setups, check the [SessionService docs](https://google.github.io/adk-docs/sessions/session/) or share error logs for troubleshooting!
