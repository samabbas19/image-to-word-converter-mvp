$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ($args.Count -eq 0) {
    throw "Usage: .\scripts\build_latex.ps1 <reference-image> [more-images...]"
}

python generate_from_image.py --input @args --output output/generated.pdf
