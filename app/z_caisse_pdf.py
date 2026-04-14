import os
from decimal import Decimal

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from data import (
    Z_CAISSE_OUTPUT_DIR,
    FONT_SIZE,
    PAGE_WIDTH,
    PAGE_HEIGHT,
    CURRENCY,
    decimal_round,
)


def ensure_z_caisse_output_dir():
    os.makedirs(Z_CAISSE_OUTPUT_DIR, exist_ok=True)


def draw_z_caisse_pdf(
    filename,
    company,
    z_date,
    z_caisse,
    z_numero,
    categories_data,
    paiements_data,
    totals,
    ecart=None,
    bank_iban=None,
    bank_bic=None,
):
    c = canvas.Canvas(filename, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle(f"Ticket Z {z_numero}")
    margin_left, y = 20 * mm, PAGE_HEIGHT - 20 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin_left, y, company["name"])
    c.setFont("Helvetica", FONT_SIZE)
    y -= 6 * mm
    for line in company.get("address", []):
        c.drawString(margin_left, y, line)
        y -= 5 * mm
    if "siret" in company:
        c.drawString(margin_left, y, f"SIRET: {company['siret']}")
        y -= 8 * mm
    else:
        y -= 2 * mm

    right_x = PAGE_WIDTH - 80 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_x, PAGE_HEIGHT - 30 * mm, "TICKET Z / CLÔTURE DE CAISSE")
    c.setFont("Helvetica", FONT_SIZE)
    c.drawString(right_x, PAGE_HEIGHT - 36 * mm, f"Date: {z_date.strftime('%d/%m/%Y')}")
    c.drawString(right_x, PAGE_HEIGHT - 42 * mm, f"Heure: {z_date.strftime('%H:%M')}")
    c.drawString(right_x, PAGE_HEIGHT - 48 * mm, f"Caisse: {z_caisse}")
    c.drawString(right_x, PAGE_HEIGHT - 54 * mm, f"N° Z: {z_numero}")

    y -= 10 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "Récapitulatif par catégorie")
    y -= 6 * mm

    table_x = margin_left
    total_col_x = PAGE_WIDTH - margin_left - 60 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(table_x - 2, y - 3 * mm, PAGE_WIDTH - 2 * margin_left + 4, 8 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", FONT_SIZE)
    c.drawString(table_x, y, "Catégorie")
    c.drawRightString(total_col_x, y, f"Total TTC ({CURRENCY})")
    y -= 8 * mm

    c.setFont("Helvetica", FONT_SIZE)
    for cat, amount in categories_data.items():
        c.drawString(table_x, y, cat)
        c.drawRightString(total_col_x, y, f"{amount:.2f}")
        y -= 6 * mm
        if y < 100 * mm:
            c.showPage()
            y = PAGE_HEIGHT - 20 * mm

    y -= 6 * mm
    c.line(table_x, y, PAGE_WIDTH - margin_left, y)
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "Récapitulatif par mode de paiement")
    y -= 6 * mm

    c.rect(table_x - 2, y - 3 * mm, PAGE_WIDTH - 2 * margin_left + 4, 8 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", FONT_SIZE)
    c.drawString(table_x, y, "Mode de paiement")
    c.drawRightString(total_col_x, y, f"Montant ({CURRENCY})")
    y -= 8 * mm

    c.setFont("Helvetica", FONT_SIZE)
    for paiement, amount in paiements_data.items():
        c.drawString(table_x, y, paiement)
        c.drawRightString(total_col_x, y, f"{amount:.2f}")
        y -= 6 * mm
        if y < 100 * mm:
            c.showPage()
            y = PAGE_HEIGHT - 20 * mm

    y -= 6 * mm
    c.line(table_x, y, PAGE_WIDTH - margin_left, y)
    y -= 8 * mm

    c.setFont("Helvetica-Bold", FONT_SIZE)
    c.drawRightString(PAGE_WIDTH - margin_left, y, f"Total HT: {totals['ht']:.2f} {CURRENCY}")
    y -= 6 * mm
    
    if totals.get("no_vat"):
        c.drawRightString(
            PAGE_WIDTH - margin_left,
            y,
            f"TVA (0%): {Decimal('0.00'):.2f} {CURRENCY}",
        )
        y -= 6 * mm
        c.setFont("Helvetica", 9)
        c.drawString(margin_left, y, "TVA non applicable (0%)")
        y -= 6 * mm
        c.setFont("Helvetica-Bold", FONT_SIZE)
    else:
        if totals.get("tva1") is not None:
            c.drawRightString(
                PAGE_WIDTH - margin_left,
                y,
                f"TVA ({totals['tva1_rate']}%): {totals['tva1']:.2f} {CURRENCY}",
            )
            y -= 6 * mm
        if totals.get("tva2") is not None:
            c.drawRightString(
                PAGE_WIDTH - margin_left,
                y,
                f"TVA ({totals['tva2_rate']}%): {totals['tva2']:.2f} {CURRENCY}",
            )
            y -= 6 * mm
    
    c.setFont("Helvetica-Bold", FONT_SIZE + 1)
    c.drawRightString(PAGE_WIDTH - margin_left, y, f"Total TTC: {totals['ttc']:.2f} {CURRENCY}")

    if ecart is not None and ecart != 0:
        y -= 8 * mm
        c.setFont("Helvetica-Bold", FONT_SIZE)
        ecart_color = colors.red if ecart < 0 else colors.darkgreen
        c.setFillColor(ecart_color)
        c.drawRightString(PAGE_WIDTH - margin_left, y, f"Écart de caisse: {ecart:.2f} {CURRENCY}")
        c.setFillColor(colors.black)

    if bank_iban:
        y -= 6 * mm
        c.setFont("Helvetica", 8)
        bic_part = f" / BIC: {bank_bic}" if bank_bic else ""
        c.drawString(margin_left, y, f"IBAN: {bank_iban}{bic_part}")

    y -= 15 * mm
    c.setFont("Helvetica", 8)
    c.drawString(margin_left, y, "Merci. Signature:")
    c.showPage()
    c.save()

