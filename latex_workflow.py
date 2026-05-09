import os
from dataclasses import dataclass
from typing import List, Optional

from generate_from_image import generate_from_images


LATEX_OUTPUT_DIR = "output"
GENERATED_TEX_FILENAME = "generated.tex"
GENERATED_PDF_FILENAME = "generated.pdf"
PROCESSING_REPORT_FILENAME = "processing_report.md"


@dataclass
class LatexConversionResult:
    tex_path: str
    pdf_path: Optional[str]
    report_path: str
    pdf_supported: bool
    compile_message: str
    ocr_blocks_path: str
    layout_blocks_path: str
    crops_dir: str


def convert_images_to_latex_pdf(
    image_paths: List[str],
    output_dir: str = LATEX_OUTPUT_DIR,
    compile_pdf: bool = True,
) -> LatexConversionResult:
    """
    Convert reference images into a dynamic LaTeX/PDF reconstruction.

    This function intentionally delegates to the image-based pipeline in
    generate_from_image.py. It does not emit predefined subject notes or
    hardcoded diagrams.
    """
    output_pdf_path = os.path.join(output_dir, GENERATED_PDF_FILENAME)
    result = generate_from_images(
        image_paths=image_paths,
        output_pdf_path=output_pdf_path,
        preferred_ocr_engine="groq",
        compile_pdf=compile_pdf,
        allow_pdf_fallback=False,
        require_text_extraction=True,
        require_pdf=compile_pdf,
    )
    return LatexConversionResult(
        tex_path=result.tex_path,
        pdf_path=result.pdf_path,
        report_path=result.report_path,
        pdf_supported=result.pdf_supported,
        compile_message=result.compile_message,
        ocr_blocks_path=result.ocr_blocks_path,
        layout_blocks_path=result.layout_blocks_path,
        crops_dir=result.crops_dir,
    )
