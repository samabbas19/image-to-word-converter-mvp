# 📄 Image-to-Word Converter

An AI-powered web application that converts scanned documents and handwritten notes into editable Word documents with automatic diagram extraction and inline placement.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- 🔍 **Advanced OCR** - AI-powered text extraction using Groq's Llama 4 model
- 🖼️ **Automatic Diagram Detection** - Intelligently identifies and extracts diagrams, flowcharts, and tables
- 📍 **Inline Diagram Placement** - Places diagrams at their correct positions in the text flow
- 📝 **Format Preservation** - Maintains headings, bullet points, and paragraph structure
- ✍️ **Handwriting Support** - Handles both printed and handwritten text
- 🎨 **Modern UI** - Beautiful yellow-themed interface with smooth animations
- ⚡ **Fast Processing** - Quick conversion with real-time progress updates

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Groq API key ([Get one here](https://console.groq.com))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Image-to-Word-Converter.git
   cd Image-to-Word-Converter
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   GROK_API_KEY=your_groq_api_key_here
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Open your browser**
   
   Navigate to `http://localhost:8501`

## 📖 Usage

1. **Upload an Image** - Click "Browse files" or drag and drop a JPG/PNG image
2. **Convert** - Click the "🚀 Convert to DOCX" button
3. **Download** - Download your formatted Word document with embedded diagrams

### Supported Formats

- **Input**: JPG, JPEG, PNG
- **Output**: DOCX (Microsoft Word)

## 🏗️ Project Structure

```
Image-to-Word-Converter/
├── app.py                  # Main Streamlit application
├── backend.py              # Original backend (diagrams at end)
├── backend_inline.py       # Enhanced backend (inline diagrams)
├── diagrams.py             # Diagram extraction module
├── text.py                 # Text processing utilities
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── .gitignore             # Git ignore rules
├── README.md              # This file
└── ENV_SETUP.md           # Detailed setup instructions
```

## 🛠️ How It Works

1. **Text Extraction** - Uses Groq's Llama 4 Maverick model for OCR
2. **Diagram Detection** - AI identifies diagram regions with bounding boxes
3. **Image Cropping** - OpenCV crops diagrams based on coordinates
4. **Document Assembly** - python-docx creates formatted DOCX with:
   - Extracted text with preserved formatting
   - Diagrams inserted at correct positions
   - Headings, bullets, and numbered lists

## 📋 Requirements

```
streamlit>=1.28.0
python-docx>=0.8.11
groq>=0.4.0
python-dotenv>=1.0.0
opencv-python>=4.8.0
Pillow>=10.0.0
```

## 🎨 UI Features

- **Yellow-Themed Design** - Modern, vibrant color scheme
- **Gradient Backgrounds** - Smooth color transitions
- **Hover Effects** - Interactive button and card animations
- **Responsive Layout** - Works on different screen sizes
- **Real-time Feedback** - Progress indicators and status messages

## 🔧 Configuration

### API Settings

The application uses Groq's API with the following configuration:
- Model: `meta-llama/llama-4-maverick-17b-128e-instruct`
- Temperature: 0 (deterministic output)
- Max tokens: 2048

### Diagram Settings

- Default output directory: `cropped_diagrams/`
- Image width in DOCX: 5.0 inches (inline), 5.5 inches (end section)
- Position tolerance: ±5% vertical alignment

## 🐛 Troubleshooting

**Images not visible in Word:**
- Ensure you're using Microsoft Word (not Google Docs)
- Check if images are set to "hidden" in Word settings
- Look for orange `[Diagram X]` labels to locate diagrams

**API Rate Limit:**
- Wait a few moments between requests
- Check your Groq API quota

**Poor OCR Quality:**
- Use higher resolution images (300+ DPI recommended)
- Ensure good lighting and contrast
- Avoid blurry or distorted images

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Groq](https://groq.com) - For the powerful AI API
- [Streamlit](https://streamlit.io) - For the amazing web framework
- [python-docx](https://python-docx.readthedocs.io) - For DOCX manipulation
- [OpenCV](https://opencv.org) - For image processing

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Made with ❤️ and ☕ | Powered by Groq AI & Streamlit**
