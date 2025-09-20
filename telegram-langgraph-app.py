import os
import re
import json
import requests
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
#from dotenv import load_dotenv
from pprint import pprint
from gtts import gTTS
from pydub import AudioSegment
from langdetect import detect
import io
from openai import OpenAI
from typing import Annotated
from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
import sqlite3

# Load environment variables from .env file
#load_dotenv()

# Configuration
BOT_TOKEN = '7715266681:AAGAOSdAR6zeQKQrCoby0FCIP6Uqy7Hs3YE'
OPENAI_API_KEY = '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'
X_RAPID_API = '1dc9e6236dmshdfe058f825b062cp17212ejsnc424e02746a5'
WEBHOOK_URL = 'https://internal-adjusted-possum.ngrok-free.app/webhook/'
DB_URL = 'sqlite:///./my_agent_data.db'
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
APP_NAME = "bol7_agent"

# Flask app setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_data.db'  # Database for Chat model
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define Chat model
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(255))
    username = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    message_type = db.Column(db.String(255))
    reply_message = db.Column(db.Text)
    message_content = db.Column(db.Text)
    download_file = db.Column(db.Text)

# Create database tables
with app.app_context():
    db.create_all()

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# LangGraph Setup
class State(TypedDict):
    messages: Annotated[list, add_messages]

@tool
def custom_chat_api(query: str) -> str:
    """Use this tool to handle all user queries related to business, sales, products, services, databases, or any information requests. Call this tool with the user's query to get an appropriate response from the Bol7 API."""
    url = "https://americangemexpo.com/api/chat/"
    payload = json.dumps({
      "response": query,
      "type": "text",
      "number": "918239957923",
      "sender": "15557038289",
      "platform": "WhatsApp",
      "agent_name": "Bol7"
    })
    headers = {
      'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, data=payload)
    return response.text

tools = [custom_chat_api]
graph_builder = StateGraph(State)
os.environ["GOOGLE_API_KEY"] = "AIzaSyB0389kCZAwr774D6fNZFVYzo2eRfTnnKk"
os.environ["GRPC_VERBOSITY"] = "ERROR"
llm = init_chat_model("google_genai:gemini-2.0-flash")
llm_with_tools = llm.bind_tools(tools)
def agent(state: State):
    messages = [SystemMessage(content="You are a helpful assistant for Bol7. For any user query about business, sales, products, services, databases, or information requests, always use the custom_chat_api tool to generate the response. Do not answer directly unless it's a simple greeting or unrelated to business.")] + state["messages"]
    return {"messages": [llm_with_tools.invoke(messages)]}
graph_builder.add_node("agent", agent)
graph_builder.add_node("tools", ToolNode(tools))
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", tools_condition)
graph_builder.add_edge("tools", "agent")
conn = sqlite3.connect("chat_history.db", check_same_thread=False)
memory = SqliteSaver(conn)
graph = graph_builder.compile(checkpointer=memory)

def clean_filename(file_name):
    """Clean file name for processing."""
    file_name = re.sub(r'\d+', '', file_name)
    file_name = re.sub(r'[^\w\s]', '', file_name)
    file_name = file_name.replace("_", " ").strip()
    return "I am feeling " + file_name

def set_webhook():
    """Set Telegram webhook."""
    url = f"{BASE_URL}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    return response.json()

def send_message(chat_id, text):
    """Send a text message to Telegram."""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_voice(chat_id, audio_file):
    """Send a voice message to Telegram."""
    url = f"{BASE_URL}/sendVoice"
    files = {"voice": ("reply.ogg", audio_file, "audio/ogg")}
    data = {"chat_id": chat_id}
    response = requests.post(url, data=data, files=files)
    return response.json()

def text_to_speech(text):
    """Convert text to OGG audio file."""
    try:
        detected_lang = detect(text)
        print(f"Detected Language: {detected_lang}")
        tts = gTTS(text=text, lang=detected_lang)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        audio = AudioSegment.from_file(mp3_fp, format="mp3")
        ogg_fp = io.BytesIO()
        audio.export(ogg_fp, format="ogg", codec="libopus")
        ogg_fp.seek(0)
        return ogg_fp
    except Exception as e:
        print(f"Error in text-to-speech conversion: {e}")
        return None

def transcribe_voice(file_name, file_content):
    """Transcribe audio using OpenAI."""
    try:
        transcription = client.audio.transcriptions.create(
            file=(file_name, file_content),
            model="whisper-1",
            response_format="verbose_json",
        )
        return transcription.text
    except Exception as e:
        return f"Sorry, I'm having trouble transcribing your audio: {str(e)}"

def fetch_twitter_video_url(twitter_url):
    """Fetch video URL from Twitter/X post."""
    api_url = f"https://twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com/status?url={twitter_url}"
    headers = {
        'x-rapidapi-key': X_RAPID_API,
        'x-rapidapi-host': 'twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        video_data = data.get("media", {}).get("video", {}).get("videoVariants", [])
        if video_data:
            video_url = max(video_data, key=lambda x: x.get("bitrate", 0)).get("url")
            return video_url
    return "API limit exceeded."

def ocr_image_with_groq(image_url: str, prompt: str = "Extract all visible text. Return plain text."):
    """Perform OCR on an image using OpenAI (replacing Groq)."""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }],
            temperature=0.2,
            top_p=1,
            max_tokens=1024,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Sorry, I couldn't read the image: {str(e)}"

def generate_agent_response(user_id, session_id, message_text):
    """Generate a response using LangGraph."""
    try:
        config = {"configurable": {"thread_id": session_id}}
        events = graph.stream(
            {"messages": [HumanMessage(content=message_text)]},
            config,
            stream_mode="values",
        )
        response_text = ""
        for event in events:
            last_message = event["messages"][-1]
            if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                response_text = last_message.content
        return response_text
    except Exception as e:
        return f"Sorry, I'm having trouble processing your request: {str(e)}"

@app.route('/webhook/', methods=['POST'])
def webhook():
    """Handle Telegram webhook requests."""
    update = request.json
    pprint(update)
    if "message" in update:
        message = update["message"]
        chat_id = str(message["chat"]["id"]) # Use chat_id as user_id
        session_id = f"session_{chat_id}" # Unique session per chat
        username = message["chat"].get("username", "")
        first_name = message["chat"].get("first_name", "")
        last_name = message["chat"].get("last_name", "")
        message_type = "unknown"
        message_content = ""
        reply_message = "No reply generated."
        download_file = ""
        if "text" in message:
            message_text = message.get("text", "")
            twitter_url_pattern = r'(https?://(?:www\.)?(?:twitter|x)\.com/[A-Za-z0-9_]+/status/\d+)'
            match = re.search(twitter_url_pattern, message_text)
            if match:
                twitter_url = match.group(0)
                video_url = fetch_twitter_video_url(twitter_url)
                reply_text = f"Download video here:\n{video_url}"
                download_file = video_url
            else:
                if message_text.startswith("/start"):
                    first_name = message["chat"].get("first_name", "User")
                    last_name = message["chat"].get("last_name", "")
                    message_text = f"Hello {first_name} {last_name}\n\nHi"
                reply_text = generate_agent_response(chat_id, session_id, message_text)
            send_message(chat_id, reply_text)
            message_type = "text"
            message_content = message_text
            reply_message = reply_text
        # # Handle different message types
        # elif "voice" in message:
        # voice = message["voice"]
        # file_id = voice["file_id"]
        # file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        # if file_info.get("ok"):
        # file_path = file_info["result"]["file_path"]
        # download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        # file_content = requests.get(download_url).content
        # transcription_text = transcribe_voice("voice.ogg", file_content)
        # reply_text = generate_agent_response(chat_id, session_id, transcription_text)
        # send_message(chat_id, reply_text)
        # audio_response = text_to_speech(reply_text)
        # if audio_response:
        # send_voice(chat_id, audio_response)
        # message_type = "voice"
        # message_content = transcription_text
        # reply_message = reply_text
        # download_file = download_url
        # else:
        # send_message(chat_id, "Sorry, could not retrieve the audio file.")
        # elif "sticker" in message:
        # sticker_info = message["sticker"]
        # emoji = sticker_info.get("emoji", "")
        # reply_text = generate_agent_response(chat_id, session_id, emoji)
        # send_message(chat_id, reply_text)
        # message_type = "sticker"
        # message_content = emoji
        # reply_message = reply_text
        # download_file = ""
        # elif "video_note" in message:
        # file_id = message["video_note"]["file_id"]
        # file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        # if file_info.get("ok"):
        # file_path = file_info["result"]["file_path"]
        # download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        # reply_text = f"Received video note.\nVideo Note: {file_path}"
        # send_message(chat_id, reply_text)
        # message_type = "video_note"
        # message_content = file_path
        # reply_message = reply_text
        # download_file = download_url
        # elif "animation" in message:
        # animation_info = message["animation"]
        # file_name = animation_info.get("file_name", "animation.gif")
        # file_name = file_name.split(".")[0]
        # cleaned_name = clean_filename(file_name)
        # reply_text = generate_agent_response(chat_id, session_id, cleaned_name)
        # send_message(chat_id, reply_text)
        # message_type = "animation"
        # message_content = cleaned_name
        # reply_message = reply_text
        # download_file = ""
        # elif "photo" in message:
        # file_id = message["photo"][-1]["file_id"]
        # file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        # if file_info.get("ok"):
        # file_path = file_info["result"]["file_path"]
        # download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        # extracted = ocr_image_with_groq(
        # download_url,
        # prompt="Extract all text in reading order. If none, say 'No text found.'"
        # )
        # send_message(chat_id, f"🖼️ I read this from your image:\n\n{extracted}")
        # reply_text = generate_agent_response(chat_id, session_id, extracted)
        # send_message(chat_id, reply_text)
        # audio_response = text_to_speech(reply_text)
        # if audio_response:
        # send_voice(chat_id, audio_response)
        # message_type = "photo"
        # message_content = file_path
        # reply_message = reply_text
        # download_file = download_url
        # else:
        # send_message(chat_id, "Sorry, could not retrieve the photo.")
        # elif "video" in message:
        # file_id = message["video"]["file_id"]
        # file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        # if file_info.get("ok"):
        # file_path = file_info["result"]["file_path"]
        # download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        # reply_text = f"Received video.\nVideo Name: {file_path}"
        # send_message(chat_id, reply_text)
        # message_type = "video"
        # message_content = file_path
        # reply_message = reply_text
        # download_file = download_url
        # elif "audio" in message:
        # file_id = message["audio"]["file_id"]
        # file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        # if file_info.get("ok"):
        # file_path = file_info["result"]["file_path"]
        # download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        # reply_text = f"Received Audio: {file_path}"
        # send_message(chat_id, reply_text)
        # message_type = "audio"
        # message_content = file_path
        # reply_message = reply_text
        # download_file = download_url
        # else:
        # send_message(chat_id, "Sorry, could not retrieve the audio file.")
        # elif "document" in message:
        # file_mime_type = message["document"].get("mime_type", "")
        # if "image" in file_mime_type:
        # file_id = message["document"]["file_id"]
        # file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        # if file_info.get("ok"):
        # file_path = file_info["result"]["file_path"]
        # download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        # extracted = ocr_image_with_groq(
        # download_url,
        # prompt="Extract all text in reading order. If none, say 'No text found.'"
        # )
        # send_message(chat_id, f"🖼️ I read this from your image:\n\n{extracted}")
        # reply_text = generate_agent_response(chat_id, session_id, extracted)
        # send_message(chat_id, reply_text)
        # audio_response = text_to_speech(reply_text)
        # if audio_response:
        # send_voice(chat_id, audio_response)
        # message_type = "document (image)"
        # message_content = file_path
        # reply_message = reply_text
        # download_file = download_url
        # else:
        # send_message(chat_id, "Sorry, could not retrieve the document.")
        # else:
        # file_id = message["document"]["file_id"]
        # file_name = message["document"].get("file_name", "Unknown Document")
        # file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        # if file_info.get("ok"):
        # file_path = file_info["result"]["file_path"]
        # download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        # reply_text = f"Received document: {file_name}"
        # send_message(chat_id, reply_text)
        # message_type = "document"
        # message_content = file_name
        # reply_message = reply_text
        # download_file = download_url
        # else:
        # send_message(chat_id, "Sorry, could not retrieve the document.")
        # elif "poll" in message:
        # poll = message["poll"]
        # question = poll.get("question", "")
        # if question:
        # reply_text = generate_agent_response(chat_id, session_id, question)
        # send_message(chat_id, reply_text)
        # message_type = "poll"
        # message_content = question
        # reply_message = reply_text
        # download_file = ""
        # elif "venue" in message:
        # venue = message["venue"]
        # venue_title = venue.get("title", "")
        # venue_address = venue.get("address", "")
        # if venue_title or venue_address:
        # venue_info = f"Venue: {venue_title}\nAddress: {venue_address}"
        # reply_text = generate_agent_response(chat_id, session_id, venue_info)
        # send_message(chat_id, reply_text)
        # message_type = "venue"
        # message_content = venue_info
        # reply_message = reply_text
        # download_file = ""
        # else:
        # send_message(chat_id, 'https://blogforge.pythonanywhere.com/blogs/')
        # reply_message = "Redirected to blog"
        # message_type = "unknown"
        # message_content = "Unknown message type"
        # Save chat interaction to database
        try:
            chat_entry = Chat(
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                message_type=message_type,
                reply_message=reply_message,
                message_content=message_content,
                download_file=download_file,
            )
            db.session.add(chat_entry)
            db.session.commit()
        except Exception as e:
            print(f"Error saving to Chat model: {e}")
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/')
def set_webhook_route():
    """Route to set Telegram webhook."""
    return jsonify(set_webhook())

if __name__ == '__main__':
    app.run(debug=True, port='5555')
