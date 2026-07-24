import base64
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import errors, types

import printer

load_dotenv()

API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is not set. Add it to your .env file.")

client = genai.Client(api_key=API_KEY)
IMAGE_MODEL = "gemini-2.5-flash-image"
VOICE_MODEL = "gemini-flash-latest"

GENERATED_DIR = Path(__file__).parent / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

PROMPT_TEMPLATE = (
    "A simple black-and-white children's coloring book page of {subject}. "
    "Bold thick black outlines only, no shading, no gray, no color, pure "
    "white background, simple friendly cartoon style, easy for a young "
    "child to color inside the lines."
)

TRANSCRIBE_INSTRUCTION = (
    "A child or parent is speaking, describing what picture they want drawn "
    "on a printed coloring sticker. Reply with ONLY a short phrase (3-8 "
    "words) naming the subject they described. No other words, no quotes, "
    "no explanation."
)

app = Flask(__name__)

last_image_bytes = None


def generate_sticker_image(subject: str) -> bytes | None:
    prompt = PROMPT_TEMPLATE.format(subject=subject)
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            return part.inline_data.data
    return None


def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    response = client.models.generate_content(
        model=VOICE_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            TRANSCRIBE_INSTRUCTION,
        ],
    )
    return (response.text or "").strip()


def generate_and_store(subject: str):
    try:
        image_bytes = generate_sticker_image(subject)
    except errors.APIError as e:
        return jsonify({"error": f"Image generation failed: {e.message}"}), 502

    if image_bytes is None:
        return jsonify({"error": "The model did not return an image. Try a different idea."}), 502

    filename = f"{int(time.time())}.png"
    (GENERATED_DIR / filename).write_bytes(image_bytes)

    global last_image_bytes
    last_image_bytes = image_bytes

    encoded = base64.b64encode(image_bytes).decode("ascii")
    return jsonify({"subject": subject, "image": f"data:image/png;base64,{encoded}"})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)
    subject = (data.get("subject") or "").strip()
    if not subject:
        return jsonify({"error": "Please enter a sticker idea."}), 400
    return generate_and_store(subject)


@app.route("/voice", methods=["POST"])
def voice():
    audio_file = request.files.get("audio")
    if audio_file is None or audio_file.read(1) == b"":
        return jsonify({"error": "No audio received."}), 400
    audio_file.seek(0)
    audio_bytes = audio_file.read()
    mime_type = audio_file.mimetype or "audio/webm"

    try:
        subject = transcribe_audio(audio_bytes, mime_type)
    except errors.APIError as e:
        return jsonify({"error": f"Transcription failed: {e.message}"}), 502

    if not subject:
        return jsonify({"error": "Couldn't understand that, try again."}), 502

    return generate_and_store(subject)


@app.route("/print", methods=["POST"])
def print_sticker():
    if last_image_bytes is None:
        return jsonify({"error": "Generate an image first."}), 400

    try:
        printer.print_image(last_image_bytes)
    except RuntimeError as e:
        return jsonify({"error": f"Printing failed: {e}"}), 502

    return jsonify({"status": "printed"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001, ssl_context="adhoc")
