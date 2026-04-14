import os
import random
import datetime
import tkinter as tk
from decimal import Decimal
from tkinter import ttk, messagebox

from data import (
    BASE_DIR,
    MAX_INVOICES,
    DEFAULT_MAX_TOTAL_TTC,
    SAMPLE_COMPANIES,
    SAMPLE_Z_PROFILES,
    CURRENCY,
    decimal_round,
    OUTPUT_DIR,
    Z_CAISSE_OUTPUT_DIR,
    RIB_PROVENANCE_LABELS,
    SAMPLE_BANKS_BY_RIB_PROVENANCE,
    RIB_OUTPUT_DIR,
)
from invoice_pdf import (
    ensure_output_dir,
    random_date_between,
    generate_invoice_number,
    generate_items,
    draw_invoice_pdf,
)
from z_caisse_pdf import (
    ensure_z_caisse_output_dir,
    draw_z_caisse_pdf,
)
from rib_pdf import (
    ensure_rib_output_dir,
    draw_rib_pdf,
)


class InvoiceGeneratorApp:
    def __init__(self, root):
        self.root = root; self.root.title("Générateur de factures PDF")
        self._setup_theme()
        self.n_var = tk.IntVar(value=1)
        self.same_company_var = tk.BooleanVar(value=True)
        self.show_company_section_var = tk.BooleanVar(value=False)
        self.custom_amounts_var = tk.BooleanVar(value=False)
        self.custom_dates_var = tk.BooleanVar(value=False)
        self.vat_var = tk.StringVar(value="20")
        self.micro_var = tk.BooleanVar(value=False)
        self.prefix_var = tk.StringVar(value="FAC-")
        self.file_prefix_var = tk.StringVar(value="")
        self.max_total_var = tk.StringVar(value=str(DEFAULT_MAX_TOTAL_TTC))
        self.show_advanced_section_var = tk.BooleanVar(value=True)
        self.company_name_var = tk.StringVar()
        self.company_address_var = tk.StringVar()
        self.company_siret_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.invoice_sections, self._updating_count = [], False
        self.vente_700_var = tk.BooleanVar(value=True)
        self.achat_600_var = tk.BooleanVar(value=False)
        self.z_n_var = tk.IntVar(value=1)
        self.z_company_var = tk.StringVar()
        self.z_profile_var = tk.StringVar(value="BOUTIQUE")
        self.z_date_var = tk.StringVar()
        self.z_caisse_var = tk.StringVar(value="C001")
        self.z_numero_var = tk.StringVar()
        self.z_random_amounts_var = tk.BooleanVar(value=True)
        self.z_tva_mode_var = tk.StringVar(value="1_rate")
        self.z_tva1_var = tk.StringVar(value="20")
        self.z_tva2_var = tk.StringVar(value="10")
        self.z_ecart_var = tk.BooleanVar(value=False)
        self.z_ecart_amount_var = tk.StringVar(value="0.00")
        self.z_paiements_vars = {}

        self.rib_provenance_key_var = tk.StringVar(value="CLIENT")
        self.rib_bank_var = tk.StringVar()
        self.rib_iban_var = tk.StringVar()
        self.rib_bic_var = tk.StringVar()
        self.rib_spaces_var = tk.BooleanVar(value=True)
        self._build_ui()

    def _setup_theme(self):
        self.style = ttk.Style(self.root)
        theme_candidates = [os.path.join(BASE_DIR, "Azure-ttk-theme", "azure.tcl"),
                            os.path.join(BASE_DIR, "azure.tcl")]
        azure_active = False
        for theme_path in theme_candidates:
            if not os.path.exists(theme_path): continue
            try:
                self.root.tk.call("source", theme_path.replace("\\", "/"))
                try: self.root.tk.call("set_theme", "light")
                except Exception: self.root.tk.call("ttk::style", "theme", "use", "azure-light")
                break
            except Exception:
                continue
        try:
            current = self.root.tk.call("ttk::style", "theme", "use")
            azure_active = current in ("azure-light", "azure-dark")
        except Exception:
            azure_active = False

        self.style.configure(".", font=("Segoe UI", 10))
        if azure_active:
            bg = self.style.lookup(".", "background") or self.style.lookup("TFrame", "background") or "#f0f0f0"
            self.root.configure(bg=bg); self.bg_color = bg
        else:
            self.root.configure(bg="#e5e7eb")
            self.style.configure("TFrame", background="#f3f4f6")
            self.style.configure("TLabel", background="#f3f4f6")
            self.style.configure("TCheckbutton", background="#f3f4f6")
            self.style.configure("TLabelframe", background="#ffffff")
            self.style.configure("TLabelframe.Label", background="#ffffff", font=("Segoe UI", 10, "bold"))
            self.bg_color = "#f3f4f6"
        self.style.configure("Accent.TButton", padding=8, font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        padding = {"padx": 10, "pady": 5}
        main_frame = ttk.Frame(self.root); main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1); self.root.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        main_frame.columnconfigure(0, weight=1); main_frame.rowconfigure(0, weight=1)

        invoice_frame = ttk.Frame(notebook)
        notebook.add(invoice_frame, text="Facture")
        self._build_invoice_ui(invoice_frame)

        z_frame = ttk.Frame(notebook)
        notebook.add(z_frame, text="Z de caisse")
        self._build_z_caisse_ui(z_frame)

        rib_frame = ttk.Frame(notebook)
        notebook.add(rib_frame, text="RIB")
        self._build_rib_ui(rib_frame)

    def _build_invoice_ui(self, frame):
        padding = {"padx": 10, "pady": 5}
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Nombre de factures (max 10)").grid(row=0, column=0, sticky="w", **padding)
        self.n_spinbox = ttk.Spinbox(frame, from_=1, to=MAX_INVOICES, textvariable=self.n_var, width=6,
                                     command=self._refresh_invoice_sections)
        self.n_spinbox.grid(row=0, column=1, sticky="w", **padding)
        self.n_var.trace_add("write", lambda *args: self._refresh_invoice_sections())

        type_frame = ttk.LabelFrame(frame, text="Type d'opération")
        type_frame.grid(row=1, column=0, columnspan=2, sticky="ew", **padding)
        ttk.Checkbutton(type_frame, text="Vente (700)", variable=self.vente_700_var).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ttk.Checkbutton(type_frame, text="Achat (600)", variable=self.achat_600_var).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ttk.Checkbutton(
            frame,
            text="Même société pour toutes (aléatoire si pas remplie ou à remplir individuellement)",
            variable=self.same_company_var,
            command=self._toggle_company_fields,
        ).grid(row=2, column=0, columnspan=2, sticky="w", **padding)

        ttk.Checkbutton(
            frame,
            text="Afficher les informations société",
            variable=self.show_company_section_var,
            command=self._toggle_company_section_visibility,
        ).grid(row=3, column=0, columnspan=2, sticky="w", **padding)

        self.company_name_label = ttk.Label(frame, text="Nom société")
        self.company_name_label.grid(row=4, column=0, sticky="w", **padding)
        self.company_name_entry = ttk.Entry(frame, textvariable=self.company_name_var, width=40)
        self.company_name_entry.grid(row=4, column=1, sticky="we", **padding)

        self.company_address_label = ttk.Label(frame, text="Adresse (séparer par ';')")
        self.company_address_label.grid(row=5, column=0, sticky="w", **padding)
        self.company_address_entry = ttk.Entry(frame, textvariable=self.company_address_var, width=40)
        self.company_address_entry.grid(row=5, column=1, sticky="we", **padding)

        self.company_siret_label = ttk.Label(frame, text="SIRET")
        self.company_siret_label.grid(row=6, column=0, sticky="w", **padding)
        self.company_siret_entry = ttk.Entry(frame, textvariable=self.company_siret_var, width=40)
        self.company_siret_entry.grid(row=6, column=1, sticky="we", **padding)

        ttk.Checkbutton(
            frame,
            text="Personnaliser les montants",
            variable=self.custom_amounts_var,
            command=self._update_section_visibility,
        ).grid(row=7, column=0, columnspan=2, sticky="w", **padding)
        ttk.Checkbutton(
            frame,
            text="Personnaliser les dates",
            variable=self.custom_dates_var,
            command=self._update_section_visibility,
        ).grid(row=8, column=0, columnspan=2, sticky="w", **padding)

        ttk.Label(frame, text="TVA (%)").grid(row=9, column=0, sticky="w", **padding)
        self.vat_entry = ttk.Entry(frame, textvariable=self.vat_var, width=10)
        self.vat_entry.grid(row=9, column=1, sticky="w", **padding)

        ttk.Checkbutton(
            frame,
            text="Micro-entreprise (TVA non applicable)",
            variable=self.micro_var,
            command=self._on_micro_toggle,
        ).grid(row=10, column=0, columnspan=2, sticky="w", **padding)

        ttk.Checkbutton(
            frame,
            text="Afficher préfixes et plafond",
            variable=self.show_advanced_section_var,
            command=self._toggle_advanced_section_visibility,
        ).grid(row=11, column=0, columnspan=2, sticky="w", **padding)

        self.prefix_label = ttk.Label(frame, text="Préfixe numéro")
        self.prefix_label.grid(row=12, column=0, sticky="w", **padding)
        self.prefix_entry = ttk.Entry(frame, textvariable=self.prefix_var, width=20)
        self.prefix_entry.grid(row=12, column=1, sticky="w", **padding)

        self.file_prefix_label = ttk.Label(frame, text="Préfixe fichier")
        self.file_prefix_label.grid(row=13, column=0, sticky="w", **padding)
        self.file_prefix_entry = ttk.Entry(frame, textvariable=self.file_prefix_var, width=20)
        self.file_prefix_entry.grid(row=13, column=1, sticky="w", **padding)

        self.max_total_label = ttk.Label(frame, text="Plafond TTC")
        self.max_total_label.grid(row=14, column=0, sticky="w", **padding)
        self.max_total_entry = ttk.Entry(frame, textvariable=self.max_total_var, width=20)
        self.max_total_entry.grid(row=14, column=1, sticky="w", **padding)

        sections_frame = ttk.LabelFrame(frame, text="Détails par facture")
        sections_frame.grid(row=15, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        self.sections_canvas = tk.Canvas(sections_frame, height=260, borderwidth=0, highlightthickness=0)
        try: self.sections_canvas.configure(bg=self.bg_color)
        except Exception: pass
        scrollbar = ttk.Scrollbar(sections_frame, orient="vertical", command=self.sections_canvas.yview)
        self.sections_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y"); self.sections_canvas.pack(side="left", fill="both", expand=True)

        self.invoices_container = ttk.Frame(self.sections_canvas)
        self.invoices_container.bind("<Configure>",
                                     lambda e: self.sections_canvas.configure(
                                         scrollregion=self.sections_canvas.bbox("all")))
        self.sections_canvas.create_window((0, 0), window=self.invoices_container, anchor="nw")

        ttk.Button(frame, text="Générer", style="Accent.TButton",
                   command=self.generate_invoices).grid(row=16, column=0, columnspan=2, pady=15)

        ttk.Label(frame, textvariable=self.status_var, foreground="green").grid(
            row=17, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(15, weight=1)
        self._toggle_company_fields()
        self._toggle_company_section_visibility()
        self._toggle_advanced_section_visibility()
        self._refresh_invoice_sections()

    def _build_z_caisse_ui(self, frame):
        padding = {"padx": 10, "pady": 5}
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Nombre de Z à générer (1-10)").grid(row=0, column=0, sticky="w", **padding)
        ttk.Spinbox(frame, from_=1, to=10, textvariable=self.z_n_var, width=6).grid(row=0, column=1, sticky="w", **padding)

        ttk.Label(frame, text="Établissement").grid(row=1, column=0, sticky="w", **padding)
        company_names = [c["name"] for c in SAMPLE_COMPANIES]
        self.z_company_combo = ttk.Combobox(frame, textvariable=self.z_company_var, values=company_names, width=37, state="readonly")
        self.z_company_combo.grid(row=1, column=1, sticky="w", **padding)
        if company_names:
            self.z_company_var.set(random.choice(company_names))

        ttk.Label(frame, text="Profil").grid(row=2, column=0, sticky="w", **padding)
        profile_combo = ttk.Combobox(frame, textvariable=self.z_profile_var, values=list(SAMPLE_Z_PROFILES.keys()), width=37, state="readonly")
        profile_combo.grid(row=2, column=1, sticky="w", **padding)
        profile_combo.bind("<<ComboboxSelected>>", lambda e: self._update_z_profile_fields())

        ttk.Label(frame, text="Date de clôture (JJ-MM-AAAA)").grid(row=3, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.z_date_var, width=20).grid(row=3, column=1, sticky="w", **padding)

        ttk.Label(frame, text="Numéro de caisse").grid(row=4, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.z_caisse_var, width=20).grid(row=4, column=1, sticky="w", **padding)

        ttk.Label(frame, text="Numéro de Z (préfixe)").grid(row=5, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.z_numero_var, width=20).grid(row=5, column=1, sticky="w", **padding)

        ttk.Checkbutton(frame, text="Montants aléatoires",
                        variable=self.z_random_amounts_var,
                        command=self._update_z_paiements_visibility).grid(row=6, column=0, columnspan=2, sticky="w", **padding)

        tva_frame = ttk.LabelFrame(frame, text="TVA")
        tva_frame.grid(row=7, column=0, columnspan=2, sticky="ew", **padding)
        ttk.Radiobutton(tva_frame, text="TVA normale (1 taux)", variable=self.z_tva_mode_var, value="1_rate",
                        command=self._update_z_tva_fields_visibility).grid(row=0, column=0, sticky="w", padx=10, pady=3)
        ttk.Radiobutton(tva_frame, text="TVA normale (2 taux)", variable=self.z_tva_mode_var, value="2_rates",
                        command=self._update_z_tva_fields_visibility).grid(row=0, column=1, sticky="w", padx=10, pady=3)
        ttk.Radiobutton(tva_frame, text="Sans TVA (0%)", variable=self.z_tva_mode_var, value="no_vat",
                        command=self._update_z_tva_fields_visibility).grid(row=0, column=2, sticky="w", padx=10, pady=3)

        self.z_tva1_label = ttk.Label(frame, text="TVA 1 (%)")
        self.z_tva1_label.grid(row=8, column=0, sticky="w", **padding)
        self.z_tva1_entry = ttk.Entry(frame, textvariable=self.z_tva1_var, width=10)
        self.z_tva1_entry.grid(row=8, column=1, sticky="w", **padding)

        self.z_tva2_label = ttk.Label(frame, text="TVA 2 (%)")
        self.z_tva2_label.grid(row=9, column=0, sticky="w", **padding)
        self.z_tva2_entry = ttk.Entry(frame, textvariable=self.z_tva2_var, width=10)
        self.z_tva2_entry.grid(row=9, column=1, sticky="w", **padding)

        ttk.Checkbutton(frame, text="Écart de caisse (mode test)",
                        variable=self.z_ecart_var).grid(row=10, column=0, columnspan=2, sticky="w", **padding)

        ttk.Label(frame, text="Montant écart").grid(row=11, column=0, sticky="w", **padding)
        ttk.Entry(frame, textvariable=self.z_ecart_amount_var, width=20).grid(row=11, column=1, sticky="w", **padding)

        paiements_frame = ttk.LabelFrame(frame, text="Modes de paiement")
        paiements_frame.grid(row=12, column=0, columnspan=2, sticky="ew", **padding)
        self.z_paiements_container = paiements_frame

        ttk.Button(frame, text="Générer Z de caisse", style="Accent.TButton",
                   command=self.generate_z_caisse).grid(row=13, column=0, columnspan=2, pady=15)

        ttk.Label(frame, textvariable=self.status_var, foreground="green").grid(
            row=14, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        self._update_z_profile_fields()
        self._update_z_tva_fields_visibility()

    def _build_rib_ui(self, frame):
        padding = {"padx": 10, "pady": 5}
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Provenance").grid(row=0, column=0, sticky="w", **padding)
        prov_values = list(RIB_PROVENANCE_LABELS.keys())
        self.rib_prov_combo = ttk.Combobox(
            frame,
            textvariable=self.rib_provenance_key_var,
            values=prov_values,
            width=18,
            state="readonly",
        )
        self.rib_prov_combo.grid(row=0, column=1, sticky="w", **padding)
        self.rib_prov_combo.bind("<<ComboboxSelected>>", lambda e: self._update_rib_bank_choices())

        ttk.Label(frame, text="Banque").grid(row=1, column=0, sticky="w", **padding)
        self.rib_bank_combo = ttk.Combobox(frame, textvariable=self.rib_bank_var, values=[], width=35, state="readonly")
        self.rib_bank_combo.grid(row=1, column=1, sticky="w", **padding)

        ttk.Checkbutton(frame, text="Afficher avec espaces", variable=self.rib_spaces_var, command=self._refresh_rib_display).grid(
            row=2, column=0, columnspan=2, sticky="w", **padding
        )

        ttk.Button(frame, text="Générer un RIB", style="Accent.TButton", command=self.generate_rib).grid(
            row=3, column=0, columnspan=2, pady=(10, 5)
        )

        ttk.Label(frame, text="IBAN").grid(row=4, column=0, sticky="w", **padding)
        self.rib_iban_entry = ttk.Entry(frame, textvariable=self.rib_iban_var, width=44, state="readonly")
        self.rib_iban_entry.grid(row=4, column=1, sticky="w", **padding)
        ttk.Button(frame, text="Copier", command=lambda: self._copy_to_clipboard(self.rib_iban_var.get())).grid(
            row=4, column=2, sticky="w", padx=(0, 10), pady=5
        )

        ttk.Label(frame, text="BIC / SWIFT").grid(row=5, column=0, sticky="w", **padding)
        self.rib_bic_entry = ttk.Entry(frame, textvariable=self.rib_bic_var, width=44, state="readonly")
        self.rib_bic_entry.grid(row=5, column=1, sticky="w", **padding)
        ttk.Button(frame, text="Copier", command=lambda: self._copy_to_clipboard(self.rib_bic_var.get())).grid(
            row=5, column=2, sticky="w", padx=(0, 10), pady=5
        )

        ttk.Button(frame, text="Générer le PDF", style="Accent.TButton", command=self.generate_rib_pdf).grid(
            row=6, column=0, columnspan=2, pady=(15, 5)
        )

        self._update_rib_bank_choices()
        self.generate_rib()

    def _update_rib_bank_choices(self):
        prov = self.rib_provenance_key_var.get() or "CLIENT"
        banks = SAMPLE_BANKS_BY_RIB_PROVENANCE.get(prov, [])
        names = [b.get("name", "") for b in banks if b.get("name")]
        self.rib_bank_combo["values"] = names
        if names:
            if self.rib_bank_var.get() not in names:
                self.rib_bank_var.set(names[0])

    def _copy_to_clipboard(self, text):
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _iban_compact(self, iban):
        return "".join(ch for ch in (iban or "") if ch.isalnum()).upper()

    def _iban_format(self, iban):
        compact = self._iban_compact(iban)
        return " ".join(compact[i:i + 4] for i in range(0, len(compact), 4))

    def _iban_checksum(self, iban):
        compact = self._iban_compact(iban)
        rearranged = compact[4:] + compact[:4]
        digits = ""
        for ch in rearranged:
            if ch.isdigit():
                digits += ch
            else:
                digits += str(ord(ch) - 55)
        return int(digits) % 97

    def _make_fr_iban(self):
        bank_code = "".join(str(random.randint(0, 9)) for _ in range(5))
        branch_code = "".join(str(random.randint(0, 9)) for _ in range(5))
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        account = "".join(random.choice(alphabet) for _ in range(11))
        rib_key = "".join(str(random.randint(0, 9)) for _ in range(2))
        bban = bank_code + branch_code + account + rib_key
        iban_wo_check = f"FR00{bban}"
        check = 98 - self._iban_checksum(iban_wo_check)
        return f"FR{check:02d}{bban}"

    def generate_rib(self):
        prov = self.rib_provenance_key_var.get() or "CLIENT"
        banks = SAMPLE_BANKS_BY_RIB_PROVENANCE.get(prov, [])
        bank = next((b for b in banks if b.get("name") == self.rib_bank_var.get()), None) or (banks[0] if banks else None)
        bic = (bank or {}).get("bic", "BNPAFRPPXXX")
        iban = self._make_fr_iban()
        self.rib_bic_var.set(bic)
        if self.rib_spaces_var.get():
            self.rib_iban_var.set(self._iban_format(iban))
        else:
            self.rib_iban_var.set(self._iban_compact(iban))

    def _refresh_rib_display(self):
        iban = self.rib_iban_var.get()
        if not iban:
            return
        compact = self._iban_compact(iban)
        if self.rib_spaces_var.get():
            self.rib_iban_var.set(self._iban_format(compact))
        else:
            self.rib_iban_var.set(compact)

    def generate_rib_pdf(self):
        prov = self.rib_provenance_key_var.get() or "CLIENT"
        prov_label = RIB_PROVENANCE_LABELS.get(prov, prov)
        bank_name = self.rib_bank_var.get() or "Banque"
        iban = self.rib_iban_var.get()
        bic = self.rib_bic_var.get()
        if not iban or not bic:
            self.generate_rib()
            iban = self.rib_iban_var.get()
            bic = self.rib_bic_var.get()

        ensure_rib_output_dir()
        safe_bank = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in bank_name).strip() or "banque"
        filename = os.path.join(RIB_OUTPUT_DIR, f"RIB_{safe_bank}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        draw_rib_pdf(filename, prov_label, bank_name, iban, bic)
        self.status_var.set(f"RIB généré dans {os.path.abspath(RIB_OUTPUT_DIR)}")
        messagebox.showinfo("Succès", f"RIB PDF généré dans\n{os.path.abspath(os.path.dirname(filename))}", parent=self.root)

    def _update_z_profile_fields(self):
        profile = self.z_profile_var.get()
        if not profile or profile not in SAMPLE_Z_PROFILES:
            return
        profile_data = SAMPLE_Z_PROFILES[profile]
        if self.z_tva_mode_var.get() != "no_vat":
            self.z_tva1_var.set(str(profile_data["tva_rates"][0]))
            if len(profile_data["tva_rates"]) > 1:
                self.z_tva2_var.set(str(profile_data["tva_rates"][1]))
        self._update_z_paiements_visibility()

    def _update_z_paiements_visibility(self):
        for widget in self.z_paiements_container.winfo_children():
            widget.destroy()
        if self.z_random_amounts_var.get():
            return
        profile = self.z_profile_var.get()
        if not profile or profile not in SAMPLE_Z_PROFILES:
            return
        paiements = SAMPLE_Z_PROFILES[profile]["paiements"]
        pad = {"padx": 5, "pady": 2}
        for i, paiement in enumerate(paiements):
            ttk.Label(self.z_paiements_container, text=f"{paiement}:").grid(row=i, column=0, sticky="w", **pad)
            var = tk.StringVar(value="0.00")
            self.z_paiements_vars[paiement] = var
            ttk.Entry(self.z_paiements_container, textvariable=var, width=15).grid(row=i, column=1, sticky="w", **pad)

    def _update_z_tva_fields_visibility(self):
        mode = self.z_tva_mode_var.get()
        if mode == "no_vat":
            self.z_tva1_label.grid_remove()
            self.z_tva1_entry.grid_remove()
            self.z_tva2_label.grid_remove()
            self.z_tva2_entry.grid_remove()
        elif mode == "2_rates":
            self.z_tva1_label.grid()
            self.z_tva1_entry.grid()
            self.z_tva2_label.grid()
            self.z_tva2_entry.grid()
        else:
            self.z_tva1_label.grid()
            self.z_tva1_entry.grid()
            self.z_tva2_label.grid_remove()
            self.z_tva2_entry.grid_remove()

    def _toggle_company_fields(self):
        same = self.same_company_var.get()
        for entry in (self.company_name_entry, self.company_address_entry, self.company_siret_entry):
            entry.state(["!disabled"] if same else ["disabled"])
        self._update_section_visibility()

    def _toggle_company_section_visibility(self):
        visible = self.show_company_section_var.get()
        widgets = (
            self.company_name_label,
            self.company_name_entry,
            self.company_address_label,
            self.company_address_entry,
            self.company_siret_label,
            self.company_siret_entry,
        )
        for w in widgets:
            if visible:
                w.grid()
            else:
                w.grid_remove()

    def _toggle_advanced_section_visibility(self):
        visible = self.show_advanced_section_var.get()
        widgets = (
            self.prefix_label,
            self.prefix_entry,
            self.file_prefix_label,
            self.file_prefix_entry,
            self.max_total_label,
            self.max_total_entry,
        )
        for w in widgets:
            if visible:
                w.grid()
            else:
                w.grid_remove()

    def _on_micro_toggle(self):
        if self.micro_var.get():
            self.vat_var.set("0"); self.vat_entry.state(["disabled"])
        else:
            self.vat_entry.state(["!disabled"])

    def _get_invoice_count(self):
        if self._updating_count:
            try: return int(self.n_var.get())
            except Exception: return 1
        try: n = int(self.n_var.get())
        except Exception: n = 1
        n = max(1, min(MAX_INVOICES, n))
        if self.n_var.get() != n:
            self._updating_count = True; self.n_var.set(n); self._updating_count = False
        return n

    def _create_invoice_section(self, index):
        frame = ttk.LabelFrame(self.invoices_container, text=f"Facture {index}")
        frame.grid(row=index - 1, column=0, sticky="ew", padx=10, pady=6)
        frame.columnconfigure(1, weight=1)
        pad = {"padx": 8, "pady": 2}

        company_name_var = tk.StringVar(); company_address_var = tk.StringVar()
        company_siret_var = tk.StringVar(); amounts_var = tk.StringVar()
        inv_date_var = tk.StringVar(); due_date_var = tk.StringVar()

        company_name_label = ttk.Label(frame, text="Nom société")
        company_name_label.grid(row=0, column=0, sticky="w", **pad)
        company_name_entry = ttk.Entry(frame, textvariable=company_name_var)
        company_name_entry.grid(row=0, column=1, sticky="we", **pad)

        company_address_label = ttk.Label(frame, text="Adresse (séparer par ';')")
        company_address_label.grid(row=1, column=0, sticky="w", **pad)
        company_address_entry = ttk.Entry(frame, textvariable=company_address_var)
        company_address_entry.grid(row=1, column=1, sticky="we", **pad)

        company_siret_label = ttk.Label(frame, text="SIRET")
        company_siret_label.grid(row=2, column=0, sticky="w", **pad)
        company_siret_entry = ttk.Entry(frame, textvariable=company_siret_var)
        company_siret_entry.grid(row=2, column=1, sticky="we", **pad)

        amounts_label = ttk.Label(frame, text="Montants (séparer par ';')")
        amounts_label.grid(row=3, column=0, sticky="w", **pad)
        amounts_entry = ttk.Entry(frame, textvariable=amounts_var)
        amounts_entry.grid(row=3, column=1, sticky="we", **pad)

        inv_date_label = ttk.Label(frame, text="Date facture (JJ-MM-AAAA)")
        inv_date_label.grid(row=4, column=0, sticky="w", **pad)
        inv_date_entry = ttk.Entry(frame, textvariable=inv_date_var)
        inv_date_entry.grid(row=4, column=1, sticky="we", **pad)

        due_date_label = ttk.Label(frame, text="Date échéance (JJ-MM-AAAA)")
        due_date_label.grid(row=5, column=0, sticky="w", **pad)
        due_date_entry = ttk.Entry(frame, textvariable=due_date_var)
        due_date_entry.grid(row=5, column=1, sticky="we", **pad)

        return {
            "frame": frame,
            "company_name_var": company_name_var, "company_address_var": company_address_var,
            "company_siret_var": company_siret_var, "company_name_label": company_name_label,
            "company_name_entry": company_name_entry, "company_address_label": company_address_label,
            "company_address_entry": company_address_entry, "company_siret_label": company_siret_label,
            "company_siret_entry": company_siret_entry, "amounts_label": amounts_label,
            "amounts_var": amounts_var, "amounts_entry": amounts_entry,
            "inv_date_label": inv_date_label, "inv_date_var": inv_date_var,
            "inv_date_entry": inv_date_entry, "due_date_label": due_date_label,
            "due_date_var": due_date_var, "due_date_entry": due_date_entry,
        }

    def _refresh_invoice_sections(self, *args):
        n = self._get_invoice_count()
        while len(self.invoice_sections) > n:
            section = self.invoice_sections.pop(); section["frame"].destroy()
        while len(self.invoice_sections) < n:
            index = len(self.invoice_sections) + 1
            self.invoice_sections.append(self._create_invoice_section(index))
        self._update_section_visibility()

    def _update_section_visibility(self, *args):
        same = self.same_company_var.get()
        custom_amounts = self.custom_amounts_var.get()
        custom_dates = self.custom_dates_var.get()
        for section in self.invoice_sections:
            if same:
                section["company_name_label"].grid_remove()
                section["company_name_entry"].grid_remove()
                section["company_address_label"].grid_remove()
                section["company_address_entry"].grid_remove()
                section["company_siret_label"].grid_remove()
                section["company_siret_entry"].grid_remove()
            else:
                section["company_name_label"].grid()
                section["company_name_entry"].grid()
                section["company_address_label"].grid()
                section["company_address_entry"].grid()
                section["company_siret_label"].grid()
                section["company_siret_entry"].grid()
            if custom_amounts:
                section["amounts_label"].grid()
                section["amounts_entry"].grid()
            else:
                section["amounts_label"].grid_remove()
                section["amounts_entry"].grid_remove()
            if custom_dates:
                section["inv_date_label"].grid()
                section["inv_date_entry"].grid()
                section["due_date_label"].grid()
                section["due_date_entry"].grid()
            else:
                section["inv_date_label"].grid_remove()
                section["inv_date_entry"].grid_remove()
                section["due_date_label"].grid_remove()
                section["due_date_entry"].grid_remove()

    def generate_invoices(self):
        vente = self.vente_700_var.get()
        achat = self.achat_600_var.get()
        if not vente and not achat:
            messagebox.showerror("Erreur", "Veuillez sélectionner au moins un type d'opération (Vente ou Achat).", parent=self.root)
            return

        n = self._get_invoice_count()
        if n > MAX_INVOICES:
            messagebox.showinfo("Information", f"Nombre ajusté à {MAX_INVOICES}.", parent=self.root)
            n = MAX_INVOICES
        try:
            vat_rate = Decimal(self.vat_var.get().replace(",", "."))
        except Exception:
            messagebox.showerror("Erreur", "TVA invalide.", parent=self.root); return
        if self.micro_var.get(): vat_rate = Decimal("0")

        prefix = self.prefix_var.get().strip() or "FAC-"
        file_prefix = self.file_prefix_var.get().strip()
        try:
            max_total_ttc = decimal_round(Decimal(self.max_total_var.get().replace(",", ".")))
        except Exception:
            messagebox.showerror("Erreur", "Plafond TTC invalide.", parent=self.root); return

        vat_multiplier = (Decimal("100") + vat_rate) / Decimal("100") if vat_rate is not None else Decimal("1")
        max_total_ht = decimal_round(max_total_ttc / vat_multiplier) if vat_multiplier != 0 else max_total_ttc

        same_company = self.same_company_var.get()
        if same_company:
            name = self.company_name_var.get().strip()
            if name:
                address = self.company_address_var.get().split(";") if self.company_address_var.get() else []
                comp = {"name": name, "address": [l.strip() for l in address if l.strip()]}
                siret = self.company_siret_var.get().strip()
                if siret: comp["siret"] = siret
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
                    if not name: name = f"Entreprise {i + 1}"
                    address = [l.strip() for l in addr_raw.split(";") if l.strip()]
                    company = {"name": name, "address": address}
                    if siret: company["siret"] = siret
                companies.append(company)

        custom_amounts_per_invoice = [None] * n
        if self.custom_amounts_var.get():
            for i, section in enumerate(self.invoice_sections):
                raw = section["amounts_var"].get()
                if not raw.strip(): continue
                parts = raw.replace(",", ";").split(";")
                values = []
                for part in (p.strip() for p in parts):
                    if not part: continue
                    try:
                        num = decimal_round(Decimal(part))
                    except Exception:
                        messagebox.showerror("Erreur", f"Montant invalide pour la facture {i+1} : {part}", parent=self.root); return
                    if num > 0: values.append(num)
                if values: custom_amounts_per_invoice[i] = values

        invoice_dates, due_dates = [None] * n, [None] * n
        if self.custom_dates_var.get():
            for i, section in enumerate(self.invoice_sections):
                inv_raw = section["inv_date_var"].get().strip()
                due_raw = section["due_date_var"].get().strip()
                if inv_raw:
                    try:
                        invoice_dates[i] = datetime.datetime.strptime(inv_raw, "%d-%m-%Y").date()
                    except Exception:
                        messagebox.showerror("Erreur", f"Date facture invalide pour la facture {i+1}", parent=self.root); return
                if due_raw:
                    try:
                        due_dates[i] = datetime.datetime.strptime(due_raw, "%d-%m-%Y").date()
                    except Exception:
                        messagebox.showerror("Erreur", f"Date échéance invalide pour la facture {i+1}", parent=self.root); return

        ensure_output_dir()
        generated_files = []
        account_types = []
        if vente: account_types.append("700")
        if achat: account_types.append("600")

        for account_type in account_types:
            for i in range(1, n + 1):
                company = companies[i - 1]
                inv_no = generate_invoice_number(prefix, i)
                if invoice_dates[i - 1]:
                    inv_date = invoice_dates[i - 1]
                else:
                    end = datetime.date.today()
                    inv_date = random_date_between(end - datetime.timedelta(days=90), end)
                if due_dates[i - 1]:
                    due_date = due_dates[i - 1]
                else:
                    due_date = inv_date + datetime.timedelta(days=30)

                custom_amts = custom_amounts_per_invoice[i - 1]
                items = generate_items(custom_amounts=custom_amts, max_total_ht=max_total_ht, account_type=account_type)
                if not items: items = generate_items(max_total_ht=max_total_ht, account_type=account_type)

                suffix = "_VENTE" if account_type == "700" else "_ACHAT"
                filename = os.path.join(OUTPUT_DIR, f"{file_prefix}facture_{inv_no}{suffix}.pdf")
                draw_invoice_pdf(filename, company, inv_no, inv_date, due_date, items, vat_rate, CURRENCY,
                                 micro_entrepreneur=self.micro_var.get(), account_type=account_type)
                generated_files.append(filename)

        self.status_var.set(f"{len(generated_files)} factures générées dans {os.path.abspath(OUTPUT_DIR)}")
        messagebox.showinfo("Succès",
                            f"{len(generated_files)} factures générées dans\n{os.path.abspath(OUTPUT_DIR)}",
                            parent=self.root)

    def generate_z_caisse(self):
        n = self.z_n_var.get()
        if n < 1 or n > 10:
            messagebox.showerror("Erreur", "Nombre de Z invalide (1-10).", parent=self.root)
            return

        company_name = self.z_company_var.get()
        if not company_name:
            messagebox.showerror("Erreur", "Veuillez sélectionner un établissement.", parent=self.root)
            return

        company = next((c for c in SAMPLE_COMPANIES if c["name"] == company_name), None)
        if not company:
            company = random.choice(SAMPLE_COMPANIES)

        profile = self.z_profile_var.get()
        if not profile or profile not in SAMPLE_Z_PROFILES:
            messagebox.showerror("Erreur", "Profil invalide.", parent=self.root)
            return

        profile_data = SAMPLE_Z_PROFILES[profile]
        categories = profile_data["categories"]
        paiements = profile_data["paiements"]

        tva_mode = self.z_tva_mode_var.get()
        if tva_mode == "no_vat":
            tva1_rate = Decimal("0")
            tva2_rate = None
        else:
            try:
                tva1_rate = Decimal(self.z_tva1_var.get().replace(",", "."))
                tva2_rate = Decimal(self.z_tva2_var.get().replace(",", ".")) if tva_mode == "2_rates" else None
            except Exception:
                messagebox.showerror("Erreur", "Taux TVA invalide.", parent=self.root)
                return

        z_caisse = self.z_caisse_var.get().strip() or "C001"
        z_prefix = self.z_numero_var.get().strip() or "Z-"

        try:
            ecart = decimal_round(Decimal(self.z_ecart_amount_var.get().replace(",", "."))) if self.z_ecart_var.get() else None
        except Exception:
            ecart = None

        ensure_z_caisse_output_dir()
        generated_files = []

        for i in range(1, n + 1):
            z_date_str = self.z_date_var.get().strip()
            if z_date_str:
                try:
                    z_date = datetime.datetime.strptime(z_date_str, "%d-%m-%Y")
                except Exception:
                    messagebox.showerror("Erreur", f"Date invalide pour Z {i}: {z_date_str}", parent=self.root)
                    return
            else:
                end = datetime.datetime.now()
                z_date = end - datetime.timedelta(days=random.randint(0, 90))

            z_numero = f"{z_prefix}{z_date.strftime('%Y%m%d')}-{i:04d}"

            if self.z_random_amounts_var.get():
                total_ttc = decimal_round(Decimal(random.uniform(500.0, 5000.0)))
                categories_data = {}
                remaining = total_ttc
                for j, cat in enumerate(categories):
                    if j == len(categories) - 1:
                        categories_data[cat] = remaining
                    else:
                        ratio = Decimal(random.uniform(0.1, 0.4))
                        amount = decimal_round(total_ttc * ratio)
                        categories_data[cat] = amount
                        remaining -= amount
                if remaining < 0:
                    categories_data[categories[-1]] = total_ttc - sum(categories_data.values()) + remaining

                paiements_data = {}
                remaining = total_ttc
                for j, paiement in enumerate(paiements):
                    if j == len(paiements) - 1:
                        paiements_data[paiement] = remaining
                    else:
                        ratio = Decimal(random.uniform(0.2, 0.6))
                        amount = decimal_round(total_ttc * ratio)
                        paiements_data[paiement] = amount
                        remaining -= amount
                if remaining < 0:
                    paiements_data[paiements[-1]] = total_ttc - sum(paiements_data.values()) + remaining
            else:
                categories_data = {}
                for cat in categories:
                    categories_data[cat] = Decimal("0.00")
                paiements_data = {}
                total_ttc = Decimal("0.00")
                for paiement in paiements:
                    var = self.z_paiements_vars.get(paiement)
                    if var:
                        try:
                            amount = decimal_round(Decimal(var.get().replace(",", ".")))
                            paiements_data[paiement] = amount
                            total_ttc += amount
                        except Exception:
                            paiements_data[paiement] = Decimal("0.00")
                    else:
                        paiements_data[paiement] = Decimal("0.00")

                if total_ttc > 0:
                    for j, cat in enumerate(categories):
                        ratio = Decimal("1.0") / Decimal(len(categories))
                        categories_data[cat] = decimal_round(total_ttc * ratio)
                else:
                    for cat in categories:
                        categories_data[cat] = Decimal("0.00")

            if tva_mode == "no_vat":
                total_ht = total_ttc
                tva1 = Decimal("0.00")
                totals = {
                    "ht": total_ht,
                    "tva1": tva1,
                    "tva1_rate": Decimal("0"),
                    "ttc": total_ttc,
                    "no_vat": True
                }
            elif tva2_rate is not None:
                ratio_tva1 = Decimal("0.7")
                ratio_tva2 = Decimal("0.3")
                base_ht_tva1 = decimal_round(total_ttc / (Decimal("1") + tva1_rate / Decimal("100")) * ratio_tva1)
                base_ht_tva2 = decimal_round(total_ttc / (Decimal("1") + tva2_rate / Decimal("100")) * ratio_tva2)
                tva1 = decimal_round(base_ht_tva1 * tva1_rate / Decimal("100"))
                tva2 = decimal_round(base_ht_tva2 * tva2_rate / Decimal("100"))
                total_ht = base_ht_tva1 + base_ht_tva2
                total_ttc_recalc = decimal_round(total_ht + tva1 + tva2)
                diff = total_ttc - total_ttc_recalc
                if diff != 0:
                    tva1 = decimal_round(tva1 + diff / Decimal("2"))
                    tva2 = decimal_round(tva2 + diff / Decimal("2"))
                    total_ht = decimal_round(total_ttc - tva1 - tva2)
                totals = {
                    "ht": total_ht,
                    "tva1": tva1,
                    "tva1_rate": tva1_rate,
                    "tva2": tva2,
                    "tva2_rate": tva2_rate,
                    "ttc": total_ttc,
                    "no_vat": False
                }
            else:
                total_ht = decimal_round(total_ttc / (Decimal("1") + tva1_rate / Decimal("100")))
                tva1 = decimal_round(total_ttc - total_ht)
                totals = {
                    "ht": total_ht,
                    "tva1": tva1,
                    "tva1_rate": tva1_rate,
                    "ttc": total_ttc,
                    "no_vat": False
                }

            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in company["name"])
            filename = os.path.join(Z_CAISSE_OUTPUT_DIR, f"Z_{safe_name}_{z_date.strftime('%Y%m%d')}_{z_numero.replace('-', '_')}.pdf")
            draw_z_caisse_pdf(filename, company, z_date, z_caisse, z_numero, categories_data, paiements_data, totals, ecart)
            generated_files.append(filename)

        self.status_var.set(f"{len(generated_files)} Z de caisse générés dans {os.path.abspath(Z_CAISSE_OUTPUT_DIR)}")
        messagebox.showinfo("Succès",
                            f"{len(generated_files)} Z de caisse générés dans\n{os.path.abspath(Z_CAISSE_OUTPUT_DIR)}",
                            parent=self.root)

def main():
    root = tk.Tk()
    InvoiceGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
