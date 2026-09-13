from datetime import datetime
from decimal import Decimal
from io import BytesIO

from fpdf import FPDF

NAVY = (11, 30, 61)
BLUE = (30, 111, 217)
MUTED = (92, 107, 128)
BORDER = (227, 232, 240)

BUSINESS_NAME = "GN TECH SOLUTIONS"
BUSINESS_ADDRESS = "3-100/26, Penta Reddy Colony, West Hanuman Nagar, Boduppal, Hyderabad, Telangana 500092"
BUSINESS_PHONE = "+91 91547 36458"


def _fmt(amount) -> str:
    return f"Rs. {Decimal(amount):,.2f}"


def generate_invoice_pdf(bill) -> bytes:
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # Header - left block (business info) and right block (invoice info)
    # are drawn independently, each starting from the same top y, then the
    # cursor is moved to below whichever block ended up taller.
    header_top = pdf.get_y()
    right_col_x = 130
    right_col_w = 195 - 15 - right_col_x  # up to the right margin

    pdf.set_xy(15, header_top)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*NAVY)
    pdf.cell(right_col_x - 15, 10, BUSINESS_NAME, ln=1)
    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(right_col_x - 15, 5, f"{BUSINESS_ADDRESS}\nPhone: {BUSINESS_PHONE}")
    left_bottom = pdf.get_y()

    pdf.set_xy(right_col_x, header_top)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*BLUE)
    pdf.cell(right_col_w, 8, "INVOICE", align="R", ln=2)
    pdf.set_x(right_col_x)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(right_col_w, 6, f"# {bill.bill_number}", align="R", ln=2)
    pdf.set_x(right_col_x)
    created = bill.created_at.strftime("%d %b %Y") if isinstance(bill.created_at, datetime) else str(bill.created_at)
    pdf.cell(right_col_w, 6, f"Date: {created}", align="R", ln=2)
    right_bottom = pdf.get_y()

    pdf.set_xy(15, max(left_bottom, right_bottom))
    pdf.ln(4)
    pdf.set_draw_color(*BORDER)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # Bill to
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, "Bill To", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 6, bill.customer_name, ln=1)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 6, bill.customer_phone, ln=1)
    pdf.ln(6)

    # Items table header
    col_widths = (95, 20, 30, 35)
    headers = ("Description", "Qty", "Unit Price", "Amount")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(246, 248, 251)
    pdf.set_text_color(*NAVY)
    for w, h in zip(col_widths, headers):
        align = "L" if h == "Description" else "R"
        pdf.cell(w, 8, h, border=0, align=align, fill=True)
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 30, 30)
    for item in bill.items:
        qty = Decimal(str(item["quantity"]))
        unit_price = Decimal(str(item["unit_price"]))
        amount = qty * unit_price
        pdf.set_draw_color(*BORDER)
        pdf.cell(col_widths[0], 8, str(item["description"])[:60], border="B", align="L")
        pdf.cell(col_widths[1], 8, f"{float(qty):g}", border="B", align="R")
        pdf.cell(col_widths[2], 8, _fmt(unit_price), border="B", align="R")
        pdf.cell(col_widths[3], 8, _fmt(amount), border="B", align="R")
        pdf.ln(8)

    pdf.ln(4)

    # Totals
    label_w, value_w = 145, 35
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(label_w, 7, "Subtotal", align="R")
    pdf.set_text_color(30, 30, 30)
    pdf.cell(value_w, 7, _fmt(bill.subtotal), align="R", ln=1)

    if Decimal(bill.tax_percent) > 0:
        pdf.set_text_color(*MUTED)
        pdf.cell(label_w, 7, f"Tax ({float(bill.tax_percent):g}%)", align="R")
        pdf.set_text_color(30, 30, 30)
        pdf.cell(value_w, 7, _fmt(bill.tax_amount), align="R", ln=1)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.cell(label_w, 9, "Total", align="R")
    pdf.cell(value_w, 9, _fmt(bill.total), align="R", ln=1)

    if bill.warranty:
        pdf.ln(8)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, "Warranty", ln=1)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(0, 5, bill.warranty)

    if bill.notes:
        pdf.ln(bill.warranty and 4 or 8)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, "Notes", ln=1)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(0, 5, bill.notes)

    # Auto page-break is disabled here because it's a preemptive check based
    # on the configured bottom margin, not actual page overflow - without
    # this, positioning the footer close to the bottom (which is the whole
    # point of a footer) reliably triggers a spurious blank second page.
    pdf.set_auto_page_break(False)

    # Signature block - "Ganesh" rendered in an italic script-like style as
    # the authorized signature, with a line and caption beneath it. This is
    # a rendered text signature (no separate image upload flow), positioned
    # above the footer so both fit without overlapping. Normally pinned near
    # the bottom of the page, but if a long item list plus warranty/notes
    # has already pushed the cursor past that point, fall back to placing it
    # right after the content instead - it would otherwise print on top of
    # the notes text.
    sig_x, sig_w = 130, 65
    content_bottom = pdf.get_y()
    pinned_sig_top = pdf.h - 50
    sig_top = content_bottom + 6 if content_bottom > pinned_sig_top - 6 else pinned_sig_top
    pdf.set_xy(sig_x, sig_top)
    pdf.set_font("Times", "BI", 22)
    pdf.set_text_color(*NAVY)
    pdf.cell(sig_w, 12, "Ganesh", align="C", ln=2)
    pdf.set_x(sig_x)
    pdf.set_draw_color(*BORDER)
    pdf.line(sig_x, pdf.get_y(), sig_x + sig_w, pdf.get_y())
    pdf.ln(2)
    pdf.set_x(sig_x)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(sig_w, 5, "Authorized Signatory", align="C")
    sig_bottom = pdf.get_y()

    footer_y = max(pdf.h - 25, sig_bottom + 8)
    pdf.set_y(footer_y)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 6, "Thank you for choosing GN Tech Solutions!", align="C")

    return bytes(pdf.output())
