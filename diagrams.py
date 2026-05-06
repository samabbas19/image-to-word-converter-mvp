import base64
import mimetypes
import os
import re
from typing import Dict, List

import cv2
from dotenv import load_dotenv
from groq import Groq


load_dotenv()

DEFAULT_GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

DIAGRAM_PROMPT = """
You are a document-layout analysis engine.

TASK:
Detect every diagram, figure, flowchart, table, graph, plot, equation box, or visual block in the image.
Return only bounding boxes for those regions. Do not transcribe the whole page.

BOUNDING BOX RULES:
- Coordinates are percentages from 0 to 100 relative to the full image.
- Use tight boxes around the visual block.
- Include nearby labels only when they are part of the diagram.
- If no diagram exists, return [DIAGRAMS] and then NONE.

OUTPUT FORMAT:
[DIAGRAMS]
Diagram_1:
Bounds: x_min=__, y_min=__, x_max=__, y_max=__

Diagram_2:
Bounds: x_min=__, y_min=__, x_max=__, y_max=__

Output only this format.
"""


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing Groq API key. Set GROQ_API_KEY in .env "
            "(GROK_API_KEY is also supported for backward compatibility)."
        )
    return Groq(api_key=api_key)


def get_groq_vision_model() -> str:
    return os.getenv("GROQ_VISION_MODEL", DEFAULT_GROQ_VISION_MODEL)


def image_bytes_to_data_url(image_bytes: bytes, filename: str = "image.png") -> str:
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "image/png"

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return "data:{0};base64,{1}".format(mime_type, encoded)


def extract_diagrams(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    image_url = image_bytes_to_data_url(image_bytes, os.path.basename(image_path))
    response = get_groq_client().chat.completions.create(
        model=get_groq_vision_model(),
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": DIAGRAM_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        temperature=0,
        max_completion_tokens=1024,
    )
    return response.choices[0].message.content or ""


def _clamp_percent(value: float) -> int:
    return int(max(0, min(100, round(value))))


def parse_diagram_bounds(llm_output: str) -> List[Dict[str, int]]:
    diagrams = []
    pattern = re.compile(
        r"Diagram_\d+\s*:\s*"
        r"(?:\r?\n|\s)*Bounds\s*:\s*"
        r"x_min\s*=\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"y_min\s*=\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"x_max\s*=\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"y_max\s*=\s*(-?\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )

    for match in pattern.finditer(llm_output or ""):
        x_min = _clamp_percent(float(match.group(1)))
        y_min = _clamp_percent(float(match.group(2)))
        x_max = _clamp_percent(float(match.group(3)))
        y_max = _clamp_percent(float(match.group(4)))

        if x_max > x_min and y_max > y_min:
            diagrams.append(
                {
                    "x_min": x_min,
                    "y_min": y_min,
                    "x_max": x_max,
                    "y_max": y_max,
                }
            )

    return diagrams


def crop_diagrams(
    image_path: str,
    diagram_bounds: List[Dict[str, int]],
    output_dir: str = "cropped_diagrams",
    filename_prefix: str = "diagram",
) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Could not read image: {0}".format(image_path))

    height, width = image.shape[:2]
    cropped_paths = []

    for index, bounds in enumerate(diagram_bounds, start=1):
        x_min = int(bounds["x_min"] / 100 * width)
        y_min = int(bounds["y_min"] / 100 * height)
        x_max = int(bounds["x_max"] / 100 * width)
        y_max = int(bounds["y_max"] / 100 * height)

        x_min = max(0, min(width - 1, x_min))
        y_min = max(0, min(height - 1, y_min))
        x_max = max(1, min(width, x_max))
        y_max = max(1, min(height, y_max))

        if x_max <= x_min or y_max <= y_min:
            continue

        cropped = image[y_min:y_max, x_min:x_max]
        if cropped.size == 0:
            continue

        output_path = os.path.join(output_dir, "{0}_{1}.png".format(filename_prefix, index))
        if cv2.imwrite(output_path, cropped):
            cropped_paths.append(output_path)

    return cropped_paths
