from groq import Groq
import base64
import mimetypes
import os
from dotenv import load_dotenv
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
import cv2
from diagrams import extract_diagrams, parse_diagram_bounds, crop_diagrams

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
    """Convert image bytes to data URL for API"""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "image/png"
    
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"

def extract_text_from_image(image_bytes, filename):
    """Extract text from image using Groq API"""
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
        max_completion_tokens=2048,
    )
    
    return completion.choices[0].message.content

def detect_formatting(text):
    """
    Detect basic formatting patterns in extracted text
    Returns structured data with formatting hints
    """
    lines = text.split('\n')
    formatted_content = []
    
    for line in lines:
        line_data = {
            'text': line,
            'is_heading': False,
            'is_bullet': False,
            'is_numbered': False,
            'indent_level': 0,
            'alignment': 'left'
        }
        
        # Detect headings (ALL CAPS or lines with # prefix)
        if line.strip().isupper() and len(line.strip()) > 0 and len(line.strip()) < 100:
            line_data['is_heading'] = True
        
        # Detect bullet points
        if re.match(r'^\s*[•\-\*]\s+', line):
            line_data['is_bullet'] = True
            line_data['indent_level'] = len(line) - len(line.lstrip())
        
        # Detect numbered lists
        if re.match(r'^\s*\d+[\.\)]\s+', line):
            line_data['is_numbered'] = True
            line_data['indent_level'] = len(line) - len(line.lstrip())
        
        # Detect indentation
        if not line_data['is_bullet'] and not line_data['is_numbered']:
            line_data['indent_level'] = len(line) - len(line.lstrip())
        
        formatted_content.append(line_data)
    
    return formatted_content

def create_formatted_docx_inline(text, output_path, diagram_data=None):
    """
    Create a formatted DOCX file with diagrams inserted inline at their positions
    diagram_data: list of dicts with 'path', 'y_min', 'y_max' (percentages)
    """
    doc = Document()
    
    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    # Detect formatting
    formatted_content = detect_formatting(text)
    
    # Sort diagrams by y_min position (top to bottom)
    if diagram_data:
        diagram_data = sorted(diagram_data, key=lambda x: x['y_min'])
    else:
        diagram_data = []
    
    # Estimate line positions (rough approximation)
    # Assume each line takes about 100/total_lines percent of vertical space
    total_lines = len(formatted_content)
    diagram_index = 0
    
    for line_idx, line_data in enumerate(formatted_content):
        # Estimate current line's vertical position (percentage)
        line_y_position = (line_idx / total_lines) * 100 if total_lines > 0 else 0
        
        # Insert any diagrams that should appear before this line
        while diagram_index < len(diagram_data):
            diagram = diagram_data[diagram_index]
            # If diagram's top is before or at current line position
            if diagram['y_min'] <= line_y_position + 5:  # Small tolerance
                # Add diagram
                if os.path.exists(diagram['path']):
                    try:
                        # Add label
                        p = doc.add_paragraph()
                        run = p.add_run(f"[Diagram {diagram_index + 1}]")
                        run.bold = True
                        run.font.color.rgb = RGBColor(255, 140, 0)  # Orange color
                        
                        # Add image
                        doc.add_picture(diagram['path'], width=Inches(5.0))
                        doc.add_paragraph()  # Spacing
                        
                        print(f"  Inserted Diagram {diagram_index + 1} at line {line_idx} (y={line_y_position:.1f}%)")
                    except Exception as e:
                        print(f"  Error inserting diagram {diagram_index + 1}: {e}")
                
                diagram_index += 1
            else:
                break
        
        # Add the text line
        text_content = line_data['text'].strip()
        
        if not text_content:  # Empty line
            doc.add_paragraph()
            continue
        
        # Add paragraph
        p = doc.add_paragraph()
        
        # Apply heading style
        if line_data['is_heading']:
            p.style = 'Heading 1'
            run = p.add_run(text_content)
            run.bold = True
        
        # Apply bullet point
        elif line_data['is_bullet']:
            p.style = 'List Bullet'
            clean_text = re.sub(r'^[•\-\*]\s+', '', text_content)
            p.add_run(clean_text)
        
        # Apply numbered list
        elif line_data['is_numbered']:
            p.style = 'List Number'
            clean_text = re.sub(r'^\d+[\.\)]\s+', '', text_content)
            p.add_run(clean_text)
        
        # Regular paragraph
        else:
            p.add_run(text_content)
        
        # Apply indentation
        if line_data['indent_level'] > 0:
            p.paragraph_format.left_indent = Inches(line_data['indent_level'] * 0.05)
    
    # Add any remaining diagrams at the end
    if diagram_index < len(diagram_data):
        doc.add_page_break()
        doc.add_heading('Additional Diagrams', level=1)
        
        while diagram_index < len(diagram_data):
            diagram = diagram_data[diagram_index]
            if os.path.exists(diagram['path']):
                try:
                    p = doc.add_paragraph()
                    run = p.add_run(f"Diagram {diagram_index + 1}:")
                    run.bold = True
                    doc.add_picture(diagram['path'], width=Inches(5.5))
                    doc.add_paragraph()
                except Exception as e:
                    doc.add_paragraph(f'[Error loading diagram: {str(e)}]')
            
            diagram_index += 1
    
    # Save document
    doc.save(output_path)
    return output_path

def process_image_to_docx_inline(image_path, output_path):
    """
    Main function to process image and create DOCX with inline diagrams
    """
    # Read image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Extract text
    extracted_text = extract_text_from_image(image_bytes, os.path.basename(image_path))
    
    # Extract and crop diagrams
    diagram_data = []
    try:
        print(f"\n=== Starting diagram extraction for {image_path} ===")
        
        # Get diagram bounds from LLM
        diagram_result = extract_diagrams(image_path)
        print(f"LLM Diagram Result:\n{diagram_result}\n")
        
        # Parse bounds
        bounds = parse_diagram_bounds(diagram_result)
        print(f"Parsed bounds: {bounds}")
        
        if bounds and len(bounds) > 0:
            print(f"Found {len(bounds)} diagram(s), cropping...")
            # Crop diagrams and save them
            diagram_paths = crop_diagrams(image_path, bounds)
            print(f"Successfully extracted {len(diagram_paths)} diagrams")
            
            # Create diagram data with position info
            for idx, (path, bound) in enumerate(zip(diagram_paths, bounds)):
                diagram_data.append({
                    'path': path,
                    'y_min': bound['y_min'],
                    'y_max': bound['y_max'],
                    'x_min': bound['x_min'],
                    'x_max': bound['x_max']
                })
                print(f"  - {path} at y={bound['y_min']}-{bound['y_max']}%")
        else:
            print("No diagrams detected in the image")
            
    except Exception as e:
        print(f"ERROR: Could not extract diagrams: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Create DOCX with inline diagrams
    print(f"\nCreating DOCX with {len(diagram_data)} diagram(s) inline...")
    docx_path = create_formatted_docx_inline(extracted_text, output_path, diagram_data)
    print(f"DOCX created at: {docx_path}\n")
    
    return extracted_text, docx_path
