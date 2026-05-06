$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

py -3.12 -c "from latex_workflow import convert_images_to_latex_pdf; r = convert_images_to_latex_pdf(['1.jpeg', '2.jpeg', '3.jpeg']); print('notes.tex=' + r.tex_path); print('notes.pdf=' + str(r.pdf_path)); print('processing_report.md=' + r.report_path); print(r.compile_message)"
