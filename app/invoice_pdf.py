import os
import random
import datetime
from decimal import Decimal

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from data import (
    OUTPUT_DIR,
    FONT_SIZE,
    PAGE_WIDTH,
    PAGE_HEIGHT,
    CURRENCY,
    CLIENT_NAME,
    CLIENT_ADDRESS,
    ITEM_DESCRIPTIONS_BY_ACCOUNT,
    decimal_round,
)


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def random_date_between(start, end):
    return start + datetime.timedelta(days=random.randint(0, (end - start).days))


def generate_invoice_number(prefix, idx):
    return f"{prefix}{datetime.datetime.now().strftime('%Y%m%d')}-{idx:04d}"


def generate_items(custom_amounts=None, max_total_ht=None, account_type="700", min_lines=1):
    items = []
    cap_ht = decimal_round(Decimal(str(max_total_ht))) if max_total_ht is not None else None
    descriptions = ITEM_DESCRIPTIONS_BY_ACCOUNT.get(account_type, ITEM_DESCRIPTIONS_BY_ACCOUNT["700"])

    if custom_amounts:
        amounts = [decimal_round(Decimal(str(a))) for a in custom_amounts]
        total_sum = sum(amounts, Decimal("0.00"))
        if cap_ht is not None and total_sum > cap_ht and total_sum > 0:
            factor = cap_ht / total_sum
            amounts = [decimal_round(a * factor) for a in amounts]
            adjusted = sum(amounts, Decimal("0.00"))
            diff = cap_ht - adjusted
            if diff != 0 and amounts:
                amounts[-1] = decimal_round(amounts[-1] + diff)
        for amt in amounts:
            if amt <= 0:
                continue
            desc = random.choice(descriptions)
            items.append({"desc": desc, "qty": 1, "unit": amt, "total": amt})
        return items

    for _ in range(random.randint(min(min_lines, 5), 5) if min_lines <= 5 else min_lines):
        desc = random.choice(descriptions)
        qty = random.randint(1, 10)
        unit = decimal_round(random.uniform(20.0, 1200.0))
        total = decimal_round(unit * qty)
        if total > 0:
            items.append({"desc": desc, "qty": qty, "unit": unit, "total": total})

    if not items:
        unit = decimal_round(random.uniform(50.0, 500.0))
        items.append({"desc": random.choice(descriptions), "qty": 1, "unit": unit, "total": unit})

    if cap_ht is not None and cap_ht > 0:
        sub_total = sum(it["total"] for it in items)
        ratio = Decimal(str(random.uniform(0.2, 1.0)))
        target_total = decimal_round(cap_ht * ratio)
        if sub_total > 0:
            factor = target_total / sub_total
            new_items = []
            for it in items:
                new_total = decimal_round(it["total"] * factor)
                if new_total <= 0:
                    continue
                qty = it["qty"]
                new_unit = decimal_round(new_total / qty)
                new_items.append({"desc": it["desc"], "qty": qty, "unit": new_unit, "total": new_total})
            if new_items:
                items = new_items
            else:
                items = [
                    {
                        "desc": random.choice(descriptions),
                        "qty": 1,
                        "unit": target_total,
                        "total": target_total,
                    }
                ]
    return items


def draw_invoice_pdf(
    filename,
    company,
    invoice_no,
    invoice_date,
    due_date,
    items,
    vat_rate,
    currency=CURRENCY,
    micro_entrepreneur=False,
    account_type="700",
    bank_iban=None,
    bank_bic=None,
    client=None,
):
    client = client or {"name": CLIENT_NAME, "address": CLIENT_ADDRESS}
    c = canvas.Canvas(filename, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle(f"Facture {invoice_no}")
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
    doc_type = "FACTURE" if account_type == "700" else "FACTURE FOURNISSEUR"
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_x, PAGE_HEIGHT - 30 * mm, doc_type)
    c.setFont("Helvetica", FONT_SIZE)
    c.drawString(right_x, PAGE_HEIGHT - 36 * mm, f"N°: {invoice_no}")
    c.drawString(right_x, PAGE_HEIGHT - 42 * mm, f"Date: {invoice_date.strftime('%d/%m/%Y')}")
    c.drawString(right_x, PAGE_HEIGHT - 48 * mm, f"Échéance: {due_date.strftime('%d/%m/%Y')}")

    y -= 6 * mm
    client_label = "Facturé à :" if account_type == "700" else "Facturé par :"
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, client_label)
    c.setFont("Helvetica", FONT_SIZE)
    y -= 6 * mm
    c.drawString(margin_left, y, client["name"])
    y -= 5 * mm
    for line in client.get("address", []):
        c.drawString(margin_left, y, line)
        y -= 5 * mm
    if client.get("siret"):
        c.drawString(margin_left, y, f"SIRET: {client['siret']}")
        y -= 5 * mm

    y -= 8 * mm
    table_x = margin_left
    line_rates = [Decimal(it.get("vat", vat_rate)) for it in items]
    # Colonne TVA uniquement quand la facture mélange plusieurs taux.
    multi_rate = len(set(line_rates)) > 1
    qty_col_x, unit_col_x, total_col_x = table_x + 100 * mm, table_x + 130 * mm, table_x + 170 * mm
    vat_col_x = table_x + 115 * mm
    if multi_rate:
        qty_col_x, unit_col_x = table_x + 95 * mm, table_x + 140 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(table_x - 2, y - 3 * mm, PAGE_WIDTH - 2 * margin_left + 4, 8 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", FONT_SIZE)
    c.drawString(table_x, y, "Description")
    c.drawRightString(qty_col_x, y, "Qté")
    if multi_rate:
        c.drawRightString(vat_col_x, y, "TVA")
    c.drawRightString(unit_col_x, y, "PU")
    c.drawRightString(total_col_x, y, f"Total ({currency})")
    y -= 8 * mm

    c.setFont("Helvetica", FONT_SIZE)
    sub_total = Decimal("0.00")
    base_by_rate = {}
    for it, rate in zip(items, line_rates):
        qty, unit = it["qty"], decimal_round(it["unit"])
        line_total = decimal_round(unit * qty)
        base_by_rate[rate] = base_by_rate.get(rate, Decimal("0.00")) + line_total
        c.drawString(table_x, y, it["desc"])
        c.drawRightString(qty_col_x, y, str(qty))
        if multi_rate:
            c.drawRightString(vat_col_x, y, f"{rate.normalize():f} %")
        c.drawRightString(unit_col_x, y, f"{unit:.2f}")
        c.drawRightString(total_col_x, y, f"{line_total:.2f}")
        sub_total += line_total
        y -= 6 * mm
        if y < 40 * mm:
            c.showPage()
            y = PAGE_HEIGHT - 20 * mm

    y -= 6 * mm
    c.line(table_x, y, PAGE_WIDTH - margin_left, y)
    y -= 8 * mm
    c.drawRightString(PAGE_WIDTH - margin_left, y, f"Sous-total: {decimal_round(sub_total):.2f} {currency}")
    y -= 6 * mm
    vat_amount = Decimal("0.00")
    # Une ligne de TVA par taux, du plus élevé au plus faible.
    for rate in sorted(base_by_rate, reverse=True):
        rate_vat = decimal_round(base_by_rate[rate] * rate / Decimal(100))
        vat_amount += rate_vat
        label = f"TVA ({rate.normalize():f}%)"
        if multi_rate:
            label += f" sur {decimal_round(base_by_rate[rate]):.2f}"
        c.drawRightString(PAGE_WIDTH - margin_left, y, f"{label}: {rate_vat:.2f} {currency}")
        y -= 6 * mm
    total = decimal_round(sub_total + vat_amount)
    c.setFont("Helvetica-Bold", FONT_SIZE)
    c.drawRightString(PAGE_WIDTH - margin_left, y, f"Total TTC: {total:.2f} {currency}")

    if bank_iban:
        y -= 6 * mm
        c.setFont("Helvetica", 8)
        bic_part = f" / BIC: {bank_bic}" if bank_bic else ""
        c.drawString(margin_left, y, f"IBAN: {bank_iban}{bic_part}")

    y -= 10 * mm
    if micro_entrepreneur:
        c.setFont("Helvetica", 9)
        c.drawString(margin_left, y, "TVA non applicable, art. 293 B du CGI")
        y -= 10 * mm
    else:
        y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawString(margin_left, y, "Merci pour votre confiance. Paiement à réception, sauf accord contraire.")
    c.showPage()
    c.save()

