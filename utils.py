
from fpdf import FPDF
from io import BytesIO

def strip_unicode(text):
    """Safely remove non-Latin1 characters for PDF compatibility."""
    return text.encode("latin-1", errors="ignore").decode("latin-1")

def generate_pdf_report(tank_name, tank_data, suggestions):
    """Generate a PDF tank report with latest parameters and suggestions."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt=strip_unicode(f"Tank Report: {tank_name}"), ln=True)
        pdf.cell(200, 10, txt="Latest Parameters:", ln=True)

        latest = tank_data.get("data", [])[-1] if tank_data.get("data") else {}
        for key, value in latest.items():
            pdf.cell(200, 8, txt=strip_unicode(f"{key}: {value}"), ln=True)

        if suggestions:
            pdf.cell(200, 10, txt="Maintenance Suggestions:", ln=True)
            for tip in suggestions:
                pdf.multi_cell(0, 8, strip_unicode(f"• {tip}"))

        pdf_buffer = BytesIO()
        pdf.output(pdf_buffer)
        pdf_buffer.seek(0)
        return pdf_buffer

    except Exception as e:
        return None
