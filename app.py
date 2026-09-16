import io
import os
import subprocess
import pandas as pd
import streamlit as st
from pypdf import PdfReader
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types

from pydantic_models import BriefAuditReport, AuditIssue, ExtractedBrief

# Automatically install Playwright browser binary once and cache it for Streamlit Cloud
@st.cache_resource
def install_playwright_browsers():
    subprocess.run(["python", "-m", "playwright", "install", "chromium"])

install_playwright_browsers()

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
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BriefAuditReport,
            temperature=0.1
        )
    )

    return BriefAuditReport.model_validate_json(response.text)


def render_full_report_html(report: BriefAuditReport, filename: str) -> str:
    """Generates a complete, responsive HTML layout matching your Pydantic schema."""
    score = report.overall_score
    score_color = "#2e7d32" if score >= 80 else ("#ef6c00" if score >= 50 else "#c62828")

    # Render audit_findings using your AuditIssue model structure
    findings_html = ""
    for issue in report.audit_findings:
        sev = issue.severity.lower()
        if sev == "blocker":
            badge_bg, badge_color = "#ffebee", "#c62828"
        elif sev == "warning":
            badge_bg, badge_color = "#fff3e0", "#ef6c00"
        else:
            badge_bg, badge_color = "#e3f2fd", "#1565c0"

        findings_html += f"""
        <div style="background-color: #fafafa; border: 1px solid #e0e0e0; border-left: 5px solid {badge_color}; border-radius: 6px; padding: 14px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                <span style="font-weight: bold; font-size: 15px; color: #212529;">{issue.issue_title}</span>
                <span style="background-color: {badge_bg}; color: {badge_color}; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{issue.severity} • {issue.category}</span>
            </div>
            <p style="margin: 4px 0; font-size: 13px; color: #424242;"><b>Why this matters:</b> {issue.explanation}</p>
            <p style="margin: 4px 0; font-size: 13px; color: #1565c0;"><b>Recommendation:</b> {issue.recommendation}</p>
        </div>
        """

    client_name = report.extracted_brief.client_name or "N/A"
    req_schemas = ", ".join(report.extracted_brief.requested_schema_types) or "None specified"
    spec_props = ", ".join(report.extracted_brief.specified_properties) or "None specified"
    data_srcs = ", ".join(report.extracted_brief.data_sources_referenced) or "None specified"
    missing_fields = ", ".join(report.missing_mandatory_fields) if report.missing_mandatory_fields else "None"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * {{ box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #ffffff;
        margin: 0;
        padding: 24px;
        color: #212529;
    }}
    .container {{
        background: #ffffff;
        padding: 28px;
        border-radius: 10px;
        border: 2px solid #e9ecef;
        max-width: 1100px;
        margin: 0 auto;
    }}
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 16px;
        margin-bottom: 20px;
    }}
    .metrics-box {{
        display: flex;
        justify-content: space-between;
        background-color: #f8f9fa;
        padding: 18px;
        border-radius: 8px;
        margin-bottom: 24px;
        border: 1px solid #e9ecef;
    }}
    .score-circle {{
        font-size: 32px;
        font-weight: bold;
        color: {score_color};
    }}
    .section-title {{
        font-size: 18px;
        font-weight: 600;
        color: #343a40;
        margin-top: 24px;
        margin-bottom: 12px;
        border-bottom: 1px solid #e9ecef;
        padding-bottom: 6px;
    }}
    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        background-color: #ffffff;
        padding: 12px;
        border: 1px solid #e9ecef;
        border-radius: 6px;
    }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h2 style="margin: 0; color: #1E88E5;">🔍 Schema Brief Audit Summary</h2>
            <p style="margin: 4px 0 0 0; color: #6c757d; font-size: 13px;">File: {filename}</p>
        </div>
        <div style="text-align: right;">
            <span style="font-size: 12px; color: #6c757d;">AUDIT PROOF REPORT</span>
        </div>
    </div>

    <div class="metrics-box">
        <div>
            <div style="font-size: 12px; color: #6c757d; font-weight: bold;">HEALTH SCORE</div>
            <div class="score-circle">{score}/100</div>
        </div>
        <div>
            <div style="font-size: 12px; color: #6c757d; font-weight: bold;">STATUS</div>
            <div style="font-size: 20px; font-weight: bold; margin-top: 6px; color: #212529;">{report.score_label}</div>
        </div>
        <div style="max-width: 50%;">
            <div style="font-size: 12px; color: #6c757d; font-weight: bold;">EXECUTIVE SUMMARY</div>
            <div style="font-size: 13px; margin-top: 6px; color: #495057;">{report.executive_summary}</div>
        </div>
    </div>

    <div class="section-title">📋 Extracted Brief Requirements</div>
    <div class="grid-2">
        <div>
            <p style="margin: 4px 0; font-size: 13px;"><b>Client/Brand:</b> {client_name}</p>
            <p style="margin: 4px 0; font-size: 13px;"><b>Target Page Type:</b> {report.extracted_brief.target_page_type}</p>
            <p style="margin: 4px 0; font-size: 13px;"><b>SEO Objective:</b> {report.extracted_brief.primary_seo_objective}</p>
        </div>
        <div>
            <p style="margin: 4px 0; font-size: 13px;"><b>Requested Schemas:</b> {req_schemas}</p>
            <p style="margin: 4px 0; font-size: 13px;"><b>Specified Properties:</b> {spec_props}</p>
            <p style="margin: 4px 0; font-size: 13px;"><b>Data Sources:</b> {data_srcs}</p>
        </div>
    </div>
    <p style="margin-top: 8px; font-size: 13px; color: {'#c62828' if report.missing_mandatory_fields else '#2e7d32'};">
        <b>Missing Mandatory Rich Result Fields:</b> {missing_fields}
    </p>

    <div class="section-title">🚨 Key Findings & Recommendations</div>
    {findings_html}
</div>
</body>
</html>"""


def generate_full_report_screenshot(html_content: str) -> bytes:
    """Uses Playwright to render HTML and capture a dynamic full-page PNG."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(viewport={"width": 1200, "height": 800}, device_scale_factor=2)
        page = context.new_page()
        
        page.set_content(html_content, wait_until="networkidle")
        
        content_height = page.evaluate("document.body.scrollHeight")
        content_width = page.evaluate("document.body.scrollWidth")
        page.set_viewport_size({"width": max(1200, content_width), "height": content_height + 40})
        
        screenshot = page.screenshot(full_page=True, type="png")
        browser.close()
        return screenshot


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

st.info("""
📄 **Upload Task Brief (PDF format)**  
Please upload your brief as a `.pdf` file.  
*If your brief is in Google Docs, open the document and go to **File** > **Download** > **PDF Document (.pdf)** before uploading.*
""")

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

                        # Generate Clean HTML View
                        html_report = render_full_report_html(report, uploaded_file.name)
                        st.markdown(html_report, unsafe_allow_html=True)

                        st.divider()

                        # --- FULL REPORT IMAGE DOWNLOAD BUTTON ---
                        st.subheader("📸 Audit Proof Image Export")
                        st.caption("Generate a full-page PNG report card showing all audit metrics, schemas, and findings.")
                        
                        with st.spinner("Rendering full visual report image..."):
                            full_report_png = generate_full_report_screenshot(html_report)
                        
                        st.download_button(
                            label="📸 Download Full Audit Report Image (PNG)",
                            data=full_report_png,
                            file_name=f"audit_proof_{uploaded_file.name.replace('.pdf', '')}.png",
                            mime="image/png",
                            type="secondary",
                            use_container_width=True
                        )

                except Exception as e:
                    st.error(f"An error occurred during audit: {str(e)}")
