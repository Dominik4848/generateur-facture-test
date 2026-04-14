import os
import datetime

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from data import RIB_OUTPUT_DIR, PAGE_WIDTH, PAGE_HEIGHT, FONT_SIZE


def ensure_rib_output_dir():
    os.makedirs(RIB_OUTPUT_DIR, exist_ok=True)


def draw_rib_pdf(filename, provenance_label, bank_name, iban, bic):
    c = canvas.Canvas(filename, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle("RIB")
    margin_left, y = 20 * mm, PAGE_HEIGHT - 25 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_left, y, "RIB / Coordonnées bancaires")

    y -= 10 * mm
    c.setFont("Helvetica", FONT_SIZE)
    now = datetime.datetime.now()
    c.drawString(margin_left, y, f"Date: {now.strftime('%d/%m/%Y %H:%M')}")

    y -= 12 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.7)
    c.line(margin_left, y, PAGE_WIDTH - margin_left, y)
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "Provenance")
    c.setFont("Helvetica", FONT_SIZE)
    c.drawString(margin_left + 35 * mm, y, provenance_label)

    y -= 8 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "Banque")
    c.setFont("Helvetica", FONT_SIZE)
    c.drawString(margin_left + 35 * mm, y, bank_name)

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "IBAN")
    y -= 7 * mm
    c.setFont("Courier", 11)
    c.drawString(margin_left, y, iban)

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "BIC / SWIFT")
    y -= 7 * mm
    c.setFont("Courier", 11)
    c.drawString(margin_left, y, bic)

    y -= 15 * mm
    c.setFont("Helvetica", 9)
    c.drawString(margin_left, y, "Document de test généré automatiquement.")

    c.showPage()
    c.save()

