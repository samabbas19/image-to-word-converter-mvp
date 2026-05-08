import argparse
import base64
import csv
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

try:
    from groq import Groq
except Exception:
    Groq = None


DEFAULT_GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
LOW_CONFIDENCE_THRESHOLD = 45.0
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class ImagePdfGenerationResult:
    tex_path: str
    pdf_path: Optional[str]
    report_path: str
    ocr_blocks_path: str
    layout_blocks_path: str
    crops_dir: str
    pdf_supported: bool
    compile_message: str
    ocr_engine: str
    warnings: List[str] = field(default_factory=list)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
    return cleaned or uuid.uuid4().hex[:10]


def _ensure_supported_image(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError("Input image does not exist: {0}".format(path))
    extension = os.path.splitext(path)[1].lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            "Unsupported input image type: {0}. Supported types: {1}".format(
                extension or "(none)",
                ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS)),
            )
        )


def _image_size(path: str) -> Tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def _bbox(x: float, y: float, width: float, height: float) -> Dict[str, int]:
    return {
        "x": int(round(x)),
        "y": int(round(y)),
        "width": int(round(width)),
        "height": int(round(height)),
    }


def _bbox_right(box: Dict[str, int]) -> int:
    return int(box["x"]) + int(box["width"])


def _bbox_bottom(box: Dict[str, int]) -> int:
    return int(box["y"]) + int(box["height"])


def _bbox_area(box: Dict[str, int]) -> int:
    return max(0, int(box["width"])) * max(0, int(box["height"]))


def _intersect_area(a: Dict[str, int], b: Dict[str, int]) -> int:
    x1 = max(int(a["x"]), int(b["x"]))
    y1 = max(int(a["y"]), int(b["y"]))
    x2 = min(_bbox_right(a), _bbox_right(b))
    y2 = min(_bbox_bottom(a), _bbox_bottom(b))
    return max(0, x2 - x1) * max(0, y2 - y1)


def _bbox_iou(a: Dict[str, int], b: Dict[str, int]) -> float:
    intersection = _intersect_area(a, b)
    union = _bbox_area(a) + _bbox_area(b) - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def _bbox_center(box: Dict[str, int]) -> Tuple[float, float]:
    return int(box["x"]) + int(box["width"]) / 2, int(box["y"]) + int(box["height"]) / 2


def _center_inside(box: Dict[str, int], container: Dict[str, int]) -> bool:
    center_x, center_y = _bbox_center(box)
    return (
        int(container["x"]) <= center_x <= _bbox_right(container)
        and int(container["y"]) <= center_y <= _bbox_bottom(container)
    )


def _union_bbox(boxes: Iterable[Dict[str, int]]) -> Dict[str, int]:
    boxes = list(boxes)
    if not boxes:
        return _bbox(0, 0, 0, 0)
    x1 = min(int(item["x"]) for item in boxes)
    y1 = min(int(item["y"]) for item in boxes)
    x2 = max(_bbox_right(item) for item in boxes)
    y2 = max(_bbox_bottom(item) for item in boxes)
    return _bbox(x1, y1, x2 - x1, y2 - y1)


def _clamp_bbox(box: Dict[str, int], image_width: int, image_height: int) -> Dict[str, int]:
    x = max(0, min(image_width - 1, int(round(box.get("x", 0)))))
    y = max(0, min(image_height - 1, int(round(box.get("y", 0)))))
    right = max(x + 1, min(image_width, int(round(box.get("x", 0) + box.get("width", 0)))))
    bottom = max(y + 1, min(image_height, int(round(box.get("y", 0) + box.get("height", 0)))))
    return _bbox(x, y, right - x, bottom - y)


def _normalise_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except Exception:
        return 0.0
    if 0 <= confidence <= 1:
        return round(confidence * 100, 2)
    return round(max(0.0, min(100.0, confidence)), 2)


def preprocess_image(image_path: str, output_dir: str, page_number: int) -> Dict[str, object]:
    os.makedirs(output_dir, exist_ok=True)
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Could not read image: {0}".format(image_path))

    original_height, original_width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    scale = 1.0
    short_side = min(original_width, original_height)
    if short_side < 1100:
        scale = min(2.0, 1100.0 / max(1, short_side))
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.bilateralFilter(gray, 5, 35, 35)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    output_path = os.path.join(output_dir, "page_{0:03d}_preprocessed.png".format(page_number))
    cv2.imwrite(output_path, enhanced)

    processed_height, processed_width = enhanced.shape[:2]
    return {
        "path": output_path,
        "original_width": original_width,
        "original_height": original_height,
        "processed_width": processed_width,
        "processed_height": processed_height,
        "scale_x": original_width / max(1, processed_width),
        "scale_y": original_height / max(1, processed_height),
    }


def _tesseract_path() -> Optional[str]:
    return shutil.which("tesseract")


def _run_tesseract_ocr(
    processed_image_path: str,
    page_number: int,
    scale_x: float,
    scale_y: float,
) -> List[Dict[str, object]]:
    executable = _tesseract_path()
    if not executable:
        raise RuntimeError("Tesseract OCR is not installed or is not on PATH.")

    command = [
        executable,
        processed_image_path,
        "stdout",
        "--oem",
        "3",
        "--psm",
        "6",
        "tsv",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "Tesseract returned an error.").strip()
        raise RuntimeError(message)

    rows = list(csv.DictReader(io.StringIO(completed.stdout), delimiter="\t"))
    grouped: Dict[Tuple[str, str, str], Dict[str, object]] = {}

    for row in rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            confidence = float(row.get("conf", "-1"))
        except ValueError:
            confidence = -1
        if confidence < 0:
            continue

        raw_box = _bbox(
            float(row.get("left", 0)) * scale_x,
            float(row.get("top", 0)) * scale_y,
            float(row.get("width", 0)) * scale_x,
            float(row.get("height", 0)) * scale_y,
        )
        key = (row.get("block_num", "0"), row.get("par_num", "0"), row.get("line_num", "0"))
        grouped.setdefault(
            key,
            {
                "page": page_number,
                "source": "tesseract",
                "text_parts": [],
                "boxes": [],
                "confidences": [],
                "words": [],
            },
        )
        grouped[key]["text_parts"].append(text)
        grouped[key]["boxes"].append(raw_box)
        grouped[key]["confidences"].append(confidence)
        grouped[key]["words"].append(
            {
                "text": text,
                "bbox": raw_box,
                "confidence": round(confidence, 2),
            }
        )

    blocks = []
    for index, item in enumerate(grouped.values(), start=1):
        text = " ".join(str(part) for part in item["text_parts"]).strip()
        if not text:
            continue
        confidences = [float(value) for value in item["confidences"]]
        blocks.append(
            {
                "id": "page_{0}_ocr_{1}".format(page_number, index),
                "page": page_number,
                "text": text,
                "bbox": _union_bbox(item["boxes"]),
                "confidence": round(sum(confidences) / max(1, len(confidences)), 2),
                "role": "unknown",
                "source": "tesseract",
                "words": item["words"],
            }
        )

    return blocks


def _groq_api_key() -> Optional[str]:
    return os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")


def _groq_model() -> str:
    return os.getenv("GROQ_VISION_MODEL", DEFAULT_GROQ_VISION_MODEL)


def _image_data_url(image_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return "data:{0};base64,{1}".format(mime_type, encoded)


def _extract_json_object(text: str) -> Dict[str, object]:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _bbox_from_model(value: object, image_width: int, image_height: int) -> Dict[str, int]:
    if not isinstance(value, dict):
        return _bbox(0, 0, image_width, image_height)

    if {"x", "y", "width", "height"}.issubset(value.keys()):
        x = float(value.get("x", 0))
        y = float(value.get("y", 0))
        width = float(value.get("width", image_width))
        height = float(value.get("height", image_height))
    elif {"x_min", "y_min", "x_max", "y_max"}.issubset(value.keys()):
        x = float(value.get("x_min", 0))
        y = float(value.get("y_min", 0))
        width = float(value.get("x_max", image_width)) - x
        height = float(value.get("y_max", image_height)) - y
    else:
        x = 0
        y = 0
        width = image_width
        height = image_height

    max_value = max(abs(x), abs(y), abs(width), abs(height))
    if max_value <= 100 and (width <= 100 or height <= 100):
        x = x / 100.0 * image_width
        y = y / 100.0 * image_height
        width = width / 100.0 * image_width
        height = height / 100.0 * image_height

    return _clamp_bbox(_bbox(x, y, width, height), image_width, image_height)


def _run_groq_vision_extraction(
    image_path: str,
    page_number: int,
    image_width: int,
    image_height: int,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    if Groq is None:
        raise RuntimeError("The groq package is not installed.")
    api_key = _groq_api_key()
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY. Set it in .env or install Tesseract for local OCR.")

    prompt = """
You are a strict OCR and document-layout extraction engine.

Extract only what is visible in the supplied image. Do not summarize, correct, complete, or invent missing content.
Use [illegible] for unreadable text.

Return valid JSON only with this schema:
{{
  "ocr_blocks": [
    {{
      "text": "visible text",
      "bbox": {{"x": 0, "y": 0, "width": 100, "height": 40}},
      "confidence": 0-100,
      "role": "heading|paragraph|list_item|numbered_item|table_text|caption|equation|diagram_label|unknown"
    }}
  ],
  "layout_blocks": [
    {{
      "type": "text|table|diagram|image",
      "bbox": {{"x": 0, "y": 0, "width": 100, "height": 40}},
      "confidence": 0-100,
      "note": "short factual reason"
    }}
  ]
}}

Coordinates may be approximate but should be relative to the full image. Prefer pixel coordinates for an image sized {width} by {height}. If using percentages, keep values between 0 and 100.
Tables, charts, flowcharts, graphs, hand-drawn diagrams, screenshots, and complex visual regions must appear in layout_blocks so they can be cropped rather than hallucinated.
""".format(
        width=image_width,
        height=image_height,
    ).strip()

    client = Groq(api_key=api_key)
    request_payload = {
        "model": _groq_model(),
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _image_data_url(image_path)}},
                ],
            }
        ],
        "temperature": 0,
    }
    try:
        response = client.chat.completions.create(**request_payload, max_completion_tokens=4096)
    except TypeError:
        response = client.chat.completions.create(**request_payload, max_tokens=4096)
    payload = _extract_json_object(response.choices[0].message.content or "{}")

    ocr_blocks = []
    for index, item in enumerate(payload.get("ocr_blocks", []) if isinstance(payload, dict) else [], start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        ocr_blocks.append(
            {
                "id": "page_{0}_ocr_{1}".format(page_number, index),
                "page": page_number,
                "text": text,
                "bbox": _bbox_from_model(item.get("bbox", {}), image_width, image_height),
                "confidence": _normalise_confidence(item.get("confidence", 0)),
                "role": str(item.get("role", "unknown")).strip() or "unknown",
                "source": "groq_vision",
                "confidence_source": "vision_model_estimate",
                "words": [],
            }
        )

    layout_blocks = []
    for index, item in enumerate(payload.get("layout_blocks", []) if isinstance(payload, dict) else [], start=1):
        if not isinstance(item, dict):
            continue
        block_type = str(item.get("type", "image")).strip().lower()
        if block_type not in {"text", "table", "diagram", "image"}:
            block_type = "image"
        layout_blocks.append(
            {
                "id": "page_{0}_vision_layout_{1}".format(page_number, index),
                "page": page_number,
                "type": block_type,
                "bbox": _bbox_from_model(item.get("bbox", {}), image_width, image_height),
                "confidence": _normalise_confidence(item.get("confidence", 0)),
                "source": "groq_vision",
                "note": str(item.get("note", "")).strip(),
            }
        )

    return ocr_blocks, layout_blocks


def extract_ocr_blocks(
    processed_image_path: str,
    original_image_path: str,
    page_number: int,
    preprocess_info: Dict[str, object],
    preferred_engine: str,
    warnings: List[str],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], str]:
    image_width = int(preprocess_info["original_width"])
    image_height = int(preprocess_info["original_height"])

    engine = preferred_engine.lower()
    if engine not in {"auto", "tesseract", "groq", "none"}:
        raise ValueError("Unknown OCR engine: {0}".format(preferred_engine))

    if engine in {"auto", "tesseract"}:
        try:
            blocks = _run_tesseract_ocr(
                processed_image_path,
                page_number,
                float(preprocess_info["scale_x"]),
                float(preprocess_info["scale_y"]),
            )
            return blocks, [], "tesseract"
        except Exception as error:
            if engine == "tesseract":
                raise
            warnings.append("Tesseract OCR unavailable or failed on page {0}: {1}".format(page_number, error))

    if engine in {"auto", "groq"}:
        try:
            blocks, regions = _run_groq_vision_extraction(original_image_path, page_number, image_width, image_height)
            warnings.append(
                "Using Groq vision extraction on page {0}; confidence values are model estimates, not native OCR confidences.".format(
                    page_number
                )
            )
            return blocks, regions, "groq_vision"
        except Exception as error:
            if engine == "groq":
                raise
            warnings.append("Groq vision extraction unavailable or failed on page {0}: {1}".format(page_number, error))

    warnings.append(
        "No OCR engine was available for page {0}; the generated LaTeX will embed the reference image instead of fake text.".format(
            page_number
        )
    )
    return [], [], "none"


def _detect_table_regions_cv(image_path: str, page_number: int) -> List[Dict[str, object]]:
    image = cv2.imread(image_path)
    if image is None:
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        12,
    )

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, width // 25), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, height // 30)))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
    grid = cv2.add(horizontal, vertical)
    grid = cv2.dilate(grid, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)), iterations=1)

    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = width * height
    regions = []
    for index, contour in enumerate(contours, start=1):
        x, y, box_width, box_height = cv2.boundingRect(contour)
        area = box_width * box_height
        if area < page_area * 0.012:
            continue
        if box_width < width * 0.22 or box_height < height * 0.045:
            continue

        line_density = cv2.countNonZero(grid[y : y + box_height, x : x + box_width]) / max(1, area)
        if line_density < 0.01:
            continue

        regions.append(
            {
                "id": "page_{0}_cv_table_{1}".format(page_number, index),
                "page": page_number,
                "type": "table",
                "bbox": _clamp_bbox(_bbox(x, y, box_width, box_height), width, height),
                "confidence": round(min(92.0, 60.0 + line_density * 900), 2),
                "source": "opencv",
                "note": "Detected horizontal/vertical ruling lines.",
            }
        )
    return regions


def _detect_visual_regions_cv(
    image_path: str,
    page_number: int,
    ocr_blocks: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    image = cv2.imread(image_path)
    if image is None:
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    edges = cv2.Canny(gray, 50, 150)
    dilated = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)), iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = width * height

    regions = []
    for index, contour in enumerate(contours, start=1):
        x, y, box_width, box_height = cv2.boundingRect(contour)
        area = box_width * box_height
        if area < page_area * 0.018 or area > page_area * 0.82:
            continue
        if box_width < width * 0.14 or box_height < height * 0.045:
            continue

        candidate = _clamp_bbox(_bbox(x, y, box_width, box_height), width, height)
        contained_text = [block for block in ocr_blocks if _center_inside(block["bbox"], candidate)]
        text_area = sum(_intersect_area(candidate, block["bbox"]) for block in contained_text)
        text_area_ratio = text_area / max(1, _bbox_area(candidate))
        edge_density = cv2.countNonZero(edges[y : y + box_height, x : x + box_width]) / max(1, area)

        if len(contained_text) >= 3 and text_area_ratio > 0.02 and edge_density < 0.08:
            continue

        regions.append(
            {
                "id": "page_{0}_cv_diagram_{1}".format(page_number, index),
                "page": page_number,
                "type": "diagram",
                "bbox": candidate,
                "confidence": round(min(88.0, 48.0 + edge_density * 650), 2),
                "source": "opencv",
                "note": "Detected non-text edge-dense region.",
            }
        )
    return regions


def _dedupe_regions(regions: List[Dict[str, object]]) -> List[Dict[str, object]]:
    type_rank = {"table": 0, "diagram": 1, "image": 2, "text": 3}
    ordered = sorted(
        regions,
        key=lambda item: (
            type_rank.get(str(item.get("type", "image")), 9),
            -float(item.get("confidence", 0)),
            -_bbox_area(item["bbox"]),
        ),
    )
    selected: List[Dict[str, object]] = []
    for region in ordered:
        box = region["bbox"]
        duplicate = False
        for existing in selected:
            iou = _bbox_iou(box, existing["bbox"])
            contained_ratio = _intersect_area(box, existing["bbox"]) / max(1, min(_bbox_area(box), _bbox_area(existing["bbox"])))
            if iou > 0.32 or contained_ratio > 0.78:
                duplicate = True
                break
        if not duplicate:
            selected.append(region)

    return sorted(selected, key=lambda item: (int(item["bbox"]["y"]), int(item["bbox"]["x"])))


def _crop_region(
    image_path: str,
    bbox: Dict[str, int],
    crops_dir: str,
    filename: str,
    padding: int = 8,
) -> str:
    os.makedirs(crops_dir, exist_ok=True)
    with Image.open(image_path) as image:
        width, height = image.size
        left = max(0, int(bbox["x"]) - padding)
        top = max(0, int(bbox["y"]) - padding)
        right = min(width, _bbox_right(bbox) + padding)
        bottom = min(height, _bbox_bottom(bbox) + padding)
        cropped = image.crop((left, top, right, bottom))
        if cropped.mode not in {"RGB", "L"}:
            cropped = cropped.convert("RGB")
        output_path = os.path.join(crops_dir, filename)
        cropped.save(output_path)
    return output_path


def _average_confidence(blocks: Sequence[Dict[str, object]]) -> float:
    if not blocks:
        return 0.0
    values = [_normalise_confidence(block.get("confidence", 0)) for block in blocks]
    return round(sum(values) / max(1, len(values)), 2)


def _classify_text_role(block: Dict[str, object], median_height: float) -> str:
    role = str(block.get("role", "unknown")).lower().strip()
    if role in {"heading", "list_item", "numbered_item", "table_text", "caption", "equation", "diagram_label"}:
        return role

    text = str(block.get("text", "")).strip()
    height = int(block.get("bbox", {}).get("height", 0))
    if re.match(r"^\s*([-*•])\s+", text):
        return "list_item"
    if re.match(r"^\s*\d+[\.)]\s+", text):
        return "numbered_item"
    if len(text) <= 90 and (text.endswith(":") or text.isupper() or height > median_height * 1.35):
        return "heading"
    return "paragraph"


def _detect_column_split(blocks: Sequence[Dict[str, object]], page_width: int) -> Optional[float]:
    if len(blocks) < 8:
        return None
    centers = sorted(_bbox_center(block["bbox"])[0] for block in blocks)
    gaps = []
    for left, right in zip(centers, centers[1:]):
        gaps.append((right - left, (left + right) / 2))
    if not gaps:
        return None
    largest_gap, split = max(gaps, key=lambda item: item[0])
    left_count = sum(1 for center in centers if center < split)
    right_count = sum(1 for center in centers if center >= split)
    if largest_gap > page_width * 0.22 and left_count >= 3 and right_count >= 3:
        return split
    return None


def _reading_order_key(block: Dict[str, object], page_width: int, split: Optional[float]) -> Tuple[float, float, float]:
    box = block["bbox"]
    center_x, _ = _bbox_center(box)
    column = 0
    if split is not None and center_x >= split:
        column = 1
    return (column, int(box["y"]), int(box["x"]))


def _clean_list_text(text: str) -> str:
    text = re.sub(r"^\s*([-*•])\s+", "", text)
    text = re.sub(r"^\s*\d+[\.)]\s+", "", text)
    return text.strip()


def _try_reconstruct_table(region: Dict[str, object], ocr_blocks: List[Dict[str, object]]) -> Optional[List[List[str]]]:
    if _normalise_confidence(region.get("confidence", 0)) < 72:
        return None

    words = []
    for block in ocr_blocks:
        for word in block.get("words", []):
            if _center_inside(word["bbox"], region["bbox"]):
                words.append(word)
    if len(words) < 6:
        return None

    average_word_confidence = _average_confidence(words)
    if average_word_confidence < 80:
        return None

    word_heights = [int(word["bbox"]["height"]) for word in words if int(word["bbox"]["height"]) > 0]
    median_height = float(np.median(word_heights)) if word_heights else 12.0
    row_tolerance = max(10.0, median_height * 0.85)
    rows: List[List[Dict[str, object]]] = []
    for word in sorted(words, key=lambda item: (_bbox_center(item["bbox"])[1], int(item["bbox"]["x"]))):
        center_y = _bbox_center(word["bbox"])[1]
        if not rows:
            rows.append([word])
            continue
        current_center = np.median([_bbox_center(item["bbox"])[1] for item in rows[-1]])
        if abs(center_y - current_center) <= row_tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])

    table_rows: List[List[str]] = []
    for row in rows:
        ordered = sorted(row, key=lambda item: int(item["bbox"]["x"]))
        gaps = []
        for left, right in zip(ordered, ordered[1:]):
            gaps.append(int(right["bbox"]["x"]) - _bbox_right(left["bbox"]))
        median_gap = float(np.median([gap for gap in gaps if gap > 0])) if any(gap > 0 for gap in gaps) else 0.0
        split_gap = max(28.0, median_gap * 2.8)
        cells = []
        current = []
        for index, word in enumerate(ordered):
            if index > 0:
                previous = ordered[index - 1]
                gap = int(word["bbox"]["x"]) - _bbox_right(previous["bbox"])
                if gap > split_gap and current:
                    cells.append(" ".join(str(item["text"]) for item in current).strip())
                    current = []
            current.append(word)
        if current:
            cells.append(" ".join(str(item["text"]) for item in current).strip())
        if cells:
            table_rows.append(cells)

    if len(table_rows) < 2:
        return None

    cell_counts = [len(row) for row in table_rows]
    target_columns = max(set(cell_counts), key=cell_counts.count)
    if target_columns < 2 or cell_counts.count(target_columns) < max(2, len(cell_counts) // 2):
        return None

    normalised = []
    for row in table_rows:
        if len(row) < target_columns:
            row = row + [""] * (target_columns - len(row))
        normalised.append(row[:target_columns])
    return normalised


def _make_text_layout_blocks(
    ocr_blocks: List[Dict[str, object]],
    excluded_regions: Sequence[Dict[str, object]],
    page_width: int,
) -> List[Dict[str, object]]:
    remaining = []
    for block in ocr_blocks:
        if any(_center_inside(block["bbox"], region["bbox"]) for region in excluded_regions):
            continue
        remaining.append(block)

    if not remaining:
        return []

    heights = [int(block["bbox"]["height"]) for block in remaining if int(block["bbox"]["height"]) > 0]
    median_height = float(np.median(heights)) if heights else 14.0
    split = _detect_column_split(remaining, page_width)
    sorted_blocks = sorted(remaining, key=lambda block: _reading_order_key(block, page_width, split))

    layout_blocks: List[Dict[str, object]] = []
    paragraph_buffer: List[Dict[str, object]] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        text = " ".join(str(item["text"]).strip() for item in paragraph_buffer if str(item["text"]).strip())
        confidences = [_normalise_confidence(item.get("confidence", 0)) for item in paragraph_buffer]
        layout_blocks.append(
            {
                "id": "page_{0}_text_{1}".format(paragraph_buffer[0]["page"], len(layout_blocks) + 1),
                "page": paragraph_buffer[0]["page"],
                "type": "text",
                "role": "paragraph",
                "text": text,
                "bbox": _union_bbox([item["bbox"] for item in paragraph_buffer]),
                "confidence": round(sum(confidences) / max(1, len(confidences)), 2),
                "source": "ocr",
            }
        )
        paragraph_buffer = []

    previous_block: Optional[Dict[str, object]] = None
    for block in sorted_blocks:
        role = _classify_text_role(block, median_height)
        if role == "paragraph":
            if previous_block is not None and paragraph_buffer:
                gap = int(block["bbox"]["y"]) - _bbox_bottom(previous_block["bbox"])
                x_delta = abs(int(block["bbox"]["x"]) - int(previous_block["bbox"]["x"]))
                if gap > median_height * 1.7 or x_delta > page_width * 0.22:
                    flush_paragraph()
            paragraph_buffer.append(block)
        else:
            flush_paragraph()
            text = str(block["text"]).strip()
            if role in {"list_item", "numbered_item"}:
                text = _clean_list_text(text)
            layout_blocks.append(
                {
                    "id": "page_{0}_text_{1}".format(block["page"], len(layout_blocks) + 1),
                    "page": block["page"],
                    "type": "text",
                    "role": role,
                    "text": text,
                    "bbox": block["bbox"],
                    "confidence": _normalise_confidence(block.get("confidence", 0)),
                    "source": block.get("source", "ocr"),
                }
            )
        previous_block = block

    flush_paragraph()
    return layout_blocks


def build_layout_blocks_for_page(
    image_path: str,
    page_number: int,
    ocr_blocks: List[Dict[str, object]],
    vision_regions: List[Dict[str, object]],
    crops_dir: str,
    warnings: List[str],
) -> List[Dict[str, object]]:
    page_width, page_height = _image_size(image_path)
    average_confidence = _average_confidence(ocr_blocks)

    if not ocr_blocks or average_confidence < LOW_CONFIDENCE_THRESHOLD:
        filename = "page_{0:03d}_full_reference.png".format(page_number)
        crop_path = _crop_region(image_path, _bbox(0, 0, page_width, page_height), crops_dir, filename, padding=0)
        reason = "No OCR text was available." if not ocr_blocks else "OCR confidence was low ({0}).".format(average_confidence)
        warnings.append(
            "{0} Page {1} was kept as an original image crop to avoid inventing content.".format(reason, page_number)
        )
        return [
            {
                "id": "page_{0}_full_reference".format(page_number),
                "page": page_number,
                "type": "image",
                "role": "full_page_fallback",
                "bbox": _bbox(0, 0, page_width, page_height),
                "confidence": average_confidence,
                "source": "fallback",
                "crop_path": crop_path,
                "note": reason,
            }
        ]

    cv_regions = _detect_table_regions_cv(image_path, page_number)
    cv_regions.extend(_detect_visual_regions_cv(image_path, page_number, ocr_blocks))
    visual_regions = _dedupe_regions(
        [
            region
            for region in [*vision_regions, *cv_regions]
            if str(region.get("type", "")).lower() in {"table", "diagram", "image"}
        ]
    )

    visual_blocks: List[Dict[str, object]] = []
    excluded_regions: List[Dict[str, object]] = []
    for index, region in enumerate(visual_regions, start=1):
        block_type = str(region.get("type", "image")).lower()
        bbox = _clamp_bbox(region["bbox"], page_width, page_height)
        if _bbox_area(bbox) < page_width * page_height * 0.008:
            continue

        table_rows = None
        if block_type == "table":
            table_rows = _try_reconstruct_table(region, ocr_blocks)

        block = {
            "id": "page_{0}_{1}_{2}".format(page_number, block_type, index),
            "page": page_number,
            "type": block_type,
            "bbox": bbox,
            "confidence": _normalise_confidence(region.get("confidence", 0)),
            "source": region.get("source", "layout_detection"),
            "note": region.get("note", ""),
        }

        if table_rows:
            block["role"] = "reconstructed_table"
            block["table_rows"] = table_rows
            warnings.append("Page {0}: reconstructed a table from high-confidence OCR.".format(page_number))
        else:
            crop_filename = "page_{0:03d}_{1}_{2}.png".format(page_number, block_type, index)
            block["role"] = "{0}_crop".format(block_type)
            block["crop_path"] = _crop_region(image_path, bbox, crops_dir, crop_filename)
            excluded_regions.append(block)
            if block_type == "table":
                warnings.append(
                    "Page {0}: table confidence was not high enough for safe LaTeX reconstruction; embedded a crop.".format(
                        page_number
                    )
                )
        visual_blocks.append(block)

    text_blocks = _make_text_layout_blocks(ocr_blocks, excluded_regions, page_width)
    combined = text_blocks + visual_blocks
    split = _detect_column_split(combined, page_width)
    return sorted(combined, key=lambda block: _reading_order_key(block, page_width, split))


LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

LATEX_INLINE_REPLACEMENTS = {
    "→": r"\(\rightarrow\)",
    "←": r"\(\leftarrow\)",
    "↔": r"\(\leftrightarrow\)",
    "≤": r"\(\leq\)",
    "≥": r"\(\geq\)",
    "±": r"\(\pm\)",
    "×": r"\(\times\)",
    "÷": r"\(\div\)",
    "°": r"\(^\circ\)",
    "Δ": r"\(\Delta\)",
    "α": r"\(\alpha\)",
    "β": r"\(\beta\)",
    "γ": r"\(\gamma\)",
    "λ": r"\(\lambda\)",
    "μ": r"\(\mu\)",
    "π": r"\(\pi\)",
}

UNICODE_TEXT_REPLACEMENTS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "--",
    "\u2014": "--",
    "\u2022": "-",
    "\u00a0": " ",
}


def latex_escape(text: object) -> str:
    value = str(text or "")
    for source, replacement in UNICODE_TEXT_REPLACEMENTS.items():
        value = value.replace(source, replacement)

    placeholders = {}
    for index, (source, replacement) in enumerate(LATEX_INLINE_REPLACEMENTS.items()):
        placeholder = "ZZZLATEXINLINE{0}ZZZ".format(index)
        if source in value:
            value = value.replace(source, placeholder)
            placeholders[placeholder] = replacement

    escaped = "".join(LATEX_SPECIAL_CHARS.get(character, character) for character in value)
    for placeholder, replacement in placeholders.items():
        escaped = escaped.replace(placeholder, replacement)
    return escaped


def _relative_tex_path(path: str, tex_dir: str) -> str:
    relative = os.path.relpath(path, tex_dir).replace("\\", "/")
    return relative


def _latex_for_table(rows: List[List[str]]) -> List[str]:
    if not rows:
        return []
    column_count = max(len(row) for row in rows)
    column_spec = " ".join(["p{{{0:.3f}\\textwidth}}".format(0.92 / max(1, column_count))] * column_count)
    lines = [
        r"\begin{center}",
        r"\renewcommand{\arraystretch}{1.18}",
        r"\begin{longtable}{" + column_spec + "}",
        r"\toprule",
    ]
    for index, row in enumerate(rows):
        padded = row + [""] * (column_count - len(row))
        lines.append(" & ".join(latex_escape(cell) for cell in padded[:column_count]) + r" \\")
        if index == 0:
            lines.append(r"\midrule")
    lines.extend([r"\bottomrule", r"\end{longtable}", r"\end{center}"])
    return lines


def _latex_for_image_block(block: Dict[str, object], tex_dir: str) -> List[str]:
    crop_path = str(block.get("crop_path", ""))
    if not crop_path:
        return []

    role = str(block.get("role", "image_crop"))
    block_type = str(block.get("type", "image"))
    relative = _relative_tex_path(crop_path, tex_dir)
    width = "0.96\\textwidth" if role == "full_page_fallback" else "0.88\\textwidth"
    lines = [
        r"\begin{figure}[H]",
        r"\centering",
        r"\includegraphics[width=" + width + r",keepaspectratio]{" + relative + r"}",
    ]
    if block_type == "diagram":
        lines.append(r"\caption*{Extracted diagram from reference image}")
    elif block_type == "table":
        lines.append(r"\caption*{Extracted table from reference image}")
    elif block_type == "image" and role != "full_page_fallback":
        lines.append(r"\caption*{Extracted visual region from reference image}")
    lines.append(r"\end{figure}")
    return lines


def _latex_document(layout_blocks: List[Dict[str, object]], tex_dir: str, source_images: Sequence[str]) -> str:
    first_heading = next(
        (
            str(block.get("text", "")).strip()
            for block in layout_blocks
            if block.get("type") == "text" and block.get("role") == "heading" and str(block.get("text", "")).strip()
        ),
        "Reference Image Reconstruction",
    )
    title = latex_escape(first_heading[:120])

    lines = [
        r"\documentclass[11pt,a4paper]{article}",
        r"\usepackage[a4paper,margin=0.72in]{geometry}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{textcomp}",
        r"\usepackage{graphicx}",
        r"\usepackage[table]{xcolor}",
        r"\usepackage{array}",
        r"\usepackage{longtable}",
        r"\usepackage{booktabs}",
        r"\usepackage{float}",
        r"\usepackage{caption}",
        r"\usepackage{hyperref}",
        r"\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0.55em}",
        r"\emergencystretch=2em",
        r"\sloppy",
        r"\begin{document}",
        r"\begin{center}",
        r"{\Large\bfseries " + title + r"}",
        r"\end{center}",
        "",
    ]

    current_page = None
    open_list: Optional[str] = None

    def close_list() -> None:
        nonlocal open_list
        if open_list:
            lines.append(r"\end{" + open_list + r"}")
            open_list = None

    for block in layout_blocks:
        page = int(block.get("page", 1))
        if current_page is None:
            current_page = page
        elif page != current_page:
            close_list()
            lines.append(r"\clearpage")
            current_page = page

        block_type = str(block.get("type", "text"))
        role = str(block.get("role", "paragraph"))

        if block_type == "text":
            text = str(block.get("text", "")).strip()
            if not text:
                continue
            if role == "heading":
                close_list()
                command = r"\section*"
                if int(block.get("bbox", {}).get("height", 0)) < 26:
                    command = r"\subsection*"
                lines.append(command + "{" + latex_escape(text) + "}")
            elif role == "numbered_item":
                if open_list != "enumerate":
                    close_list()
                    lines.append(r"\begin{enumerate}")
                    open_list = "enumerate"
                lines.append(r"\item " + latex_escape(text))
            elif role == "list_item":
                if open_list != "itemize":
                    close_list()
                    lines.append(r"\begin{itemize}")
                    open_list = "itemize"
                lines.append(r"\item " + latex_escape(text))
            else:
                close_list()
                lines.append(latex_escape(text))
        elif block_type == "table" and block.get("table_rows"):
            close_list()
            lines.extend(_latex_for_table(block["table_rows"]))
        else:
            close_list()
            lines.extend(_latex_for_image_block(block, tex_dir))

        lines.append("")

    close_list()
    lines.append(r"\end{document}")
    return "\n".join(lines)


def _find_latex_engine() -> Optional[str]:
    local_tectonic = os.path.join(os.path.dirname(__file__), "tools", "tectonic", "tectonic.exe")
    if os.path.exists(local_tectonic):
        return local_tectonic

    for engine in ("tectonic", "pdflatex", "xelatex", "lualatex"):
        path = shutil.which(engine)
        if path:
            return path
    return None


def _cleanup_latex_artifacts(output_dir: str, stem: str) -> None:
    for extension in (".aux", ".log", ".out", ".toc"):
        path = os.path.join(output_dir, stem + extension)
        if os.path.exists(path):
            os.remove(path)


def _compile_latex(tex_path: str, output_pdf_path: str) -> Tuple[Optional[str], bool, str]:
    output_dir = os.path.dirname(os.path.abspath(output_pdf_path))
    stem = os.path.splitext(os.path.basename(tex_path))[0]
    engine = _find_latex_engine()
    if not engine:
        return None, False, "No LaTeX engine found on PATH. Install Tectonic, MiKTeX, or TeX Live to compile generated.tex."

    engine_name = os.path.basename(engine).lower()
    try:
        if "tectonic" in engine_name:
            command = [engine, tex_path, "--outdir", output_dir]
            run = subprocess.run(command, capture_output=True, text=True, timeout=180)
        else:
            command = [
                engine,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                output_dir,
                tex_path,
            ]
            run = subprocess.run(command, capture_output=True, text=True, timeout=180)
            if run.returncode == 0:
                run = subprocess.run(command, capture_output=True, text=True, timeout=180)

        produced_pdf = os.path.join(output_dir, stem + ".pdf")
        if run.returncode == 0 and os.path.exists(produced_pdf):
            if os.path.abspath(produced_pdf) != os.path.abspath(output_pdf_path):
                shutil.copyfile(produced_pdf, output_pdf_path)
            _cleanup_latex_artifacts(output_dir, stem)
            return output_pdf_path, True, "Generated PDF with {0}.".format(os.path.basename(engine))

        message = (run.stderr or run.stdout or "LaTeX engine returned an error.").strip()
        return None, True, message[-1600:]
    except Exception as error:
        return None, True, "PDF compilation failed: {0}".format(error)


def _create_direct_image_pdf(image_paths: Sequence[str], output_pdf_path: str) -> Optional[str]:
    pages = []
    for image_path in image_paths:
        try:
            image = Image.open(image_path)
            if image.mode != "RGB":
                image = image.convert("RGB")
            pages.append(image)
        except Exception:
            continue

    if not pages:
        return None

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    first, rest = pages[0], pages[1:]
    first.save(output_pdf_path, "PDF", resolution=100.0, save_all=True, append_images=rest)
    for page in pages:
        page.close()
    return output_pdf_path


def _write_json(path: str, payload: Dict[str, object]) -> None:
    with open(path, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)


def _processing_report(
    image_paths: Sequence[str],
    ocr_engine: str,
    compile_message: str,
    warnings: Sequence[str],
    tex_path: str,
    pdf_path: Optional[str],
    ocr_path: str,
    layout_path: str,
    crops_dir: str,
) -> str:
    image_lines = "\n".join("- {0}".format(os.path.abspath(path)) for path in image_paths)
    warning_lines = "\n".join("- {0}".format(warning) for warning in warnings) or "- No warnings."
    pdf_line = pdf_path if pdf_path else "Not generated."
    return """# Image-to-LaTeX Processing Report

Generated at: {generated_at}

## Input Images

{image_lines}

## Pipeline

Input image -> preprocess image -> OCR text extraction -> layout/region detection -> classify regions -> generate LaTeX dynamically -> crop diagrams/tables/images when needed -> compile PDF or use direct image PDF fallback when no LaTeX engine is available.

## Selected OCR/Layout Method

- OCR engine: {ocr_engine}
- Tesseract is preferred when installed because it provides real OCR coordinates and confidence scores.
- Groq vision is used only when local OCR is unavailable and a `GROQ_API_KEY` is configured.
- If neither OCR path is available or confidence is low, the source image is embedded as a crop instead of inventing text.

## Output Files

- LaTeX: `{tex_path}`
- PDF: `{pdf_line}`
- OCR blocks: `{ocr_path}`
- Layout blocks: `{layout_path}`
- Crops directory: `{crops_dir}`

## Warnings and Confidence Notes

{warning_lines}

## PDF Compilation

{compile_message}
""".format(
        generated_at=_now(),
        image_lines=image_lines or "- No image paths supplied.",
        ocr_engine=ocr_engine,
        tex_path=tex_path,
        pdf_line=pdf_line,
        ocr_path=ocr_path,
        layout_path=layout_path,
        crops_dir=crops_dir,
        warning_lines=warning_lines,
        compile_message=compile_message,
    )


def generate_from_images(
    image_paths: Sequence[str],
    output_pdf_path: str = os.path.join("output", "generated.pdf"),
    preferred_ocr_engine: str = "auto",
    compile_pdf: bool = True,
    allow_pdf_fallback: bool = True,
) -> ImagePdfGenerationResult:
    if not image_paths:
        raise ValueError("At least one input image is required.")

    absolute_images = [os.path.abspath(path) for path in image_paths]
    for image_path in absolute_images:
        _ensure_supported_image(image_path)

    output_pdf_path = os.path.abspath(output_pdf_path)
    output_dir = os.path.dirname(output_pdf_path)
    os.makedirs(output_dir, exist_ok=True)
    tex_path = os.path.splitext(output_pdf_path)[0] + ".tex"
    report_path = os.path.join(output_dir, "processing_report.md")
    ocr_blocks_path = os.path.join(output_dir, "ocr_blocks.json")
    layout_blocks_path = os.path.join(output_dir, "layout_blocks.json")
    crops_dir = os.path.join(output_dir, "crops")
    preprocessed_dir = os.path.join(output_dir, "preprocessed")
    os.makedirs(crops_dir, exist_ok=True)
    os.makedirs(preprocessed_dir, exist_ok=True)

    warnings: List[str] = []
    all_ocr_blocks: List[Dict[str, object]] = []
    all_layout_blocks: List[Dict[str, object]] = []
    engines_used: List[str] = []

    for page_number, image_path in enumerate(absolute_images, start=1):
        preprocess_info = preprocess_image(image_path, preprocessed_dir, page_number)
        ocr_blocks, vision_regions, engine = extract_ocr_blocks(
            str(preprocess_info["path"]),
            image_path,
            page_number,
            preprocess_info,
            preferred_ocr_engine,
            warnings,
        )
        engines_used.append(engine)
        all_ocr_blocks.extend(ocr_blocks)
        layout_blocks = build_layout_blocks_for_page(
            image_path,
            page_number,
            ocr_blocks,
            vision_regions,
            crops_dir,
            warnings,
        )
        all_layout_blocks.extend(layout_blocks)

    tex_dir = os.path.dirname(tex_path)
    with open(tex_path, "w", encoding="utf-8") as tex_file:
        tex_file.write(_latex_document(all_layout_blocks, tex_dir, absolute_images))

    selected_engine = ", ".join(sorted(set(engines_used))) or "none"
    _write_json(
        ocr_blocks_path,
        {
            "generated_at": _now(),
            "ocr_engine": selected_engine,
            "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
            "blocks": all_ocr_blocks,
            "warnings": warnings,
        },
    )
    _write_json(
        layout_blocks_path,
        {
            "generated_at": _now(),
            "blocks": all_layout_blocks,
            "warnings": warnings,
        },
    )

    pdf_path = None
    pdf_supported = False
    compile_message = "PDF compilation was skipped."
    if compile_pdf:
        pdf_path, pdf_supported, compile_message = _compile_latex(tex_path, output_pdf_path)
        if not pdf_path and allow_pdf_fallback:
            fallback_pdf = _create_direct_image_pdf(absolute_images, output_pdf_path)
            if fallback_pdf:
                pdf_path = fallback_pdf
                compile_message = (
                    compile_message
                    + " Direct image-to-PDF fallback created {0}; generated.tex remains available for LaTeX compilation.".format(
                        output_pdf_path
                    )
                )
                warnings.append("PDF was produced by direct image-to-PDF fallback because LaTeX compilation was unavailable or failed.")

    with open(report_path, "w", encoding="utf-8") as report_file:
        report_file.write(
            _processing_report(
                absolute_images,
                selected_engine,
                compile_message,
                warnings,
                tex_path,
                pdf_path,
                ocr_blocks_path,
                layout_blocks_path,
                crops_dir,
            )
        )

    return ImagePdfGenerationResult(
        tex_path=tex_path,
        pdf_path=pdf_path,
        report_path=report_path,
        ocr_blocks_path=ocr_blocks_path,
        layout_blocks_path=layout_blocks_path,
        crops_dir=crops_dir,
        pdf_supported=pdf_supported,
        compile_message=compile_message,
        ocr_engine=selected_engine,
        warnings=warnings,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a LaTeX/PDF reconstruction from reference image(s).")
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="One or more reference images or screenshots.",
    )
    parser.add_argument(
        "--output",
        default=os.path.join("output", "generated.pdf"),
        help="Output PDF path. The .tex file is written next to it with the same base name.",
    )
    parser.add_argument(
        "--ocr-engine",
        choices=["auto", "tesseract", "groq", "none"],
        default="auto",
        help="OCR/layout engine preference. auto tries Tesseract, then Groq, then image fallback.",
    )
    parser.add_argument(
        "--no-compile",
        action="store_true",
        help="Write generated.tex and JSON outputs without trying to create a PDF.",
    )
    parser.add_argument(
        "--no-pdf-fallback",
        action="store_true",
        help="Do not create a direct image PDF when LaTeX compilation is unavailable.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = generate_from_images(
        image_paths=args.input,
        output_pdf_path=args.output,
        preferred_ocr_engine=args.ocr_engine,
        compile_pdf=not args.no_compile,
        allow_pdf_fallback=not args.no_pdf_fallback,
    )
    print("generated.tex={0}".format(result.tex_path))
    print("generated.pdf={0}".format(result.pdf_path))
    print("ocr_blocks.json={0}".format(result.ocr_blocks_path))
    print("layout_blocks.json={0}".format(result.layout_blocks_path))
    print("crops={0}".format(result.crops_dir))
    print(result.compile_message)
    if result.warnings:
        print("warnings:")
        for warning in result.warnings:
            print("- {0}".format(warning))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
