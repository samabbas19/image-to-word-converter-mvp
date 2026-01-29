from groq import Groq
import base64
import mimetypes

import os 
from dotenv import load_dotenv 

load_dotenv() 
groq_key = os.getenv("GROK_API_KEY")
client = Groq(api_key=groq_key)


PROMPT = """
You are an OCR, layout analysis, and diagram detection engine.

TASKS:
1. Detect ALL diagrams, figures, flowcharts, tables, graphs. 
2. DONOT extract the text with it 
3. EXTRACT the region containing the diagram only (5-10% text in the proximity is tolerable)

FOR EACH DIAGRAM:
- Assign an ID: Diagram_1, Diagram_2, ...
- Provide bounding box coordinates as percentages (0–100) relative to the image:
  x_min, y_min, x_max, y_max

STRICT RULES:
- NO explanations, NO reasoning, NO commentary.
- NO spelling or formatting correction.
- NO inference of missing text.
- If unclear text exists, write [illegible].

OUTPUT FORMAT (FOLLOW EXACTLY):

[RAW_TEXT]
<verbatim extracted text>

[DIAGRAMS]
Diagram_1:
Bounds: x_min=__, y_min=__, x_max=__, y_max=__


Diagram_2:
Bounds: ...
...

Output ONLY this format.
"""

def image_bytes_to_data_url(image_bytes, filename="image.png"):
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "image/png"

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"

def extract_diagrams(image_path):
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_url = image_bytes_to_data_url(image_bytes, image_path)

    response = client.chat.completions.create(
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
        max_completion_tokens=2048,
    )

    return response.choices[0].message.content

import re

def parse_diagram_bounds(llm_output):
    diagrams = []

    # More flexible pattern to handle variations in LLM output
    # Handles both "x_min=10" and "x_min = 10" formats
    pattern = (
        r"Diagram_\d+:\s*\n"
        r"Bounds:\s*x_min\s*=\s*(\d+)\s*,\s*y_min\s*=\s*(\d+)\s*,\s*x_max\s*=\s*(\d+)\s*,\s*y_max\s*=\s*(\d+)"
    )

    for match in re.finditer(pattern, llm_output):
        diagrams.append({
            "x_min": int(match.group(1)),
            "y_min": int(match.group(2)),
            "x_max": int(match.group(3)),
            "y_max": int(match.group(4)),
        })

    return diagrams

import cv2
import os

def crop_diagrams(image_path, diagram_bounds, output_dir="cropped_diagrams"):
    """
    image_path: path to original image
    diagram_bounds: list of dicts with x_min, y_min, x_max, y_max (percentages)
    output_dir: folder to save cropped diagrams
    """

    os.makedirs(output_dir, exist_ok=True)

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    h, w, _ = image.shape
    print(f"Image dimensions: {w}x{h}")

    cropped_paths = []

    for idx, bounds in enumerate(diagram_bounds, start=1):
        x_min = int(bounds["x_min"] / 100 * w)
        y_min = int(bounds["y_min"] / 100 * h)
        x_max = int(bounds["x_max"] / 100 * w)
        y_max = int(bounds["y_max"] / 100 * h)

        # Safety clamp
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(w, x_max)
        y_max = min(h, y_max)

        print(f"Diagram {idx}: Cropping region ({x_min},{y_min}) to ({x_max},{y_max})")

        # Validate bounds
        if x_max <= x_min or y_max <= y_min:
            print(f"  WARNING: Invalid bounds for diagram {idx}, skipping")
            continue

        cropped = image[y_min:y_max, x_min:x_max]

        # Check if cropped image is valid
        if cropped.size == 0:
            print(f"  WARNING: Empty cropped image for diagram {idx}, skipping")
            continue

        output_path = os.path.join(output_dir, f"diagram_{idx}.png")
        success = cv2.imwrite(output_path, cropped)
        
        if success:
            print(f"  Saved to: {output_path}")
            cropped_paths.append(output_path)
        else:
            print(f"  ERROR: Failed to save diagram {idx}")

    return cropped_paths


img_path = rf"1.jpeg"
result = extract_diagrams(img_path)
print(result)
bounds = parse_diagram_bounds(result)
cropped_images = crop_diagrams(img_path,bounds)