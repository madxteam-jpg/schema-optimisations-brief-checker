import io
import os
import streamlit as st
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types

from pydantic_models import BriefAuditReport

# Page configuration
st.set_page_config(
    page_title="Schema Optimisation Brief Checker",
    page_icon="🔍",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .block-container { padding-top: 2rem; }
    .stAlert { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)


def extract_text_from_pdf(pdf_file) -> str:
    """Extracts plain text content from an uploaded PDF document."""
    reader = PdfReader(pdf_file)
    extracted_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text + "\n"
    return extracted_text.strip()


def analyze_brief_with_gemini(api_key: str, brief_text: str) -> BriefAuditReport:
    """Sends brief text to Gemini with structured Pydantic output enforcement."""
    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an expert Technical SEO Specialist and Schema.org Architect.
    Perform a comprehensive audit on the following Task Brief text.

    TASK BRIEF TEXT:
    ---
    {brief_text}
    ---

    AUDIT OBJECTIVES:
    1. Extract all key brief attributes (target page type, requested schemas, properties, source data).
    2. Check for technical compliance against standard Schema.org specs and Google Rich Results guidelines.
    3. Identify gaps where required properties for Rich Result eligibility are missing in the brief.
    4. Check if requested properties have specified data sources/mappings in the brief.
    5. Evaluate relational integrity and nesting (e.g., Organization nested in Publisher).
    6. Provide a score (0-100) and actionable recommendations categorized by Blocker, Warning, or Opportunity.
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BriefAuditReport,
            temperature=0.1
        )
    )

    return BriefAuditReport.model_validate_json(response.text)


def create_scorecard_image(report: BriefAuditReport, filename: str) -> bytes:
    """Generates a professional PNG scorecard image as audit proof."""
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color=(248, 249, 250))
    draw = ImageDraw.Draw(img)

    # Use default bitmap font
    font = ImageFont.load_default()

    # Outer Border & Header Box
    draw.rectangle([(20, 20), (780, 580)], outline=(200, 200, 200), width=2)
    draw.rectangle([(20, 20), (780, 100)], fill=(30, 41, 59))

    # Header Text
    draw.text((40, 35), "SCHEMA OPTIMISATION BRIEF AUDIT PROOF", fill=(255, 255, 255), font=font)
    draw.text((40, 60), f"File: {filename}", fill=(203, 213, 225), font=font)

    # Score Card Banner
    score = report.overall_score
    if score >= 80:
        score_color = (22, 101, 52)  # Green
    elif score >= 50:
        score_color = (161, 98, 7)   # Yellow/Amber
    else:
        score_color = (153, 27, 27)  # Red

    draw.rectangle([(40, 120), (760, 210)], fill=score_color)
    draw.text((60, 140), f"HEALTH SCORE: {score}/100", fill=(255, 255, 255), font=font)
    draw.text((60, 170), f"STATUS: {report.score_label}", fill=(255, 255, 255), font=font)

    # Extracted Details Box
    draw.rectangle([(40, 230), (760, 380)], outline=(226, 232, 240), fill=(255, 255, 255), width=2)
    draw.text((60, 245), f"Client / Brand: {report.extracted_brief.client_name}", fill=(15, 23, 42), font=font)
    draw.text((60, 270), f"Target Page Type: {report.extracted_brief.target_page_type}", fill=(15, 23, 42), font=font)
    draw.text((60, 295), f"Primary Objective: {report.extracted_brief.primary_seo_objective}", fill=(15, 23, 42), font=font)
    
    schemas_str = ", ".join(report.extracted_brief.requested_schema_types) or "None specified"
    draw.text((60, 320), f"Requested Schemas: {schemas_str}", fill=(15, 23, 42), font=font)
    
    missing_str = ", ".join(report.missing_mandatory_fields) if report.missing_mandatory_fields else "None"
    draw.text((60, 345), f"Missing Mandatory Fields: {missing_str}", fill=(185, 28, 28) if report.missing_mandatory_fields else (22, 101, 52), font=font)

    # Executive Summary Text
    draw.rectangle([(40, 400), (760, 540)], outline=(226, 232, 240), fill=(255, 255, 255), width=2)
    draw.text((60, 415), "Executive Summary:", fill=(15, 23, 42), font=font)
    
    # Wrap executive summary simple line splitting
    summary = report.executive_summary
    lines = [summary[i:i+90] for i in range(0, min(len(summary), 270), 90)]
    y_offset = 440
    for line in lines:
        draw.text((60, y_offset), line, fill=(71, 85, 105), font=font)
        y_offset += 20

    # Footer Timestamp
    draw.text((40, 555), "Verified by Schema Optimisation Brief Checker", fill=(148, 163, 184), font=font)

    # Convert image to byte buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    gemini_api_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Enter your Google Gemini API Key"
    )
    st.info("Tip: Get your API Key from Google AI Studio.")

# Header Section
st.title("🔍 Schema Optimisation Brief Checker")
st.caption("Upload a task brief to validate Schema.org alignment, Rich Result readiness, and technical specs.")

# UI Download Instructions Notice
st.info("""
📄 **Upload Task Brief (PDF format)**  
Please upload your brief as a `.pdf` file.  
*If your brief is in Google Docs, open the document and go to **File** > **Download** > **PDF Document (.pdf)** before uploading.*
""")

# File Upload Input
uploaded_file = st.file_uploader("Choose a task brief PDF file", type=["pdf"])

if uploaded_file is not None:
    st.success(f"File uploaded: **{uploaded_file.name}**")
    
    if st.button("🚀 Run Brief Audit", type="primary", use_container_width=True):
        if not gemini_api_key:
            st.error("Please enter your Gemini API Key in the sidebar to run the audit.")
        else:
            with st.spinner("Extracting text and auditing brief against Schema.org standards..."):
                try:
                    # 1. Read PDF
                    pdf_text = extract_text_from_pdf(uploaded_file)
                    
                    if not pdf_text or len(pdf_text) < 30:
                        st.error("Could not extract enough readable text from the PDF. Ensure it isn't an image-only scan.")
                    else:
                        # 2. Perform Audit
                        report: BriefAuditReport = analyze_brief_with_gemini(gemini_api_key, pdf_text)

                        st.divider()
                        st.subheader("📊 Audit Results Summary")

                        # Scorecard Display
                        col1, col2, col3 = st.columns([1, 2, 2])
                        with col1:
                            st.metric(label="Brief Health Score", value=f"{report.overall_score}/100")
                        with col2:
                            st.subheader(f"Status: {report.score_label}")
                        with col3:
                            st.write(f"**Executive Summary:**\n{report.executive_summary}")

                        st.divider()

                        # Extracted Brief Overview
                        st.subheader("📋 Extracted Brief Requirements")
                        e_col1, e_col2 = st.columns(2)
                        
                        with e_col1:
                            st.markdown(f"**Client/Brand:** {report.extracted_brief.client_name}")
                            st.markdown(f"**Target Page Type:** {report.extracted_brief.target_page_type}")
                            st.markdown(f"**SEO Objective:** {report.extracted_brief.primary_seo_objective}")
                        
                        with e_col2:
                            st.markdown(f"**Requested Schemas:** {', '.join(report.extracted_brief.requested_schema_types) or 'None'}")
                            st.markdown(f"**Properties Mentioned:** {', '.join(report.extracted_brief.specified_properties) or 'None'}")
                            st.markdown(f"**Data Sources:** {', '.join(report.extracted_brief.data_sources_referenced) or 'None'}")

                        if report.missing_mandatory_fields:
                            st.warning(f"⚠️ **Missing Rich Result Mandatory Fields:** {', '.join(report.missing_mandatory_fields)}")

                        st.divider()

                        # Audit Findings Details
                        st.subheader("🚨 Key Findings & Recommendations")
                        
                        for issue in report.audit_findings:
                            if issue.severity.lower() == "blocker":
                                icon = "❌"
                                box = st.error
                            elif issue.severity.lower() == "warning":
                                icon = "⚠️"
                                box = st.warning
                            else:
                                icon = "💡"
                                box = st.info

                            with box(f"{icon} [{issue.severity.upper()}] {issue.issue_title} ({issue.category})"):
                                st.write(f"**Why this matters:** {issue.explanation}")
                                st.write(f"**Recommended Action:** {issue.recommendation}")

                        st.divider()

                        # --- IMAGE DOWNLOAD BUTTON AT THE BOTTOM ---
                        st.subheader("📸 Audit Proof Image Export")
                        st.caption("Generate a downloadable PNG proof card to attach to tickets or upload as proof.")
                        
                        image_bytes = create_scorecard_image(report, uploaded_file.name)
                        
                        st.download_button(
                            label="📸 Download Audit Proof Image (PNG)",
                            data=image_bytes,
                            file_name=f"audit_proof_{uploaded_file.name.replace('.pdf', '')}.png",
                            mime="image/png",
                            type="secondary",
                            use_container_width=True
                        )

                except Exception as e:
                    st.error(f"An error occurred during audit: {str(e)}")
