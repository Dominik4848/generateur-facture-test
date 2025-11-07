import os
import random
import datetime
from decimal import Decimal, ROUND_HALF_UP
import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "factures_sortie")
FONT_SIZE = 11
PAGE_WIDTH, PAGE_HEIGHT = A4
CURRENCY = "€"

# donnees client (même client pour toutes les factures)
CLIENT_NAME = "test test"
CLIENT_ADDRESS = [
    "12 rue Fictive",
    "75000 Faillotte",
    "France"
]

SAMPLE_COMPANIES = [
    {"name": "SARL Alpha", "address": ["1 Place du Marché", "75001 Paris"], "siret": "123 456 789 00010"},
    {"name": "EURL Beta", "address": ["9 Avenue Imaginaire", "69000 Lyon"], "siret": "987 654 321 00020"},
    {"name": "SAS Gamma", "address": ["5 Boulevard Exemple", "06000 Nice"], "siret": "555 555 555 00030"},
    {"name": "SARL Delta", "address": ["12 Rue du Port", "33000 Bordeaux"], "siret": "111 222 333 00040"},
    {"name": "SASU Epsilon", "address": ["18 Chemin des Bois", "31000 Toulouse"], "siret": "222 333 444 00050"},
    {"name": "SARL Zeta", "address": ["7 Rue des Lilas", "44000 Nantes"], "siret": "333 444 555 00060"},
    {"name": "SCI Eta", "address": ["3 Impasse des Jardins", "13000 Marseille"], "siret": "444 555 666 00070"},
    {"name": "SARL Theta", "address": ["21 Avenue des Arts", "67000 Strasbourg"], "siret": "555 666 777 00080"},
    {"name": "SA Iota", "address": ["8 Boulevard du Centre", "59000 Lille"], "siret": "666 777 888 00090"},
    {"name": "SARL Kappa", "address": ["15 Rue des Forges", "25000 Besançon"], "siret": "777 888 999 00100"},
]

MAX_INVOICES = len(SAMPLE_COMPANIES)
# plafond total TTC par facture en dur possible à modifier
DEFAULT_MAX_TOTAL_TTC = Decimal("5000")

# descriptions d'items possible à modifier
ITEM_DESCRIPTIONS = [
    "Consultation",
    "Développement",
    "Maintenance",
    "Licence logicielle",
    "Prestation horaire",
    "Frais de voyage",
    "Formation",
    "Design graphique"
]

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def decimal_round(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def random_date_between(start_date, end_date):
    delta = end_date - start_date
    rand_days = random.randint(0, delta.days)
    return start_date + datetime.timedelta(days=rand_days)

def generate_invoice_number(prefix, idx):
    date_part = datetime.datetime.now().strftime("%Y%m%d")
    return f"{prefix}{date_part}-{idx:04d}"

def generate_items(custom_amounts=None, max_total_ht=None):
    items = []
    cap_ht = None
    if max_total_ht is not None:
        cap_ht = decimal_round(Decimal(str(max_total_ht)))
    if custom_amounts:
        amounts = [decimal_round(Decimal(str(amt))) for amt in custom_amounts]
        total_sum = sum(amounts, Decimal("0.00"))
        if cap_ht is not None and total_sum > cap_ht and total_sum > Decimal("0.00"):
            factor = cap_ht / total_sum
            amounts = [decimal_round(a * factor) for a in amounts]
            adjusted_total = sum(amounts, Decimal("0.00"))
            diff = cap_ht - adjusted_total
            if diff != Decimal("0.00"):
                amounts[-1] = decimal_round(amounts[-1] + diff)
        for amt in amounts:
            if amt <= Decimal("0.00"):
                continue
            desc = random.choice(ITEM_DESCRIPTIONS)
            qty = 1
            line_total = decimal_round(amt * qty)
            items.append({"desc": desc, "qty": qty, "unit": amt, "total": line_total})
        return items
    count = random.randint(1, 5)
    sub_total = Decimal("0.00")
    for _ in range(count):
        remaining = None
        if cap_ht is not None:
            remaining = cap_ht - sub_total
            if remaining <= Decimal("0.00"):
                break
        desc = random.choice(ITEM_DESCRIPTIONS)
        qty = random.randint(1, 10)
        unit = decimal_round(random.uniform(20.0, 1200.0))
        total = decimal_round(unit * qty)
        if remaining is not None and total > remaining:
            total = decimal_round(remaining)
            qty = 1
            unit = total
        if total <= Decimal("0.00"):
            continue
        items.append({"desc": desc, "qty": qty, "unit": unit, "total": total})
        sub_total += total
    return items

def draw_invoice_pdf(filename, company, invoice_no, invoice_date, due_date, items, vat_rate, currency=CURRENCY):
    c = canvas.Canvas(filename, pagesize=A4)
    c.setTitle(f"Facture {invoice_no}")

    margin_left = 20 * mm
    y = PAGE_HEIGHT - 20 * mm

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
    c.drawString(right_x, PAGE_HEIGHT - 30 * mm, f"FACTURE")
    c.setFont("Helvetica", FONT_SIZE)
    c.drawString(right_x, PAGE_HEIGHT - 36 * mm, f"N°: {invoice_no}")
    c.drawString(right_x, PAGE_HEIGHT - 42 * mm, f"Date: {invoice_date.strftime('%d/%m/%Y')}")
    c.drawString(right_x, PAGE_HEIGHT - 48 * mm, f"Échéance: {due_date.strftime('%d/%m/%Y')}")

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_left, y, "Facturé à :")
    c.setFont("Helvetica", FONT_SIZE)
    y -= 6 * mm
    c.drawString(margin_left, y, CLIENT_NAME)
    y -= 5 * mm
    for line in CLIENT_ADDRESS:
        c.drawString(margin_left, y, line)
        y -= 5 * mm

    y -= 8 * mm
    table_x = margin_left
    qty_col_x = table_x + 100 * mm
    unit_col_x = table_x + 130 * mm
    total_col_x = table_x + 170 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(table_x - 2, y - 3 * mm, PAGE_WIDTH - 2 * margin_left + 4, 8 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", FONT_SIZE)
    c.drawString(table_x, y, "Description")
    c.drawRightString(qty_col_x, y, "Qté")
    c.drawRightString(unit_col_x, y, "PU")
    c.drawRightString(total_col_x, y, f"Total ({currency})")
    y -= 8 * mm

    c.setFont("Helvetica", FONT_SIZE)
    sub_total = Decimal("0.00")
    for it in items:
        qty = it["qty"]
        unit = decimal_round(it["unit"])
        line_total = decimal_round(unit * qty)
        c.drawString(table_x, y, it["desc"])
        c.drawRightString(qty_col_x, y, str(qty))
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
    vat_amount = decimal_round(sub_total * Decimal(vat_rate) / Decimal(100))
    c.drawRightString(PAGE_WIDTH - margin_left, y, f"TVA ({vat_rate}%): {vat_amount:.2f} {currency}")
    y -= 6 * mm
    total = decimal_round(sub_total + vat_amount)
    c.setFont("Helvetica-Bold", FONT_SIZE)
    c.drawRightString(PAGE_WIDTH - margin_left, y, f"Total TTC: {total:.2f} {currency}")

    y -= 15 * mm
    c.setFont("Helvetica", 8)
    c.drawString(margin_left, y, "Merci pour votre confiance. Paiement à réception, sauf accord contraire.")
    c.showPage()
    c.save()

class InvoiceGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Générateur de factures PDF")
        self.n_var = tk.IntVar(value=1)
        self.same_company_var = tk.BooleanVar(value=True)
        self.custom_amounts_var = tk.BooleanVar(value=False)
        self.custom_dates_var = tk.BooleanVar(value=False)
        self.vat_var = tk.StringVar(value="20")
        self.prefix_var = tk.StringVar(value="FAC-")
        self.file_prefix_var = tk.StringVar(value="")
        self.max_total_var = tk.StringVar(value=str(DEFAULT_MAX_TOTAL_TTC))
        self.company_name_var = tk.StringVar()
        self.company_address_var = tk.StringVar()
        self.company_siret_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.invoice_sections = []
        self._updating_count = False
        self._build_ui()

    def _build_ui(self):
        padding = {"padx": 10, "pady": 5}
        frame = ttk.Frame(self.root)
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(frame, text="Nombre de factures (max 10)").grid(row=0, column=0, sticky="w", **padding)
        self.n_spinbox = ttk.Spinbox(frame, from_=1, to=MAX_INVOICES, textvariable=self.n_var, width=6, command=self._refresh_invoice_sections)
        self.n_spinbox.grid(row=0, column=1, sticky="w", **padding)
        self.n_var.trace_add("write", lambda *args: self._refresh_invoice_sections())

        ttk.Checkbutton(frame, text="Même société pour toutes (aléatoire si pas remplie ou à remplir individuellement)", variable=self.same_company_var, command=self._toggle_company_fields).grid(row=1, column=0, columnspan=2, sticky="w", **padding)

        ttk.Label(frame, text="Nom société").grid(row=2, column=0, sticky="w", **padding)
        self.company_name_entry = ttk.Entry(frame, textvariable=self.company_name_var, width=40)
        self.company_name_entry.grid(row=2, column=1, sticky="we", **padding)

        ttk.Label(frame, text="Adresse (séparer par ';')").grid(row=3, column=0, sticky="w", **padding)
        self.company_address_entry = ttk.Entry(frame, textvariable=self.company_address_var, width=40)
        self.company_address_entry.grid(row=3, column=1, sticky="we", **padding)

        ttk.Label(frame, text="SIRET").grid(row=4, column=0, sticky="w", **padding)
        self.company_siret_entry = ttk.Entry(frame, textvariable=self.company_siret_var, width=40)
        self.company_siret_entry.grid(row=4, column=1, sticky="we", **padding)

        ttk.Checkbutton(frame, text="Personnaliser les montants", variable=self.custom_amounts_var, command=self._update_section_visibility).grid(row=5, column=0, columnspan=2, sticky="w", **padding)
        ttk.Checkbutton(frame, text="Personnaliser les dates", variable=self.custom_dates_var, command=self._update_section_visibility).grid(row=6, column=0, columnspan=2, sticky="w", **padding)

        ttk.Label(frame, text="TVA (%)").grid(row=7, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.vat_var, width=10).grid(row=7, column=1, sticky="w", **padding)

        ttk.Label(frame, text="Préfixe numéro").grid(row=8, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.prefix_var, width=20).grid(row=8, column=1, sticky="w", **padding)

        ttk.Label(frame, text="Préfixe fichier").grid(row=9, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.file_prefix_var, width=20).grid(row=9, column=1, sticky="w", **padding)

        ttk.Label(frame, text="Plafond TTC").grid(row=10, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.max_total_var, width=20).grid(row=10, column=1, sticky="w", **padding)

        sections_frame = ttk.LabelFrame(frame, text="Détails par facture")
        sections_frame.grid(row=11, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        self.sections_canvas = tk.Canvas(sections_frame, height=260, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(sections_frame, orient="vertical", command=self.sections_canvas.yview)
        self.sections_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.sections_canvas.pack(side="left", fill="both", expand=True)

        self.invoices_container = ttk.Frame(self.sections_canvas)
        self.invoices_container.bind("<Configure>", lambda e: self.sections_canvas.configure(scrollregion=self.sections_canvas.bbox("all")))
        self.sections_canvas.create_window((0, 0), window=self.invoices_container, anchor="nw")

        self.generate_button = ttk.Button(frame, text="Générer", command=self.generate_invoices)
        self.generate_button.grid(row=12, column=0, columnspan=2, pady=15)

        ttk.Label(frame, textvariable=self.status_var, foreground="green").grid(row=13, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        frame.columnconfigure(1, weight=1)
        self._toggle_company_fields()
        self._refresh_invoice_sections()

    def _toggle_company_fields(self):
        same = self.same_company_var.get()
        for entry in (self.company_name_entry, self.company_address_entry, self.company_siret_entry):
            if same:
                entry.state(["!disabled"])
            else:
                entry.state(["disabled"])
        self._update_section_visibility()

    def _get_invoice_count(self):
        if self._updating_count:
            try:
                return int(self.n_var.get())
            except Exception:
                return 1
        try:
            n = int(self.n_var.get())
        except Exception:
            n = 1
        n = max(1, min(MAX_INVOICES, n))
        if self.n_var.get() != n:
            self._updating_count = True
            self.n_var.set(n)
            self._updating_count = False
        return n

    def _create_invoice_section(self, index):
        frame = ttk.LabelFrame(self.invoices_container, text=f"Facture {index}")
        frame.grid(row=index - 1, column=0, sticky="ew", padx=10, pady=6)
        frame.columnconfigure(1, weight=1)

        pad = {"padx": 8, "pady": 2}

        company_name_var = tk.StringVar()
        company_address_var = tk.StringVar()
        company_siret_var = tk.StringVar()
        amounts_var = tk.StringVar()
        inv_date_var = tk.StringVar()
        due_date_var = tk.StringVar()

        ttk.Label(frame, text="Nom société").grid(row=0, column=0, sticky="w", **pad)
        company_name_entry = ttk.Entry(frame, textvariable=company_name_var)
        company_name_entry.grid(row=0, column=1, sticky="we", **pad)

        ttk.Label(frame, text="Adresse (séparer par ';')").grid(row=1, column=0, sticky="w", **pad)
        company_address_entry = ttk.Entry(frame, textvariable=company_address_var)
        company_address_entry.grid(row=1, column=1, sticky="we", **pad)

        ttk.Label(frame, text="SIRET").grid(row=2, column=0, sticky="w", **pad)
        company_siret_entry = ttk.Entry(frame, textvariable=company_siret_var)
        company_siret_entry.grid(row=2, column=1, sticky="we", **pad)

        ttk.Label(frame, text="Montants (séparer par ';')").grid(row=3, column=0, sticky="w", **pad)
        amounts_entry = ttk.Entry(frame, textvariable=amounts_var)
        amounts_entry.grid(row=3, column=1, sticky="we", **pad)

        ttk.Label(frame, text="Date facture (JJ-MM-AAAA)").grid(row=4, column=0, sticky="w", **pad)
        inv_date_entry = ttk.Entry(frame, textvariable=inv_date_var)
        inv_date_entry.grid(row=4, column=1, sticky="we", **pad)

        ttk.Label(frame, text="Date échéance (JJ-MM-AAAA)").grid(row=5, column=0, sticky="w", **pad)
        due_date_entry = ttk.Entry(frame, textvariable=due_date_var)
        due_date_entry.grid(row=5, column=1, sticky="we", **pad)

        return {
            "frame": frame,
            "company_name_var": company_name_var,
            "company_address_var": company_address_var,
            "company_siret_var": company_siret_var,
            "company_name_entry": company_name_entry,
            "company_address_entry": company_address_entry,
            "company_siret_entry": company_siret_entry,
            "amounts_var": amounts_var,
            "amounts_entry": amounts_entry,
            "inv_date_var": inv_date_var,
            "inv_date_entry": inv_date_entry,
            "due_date_var": due_date_var,
            "due_date_entry": due_date_entry,
        }

    def _refresh_invoice_sections(self, *args):
        n = self._get_invoice_count()
        while len(self.invoice_sections) > n:
            section = self.invoice_sections.pop()
            section["frame"].destroy()
        while len(self.invoice_sections) < n:
            index = len(self.invoice_sections) + 1
            section = self._create_invoice_section(index)
            self.invoice_sections.append(section)
        self._update_section_visibility()

    def _update_section_visibility(self, *args):
        same = self.same_company_var.get()
        custom_amounts = self.custom_amounts_var.get()
        custom_dates = self.custom_dates_var.get()
        for section in self.invoice_sections:
            if same:
                section["company_name_entry"].state(["disabled"])
                section["company_address_entry"].state(["disabled"])
                section["company_siret_entry"].state(["disabled"])
            else:
                section["company_name_entry"].state(["!disabled"])
                section["company_address_entry"].state(["!disabled"])
                section["company_siret_entry"].state(["!disabled"])

            if custom_amounts:
                section["amounts_entry"].state(["!disabled"])
            else:
                section["amounts_entry"].state(["disabled"])

            if custom_dates:
                section["inv_date_entry"].state(["!disabled"])
                section["due_date_entry"].state(["!disabled"])
            else:
                section["inv_date_entry"].state(["disabled"])
                section["due_date_entry"].state(["disabled"])

    def generate_invoices(self):
        n = self._get_invoice_count()
        if n > MAX_INVOICES:
            messagebox.showinfo("Information", f"Nombre ajusté à {MAX_INVOICES}.", parent=self.root)
            n = MAX_INVOICES

        try:
            vat_rate = Decimal(self.vat_var.get().replace(",", "."))
        except Exception:
            messagebox.showerror("Erreur", "TVA invalide.", parent=self.root)
            return

        prefix = self.prefix_var.get().strip() or "FAC-"
        file_prefix = self.file_prefix_var.get().strip()

        try:
            max_total_ttc = decimal_round(Decimal(self.max_total_var.get().replace(",", ".")))
        except Exception:
            messagebox.showerror("Erreur", "Plafond TTC invalide.", parent=self.root)
            return

        vat_multiplier = (Decimal("100") + vat_rate) / Decimal("100") if vat_rate is not None else Decimal("1")
        max_total_ht = decimal_round(max_total_ttc / vat_multiplier) if vat_multiplier != 0 else max_total_ttc

        same_company = self.same_company_var.get()

        if same_company:
            name = self.company_name_var.get().strip()
            if name:
                address = self.company_address_var.get().split(";") if self.company_address_var.get() else []
                comp = {"name": name, "address": [line.strip() for line in address if line.strip()]}
                siret = self.company_siret_var.get().strip()
                if siret:
                    comp["siret"] = siret
            else:
                comp = random.choice(SAMPLE_COMPANIES)
            companies = [dict(comp) for _ in range(n)]
        else:
            companies = []
            for i, section in enumerate(self.invoice_sections):
                name = section["company_name_var"].get().strip()
                addr_raw = section["company_address_var"].get()
                siret = section["company_siret_var"].get().strip()
                if not name and not addr_raw and not siret:
                    company = random.choice(SAMPLE_COMPANIES)
                else:
                    if not name:
                        name = f"Entreprise {i + 1}"
                    address = [line.strip() for line in addr_raw.split(";") if line.strip()]
                    company = {"name": name, "address": address}
                    if siret:
                        company["siret"] = siret
                companies.append(company)

        custom_amounts_per_invoice = [None] * n
        if self.custom_amounts_var.get():
            for i, section in enumerate(self.invoice_sections):
                raw = section["amounts_var"].get()
                if not raw.strip():
                    continue
                parts = raw.replace(",", ";").split(";")
                values = []
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        num = decimal_round(Decimal(part))
                    except Exception:
                        messagebox.showerror("Erreur", f"Montant invalide pour la facture {i+1} : {part}", parent=self.root)
                        return
                    if num <= Decimal("0"):
                        continue
                    values.append(num)
                if values:
                    custom_amounts_per_invoice[i] = values

        invoice_dates = [None] * n
        due_dates = [None] * n
        if self.custom_dates_var.get():
            for i, section in enumerate(self.invoice_sections):
                inv_raw = section["inv_date_var"].get().strip()
                due_raw = section["due_date_var"].get().strip()
                if inv_raw:
                    try:
                        invoice_dates[i] = datetime.datetime.strptime(inv_raw, "%d-%m-%Y").date()
                    except Exception:
                        messagebox.showerror("Erreur", f"Date facture invalide pour la facture {i+1}", parent=self.root)
                        return
                if due_raw:
                    try:
                        due_dates[i] = datetime.datetime.strptime(due_raw, "%d-%m-%Y").date()
                    except Exception:
                        messagebox.showerror("Erreur", f"Date échéance invalide pour la facture {i+1}", parent=self.root)
                        return

        ensure_output_dir()

        generated_files = []
        for i in range(1, n + 1):
            company = companies[i - 1]
            inv_no = generate_invoice_number(prefix, i)
            if invoice_dates[i - 1]:
                inv_date = invoice_dates[i - 1]
            else:
                end = datetime.date.today()
                start = end - datetime.timedelta(days=90)
                inv_date = random_date_between(start, end)
            if due_dates[i - 1]:
                due_date = due_dates[i - 1]
            else:
                due_date = inv_date + datetime.timedelta(days=30)

            custom_amts = custom_amounts_per_invoice[i - 1]
            items = generate_items(custom_amounts=custom_amts, max_total_ht=max_total_ht)
            if not items:
                items = generate_items(max_total_ht=max_total_ht)

            filename = os.path.join(OUTPUT_DIR, f"{file_prefix}facture_{inv_no}.pdf")
            draw_invoice_pdf(filename, company, inv_no, inv_date, due_date, items, vat_rate, CURRENCY)
            generated_files.append(filename)

        self.status_var.set(f"{len(generated_files)} factures générées dans {os.path.abspath(OUTPUT_DIR)}")
        messagebox.showinfo("Succès", f"{len(generated_files)} factures générées dans\n{os.path.abspath(OUTPUT_DIR)}", parent=self.root)


def main():
    root = tk.Tk()
    InvoiceGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
