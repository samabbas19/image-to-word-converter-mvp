from groq import Groq
import base64
import mimetypes
import os 
from dotenv import load_dotenv 

load_dotenv() 
groq_key = os.getenv("GROK_API_KEY")
client = Groq(api_key=groq_key)

PROMPT = (
    "You are an OCR and transcription engine.\n\n"
    "Extract and reproduce ALL visible text and symbols from the provided image exactly as they appear.\n\n"
    "STRICT RULES:\n"
    "- Do NOT explain, summarize, reason, or interpret anything.\n"
    "- Do NOT add headings, comments, or descriptions.\n"
    "- Do NOT infer missing or unclear text.\n"
    "- Do NOT correct spelling, grammar, or formatting.\n"
    "- Do NOT reorganize or reformat content.\n"
    "- Do NOT describe diagrams — reproduce their text labels and structure using ASCII where needed.\n"
    "- Preserve original line breaks, spacing, indentation, arrows, boxes, bullet points, equations, and symbols.\n"
    "- If text is unclear or illegible, write: [illegible]\n"
    "- If a diagram contains text, include that text in its relative position.\n\n"
    "OUTPUT FORMAT:\n"
    "- Output ONLY the extracted content.\n"
    "- Plain text only.\n\n"
    "Any reasoning, explanation, or commentary is a violation of the task."
)

def image_bytes_to_data_url(image_bytes, filename="image.png"):
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "image/png"

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"

def extract_text_from_image(image_bytes, filename):
    image_url = image_bytes_to_data_url(image_bytes, filename)

    completion = client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        temperature=0,
        max_completion_tokens=1024,
    )

    return completion.choices[0].message.content