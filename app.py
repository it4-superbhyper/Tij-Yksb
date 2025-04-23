import streamlit as st
import fitz  # PyMuPDF
import re
import matplotlib.pyplot as plt
import io

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

# ------------------ Page Config ------------------ #
st.set_page_config(page_title="Analysis Tij", layout="centered")
st.title("📊 Analysis Tij")

# ------------------ Upload UI ------------------ #
col1, col2 = st.columns(2)
with col1:
    file_1 = st.file_uploader("📄 Upload Tij4", type="pdf", key="tij4")
with col2:
    file_2 = st.file_uploader("📄 Upload Tij5", type="pdf", key="tij5")

if not (file_1 and file_2):
    st.markdown("""
    Upload **Tij4** and **Tij5** PDF files to extract:

    - **Tij**
    - **Yksb 1**
    - **Yksb 2**
    - **Ikh**
    """)

# ------------------ Extract Final Totals ------------------ #
def extract_final_totals(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()

    pattern = r"\*\*\* Final Total \*\*\*\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)"
    match = re.search(pattern, text)
    if match:
        tij = float(match.group(2).replace(",", ""))
        yksb1 = float(match.group(4).replace(",", ""))
        yksb2 = float(match.group(3).replace(",", ""))
        return {"Tij": tij, "Yksb 1": yksb1, "Yksb 2": yksb2}
    return None

# ------------------ Extract Date-Based Label ------------------ #
def extract_date_label(pdf_file):
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text = page.get_text()
            match = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
            if match:
                day, month, year = match.groups()
                return f"Tij{int(month):02d}{year[-2:]}{day}"
    return "TijUnknown"

# ------------------ PDF Report Generator ------------------ #
def generate_pdf(data_table, fig_img_bytes, label_1, label_2):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    table_data = [["", label_1, label_2, "Ikh"]]
    for i, label in enumerate(["Tij", "Yksb 1", "Yksb 2"]):
        row = [
            label,
            f"{int(round(data_table[label_1][i])):,}" if label != "Yksb 2" else f"{data_table[label_1][i]:,.2f}",
            f"{int(round(data_table[label_2][i])):,}" if label != "Yksb 2" else f"{data_table[label_2][i]:,.2f}",
            f"{int(round(data_table['Ikh'][i])):,}" if label != "Yksb 2" else f"{data_table['Ikh'][i]:,.2f}"
        ]
        table_data.append(row)

    t = Table(table_data, hAlign='LEFT', colWidths=[80, 120, 120, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    img = Image(fig_img_bytes, width=400, height=250)
    img.hAlign = 'CENTER'
    elements.append(img)
    elements.append(Spacer(1, 20))

    summary_lines = []
    if data_table['Ikh'][0] > 0:
        summary_lines.append("🔼 Tij increased.")
    elif data_table['Ikh'][0] < 0:
        summary_lines.append("🔽 Tij decreased.")
    if data_table['Ikh'][1] > 0:
        summary_lines.append("🔼 Yksb 1 increased.")
    if data_table['Ikh'][2] > 0:
        summary_lines.append("🔼 Yksb 2 increased.")
    if not summary_lines:
        summary_lines.append("No significant changes detected.")

    elements.append(Paragraph("<b>Automated Summary:</b>", styles["Heading3"]))
    for line in summary_lines:
        elements.append(Paragraph(line, styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ------------------ Main App Logic ------------------ #
if file_1 and file_2:
    with st.spinner("🔍 Extracting values from both PDFs..."):
        label_1 = extract_date_label(file_1)
        file_1.seek(0)  # Reset after reading
        label_2 = extract_date_label(file_2)
        file_2.seek(0)  # Reset after reading

        data_1 = extract_final_totals(file_1)
        file_1.seek(0)  # Reset again if reused later
        data_2 = extract_final_totals(file_2)
        file_2.seek(0)

    if data_1 and data_2:
        st.success("✅ Data extracted successfully!")

        labels = ["Tij", "Yksb 1", "Yksb 2"]
        data_table = {
            "Metric": labels,
            label_1: [data_1[m] for m in labels],
            label_2: [data_2[m] for m in labels],
            "Ikh": [data_2[m] - data_1[m] for m in labels]
        }

        # Convert Tij and Yksb 1 (and their Ikh) to thousands
        for i, metric in enumerate(["Tij", "Yksb 1"]):
            data_table[label_1][i] = round(data_table[label_1][i] / 1000)
            data_table[label_2][i] = round(data_table[label_2][i] / 1000)
            data_table["Ikh"][i] = round(data_table["Ikh"][i] / 1000)

        # Keep Yksb 2 Ikh with 2 decimal places
        data_table["Ikh"][2] = round(data_table["Ikh"][2], 2)

        st.subheader(f"📋 Tij/Yksb Comparison: {label_1} vs {label_2}")
        st.table(data_table)

        # ------------------ Chart ------------------ #
        st.subheader("📊 Chart View")
        fig, ax = plt.subplots()
        bar_width = 0.35
        x = range(len(labels))
        ax.bar([i - bar_width/2 for i in x], data_table[label_1], width=bar_width, label=label_1, color='blue')
        ax.bar([i + bar_width/2 for i in x], data_table[label_2], width=bar_width, label=label_2, color='red')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel("Values (in thousands)")
        ax.set_title(f"{label_1} vs {label_2}")
        ax.legend()

        fig_buf = io.BytesIO()
        plt.savefig(fig_buf, format="png", bbox_inches='tight')
        fig_buf.seek(0)
        st.pyplot(fig)
        plt.close(fig)

        # ------------------ Downloadable PDF ------------------ #
        pdf_report = generate_pdf(data_table, fig_buf, label_1, label_2)
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_report,
            file_name=f"{label_1}_{label_2}_Report.pdf",
            mime="application/pdf"
        )

    else:
        st.error("❌ Could not find Final Totals in one or both PDFs.")
