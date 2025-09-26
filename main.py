# main.py (with photo OCR support)
import os, io, asyncio, atexit, requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
from pydub import AudioSegment
from langdetect import detect
from google.adk.runners import Runner
from google.genai.types import Content, Part
from google.adk.sessions import DatabaseSessionService
from instance.agent import root_agent

# -------- ENV & CONFIG --------
load_dotenv()
BOT_TOKEN   = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
GROQ_API_KEY= os.getenv('GROQ_API_KEY')
DB_URL      = os.getenv('DB_URL')

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
APP_NAME = "instance"

# -------- FLASK --------
app = Flask(__name__)

# -------- GLOBAL ASYNC LOOP --------
LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)
def arun(coro): return LOOP.run_until_complete(coro)
@atexit.register
def _shutdown_loop():
    try:
        pending = asyncio.all_tasks(loop=LOOP)
        for t in pending: t.cancel()
        LOOP.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    finally:
        try: LOOP.stop()
        except Exception: pass
        try: LOOP.close()
        except Exception: pass

# -------- CLIENTS & RUNNER --------
client = Groq(api_key=GROQ_API_KEY)
session_service = DatabaseSessionService(db_url=DB_URL)
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

# -------- HELPERS --------
async def ensure_session(user_id, session_id):
    if not await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id):
        await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)

async def agent_reply(user_id, session_id, text):
    await ensure_session(user_id, session_id)
    msg = Content(role="user", parts=[Part(text=text)])
    async for ev in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        if hasattr(ev, "is_final_response") and ev.is_final_response():
            return ev.content.parts[0].text if getattr(ev, "content", None) and ev.content.parts else ""
    return ""

def telegram_send(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def telegram_send_voice(chat_id, audio_fp):
    requests.post(
        f"{BASE_URL}/sendVoice",
        data={"chat_id": chat_id},
        files={"voice": ("reply.ogg", audio_fp, "audio/ogg")}
    )

def tts_ogg(text):
    try:
        lang = detect(text or "")
        buf = io.BytesIO()
        gTTS(text=text, lang=lang).write_to_fp(buf)
        buf.seek(0)
        ogg = io.BytesIO()
        AudioSegment.from_file(buf, format="mp3").export(ogg, format="ogg", codec="libopus")
        ogg.seek(0)
        return ogg
    except Exception:
        return None

def transcribe_ogg(name, content):
    try:
        r = client.audio.transcriptions.create(
            file=(name, content),
            model="whisper-large-v3",
            response_format="verbose_json",
        )
        return r.text
    except Exception as e:
        return f"Transcription error: {e}"

def ocr_image_with_groq(image_url: str, prompt: str = "Extract all visible text. Return plain text."):
    """Use Groq multimodal chat completion to OCR a Telegram file URL."""
    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }],
            temperature=0.2,
            top_p=1,
            max_completion_tokens=1024,
            stream=False,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as e:
        return f"Sorry, I couldn't read the image. ({e})"

def set_webhook():
    return requests.post(f"{BASE_URL}/setWebhook", json={"url": WEBHOOK_URL}).json()

# -------- ROUTES --------
@app.route('/webhook/', methods=['POST'])
def webhook():
    u = request.json or {}
    if "message" not in u:
        return jsonify({"status": "ignored"})
    m = u["message"]
    # print(m)

    chat = m.get("chat", {})
    chat_id = str(chat.get("id"))
    session_id = f"s_{chat_id}"

    # TEXT
    if "text" in m:
        text = m["text"]
        if text.startswith("/start"):
            text = f"Hello {chat.get('first_name','')} {chat.get('last_name','')}".strip()
        reply = arun(agent_reply(chat_id, session_id, text))
        telegram_send(chat_id, reply or "…")
        if reply:
            ogg = tts_ogg(reply)
            if ogg: telegram_send_voice(chat_id, ogg)
        return jsonify({"status": "ok"})

    # VOICE
    if "voice" in m:
        file_id = m["voice"]["file_id"]
        f = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        if not f.get("ok"):
            telegram_send(chat_id, "Couldn't fetch voice note.")
            return jsonify({"status": "ok"})
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f['result']['file_path']}"
        audio_bytes = requests.get(url).content
        text = transcribe_ogg("voice.ogg", audio_bytes)
        reply = arun(agent_reply(chat_id, session_id, text))
        telegram_send(chat_id, reply or "…")
        if reply:
            ogg = tts_ogg(reply)
            if ogg: telegram_send_voice(chat_id, ogg)
        return jsonify({"status": "ok"})

    # PHOTO (images sent as photos)
    if "photo" in m:
        file_id = m["photo"][-1]["file_id"]  # highest-res
        f = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        if not f.get("ok"):
            telegram_send(chat_id, "Sorry, could not retrieve the photo.")
            return jsonify({"status": "ok"})
        file_path = f["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        # read optional user caption
        caption = (m.get("caption") or "").strip()

        extracted = ocr_image_with_groq(
            download_url,
            prompt="Extract all text in reading order. If none, say 'No text found.'"
        )

        # show both to the user
        preview = "🖼️ I read this from your image:\n\n"
        if caption:
            preview += f"📎 Caption: {caption}\n\n"
        preview += f"🔎 OCR:\n{extracted}"
        telegram_send(chat_id, preview)

        # combine caption + OCR for the agent
        combined = (caption + "\n\n[OCR]\n" + extracted).strip() if caption else extracted
        print(combined)

        reply = arun(agent_reply(chat_id, session_id, combined))
        telegram_send(chat_id, reply or "…")
        if reply:
            ogg = tts_ogg(reply)
            if ogg: telegram_send_voice(chat_id, ogg)
        return jsonify({"status": "ok"})

    # STICKER
    if "sticker" in m:
        sticker_info = m["sticker"]
        emoji = sticker_info.get("emoji", "")

        # Send sticker emoji or just acknowledge the sticker
        sticker_message = f"📌 Sticker received"

        # If emoji is available in the sticker
        if emoji:
            sticker_message = f"{emoji}"

        # Get reply from the agent based on the sticker emoji
        reply = arun(agent_reply(chat_id, session_id, sticker_message))

        telegram_send(chat_id, reply or "…")
        return jsonify({"status": "ok"})

    # FALLBACK
    telegram_send(chat_id, "Unsupported message type.")
    return jsonify({"status": "ok"})

    # DOCUMENT image (treat image documents like photos)
    if "document" in m and "image" in (m["document"].get("mime_type") or ""):
        file_id = m["document"]["file_id"]
        f = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        if not f.get("ok"):
            telegram_send(chat_id, "Sorry, could not retrieve the image document.")
            return jsonify({"status": "ok"})
        file_path = f["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        caption = (m.get("caption") or "").strip()

        extracted = ocr_image_with_groq(
            download_url,
            prompt="Extract all text in reading order. If none, say 'No text found.'"
        )

        preview = "🖼️ I read this from your image document:\n\n"
        if caption:
            preview += f"📎 Caption: {caption}\n\n"
        preview += f"🔎 OCR:\n{extracted}"
        telegram_send(chat_id, preview)

        combined = (extracted + "\n\n" + caption).strip() if caption else extracted
        reply = arun(agent_reply(chat_id, session_id, combined))
        telegram_send(chat_id, reply or "…")
        if reply:
            ogg = tts_ogg(reply)
            if ogg: telegram_send_voice(chat_id, ogg)
        return jsonify({"status": "ok"})

    # FALLBACK
    telegram_send(chat_id, "Unsupported message type.")
    return jsonify({"status": "ok"})

@app.route('/')
def webhook_route():
    return jsonify(set_webhook())

# -------- MAIN --------
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
