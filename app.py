import streamlit as st
import os
from PIL import Image
import io
from backend_inline import process_image_to_docx_inline as process_image_to_docx
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Image-to-Word Converter",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for stunning yellow-themed design
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main background with gradient */
    .main {
        background: linear-gradient(135deg, #FFF9E6 0%, #FFFBF0 50%, #FFF4D6 100%);
        padding: 2rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFD700 0%, #FFA500 100%);
        border-right: 3px solid #FF8C00;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] li {
        color: #1a1a1a !important;
    }
    
    /* Primary button styling */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        color: #1a1a1a;
        font-size: 18px;
        font-weight: 700;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 15px rgba(255, 165, 0, 0.4);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #FFA500 0%, #FF8C00 100%);
        box-shadow: 0 8px 25px rgba(255, 140, 0, 0.6);
        transform: translateY(-2px);
    }
    
    .stButton>button:active {
        transform: translateY(0px);
    }
    
    /* Download button */
    .stDownloadButton>button {
        width: 100%;
        background: linear-gradient(135deg, #32CD32 0%, #228B22 100%);
        color: white;
        font-size: 16px;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 15px rgba(50, 205, 50, 0.4);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stDownloadButton>button:hover {
        background: linear-gradient(135deg, #228B22 0%, #006400 100%);
        box-shadow: 0 8px 25px rgba(34, 139, 34, 0.6);
        transform: translateY(-2px);
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background: white;
        border: 3px dashed #FFD700;
        border-radius: 16px;
        padding: 2rem;
        transition: all 0.3s ease;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #FFA500;
        background: #FFFEF8;
        box-shadow: 0 8px 20px rgba(255, 215, 0, 0.2);
    }
    
    /* Success box */
    .success-box {
        padding: 1.5rem;
        background: linear-gradient(135deg, #90EE90 0%, #32CD32 100%);
        border: none;
        border-radius: 12px;
        color: #1a1a1a;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(50, 205, 50, 0.3);
        margin: 1rem 0;
    }
    
    /* Info box */
    .info-box {
        padding: 1.5rem;
        background: linear-gradient(135deg, #FFFACD 0%, #FFD700 100%);
        border: none;
        border-radius: 12px;
        color: #1a1a1a;
        font-weight: 500;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
        margin: 1rem 0;
    }
    
    /* Warning box */
    .warning-box {
        padding: 1.5rem;
        background: linear-gradient(135deg, #FFE4B5 0%, #FFA500 100%);
        border: none;
        border-radius: 12px;
        color: #1a1a1a;
        font-weight: 500;
        box-shadow: 0 4px 15px rgba(255, 165, 0, 0.3);
        margin: 1rem 0;
    }
    
    /* Headers */
    h1 {
        background: linear-gradient(135deg, #FFD700 0%, #FF8C00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
        text-align: center;
        padding-bottom: 1rem;
        font-size: 3rem;
        text-shadow: 2px 2px 4px rgba(255, 215, 0, 0.1);
    }
    
    h2, h3 {
        color: #FF8C00;
        font-weight: 700;
    }
    
    /* Feature cards */
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 8px 30px rgba(255, 165, 0, 0.15);
        margin-bottom: 1.5rem;
        border: 2px solid #FFD700;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #FFD700 0%, #FFA500 100%);
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(255, 140, 0, 0.25);
        border-color: #FFA500;
    }
    
    .feature-card h4 {
        color: #FF8C00;
        font-weight: 700;
        margin-bottom: 0.5rem;
        font-size: 1.3rem;
    }
    
    .feature-card p {
        color: #4a4a4a;
        line-height: 1.6;
    }
    
    /* Image container */
    .stImage {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        border: 3px solid #FFD700;
        transition: all 0.3s ease;
    }
    
    .stImage:hover {
        box-shadow: 0 12px 35px rgba(255, 165, 0, 0.3);
        transform: scale(1.02);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #FFFACD 0%, #FFD700 100%);
        border-radius: 8px;
        font-weight: 600;
        color: #1a1a1a;
    }
    
    /* Text area */
    .stTextArea textarea {
        border: 2px solid #FFD700;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #FFD700 !important;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, #FFD700 50%, transparent 100%);
        margin: 2rem 0;
    }
    
    /* Animations */
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.8;
        }
    }
    
    .pulse {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #666;
        padding: 2rem;
        background: linear-gradient(135deg, #FFFACD 0%, #FFE4B5 100%);
        border-radius: 12px;
        margin-top: 2rem;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.2);
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        color: #FF8C00;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# Header with emoji and gradient
st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h1>✨ Image-to-Word Converter ✨</h1>
        <p style="font-size: 1.2rem; color: #666; font-weight: 500;">
            Transform your scanned documents into editable Word files with AI-powered precision
        </p>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

# Sidebar
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #1a1a1a;">ℹ️ About</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.3); padding: 1rem; border-radius: 12px; margin: 1rem 0;">
        <p style="color: #1a1a1a; font-weight: 500;">
        This application converts images (JPG/PNG) to formatted Word documents (.docx) with AI-powered OCR.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    **✨ Features:**
    - 🔍 Advanced OCR using AI
    - 📝 Preserves formatting
    - 🖼️ Extracts diagrams & images
    - 📊 Handles handwritten text
    - ⚡ Lightning-fast processing
    
    **📁 Supported Formats:**
    - JPG/JPEG
    - PNG
    
    **🚀 Quick Start:**
    1. Upload an image
    2. Click "Convert to DOCX"
    3. Download your document
    """)
    
    st.markdown("---")
    st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.3); padding: 1rem; border-radius: 8px; text-align: center;">
            <p style="color: #1a1a1a; font-weight: 600; margin: 0;">
                📚 Project Phase 1
            </p>
            <p style="color: #1a1a1a; font-size: 0.9rem; margin: 0;">
                Virtual Company Task 1
            </p>
        </div>
    """, unsafe_allow_html=True)

# Main content
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 8px 30px rgba(255, 165, 0, 0.15); border: 2px solid #FFD700;">
            <h2 style="color: #FF8C00; margin-top: 0;">📤 Upload Image</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an image file (JPG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        help="Upload a clear image of a document for best results",
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        # Display uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="📸 Uploaded Image", width="stretch")
        
        # Image info
        st.markdown(f"""
        <div class="info-box">
        <strong>📊 Image Details:</strong><br>
        📏 Dimensions: {image.size[0]} × {image.size[1]} pixels<br>
        📦 Format: {image.format}<br>
        💾 File Size: {len(uploaded_file.getvalue()) / 1024:.2f} KB
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 8px 30px rgba(255, 165, 0, 0.15); border: 2px solid #FFD700;">
            <h2 style="color: #FF8C00; margin-top: 0;">📥 Output</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if uploaded_file is not None:
        # Process button
        if st.button("🚀 Convert to DOCX", type="primary"):
            with st.spinner("🔄 Processing image... Extracting text and diagrams..."):
                try:
                    # Create temp directory if it doesn't exist
                    temp_dir = "temp"
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    # Save uploaded file temporarily
                    temp_image_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_image_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    
                    # Generate output filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"converted_{timestamp}.docx"
                    output_path = os.path.join(temp_dir, output_filename)
                    
                    # Process image
                    extracted_text, docx_path = process_image_to_docx(temp_image_path, output_path)
                    
                    # Store in session state
                    st.session_state['extracted_text'] = extracted_text
                    st.session_state['docx_path'] = docx_path
                    st.session_state['output_filename'] = output_filename
                    
                    st.balloons()
                    st.success("✅ Conversion completed successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error during conversion: {str(e)}")
                    st.exception(e)
        
        # Display results if available
        if 'extracted_text' in st.session_state:
            st.markdown("""
            <div class="success-box">
            ✅ <strong>Conversion Complete!</strong><br>
            Your document is ready with extracted text and diagrams.
            </div>
            """, unsafe_allow_html=True)
            
            # Download button
            with open(st.session_state['docx_path'], 'rb') as f:
                docx_bytes = f.read()
            
            st.download_button(
                label="📥 Download DOCX File",
                data=docx_bytes,
                file_name=st.session_state['output_filename'],
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary"
            )
            
            # Show extracted text preview
            with st.expander("👁️ Preview Extracted Text"):
                st.text_area(
                    "Extracted Content",
                    st.session_state['extracted_text'],
                    height=300,
                    disabled=True
                )
    else:
        st.markdown("""
        <div class="warning-box">
        <strong>👆 Get Started</strong><br>
        Upload an image on the left to begin the conversion process.
        </div>
        """, unsafe_allow_html=True)

# Footer section
st.markdown("---")

# Statistics/Features section
st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h2 style="color: #FF8C00;">✨ Key Features</h2>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.markdown("""
    <div class="feature-card">
    <h4>🎯 High Accuracy</h4>
    <p>Advanced AI-powered OCR for accurate text extraction from both printed and handwritten documents with diagram detection.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
    <h4>📝 Format Preservation</h4>
    <p>Maintains document structure including headings, bullet points, paragraph formatting, and embedded diagrams.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
    <h4>⚡ Fast Processing</h4>
    <p>Quick conversion with real-time progress updates, instant download capability, and automatic diagram extraction.</p>
    </div>
    """, unsafe_allow_html=True)

# Instructions
with st.expander("📖 Detailed Instructions & Tips"):
    st.markdown("""
    ### 🎓 How to Use This Application
    
    **Step 1: Upload Your Image**
    - Click on the "Browse files" button or drag and drop your image
    - Supported formats: JPG, JPEG, PNG
    - For best results, use clear, well-lit images
    
    **Step 2: Review the Preview**
    - Check the uploaded image preview
    - Verify image quality and readability
    - Review the image details shown
    
    **Step 3: Convert to DOCX**
    - Click the "Convert to DOCX" button
    - Wait for the processing to complete (usually 10-30 seconds)
    - The system will extract both text and diagrams
    
    **Step 4: Download Your Document**
    - Click the "Download DOCX File" button
    - Open the file in Microsoft Word or compatible software
    - Edit and format as needed
    - Diagrams will appear in a separate section
    
    ### 💡 Tips for Best Results
    
    - ✅ Use high-resolution images (at least 300 DPI)
    - ✅ Ensure good lighting and contrast
    - ✅ Keep the document flat and avoid shadows
    - ✅ Use clear, legible handwriting or printed text
    - ✅ Ensure diagrams are clearly visible
    - ❌ Avoid blurry or low-quality images
    - ❌ Avoid images with heavy background patterns
    - ❌ Avoid extreme angles or distortion
    
    ### 🔧 Troubleshooting
    
    **Problem:** Text not extracted correctly
    - **Solution:** Try uploading a higher quality image with better lighting
    
    **Problem:** Diagrams not detected
    - **Solution:** Ensure diagrams are clearly separated from text and have visible boundaries
    
    **Problem:** Formatting not preserved
    - **Solution:** Ensure the original document has clear structure and spacing
    
    **Problem:** Processing takes too long
    - **Solution:** Check your internet connection or try a smaller image
    """)

# Footer
st.markdown("""
<div class="footer">
    <h3 style="color: #FF8C00; margin-top: 0;">📄 Image-to-Word Converter</h3>
    <p style="font-size: 1.1rem; color: #666; margin: 0.5rem 0;">
        Developed for Project Phase 1: Virtual Company
    </p>
    <p style="color: #888; margin: 0.5rem 0;">
        Powered by Groq AI 🤖 | Streamlit ⚡ | Python 🐍
    </p>
    <p style="color: #999; font-size: 0.9rem; margin-top: 1rem;">
        © 2026 | Built with ❤️ and ☕
    </p>
</div>
""", unsafe_allow_html=True)
