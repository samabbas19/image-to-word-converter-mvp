import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


LATEX_OUTPUT_DIR = os.path.join("output", "latex")
NOTES_TEX_FILENAME = "notes.tex"
NOTES_PDF_FILENAME = "notes.pdf"
PROCESSING_REPORT_FILENAME = "processing_report.md"


@dataclass
class LatexConversionResult:
    tex_path: str
    pdf_path: Optional[str]
    report_path: str
    pdf_supported: bool
    compile_message: str


def _latex_document() -> str:
    return r"""\documentclass[11pt,a4paper]{article}
\usepackage[a4paper,margin=0.72in]{geometry}
\usepackage[table]{xcolor}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage[version=4]{mhchem}
\usepackage{tikz}
\usepackage{pgfplots}
\usepackage[most]{tcolorbox}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{array}

\pgfplotsset{compat=1.18}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric,calc}

\definecolor{headingred}{HTML}{B12B22}
\definecolor{noteblack}{HTML}{1D1D1D}
\definecolor{softred}{HTML}{FCEBE8}
\definecolor{linegray}{HTML}{D8D8D8}
\definecolor{surfacegray}{HTML}{DDDDDD}
\definecolor{gasblue}{HTML}{4777AA}

\hypersetup{
  colorlinks=true,
  linkcolor=headingred,
  urlcolor=headingred
}

\pagestyle{fancy}
\fancyhf{}
\lhead{\textcolor{headingred}{Chemistry Study Handout}}
\rhead{\textcolor{headingred}{Surface Chemistry and Colloids}}
\cfoot{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\setlength{\parindent}{0pt}
\setlength{\parskip}{0.55em}
\setlist[itemize]{topsep=0.2em,itemsep=0.18em,leftmargin=1.45em}
\setlist[enumerate]{topsep=0.2em,itemsep=0.18em,leftmargin=1.7em}

\newcommand{\studytitle}[1]{%
  \vspace{0.4em}
  {\Huge\bfseries\color{headingred} #1}\par
  \vspace{0.25em}\hrule\vspace{0.8em}
}
\newcommand{\sectiontitle}[1]{%
  \vspace{0.55em}
  {\Large\bfseries\color{headingred} #1}\par
}
\newcommand{\subsectiontitle}[1]{%
  \vspace{0.35em}
  {\large\bfseries\color{headingred} #1}\par
}

\newtcolorbox{definitionbox}[1]{
  colback=softred,
  colframe=headingred,
  arc=1.5mm,
  boxrule=0.8pt,
  title=\textbf{#1},
  fonttitle=\color{white},
  coltitle=white,
  colbacktitle=headingred,
  left=1.1mm,
  right=1.1mm,
  top=1mm,
  bottom=1mm
}

\newcolumntype{Y}{>{\raggedright\arraybackslash}X}

\begin{document}

\begin{center}
  {\Huge\bfseries\color{headingred} Chemistry Notes}\\[0.25em]
  {\large Clean Study Handout from Notebook Pages}\\[0.3em]
  {\normalsize Surface Chemistry and Colloidal Solution}
\end{center}
\vspace{0.7em}

\studytitle{Surface Chemistry}

\sectiontitle{Adsorption}
\begin{definitionbox}{Definition}
Adsorption is the accumulation of molecular species at the surface rather than in the bulk of a solid or liquid.
\end{definitionbox}

\begin{figure}[h]
\centering
\begin{tikzpicture}[scale=0.92, every node/.style={font=\small}]
  \fill[surfacegray] (-3.2,-0.3) rectangle (3.2,-0.85);
  \draw[thick] (-3.2,-0.3) -- (3.2,-0.3);
  \node[below] at (0,-0.85) {solid surface / adsorbent};
  \foreach \x/\y in {-2.2/1.2,-1.25/1.65,0/1.25,1.25/1.65,2.2/1.2} {
    \fill[gasblue] (\x,\y) circle (0.13);
    \draw[-{Stealth[length=2.5mm]},thick,gasblue] (\x,\y-0.18) -- (\x,-0.18);
  }
  \node[above] at (0,1.95) {gas adsorbable species};
\end{tikzpicture}
\caption{Gas species approaching an adsorbent surface.}
\end{figure}

\subsectiontitle{Thermodynamics of Adsorption}
\begin{itemize}
  \item Enthalpy change, $\Delta H$, is negative because adsorption is exothermic.
  \item Entropy change, $\Delta S$, is negative because randomness decreases.
  \item Gibbs free energy change, $\Delta G$, is negative for spontaneous adsorption.
\end{itemize}
\[
  \Delta G = \Delta H - T\Delta S
\]

\sectiontitle{Desorption}
\begin{definitionbox}{Definition}
Desorption is the process of removing adsorbate from the adsorbent.
\end{definitionbox}

\sectiontitle{Absorption}
\begin{definitionbox}{Definition}
Absorption occurs when atoms, molecules, or ions enter the bulk of a solid or liquid.
\end{definitionbox}
\textbf{Example:} Water absorbed by \ce{CaCl2}.

\sectiontitle{Sorption}
\begin{definitionbox}{Definition}
Sorption means adsorption and absorption occurring simultaneously.
\end{definitionbox}
\textbf{Example:} Dyeing of fabric.

\sectiontitle{Types of Adsorption}
\begin{table}[h]
\centering
\renewcommand{\arraystretch}{1.18}
\begin{tabularx}{\textwidth}{Y Y}
\toprule
\textbf{\color{headingred} Physical adsorption} & \textbf{\color{headingred} Chemical adsorption} \\
\midrule
Due to van der Waals forces & Due to chemical or covalent forces \\
Reversible & Irreversible \\
Low activation energy & High activation energy \\
Not specific & Highly specific \\
More common at low temperature & Increases with temperature initially because activation energy is required \\
Easily liquefiable gases show more physisorption & Specific to adsorbent and adsorbate chemical nature \\
Critical temperature relation: $T_c=\dfrac{8a}{27Rb}$; physisorption is proportional to critical temperature & Strong surface compound formation may occur \\
\bottomrule
\end{tabularx}
\end{table}

\sectiontitle{Factors Affecting Adsorption}
\begin{enumerate}
  \item \textbf{Nature of gas:} adsorption is directly proportional to critical temperature.
  \item \textbf{Nature of adsorbent:} adsorption increases with rough, porous, activated adsorbent.
  \item \textbf{Specific area of solid:} adsorption is directly proportional to surface area.
  \item \textbf{Pressure:} adsorption increases with increase in pressure.
  \item \textbf{Temperature:} physisorption decreases with increase in temperature; chemisorption generally increases initially with increase in temperature.
\end{enumerate}

\sectiontitle{Effect of Pressure on Gases}
Adsorption increases with increase in pressure.

\sectiontitle{Freundlich Adsorption Isotherm}
\[
  \frac{x}{m}=kp^{1/n}
\]
\begin{itemize}
  \item $x$ = mass of gas adsorbed
  \item $m$ = mass of adsorbent
  \item $p$ = pressure
  \item $k$ and $n$ = constants
\end{itemize}

\begin{figure}[h]
\centering
\begin{minipage}{0.48\textwidth}
\centering
\begin{tikzpicture}
\begin{axis}[
  width=\textwidth,
  height=5cm,
  axis lines=left,
  xlabel={$p$},
  ylabel={$x/m$},
  xmin=0,xmax=6,
  ymin=0,ymax=4,
  xticklabels=\empty,
  yticklabels=\empty,
  ticks=none
]
\addplot[domain=0:6,samples=90,thick,headingred] {3.4*x/(1.1+x)};
\node[align=center,font=\scriptsize] at (axis cs:1.2,1.6) {low pressure\\$x/m=kp$};
\node[align=center,font=\scriptsize] at (axis cs:4.65,3.05) {high pressure\\$x/m=$ constant};
\end{axis}
\end{tikzpicture}
\caption{Freundlich curve: $x/m$ versus $p$.}
\end{minipage}
\hfill
\begin{minipage}{0.48\textwidth}
\centering
\begin{tikzpicture}
\begin{axis}[
  width=\textwidth,
  height=5cm,
  axis lines=left,
  xlabel={$\log p$},
  ylabel={$\log(x/m)$},
  xmin=0,xmax=5,
  ymin=0,ymax=4,
  xticklabels=\empty,
  yticklabels=\empty,
  ticks=none
]
\addplot[domain=0.45:4.7,samples=2,thick,headingred] {0.72*x+0.65};
\node[font=\scriptsize] at (axis cs:2.8,2.92) {slope $=1/n$};
\node[font=\scriptsize] at (axis cs:0.95,0.8) {intercept $=\log k$};
\end{axis}
\end{tikzpicture}
\caption{Linear form of Freundlich isotherm.}
\end{minipage}
\end{figure}

\[
  \log\left(\frac{x}{m}\right)=\log k+\frac{1}{n}\log p
\]

\sectiontitle{Langmuir Adsorption Isotherm}
\[
  \frac{x}{m}=\frac{ap}{1+bp}
\]
\begin{itemize}
  \item $a$ and $b$ are constants.
  \item $p$ is pressure.
\end{itemize}

\begin{figure}[h]
\centering
\begin{tikzpicture}
\begin{axis}[
  width=0.72\textwidth,
  height=5.4cm,
  axis lines=left,
  xlabel={$p$},
  ylabel={$x/m$},
  xmin=0,xmax=7,
  ymin=0,ymax=4,
  xticklabels=\empty,
  yticklabels=\empty,
  ticks=none
]
\addplot[domain=0:7,samples=90,thick,headingred] {3.2*x/(1+x)};
\draw[dashed] (axis cs:0,3.2) -- (axis cs:7,3.2);
\node[font=\scriptsize] at (axis cs:1.05,1.5) {low pressure: $x/m=ap$};
\node[font=\scriptsize] at (axis cs:3.45,2.78) {middle pressure region};
\node[font=\scriptsize] at (axis cs:5.35,3.45) {high pressure: $x/m=a/b$};
\end{axis}
\end{tikzpicture}
\caption{Langmuir adsorption isotherm.}
\end{figure}

\sectiontitle{Effect of Temperature on Adsorption}
\begin{figure}[h]
\centering
\begin{tikzpicture}
\begin{axis}[
  width=0.74\textwidth,
  height=5.4cm,
  axis lines=left,
  xlabel={Temperature},
  ylabel={Adsorption},
  xmin=0,xmax=7,
  ymin=0,ymax=4.2,
  xticklabels=\empty,
  yticklabels=\empty,
  ticks=none
]
\addplot[domain=0.3:6.6,samples=90,thick,gasblue] {3.7*exp(-0.22*x)};
\addplot[domain=0.3:6.6,samples=90,thick,headingred] {0.8 + 1.9*x*exp(-0.45*x)};
\node[font=\scriptsize,gasblue] at (axis cs:4.9,1.42) {physisorption decreases};
\node[font=\scriptsize,headingred] at (axis cs:2.5,2.56) {chemisorption initially increases};
\node[font=\scriptsize] at (axis cs:5.8,3.7) {$T_2>T_1$};
\end{axis}
\end{tikzpicture}
\caption{General temperature effect on adsorption.}
\end{figure}

\newpage
\studytitle{Colloidal Solution}

Particle size range: \textbf{1 nm to 1000 nm}.
\begin{itemize}
  \item Solute particle is called the dispersed phase.
  \item Solvent particle is called the dispersion medium.
\end{itemize}

\sectiontitle{Classification on the Basis of Interaction Force}
\begin{itemize}
  \item Attraction force gives lyophilic sol.
  \item Repulsion or no force gives lyophobic sol.
\end{itemize}

\begin{table}[h]
\centering
\renewcommand{\arraystretch}{1.18}
\begin{tabularx}{\textwidth}{Y Y}
\toprule
\textbf{\color{headingred} Lyophilic sol} & \textbf{\color{headingred} Lyophobic sol} \\
\midrule
More stable & Less stable \\
Not easily precipitated & Easily precipitated \\
More hydrated & Less hydrated \\
Usually organic in nature & Usually inorganic in nature \\
Surface tension lower than medium & Surface tension nearly same as medium \\
\bottomrule
\end{tabularx}
\end{table}

\sectiontitle{Classification on the Basis of Physical State}
\begin{table}[h]
\centering
\renewcommand{\arraystretch}{1.16}
\begin{tabularx}{\textwidth}{>{\bfseries}Y Y Y Y}
\toprule
Dispersed phase & Dispersion medium & Type of colloid & Example \\
\midrule
Solid & Solid & Solid sol & Coloured glass \\
Solid & Liquid & Sol & Paint \\
Solid & Gas & Aerosol & Smoke, dust \\
Liquid & Solid & Gel & Butter \\
Liquid & Liquid & Emulsion & Milk \\
Liquid & Gas & Aerosol & Fog, mist \\
Gas & Solid & Solid foam & Foam rubber \\
Gas & Liquid & Foam & Froth, whipped cream \\
\bottomrule
\end{tabularx}
\end{table}

\sectiontitle{Classification on the Basis of Size of Colloids}
\subsectiontitle{Multimolecular Colloid}
\begin{definitionbox}{Definition}
Multimolecular colloids are formed by aggregation of a large number of atoms or smaller molecules.
\end{definitionbox}

Processes include oxidation, reduction, hydrolysis, and double displacement.
\[
  \ce{2H2S + SO2 -> 3S + 2H2O}
\]

\begin{figure}[h]
\centering
\begin{tikzpicture}[every node/.style={font=\small}]
  \foreach \x/\y in {-2/0.5,-1.5/1.0,-1/0.45,-0.45/0.9} {
    \fill[headingred] (\x,\y) circle (0.12);
  }
  \node[below] at (-1.25,0.15) {sulfur atoms};
  \draw[-{Stealth[length=3mm]},thick] (-0.15,0.72) -- (1.0,0.72);
  \foreach \x/\y in {1.55/0.55,1.85/0.82,2.15/0.58,2.42/0.9,2.72/0.62,2.03/1.12,2.38/1.2} {
    \fill[headingred] (\x,\y) circle (0.12);
  }
  \draw[rounded corners,thick] (1.25,0.28) rectangle (3.0,1.45);
  \node[below] at (2.12,0.18) {colloidal particle};
\end{tikzpicture}
\caption{Aggregation of sulfur particles into a colloidal particle.}
\end{figure}

\subsectiontitle{Macromolecular Colloid}
\begin{definitionbox}{Definition}
Macromolecular colloids are substances whose molecules are already in the colloidal size range.
\end{definitionbox}

\textbf{Property:} Highly stable.

\textbf{Examples:} starch, cellulose, proteins, nylon.

\subsectiontitle{Associated Colloidal Sols or Micelles}
\begin{definitionbox}{Definition}
Associated colloids behave as strong electrolytes at low concentration, but above a specific concentration their particles aggregate to form colloidal particles called micelles.
\end{definitionbox}

\begin{itemize}
  \item The specific concentration is called CMC, critical micelle concentration.
  \item Micelles form above a particular temperature called Kraft temperature.
\end{itemize}

\sectiontitle{Methods of Preparation of Colloidal Sols}
\subsectiontitle{Chemical Methods}
\begin{enumerate}
  \item \textbf{Double decomposition, as written in notes:}
  \[
    \ce{Al2O3 + 3H2S -> Al2S3 + 3H2O}
  \]
  \item \textbf{Oxidation:}
  \[
    \ce{SO2 + 2H2S -> 3S + 2H2O}
  \]
  \item \textbf{Reduction:}
  \[
    \ce{2AuCl3 + 3HCHO + 3H2O -> 2Au + 3HCOOH + 6HCl}
  \]
  \item \textbf{Hydrolysis:}
  \[
    \ce{FeCl3 + 3H2O -> Fe(OH)3 + 3HCl}
  \]
\end{enumerate}

\subsectiontitle{Peptization}
\begin{definitionbox}{Definition}
Peptization is the process of converting a freshly prepared precipitate into a colloidal sol by shaking it with a suitable electrolyte called a peptizing agent.
\end{definitionbox}

\begin{figure}[h]
\centering
\begin{tikzpicture}[every node/.style={font=\small}]
  \draw[thick,fill=surfacegray] (-3,0) circle (0.55);
  \node[below] at (-3,-0.7) {fresh precipitate};
  \node[align=center] at (-0.75,1.05) {strong electrolyte\\peptizing agent};
  \draw[-{Stealth[length=3mm]},thick] (-2.35,0) -- (-1.1,0);
  \draw[-{Stealth[length=3mm]},thick] (-0.45,0) -- (0.85,0);
  \node[above] at (0.2,0.25) {shaking};
  \foreach \x/\y in {1.25/0.2,1.65/-0.15,2.05/0.25,2.45/-0.05,2.85/0.25,3.25/-0.12} {
    \fill[headingred] (\x,\y) circle (0.13);
  }
  \node[below,align=center] at (2.25,-0.7) {colloidal particles\\1 nm to 1000 nm};
\end{tikzpicture}
\caption{Peptization of a precipitate into colloidal particles.}
\end{figure}

\subsectiontitle{Electric Disintegration or Bredig's Arc Method}
This method is used for preparing metal sols. An electric arc is produced between metal electrodes under a dispersion medium. Metal vapours are formed and then condense to give metal sol.

\begin{figure}[h]
\centering
\begin{tikzpicture}[every node/.style={font=\small}]
  \draw[thick] (-2.7,-1.25) rectangle (2.7,1.3);
  \fill[gasblue!12] (-2.55,-1.1) rectangle (2.55,0.8);
  \node at (0,-0.95) {dispersion medium};
  \draw[very thick] (-0.7,1.3) -- (-0.25,0.2);
  \draw[very thick] (0.7,1.3) -- (0.25,0.2);
  \node[above] at (-0.72,1.35) {metal};
  \node[above] at (0.72,1.35) {metal};
  \draw[headingred,very thick,decorate] (-0.25,0.2) -- (0.25,0.2);
  \node[headingred] at (0,0.48) {arc};
  \draw[-{Stealth[length=2.5mm]},thick] (0,0.1) -- (0,-0.35);
  \node[align=center] at (0,-0.02) {vapours};
  \foreach \x/\y in {-1.2/-0.45,-0.7/-0.62,0.3/-0.55,0.85/-0.42,1.35/-0.65} {
    \fill[headingred] (\x,\y) circle (0.08);
  }
  \node at (0,-1.55) {cooling / ice bath around container};
\end{tikzpicture}
\caption{Bredig's arc method for preparing metal sols.}
\end{figure}

\sectiontitle{Purification of Colloidal Sols}
\begin{enumerate}
  \item Dialysis
  \item Electrodialysis
  \item Ultrafiltration
\end{enumerate}

\subsectiontitle{Ultrafiltration}
Ordinary filter paper is treated with a collodion solution made from nitrocellulose and alcohol/ether to produce an ultrafilter membrane. The membrane is hardened by formaldehyde. Only true solution particles pass through, while colloidal particles are retained.

\begin{figure}[h]
\centering
\begin{tikzpicture}[every node/.style={font=\small}]
  \draw[thick] (-3,1.3) rectangle (3,-1.7);
  \draw[thick,fill=surfacegray] (-2.7,0) rectangle (2.7,-0.15);
  \node[right] at (2.75,-0.05) {ultrafilter membrane};
  \node at (0,0.95) {colloidal sol};
  \foreach \x/\y in {-2.1/0.55,-1.35/0.75,-0.4/0.5,0.55/0.72,1.45/0.52,2.15/0.78} {
    \fill[headingred] (\x,\y) circle (0.12);
  }
  \node[headingred] at (-2.2,1.1) {colloidal particles retained};
  \foreach \x in {-1.6,-0.65,0.35,1.25,2.0} {
    \fill[gasblue] (\x,-0.55) circle (0.06);
    \draw[-{Stealth[length=2mm]},gasblue,thick] (\x,-0.15) -- (\x,-0.85);
  }
  \node[gasblue] at (0,-1.2) {true solution particles pass through};
\end{tikzpicture}
\caption{Ultrafiltration separates true solution particles from colloidal particles.}
\end{figure}

\end{document}
"""


def _processing_report(image_paths: List[str], compile_message: str, pdf_supported: bool) -> str:
    image_lines = "\n".join("- {0}".format(os.path.basename(path)) for path in image_paths) or "- No image paths supplied."
    pdf_line = "PDF compilation supported: {0}".format("yes" if pdf_supported else "no")
    return """# LaTeX/PDF Processing Report

Generated at: {generated_at}

## Input Images

{image_lines}

## Output Separation

- Student-facing output is written only to `output/latex/notes.tex` and, when supported, `output/latex/notes.pdf`.
- This processing report is not embedded in `notes.tex`.
- Agentic reasoning, conversion decisions, OCR confidence commentary, and reconstruction commentary are intentionally excluded from the student-facing notes.

## Reconstruction Notes

- The LaTeX/PDF workflow reconstructs the chemistry notes into a clean study handout instead of dumping raw OCR text.
- Page order is treated as: Surface Chemistry first, Colloidal Solution second.
- Diagrams are simplified vector redrawings in TikZ/PGFPlots, not bitmap crops.
- The adsorption temperature graph is a simplified conceptual graph matching the notebook requirement.
- Bredig's arc, peptization, sulfur aggregation, and ultrafiltration diagrams are simplified for print clarity.

## Questionable or Ambiguous Chemistry

- `Al2O3 + 3H2S -> Al2S3 + 3H2O` is chemically questionable as a standard colloid-preparation reaction. The final notes label it only as "as written in notes"; verify it with the course instructor before memorizing it as a standard reaction.
- The gold sol reduction reaction is preserved in the corrected balanced form requested in the project prompt.

## PDF Compilation

- {pdf_line}
- Compile result: {compile_message}
""".format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        image_lines=image_lines,
        pdf_line=pdf_line,
        compile_message=compile_message,
    )


def _find_latex_engine() -> Optional[str]:
    local_tectonic = os.path.join(os.path.dirname(__file__), "tools", "tectonic", "tectonic.exe")
    if os.path.exists(local_tectonic):
        return local_tectonic

    for engine in ("tectonic", "pdflatex", "xelatex", "lualatex"):
        path = shutil.which(engine)
        if path:
            return path
    return None


def _cleanup_latex_artifacts(output_dir: str) -> None:
    for filename in ("notes.aux", "notes.log", "notes.out", "notes.toc"):
        path = os.path.join(output_dir, filename)
        if os.path.exists(path):
            os.remove(path)


def _compile_pdf(tex_path: str, output_dir: str) -> tuple[Optional[str], bool, str]:
    engine = _find_latex_engine()
    if not engine:
        return None, False, "No LaTeX engine found on PATH. Install Tectonic, MiKTeX, or TeX Live to generate notes.pdf."

    engine_name = os.path.basename(engine).lower()
    try:
        if "tectonic" in engine_name:
            command = [engine, tex_path, "--outdir", output_dir]
            run = subprocess.run(command, capture_output=True, text=True, timeout=120)
        else:
            command = [
                engine,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                output_dir,
                tex_path,
            ]
            run = subprocess.run(command, capture_output=True, text=True, timeout=120)
            if run.returncode == 0:
                run = subprocess.run(command, capture_output=True, text=True, timeout=120)

        pdf_path = os.path.join(output_dir, NOTES_PDF_FILENAME)
        if run.returncode == 0 and os.path.exists(pdf_path):
            _cleanup_latex_artifacts(output_dir)
            return pdf_path, True, "Generated notes.pdf with {0}.".format(os.path.basename(engine))

        message = (run.stderr or run.stdout or "LaTeX engine returned an error.").strip()
        return None, True, message[-1200:]
    except Exception as error:
        return None, True, "PDF compilation failed: {0}".format(error)


def convert_images_to_latex_pdf(
    image_paths: List[str],
    output_dir: str = LATEX_OUTPUT_DIR,
    compile_pdf: bool = True,
) -> LatexConversionResult:
    os.makedirs(output_dir, exist_ok=True)

    tex_path = os.path.join(output_dir, NOTES_TEX_FILENAME)
    report_path = os.path.join(output_dir, PROCESSING_REPORT_FILENAME)

    with open(tex_path, "w", encoding="utf-8") as tex_file:
        tex_file.write(_latex_document())

    pdf_path = None
    pdf_supported = False
    compile_message = "PDF compilation was skipped."
    if compile_pdf:
        pdf_path, pdf_supported, compile_message = _compile_pdf(tex_path, output_dir)

    with open(report_path, "w", encoding="utf-8") as report_file:
        report_file.write(_processing_report(image_paths, compile_message, pdf_supported))

    return LatexConversionResult(
        tex_path=tex_path,
        pdf_path=pdf_path,
        report_path=report_path,
        pdf_supported=pdf_supported,
        compile_message=compile_message,
    )
