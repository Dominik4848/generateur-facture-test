import os
import random
import datetime
import tkinter as tk
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk
from typing import Callable, Optional

from data import (
    BASE_DIR,
    MAX_INVOICES,
    DEFAULT_MAX_TOTAL_TTC,
    SAMPLE_COMPANIES,
    SAMPLE_CLIENTS,
    SAMPLE_Z_PROFILES,
    CURRENCY,
    decimal_round,
    OUTPUT_DIR,
    Z_CAISSE_OUTPUT_DIR,
    RIB_OUTPUT_DIR,
    TEMPLATES_PATH,
    RIB_PROVENANCE_LABELS,
    SAMPLE_BANKS_BY_RIB_PROVENANCE,
    ITEM_DESCRIPTIONS_BY_ACCOUNT,
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
from templates import TABS as TEMPLATE_TABS, TemplateStore
import theme_perf


MAX_Z = 10
LABEL_WIDTH = 22
DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y")
RANDOM_COMPANY_LABEL = "Au hasard"
NO_TEMPLATE_LABEL = "Aucun modèle enregistré"
# Défilement : un cran de molette = SCROLL_STEPS_PER_NOTCH × SCROLL_STEP_PX pixels.
SCROLL_STEP_PX = 20
SCROLL_STEPS_PER_NOTCH = 3
SCROLL_BATCH_MS = 15

# Les deux parties d'une facture, personnalisables de la même façon.
# (clé, titre de section, libellés des 3 modes, pool aléatoire, nom par défaut)
PARTIES = (
    ("company", "Société émettrice", ("Au hasard", "La même pour toutes", "Une par facture"),
     SAMPLE_COMPANIES, "Entreprise"),
    ("client", "Client / tiers", ("Au hasard", "Le même pour toutes", "Un par facture"),
     SAMPLE_CLIENTS, "Client"),
)

COLOR_HINT = "#6b7280"
COLOR_ERROR = "#dc2626"
COLOR_OK = "#15803d"
COLOR_ACCENT = "#005fb8"


# ----------------------------------------------------------------------
# Parsing / validation
# ----------------------------------------------------------------------

def parse_decimal(raw):
    text = (raw or "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(raw)
    if not value.is_finite():
        raise ValueError(raw)
    return value


def parse_date(raw):
    text = (raw or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(raw)


def parse_rate_list(raw):
    """Taux de TVA séparés par ';', sans doublon, dans l'ordre saisi."""
    rates = []
    for part in (raw or "").split(";"):
        if not part.strip():
            continue
        try:
            rate = parse_decimal(part)
        except ValueError:
            raise ValueError(part.strip())
        if not 0 <= rate <= 100:
            raise ValueError(part.strip())
        if rate not in rates:
            rates.append(rate)
    return rates


def parse_count(raw, max_value):
    try:
        n = int(str(raw).strip())
    except ValueError:
        return None
    return n if 1 <= n <= max_value else None


def check_count(max_value):
    def check(raw):
        return None if parse_count(raw, max_value) else f"Entre 1 et {max_value}"
    return check


def check_decimal(min_value=None, max_value=None, allow_empty=False, non_zero=False):
    def check(raw):
        if not raw.strip():
            return None if allow_empty else "Champ obligatoire"
        try:
            value = parse_decimal(raw)
        except ValueError:
            return "Nombre invalide"
        if min_value is not None and value < min_value:
            return f"Doit être ≥ {min_value}"
        if max_value is not None and value > max_value:
            return f"Doit être ≤ {max_value}"
        if non_zero and value == 0:
            return "Doit être différent de 0"
        return None
    return check


def check_date(raw):
    if not raw.strip():
        return None
    try:
        parse_date(raw)
    except ValueError:
        return "Date invalide (format JJ-MM-AAAA)"
    return None


def check_rates(raw):
    try:
        rates = parse_rate_list(raw)
    except ValueError as exc:
        return f"Taux invalide : « {exc.args[0]} »"
    if len(rates) < 2:
        return "Saisis au moins deux taux séparés par ;"
    return None


def format_rate(rate):
    return f"{rate.normalize():f}".replace(".", ",") + " %"


def safe_filename(name, fallback="document"):
    cleaned = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name).strip()
    return cleaned or fallback


def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{base}_{i}{ext}"):
        i += 1
    return f"{base}_{i}{ext}"


def plural(n, singular, plural_form):
    return singular if n == 1 else plural_form


# ----------------------------------------------------------------------
# Widgets
# ----------------------------------------------------------------------

@dataclass
class Field:
    """Champ validé en direct : l'erreur s'affiche en rouge à droite du champ."""
    name: str
    var: tk.Variable
    widget: tk.Widget
    error_label: ttk.Label
    check: Callable[[str], Optional[str]]
    is_active: Callable[[], bool]
    on_error: Optional[Callable[[], None]] = None
    focus_widget: Optional[Callable[[], tk.Widget]] = None

    def error(self):
        if not self.is_active():
            return None
        return self.check(str(self.var.get()))

    def refresh(self):
        err = self.error()
        if self.error_label.winfo_exists():
            self.error_label.configure(text=err or "")
        return err


@dataclass
class PartyInputs:
    name_var: tk.StringVar
    address_var: tk.StringVar
    siret_var: tk.StringVar
    rows: list


@dataclass
class LineInputs:
    desc_var: tk.StringVar
    qty_var: tk.StringVar
    unit_var: tk.StringVar
    vat_var: tk.StringVar
    widgets: list
    vat_combo: ttk.Combobox
    field: Optional[Field] = None


@dataclass
class InvoiceCard:
    index: int
    frame: ttk.LabelFrame
    parties: dict
    lines_box: ttk.Frame
    lines: list
    actions: ttk.Frame
    copy_button: Optional[ttk.Button]
    inv_date_var: tk.StringVar
    due_date_var: tk.StringVar
    date_rows: list
    fields: list


class ScrollableFrame(ttk.Frame):
    """Zone défilante verticale ; le contenu suit la largeur de la fenêtre."""

    def __init__(self, parent, bg):
        super().__init__(parent)
        self.canvas = tk.Canvas(
            self, borderwidth=0, highlightthickness=0, bg=bg, yscrollincrement=SCROLL_STEP_PX,
        )
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._refresh_pending = None
        self._scroll_pending = None
        self._pending_delta = 0
        self.body = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self._update_scrollregion())
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)
        self._update_scrollregion()

    def refresh(self):
        """À appeler après avoir affiché/masqué du contenu : si la vue est sous la nouvelle
        fin du contenu, Tk ne redimensionne pas la zone et <Configure> ne se déclenche pas."""
        if self._refresh_pending is None:
            # Un délai plutôt qu'after_idle : grid recalcule les tailles en tâche idle,
            # il faut passer après lui pour lire la nouvelle hauteur.
            self._refresh_pending = self.after(15, self._update_scrollregion)

    def _update_scrollregion(self):
        self._refresh_pending = None
        content_height = self.body.winfo_reqheight()
        view_height = self.canvas.winfo_height()
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), content_height))
        if content_height <= view_height:
            self.vbar.grid_remove()
            self.canvas.yview_moveto(0)
        else:
            self.vbar.grid()
            # Si le contenu a raccourci, on évite de rester positionné dans le vide.
            if self.canvas.canvasy(0) + view_height > content_height:
                self.canvas.yview_moveto((content_height - view_height) / content_height)

    def can_scroll(self):
        return self.canvas.yview() != (0.0, 1.0)

    def scroll(self, delta):
        """Les crans de molette sont cumulés puis appliqués en une fois : redessiner les widgets
        du thème est lent, et un redessin par cran accumulerait du retard."""
        if not self.can_scroll():
            return
        self._pending_delta += delta
        if self._scroll_pending is None:
            self._scroll_pending = self.after(SCROLL_BATCH_MS, self._apply_scroll)

    def _apply_scroll(self):
        self._scroll_pending = None
        # Le reste (pavé tactile : petits deltas) est gardé pour l'événement suivant.
        steps = int(self._pending_delta / 120 * SCROLL_STEPS_PER_NOTCH)
        self._pending_delta -= steps * 120 / SCROLL_STEPS_PER_NOTCH
        if steps:
            self.canvas.yview_scroll(-steps, "units")

    def scroll_to(self, widget):
        self.update_idletasks()
        total = self.body.winfo_height()
        if total <= 0:
            return
        y = widget.winfo_rooty() - self.body.winfo_rooty()
        visible_top = self.canvas.canvasy(0)
        visible_bottom = visible_top + self.canvas.winfo_height()
        if visible_top <= y <= visible_bottom - widget.winfo_height():
            return
        self.canvas.yview_moveto(max(0, y - 40) / total)


# ----------------------------------------------------------------------
# Application
# ----------------------------------------------------------------------

class InvoiceGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Générateur de documents de test")
        icon_path = os.path.join(BASE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(default=icon_path)
            except tk.TclError:
                pass
        self._setup_theme()

        # Factures
        self.n_var = tk.StringVar(value="1")
        self.vente_700_var = tk.BooleanVar(value=True)
        self.achat_600_var = tk.BooleanVar(value=False)
        self.party_modes = {key: tk.StringVar(value="random") for key, *_ in PARTIES}
        self.party_single: dict[str, PartyInputs] = {}
        self.vat_mode_var = tk.StringVar(value="single")
        self.vat_var = tk.StringVar(value="20")
        self.vat_multi_var = tk.StringVar(value="20 ; 10 ; 5,5")
        self.micro_var = tk.BooleanVar(value=False)
        self._vat_before_micro = "20"
        self.custom_lines_var = tk.BooleanVar(value=False)
        self.custom_dates_var = tk.BooleanVar(value=False)
        self.prefix_var = tk.StringVar(value="FAC-")
        self.file_prefix_var = tk.StringVar(value="")
        self.max_total_var = tk.StringVar(value=str(DEFAULT_MAX_TOTAL_TTC))
        self.advanced_open = False
        self.invoice_cards: list[InvoiceCard] = []

        # Z de caisse
        self.z_profile_by_label = {key.capitalize(): key for key in SAMPLE_Z_PROFILES}
        self.z_n_var = tk.StringVar(value="1")
        self.z_company_var = tk.StringVar(value=RANDOM_COMPANY_LABEL)
        self.z_profile_var = tk.StringVar(value=next(iter(self.z_profile_by_label)))
        self.z_date_var = tk.StringVar()
        self.z_caisse_var = tk.StringVar(value="C001")
        self.z_numero_var = tk.StringVar(value="Z-")
        self.z_random_amounts_var = tk.BooleanVar(value=True)
        self.z_tva_mode_var = tk.StringVar(value="1_rate")
        self.z_tva1_var = tk.StringVar(value="20")
        self.z_tva2_var = tk.StringVar(value="10")
        self.z_ecart_var = tk.BooleanVar(value=False)
        self.z_ecart_amount_var = tk.StringVar(value="-5,00")
        self.z_paiements_vars: dict[str, tk.StringVar] = {}
        self.z_payment_fields: list[Field] = []

        # RIB
        self.rib_key_by_label = {label: key for key, label in RIB_PROVENANCE_LABELS.items()}
        self.rib_provenance_var = tk.StringVar(value=RIB_PROVENANCE_LABELS["CLIENT"])
        self.rib_bank_var = tk.StringVar()
        self.rib_iban_var = tk.StringVar()
        self.rib_bic_var = tk.StringVar()
        self.rib_spaces_var = tk.BooleanVar(value=True)

        # Variables simples enregistrées dans les modèles, par onglet.
        self.template_vars: dict[str, dict[str, tk.Variable]] = {
            "facture": {
                "n": self.n_var, "vente_700": self.vente_700_var, "achat_600": self.achat_600_var,
                **{f"{party}_mode": var for party, var in self.party_modes.items()},
                "vat_mode": self.vat_mode_var, "vat": self.vat_var, "vat_multi": self.vat_multi_var,
                "micro": self.micro_var, "custom_lines": self.custom_lines_var,
                "custom_dates": self.custom_dates_var, "prefix": self.prefix_var,
                "file_prefix": self.file_prefix_var, "max_total": self.max_total_var,
            },
            "z": {
                "n": self.z_n_var, "company": self.z_company_var, "profile": self.z_profile_var,
                "date": self.z_date_var, "caisse": self.z_caisse_var, "numero": self.z_numero_var,
                "random_amounts": self.z_random_amounts_var, "tva_mode": self.z_tva_mode_var,
                "tva1": self.z_tva1_var, "tva2": self.z_tva2_var, "ecart": self.z_ecart_var,
                "ecart_amount": self.z_ecart_amount_var,
            },
            "rib": {
                "provenance": self.rib_provenance_var, "bank": self.rib_bank_var, "iban": self.rib_iban_var,
                "bic": self.rib_bic_var, "spaces": self.rib_spaces_var,
            },
        }
        self.template_store = TemplateStore(TEMPLATES_PATH)
        self.template_name_vars = {tab: tk.StringVar() for tab in TEMPLATE_TABS}
        self.template_combos: dict[str, ttk.Combobox] = {}
        self.template_delete_buttons: dict[str, ttk.Button] = {}

        self.fields: dict[str, list[Field]] = {"facture": [], "z": [], "rib": []}
        self.status_labels: dict[str, ttk.Label] = {}
        self.scrolls: dict[str, ScrollableFrame] = {}
        self._build_ui()

        # Valeurs de départ, pour « Réinitialiser » ; le RIB en reprend un nouveau au hasard.
        self.default_states = {tab: self._capture_state(tab) for tab in TEMPLATE_TABS}
        for name in ("iban", "bic"):
            self.default_states["rib"].pop(name)
        self._restore_last_session()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Thème et structure générale
    # ------------------------------------------------------------------

    def _setup_theme(self):
        self.style = ttk.Style(self.root)
        theme_candidates = [
            os.path.join(BASE_DIR, "Azure-ttk-theme", "azure.tcl"),
            os.path.join(BASE_DIR, "azure.tcl"),
        ]
        theme_perf.install(self.root)
        for theme_path in theme_candidates:
            if not os.path.exists(theme_path):
                continue
            try:
                self.root.tk.call("source", theme_path.replace("\\", "/"))
                try:
                    self.root.tk.call("set_theme", "light")
                except Exception:
                    self.root.tk.call("ttk::style", "theme", "use", "azure-light")
                break
            except Exception:
                continue
        theme_perf.uninstall(self.root)

        azure_active = False
        try:
            current = self.root.tk.call("ttk::style", "theme", "use")
            azure_active = current in ("azure-light", "azure-dark")
        except Exception:
            azure_active = False

        self.style.configure(".", font=("Segoe UI", 10))
        if azure_active:
            bg = (
                self.style.lookup(".", "background")
                or self.style.lookup("TFrame", "background")
                or "#f0f0f0"
            )
            self.root.configure(bg=bg)
            self.bg_color = bg
        else:
            self.root.configure(bg="#e5e7eb")
            self.style.configure("TFrame", background="#f3f4f6")
            self.style.configure("TLabel", background="#f3f4f6")
            self.style.configure("TCheckbutton", background="#f3f4f6")
            self.style.configure("TRadiobutton", background="#f3f4f6")
            self.style.configure("TLabelframe", background="#f3f4f6")
            self.style.configure("TLabelframe.Label", background="#f3f4f6")
            self.bg_color = "#f3f4f6"

        self.style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        self.style.configure("Accent.TButton", padding=(16, 6), font=("Segoe UI", 10, "bold"))
        self.style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        self.style.configure("Error.TLabel", foreground=COLOR_ERROR, font=("Segoe UI", 9))
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 9, "bold"), foreground=COLOR_HINT)
        self.style.configure("Link.TLabel", foreground=COLOR_ACCENT, font=("Segoe UI", 10, "bold"))

        # La molette fait défiler la page plutôt que de changer la valeur
        # des listes déroulantes et compteurs survolés.
        for widget_class in ("TCombobox", "TSpinbox"):
            self.root.unbind_class(widget_class, "<MouseWheel>")

    def _build_ui(self):
        self.root.geometry("860x780")
        self.root.minsize(700, 560)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(18, 14, 18, 4))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Générateur de documents de test", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6, 12))

        self._build_invoice_ui()
        self._build_z_caisse_ui()
        self._build_rib_ui()

        self.root.bind("<Control-Return>", self._on_generate_shortcut)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_generate_shortcut(self, _event=None):
        actions = (self.generate_invoices, self.generate_z_caisse, self.generate_rib_pdf)
        actions[self.notebook.index("current")]()
        return "break"

    def _on_mousewheel(self, event):
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            # Widget interne à Tk (ex. liste ouverte d'une combobox) : on le laisse gérer.
            return
        while widget is not None:
            if isinstance(widget, ScrollableFrame):
                widget.scroll(event.delta)
                return
            widget = widget.master

    def _make_tab(self, key, title, generate_text, generate_command, folder):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=f"  {title}  ")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        self._build_template_bar(tab, key)
        ttk.Separator(tab).grid(row=1, column=0, sticky="ew")

        scroll = ScrollableFrame(tab, self.bg_color)
        scroll.grid(row=2, column=0, sticky="nsew")
        scroll.body.columnconfigure(0, weight=1)
        self.scrolls[key] = scroll

        ttk.Separator(tab).grid(row=3, column=0, sticky="ew")
        bar = ttk.Frame(tab, padding=(14, 10))
        bar.grid(row=4, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)

        status = ttk.Label(bar, text="", justify="left")
        status.grid(row=0, column=0, sticky="w")
        ttk.Button(bar, text="Ouvrir le dossier", command=lambda: self._open_folder(key, folder)).grid(
            row=0, column=1, padx=(10, 8)
        )
        ttk.Button(bar, text=generate_text, style="Accent.TButton", command=generate_command).grid(
            row=0, column=2
        )
        bar.bind("<Configure>", lambda e: status.configure(wraplength=max(200, e.width - 380)))
        self.status_labels[key] = status
        return scroll.body

    def _section(self, parent, row, title):
        section = ttk.LabelFrame(parent, text=title, padding=(12, 6, 12, 10))
        section.grid(row=row, column=0, sticky="ew", padx=14, pady=(10, 0))
        section.columnconfigure(2, weight=1)
        return section

    def _add_field(
        self, registry, parent, row, label, var, check=None, width=24,
        is_active=None, widget=None, name=None, on_error=None,
    ):
        """Ligne libellé / champ / erreur. Retourne (widgets de la ligne, Field ou None)."""
        label_widget = ttk.Label(parent, text=label, width=LABEL_WIDTH)
        label_widget.grid(row=row, column=0, sticky="w", pady=3)
        entry = widget or ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=1, sticky="w", pady=3)
        error_label = ttk.Label(parent, text="", style="Error.TLabel")
        error_label.grid(row=row, column=2, sticky="w", padx=(10, 0))
        row_widgets = [label_widget, entry, error_label]

        field = None
        if check is not None:
            field = Field(
                name=name or label, var=var, widget=entry, error_label=error_label,
                check=check, is_active=is_active or (lambda: True), on_error=on_error,
            )
            var.trace_add("write", lambda *args: field.refresh())
            if registry is not None:
                registry.append(field)
        return row_widgets, field

    def _show(self, widgets, visible):
        for w in widgets:
            if visible:
                w.grid()
            else:
                w.grid_remove()
        for scroll in self.scrolls.values():
            scroll.refresh()

    def _set_status(self, key, text, kind="info"):
        colors = {"ok": COLOR_OK, "error": COLOR_ERROR, "info": COLOR_HINT}
        self.status_labels[key].configure(text=text, foreground=colors[kind])

    def _validate(self, key, fields):
        for f in fields:
            err = f.refresh()
            if err:
                if f.on_error:
                    f.on_error()
                self._set_status(key, f"✗ {f.name} : {err}", "error")
                target = f.focus_widget() if f.focus_widget else f.widget
                self.scrolls[key].scroll_to(target)
                target.focus_set()
                return False
        return True

    def _open_folder(self, key, folder):
        try:
            os.makedirs(folder, exist_ok=True)
            os.startfile(folder)
        except OSError as exc:
            self._set_status(key, f"✗ Impossible d'ouvrir le dossier : {exc}", "error")

    def _write_error(self, key, exc, done_count):
        done = f" ({done_count} {plural(done_count, 'fichier créé', 'fichiers créés')} avant l'erreur)" if done_count else ""
        if isinstance(exc, PermissionError):
            name = os.path.basename(exc.filename or "") or "le fichier"
            msg = f"✗ Impossible d'écrire {name} : il est peut-être ouvert dans un lecteur PDF.{done}"
        else:
            msg = f"✗ Erreur lors de l'écriture : {exc}{done}"
        self._set_status(key, msg, "error")

    def _busy(self, busy):
        self.root.configure(cursor="watch" if busy else "")
        self.root.update_idletasks()

    # ------------------------------------------------------------------
    # Modèles et dernière session
    # ------------------------------------------------------------------

    def _build_template_bar(self, tab, key):
        bar = ttk.Frame(tab, padding=(14, 8))
        bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(bar, text="Modèle").pack(side="left", padx=(0, 8))
        combo = ttk.Combobox(bar, textvariable=self.template_name_vars[key], state="readonly", width=32)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda e: self._load_template(key))
        ttk.Button(bar, text="Enregistrer…", command=lambda: self._save_template(key)).pack(
            side="left", padx=(8, 0)
        )
        delete = ttk.Button(bar, text="Supprimer", command=lambda: self._delete_template(key))
        delete.pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Réinitialiser", command=lambda: self._reset_tab(key)).pack(side="right")
        self.template_combos[key] = combo
        self.template_delete_buttons[key] = delete
        self._refresh_template_choices(key)

    def _selected_template(self, key):
        name = self.template_name_vars[key].get()
        return name if name in self.template_store.templates[key] else None

    def _refresh_template_choices(self, key, selected=None):
        names = self.template_store.names(key)
        combo, var = self.template_combos[key], self.template_name_vars[key]
        combo.configure(values=names)
        if names:
            combo.state(["!disabled"])
            var.set(selected if selected in names else "")
        else:
            combo.state(["disabled"])
            var.set(NO_TEMPLATE_LABEL)
        self.template_delete_buttons[key].state(["!disabled"] if selected in names else ["disabled"])

    def _load_template(self, key):
        name = self._selected_template(key)
        if name is None:
            return
        self.template_delete_buttons[key].state(["!disabled"])
        if self._apply_state(key, self.template_store.get(key, name)):
            self._set_status(key, f"Modèle « {name} » chargé.", "info")
        else:
            self._set_status(key, f"✗ Le modèle « {name} » est illisible ou incomplet.", "error")

    def _save_template(self, key):
        current = self._selected_template(key)
        name = self._ask_template_name(current or "")
        if name is None:
            return
        # Réenregistrer le modèle chargé le met à jour ; écraser un autre modèle demande confirmation.
        if name != current and name in self.template_store.templates[key] and not messagebox.askyesno(
            "Modèle existant", f"Le modèle « {name} » existe déjà. Le remplacer ?", parent=self.root,
        ):
            return
        try:
            self.template_store.save(key, name, self._capture_state(key))
        except OSError as exc:
            self._set_status(key, f"✗ Impossible d'enregistrer le modèle : {exc}", "error")
            return
        self._refresh_template_choices(key, name)
        self._set_status(key, f"✓ Modèle « {name} » enregistré.", "ok")

    def _delete_template(self, key):
        name = self._selected_template(key)
        if name is None or not messagebox.askyesno(
            "Supprimer le modèle", f"Supprimer le modèle « {name} » ?", parent=self.root,
        ):
            return
        try:
            self.template_store.delete(key, name)
        except OSError as exc:
            self._set_status(key, f"✗ Impossible de supprimer le modèle : {exc}", "error")
            return
        self._refresh_template_choices(key)
        self._set_status(key, f"Modèle « {name} » supprimé.", "info")

    def _reset_tab(self, key):
        self._apply_state(key, self.default_states[key])
        self._refresh_template_choices(key)
        self._set_status(key, "Champs remis aux valeurs par défaut.", "info")

    def _ask_template_name(self, initial):
        """Petite fenêtre modale qui demande un nom ; None si annulée."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Enregistrer le modèle")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_color)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Nom du modèle").pack(anchor="w")
        name_var = tk.StringVar(value=initial)
        entry = ttk.Entry(frame, textvariable=name_var, width=40)
        entry.pack(fill="x", pady=(4, 2))
        ttk.Label(
            frame, text="Les champs actuels de l'onglet seront enregistrés sous ce nom.", foreground=COLOR_HINT,
        ).pack(anchor="w", pady=(0, 12))
        buttons = ttk.Frame(frame)
        buttons.pack(anchor="e")
        result = {}

        def confirm(_event=None):
            name = name_var.get().strip()
            if not name:
                dialog.bell()
                return
            result["name"] = name
            dialog.destroy()

        ttk.Button(buttons, text="Annuler", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Enregistrer", style="Accent.TButton", command=confirm).pack(
            side="right", padx=(0, 8)
        )
        dialog.bind("<Return>", confirm)
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_reqwidth()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_reqheight()) // 3
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        entry.select_range(0, "end")
        entry.focus_set()
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result.get("name")

    def _restore_last_session(self):
        for key, state in self.template_store.last_session.items():
            self._apply_state(key, state)
        if self.template_store.backup_name:
            self._set_status(
                "facture",
                f"⚠ {os.path.basename(TEMPLATES_PATH)} était illisible : il a été mis de côté sous "
                f"« {self.template_store.backup_name} ».",
                "error",
            )

    def _on_close(self):
        try:
            self.template_store.save_session({key: self._capture_state(key) for key in TEMPLATE_TABS})
        except OSError:
            pass  # Ne jamais empêcher la fermeture pour une sauvegarde de confort.
        finally:
            self.root.destroy()

    # Lecture / écriture de l'état des onglets ---------------------------

    def _capture_state(self, key):
        state = {name: var.get() for name, var in self.template_vars[key].items()}
        if key == "facture":
            n = self._invoice_count() or len(self.invoice_cards)
            state["vat_before_micro"] = self._vat_before_micro
            state["advanced_open"] = self.advanced_open
            state["party_single"] = {party: self._party_state(inputs) for party, inputs in self.party_single.items()}
            state["cards"] = [
                {
                    "parties": {party: self._party_state(inputs) for party, inputs in card.parties.items()},
                    "lines": [
                        [v.get() for v in (line.desc_var, line.qty_var, line.unit_var, line.vat_var)]
                        for line in card.lines
                    ],
                    "inv_date": card.inv_date_var.get(),
                    "due_date": card.due_date_var.get(),
                }
                for card in self.invoice_cards[:n]
            ]
        elif key == "z":
            state["paiements"] = {paiement: var.get() for paiement, var in self.z_paiements_vars.items()}
        return state

    def _apply_state(self, key, state):
        """Remplit l'onglet avec un état enregistré ; False si l'état est illisible."""
        appliers = {"facture": self._apply_invoice_state, "z": self._apply_z_state, "rib": self._apply_rib_state}
        try:
            appliers[key](state)
        except (AttributeError, KeyError, TypeError, ValueError, tk.TclError):
            return False
        return True

    def _set_vars(self, key, state):
        """Variables simples ; une clé absente (ancien modèle) garde la valeur actuelle."""
        for name, var in self.template_vars[key].items():
            if name in state:
                value = state[name]
                var.set(bool(value) if isinstance(var, tk.BooleanVar) else str(value))

    @staticmethod
    def _party_state(inputs):
        return {"name": inputs.name_var.get(), "address": inputs.address_var.get(), "siret": inputs.siret_var.get()}

    @staticmethod
    def _set_party_state(inputs, state):
        for name, var in (("name", inputs.name_var), ("address", inputs.address_var), ("siret", inputs.siret_var)):
            var.set(str(state.get(name, "")))

    def _apply_invoice_state(self, state):
        # Le nombre de factures crée les cartes manquantes ; les taux de TVA passent avant les lignes.
        self._set_vars("facture", state)
        self._vat_before_micro = str(state.get("vat_before_micro", self._vat_before_micro))
        party_single = state.get("party_single", {})
        for party, inputs in self.party_single.items():
            self._set_party_state(inputs, party_single.get(party, {}))
        cards = state.get("cards", [])
        # Les cartes absentes du modèle sont vidées : le modèle remplace toute la saisie.
        for i, card in enumerate(self.invoice_cards):
            data = cards[i] if i < len(cards) else {}
            parties = data.get("parties", {})
            for party, inputs in card.parties.items():
                self._set_party_state(inputs, parties.get(party, {}))
            card.inv_date_var.set(str(data.get("inv_date", "")))
            card.due_date_var.set(str(data.get("due_date", "")))
            for line in list(card.lines):
                self._remove_line(card, line)
            for values in data.get("lines") or [[]]:
                values = [str(v) for v in values][:4]
                self._add_line(card, tuple(values + [""] * (4 - len(values))))
        self._set_advanced_open(bool(state.get("advanced_open", self.advanced_open)))
        self._on_party_mode_change()
        self._update_vat_fields()

    def _apply_z_state(self, state):
        # Le type de commerce est posé sans _on_z_profile_change : les taux du modèle sont gardés.
        self._set_vars("z", state)
        if self.z_company_var.get() not in {c["name"] for c in SAMPLE_COMPANIES}:
            self.z_company_var.set(RANDOM_COMPANY_LABEL)
        if self._z_profile_key() is None:
            self.z_profile_var.set(next(iter(self.z_profile_by_label)))
        for paiement, amount in dict(state.get("paiements", {})).items():
            self.z_paiements_vars.setdefault(paiement, tk.StringVar()).set(str(amount))
        self._update_z_paiements()
        self._update_z_tva_fields_visibility()
        self._update_z_ecart_state()

    def _apply_rib_state(self, state):
        self._set_vars("rib", state)
        if self.rib_provenance_var.get() not in self.rib_key_by_label:
            self.rib_provenance_var.set(RIB_PROVENANCE_LABELS["CLIENT"])
        self._update_rib_bank_choices()
        if not state.get("iban") or not state.get("bic"):
            self.generate_rib()
        self._refresh_rib_display()

    # ------------------------------------------------------------------
    # Onglet Factures
    # ------------------------------------------------------------------

    def _build_invoice_ui(self):
        body = self._make_tab("facture", "Factures", "Générer les factures", self.generate_invoices, OUTPUT_DIR)
        reg = self.fields["facture"]

        # Quoi générer
        sec = self._section(body, 0, "Factures à générer")
        spin = ttk.Spinbox(sec, from_=1, to=MAX_INVOICES, textvariable=self.n_var, width=6)
        self._add_field(
            reg, sec, 0, "Nombre de factures", self.n_var, check_count(MAX_INVOICES), widget=spin,
        )
        ttk.Label(sec, text="Type d'opération", width=LABEL_WIDTH).grid(row=1, column=0, sticky="w", pady=3)
        types = ttk.Frame(sec)
        types.grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Checkbutton(
            types, text="Vente (700)", variable=self.vente_700_var
        ).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(
            types, text="Achat (600)", variable=self.achat_600_var
        ).pack(side="left")
        # Société émettrice et client
        for row, (party, title, mode_labels, _, _) in enumerate(PARTIES, start=1):
            sec = self._section(body, row, title)
            modes = ttk.Frame(sec)
            modes.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
            for value, text in zip(("random", "single", "per_invoice"), mode_labels):
                ttk.Radiobutton(
                    modes, text=text, value=value, variable=self.party_modes[party],
                    command=self._on_party_mode_change,
                ).pack(side="left", padx=(0, 18))
            self.party_single[party] = self._add_party_inputs(sec, 1, width=40)

        # TVA
        sec = self._section(body, 3, "TVA")
        modes = ttk.Frame(sec)
        modes.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self.vat_mode_buttons = [
            ttk.Radiobutton(
                modes, text=text, value=value, variable=self.vat_mode_var, command=self._update_vat_fields,
            )
            for value, text in (("single", "Un taux"), ("multi", "Plusieurs taux"))
        ]
        for button in self.vat_mode_buttons:
            button.pack(side="left", padx=(0, 18))
        self.vat_single_row, _ = self._add_field(
            reg, sec, 1, "Taux de TVA (%)", self.vat_var, check_decimal(0, 100), width=10,
            is_active=lambda: not self.micro_var.get() and self.vat_mode_var.get() == "single",
        )
        self.vat_multi_row, _ = self._add_field(
            reg, sec, 2, "Taux de TVA (%)", self.vat_multi_var, check_rates, width=20,
            is_active=lambda: not self.micro_var.get() and self.vat_mode_var.get() == "multi",
        )
        ttk.Checkbutton(
            sec, text="Micro-entreprise (TVA non applicable, art. 293 B du CGI)",
            variable=self.micro_var, command=self._on_micro_toggle,
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # Détail par facture
        sec = self._section(body, 4, "Détail par facture")
        sec.columnconfigure(0, weight=1)
        opts = ttk.Frame(sec)
        opts.grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(
            opts, text="Saisir les lignes", variable=self.custom_lines_var,
            command=self._update_card_visibility,
        ).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(
            opts, text="Saisir les dates", variable=self.custom_dates_var,
            command=self._update_card_visibility,
        ).pack(side="left")
        self.invoices_container = ttk.Frame(sec)
        self.invoices_container.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.invoices_container.columnconfigure(0, weight=1)

        # Options avancées (repliées par défaut)
        self.advanced_toggle = ttk.Label(body, style="Link.TLabel", cursor="hand2")
        self.advanced_toggle.grid(row=5, column=0, sticky="w", padx=18, pady=(12, 0))
        self.advanced_toggle.bind("<Button-1>", lambda e: self._set_advanced_open(not self.advanced_open))
        self.advanced_frame = self._section(body, 6, "Options avancées")
        open_advanced = lambda: self._set_advanced_open(True)
        self._add_field(None, self.advanced_frame, 0, "Préfixe du numéro", self.prefix_var, width=14)
        self._add_field(
            None, self.advanced_frame, 1, "Préfixe du fichier", self.file_prefix_var, width=14,
        )
        self._add_field(
            reg, self.advanced_frame, 2, f"Plafond TTC ({CURRENCY})", self.max_total_var,
            check_decimal(Decimal("0.01")), width=14,
            on_error=open_advanced,
        )
        ttk.Frame(body, height=14).grid(row=7, column=0)

        self.n_var.trace_add("write", lambda *args: self._refresh_invoice_cards())
        for var in (self.vat_var, self.vat_multi_var):
            var.trace_add("write", lambda *args: self._refresh_line_vat_choices())
        self._set_advanced_open(False)
        self._on_party_mode_change()
        self._update_vat_fields()
        self._refresh_invoice_cards()

    def _set_advanced_open(self, is_open):
        self.advanced_open = is_open
        self._show([self.advanced_frame], is_open)
        self.advanced_toggle.configure(text=("▾" if is_open else "▸") + "  Options avancées")

    def _add_party_inputs(self, parent, row, width, title=None):
        """Champs Nom / Adresse / SIRET à partir de la ligne row (avec un sous-titre optionnel)."""
        rows = []
        if title:
            header = ttk.Label(parent, text=title, style="SubHeader.TLabel")
            header.grid(row=row, column=0, columnspan=3, sticky="w", pady=(6, 0))
            rows.append(header)
            row += 1
        name_var, address_var, siret_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for offset, (label, var) in enumerate((("Nom", name_var), ("Adresse", address_var), ("SIRET", siret_var))):
            rows += self._add_field(None, parent, row + offset, label, var, width=width)[0]
        return PartyInputs(name_var=name_var, address_var=address_var, siret_var=siret_var, rows=rows)

    def _on_party_mode_change(self):
        for party, inputs in self.party_single.items():
            self._show(inputs.rows, self.party_modes[party].get() == "single")
        self._update_card_visibility()

    def _on_micro_toggle(self):
        if self.micro_var.get():
            self._vat_before_micro = self.vat_var.get()
            self.vat_var.set("0")
        else:
            self.vat_var.set(self._vat_before_micro)
        self._update_vat_fields()

    def _update_vat_fields(self):
        multi = self.vat_mode_var.get() == "multi"
        self._show(self.vat_single_row, not multi)
        self._show(self.vat_multi_row, multi)
        state = ["disabled"] if self.micro_var.get() else ["!disabled"]
        for widget in [self.vat_single_row[1], self.vat_multi_row[1], *self.vat_mode_buttons]:
            widget.state(state)
        for f in self.fields["facture"]:
            f.refresh()
        self._refresh_line_vat_choices()

    def _current_vat_rates(self):
        """Taux proposés dans les lignes saisies ; None si la saisie TVA est invalide."""
        if self.micro_var.get():
            return [Decimal("0")]
        try:
            if self.vat_mode_var.get() == "multi":
                return parse_rate_list(self.vat_multi_var.get()) or None
            return [parse_decimal(self.vat_var.get())]
        except ValueError:
            return None

    def _refresh_line_vat_choices(self):
        rates = self._current_vat_rates()
        if rates is None:
            return
        choices = [format_rate(r) for r in rates]
        state = ["disabled"] if self.micro_var.get() else ["readonly"]
        for card in self.invoice_cards:
            for line in card.lines:
                line.vat_combo.configure(values=choices)
                line.vat_combo.state(["!disabled"])
                line.vat_combo.state(state)
                if line.vat_var.get() not in choices:
                    line.vat_var.set(choices[0])

    def _invoice_count(self):
        return parse_count(self.n_var.get(), MAX_INVOICES)

    def _invoice_fields(self):
        n = self._invoice_count() or len(self.invoice_cards)
        card_fields = [
            f for card in self.invoice_cards[:n]
            for f in card.fields + [line.field for line in card.lines]
        ]
        return self.fields["facture"] + card_fields

    def _create_invoice_card(self, index) -> InvoiceCard:
        frame = ttk.LabelFrame(self.invoices_container, text=f"Facture {index}", padding=(10, 4, 10, 8))
        frame.grid(row=index - 1, column=0, sticky="ew", pady=(8, 0))
        frame.columnconfigure(2, weight=1)

        inv_date_var, due_date_var = tk.StringVar(), tk.StringVar()
        fields = []
        prefix = f"Facture {index} – "

        parties = {
            party: self._add_party_inputs(frame, i * 4, width=28, title=title)
            for i, (party, title, *_) in enumerate(PARTIES)
        }
        row = len(PARTIES) * 4

        lines_box = ttk.Frame(frame)
        lines_box.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 2))
        for col, text in enumerate(("Libellé", "Qté", f"PU HT ({CURRENCY})", "TVA")):
            ttk.Label(lines_box, text=text, style="SubHeader.TLabel").grid(
                row=0, column=col, sticky="w", padx=(0, 6)
            )
        actions = ttk.Frame(lines_box)
        card = InvoiceCard(
            index=index, frame=frame, parties=parties, lines_box=lines_box, lines=[], actions=actions,
            copy_button=None, inv_date_var=inv_date_var, due_date_var=due_date_var, date_rows=[], fields=fields,
        )
        ttk.Button(actions, text="+ Ajouter une ligne", command=lambda: self._add_line(card)).pack(side="left")
        if index == 1:
            card.copy_button = ttk.Button(
                actions, text="Copier vers les autres factures", command=lambda: self._copy_lines_to_others(card),
            )
            card.copy_button.pack(side="left", padx=(10, 0))

        inv_rows, _ = self._add_field(
            fields, frame, row + 1, "Date de facture", inv_date_var, check_date, width=14,
            name=prefix + "Date de facture", is_active=self.custom_dates_var.get,
        )
        due_rows, _ = self._add_field(
            fields, frame, row + 2, "Date d'échéance", due_date_var, check_date, width=14,
            name=prefix + "Date d'échéance", is_active=self.custom_dates_var.get,
        )
        card.date_rows = inv_rows + due_rows
        self._add_line(card)
        return card

    # Lignes saisies ----------------------------------------------------

    def _add_line(self, card, values=None):
        desc_var, qty_var, unit_var, vat_var = (tk.StringVar(value=v) for v in (values or ("", "", "", "")))
        box = card.lines_box
        desc = ttk.Entry(box, textvariable=desc_var, width=24)
        qty = ttk.Entry(box, textvariable=qty_var, width=5)
        unit = ttk.Entry(box, textvariable=unit_var, width=10)
        vat_combo = ttk.Combobox(box, textvariable=vat_var, width=7, state="readonly")
        error_label = ttk.Label(box, text="", style="Error.TLabel")
        line = LineInputs(desc_var, qty_var, unit_var, vat_var, [], vat_combo)
        remove = ttk.Button(box, text="✕", width=3, command=lambda: self._remove_line(card, line))
        line.widgets = [desc, qty, unit, vat_combo, remove, error_label]

        def check(_raw):
            return self._line_error(line)

        line.field = Field(
            name="", var=unit_var, widget=unit, error_label=error_label, check=check,
            is_active=lambda: self.custom_lines_var.get() and line in card.lines,
            focus_widget=lambda: qty if (self._line_error(line) or "").startswith("Quantité") else unit,
        )
        for var in (desc_var, qty_var, unit_var):
            var.trace_add("write", lambda *args: line.field.refresh())
        card.lines.append(line)
        self._layout_lines(card)
        self._refresh_line_vat_choices()
        if values and values[3]:
            vat_var.set(values[3])
        return line

    def _remove_line(self, card, line):
        for w in line.widgets:
            w.destroy()
        card.lines.remove(line)
        self._layout_lines(card)

    def _layout_lines(self, card):
        for j, line in enumerate(card.lines, start=1):
            line.field.name = f"Facture {card.index} – ligne {j}"
            for col, w in enumerate(line.widgets):
                padx = (8, 0) if col == 5 else (0, 6)
                w.grid(row=j, column=col, sticky="w", padx=padx, pady=2)
        card.actions.grid(row=len(card.lines) + 1, column=0, columnspan=6, sticky="w", pady=(4, 0))
        for scroll in self.scrolls.values():
            scroll.refresh()

    @staticmethod
    def _line_error(line):
        desc, qty, unit = (v.get().strip() for v in (line.desc_var, line.qty_var, line.unit_var))
        if not (desc or qty or unit):
            return None
        if not unit:
            return "Prix unitaire manquant"
        try:
            if parse_decimal(unit) == 0:
                return "Prix unitaire à 0"
        except ValueError:
            return "Prix unitaire invalide"
        if qty:
            try:
                if parse_decimal(qty) <= 0:
                    return "Quantité doit être > 0"
            except ValueError:
                return "Quantité invalide"
        return None

    def _card_lines(self, card):
        """Lignes remplies d'une carte : [(libellé, qté, PU, taux)] ; lignes vides ignorées."""
        result = []
        for line in card.lines:
            desc, qty, unit = (v.get().strip() for v in (line.desc_var, line.qty_var, line.unit_var))
            if not unit:
                continue
            rate = Decimal("0") if self.micro_var.get() else parse_decimal(line.vat_var.get().replace("%", ""))
            result.append((desc, parse_decimal(qty) if qty else Decimal("1"), decimal_round(parse_decimal(unit)), rate))
        return result

    def _copy_lines_to_others(self, source):
        n = self._invoice_count() or 1
        values = [
            tuple(v.get() for v in (l.desc_var, l.qty_var, l.unit_var, l.vat_var)) for l in source.lines
        ]
        for card in self.invoice_cards[1:n]:
            for line in list(card.lines):
                self._remove_line(card, line)
            for v in values:
                self._add_line(card, v)
        self._set_status("facture", f"Lignes copiées vers les factures 2 à {n}.", "info")

    def _refresh_invoice_cards(self):
        n = self._invoice_count()
        if n is not None:
            # Les cartes au-delà de n sont gardées masquées pour ne pas perdre la saisie.
            while len(self.invoice_cards) < n:
                self.invoice_cards.append(self._create_invoice_card(len(self.invoice_cards) + 1))
        self._update_card_visibility()

    def _update_card_visibility(self):
        n = self._invoice_count() or 0
        per_invoice = {party: mode.get() == "per_invoice" for party, mode in self.party_modes.items()}
        lines = self.custom_lines_var.get()
        dates = self.custom_dates_var.get()
        anything = any(per_invoice.values()) or lines or dates
        # Un conteneur grid vidé garde sa hauteur : on masque le conteneur lui-même.
        self._show([self.invoices_container], anything)
        for i, card in enumerate(self.invoice_cards):
            self._show([card.frame], anything and i < n)
            for party, inputs in card.parties.items():
                self._show(inputs.rows, per_invoice[party])
            self._show([card.lines_box], lines)
            if card.copy_button is not None:
                if n > 1:
                    card.copy_button.pack(side="left", padx=(10, 0))
                else:
                    card.copy_button.pack_forget()
            self._show(card.date_rows, dates)
        for f in self._invoice_fields():
            f.refresh()

    @staticmethod
    def _party_from_inputs(inputs, fallback_name):
        name, siret = inputs.name_var.get().strip(), inputs.siret_var.get().strip()
        address = [line.strip() for line in inputs.address_var.get().split(";") if line.strip()]
        if not name and not address and not siret:
            return None
        party = {"name": name or fallback_name, "address": address}
        if siret:
            party["siret"] = siret
        return party

    def _build_party_list(self, party, pool, fallback_name, n, cards):
        """Société ou client de chaque facture selon le mode choisi ; champs vides = au hasard."""
        mode = self.party_modes[party].get()
        if mode == "random":
            if n <= len(pool):
                return [dict(p) for p in random.sample(pool, n)]
            return [dict(random.choice(pool)) for _ in range(n)]
        if mode == "single":
            chosen = self._party_from_inputs(self.party_single[party], fallback_name) or random.choice(pool)
            return [dict(chosen) for _ in range(n)]
        return [
            self._party_from_inputs(card.parties[party], f"{fallback_name} {i + 1}") or dict(random.choice(pool))
            for i, card in enumerate(cards)
        ]

    @staticmethod
    def _assign_vat_rates(items, rates):
        """Répartit les taux au hasard sur les lignes générées, chaque taux au moins une fois."""
        order = list(rates)
        random.shuffle(order)
        for i, item in enumerate(items):
            item["vat"] = order[i % len(order)]

    @staticmethod
    def _invoice_filename(file_prefix, inv_no, account_type):
        suffix = "_VENTE" if account_type == "700" else "_ACHAT"
        return os.path.join(OUTPUT_DIR, f"{file_prefix}facture_{inv_no}{suffix}.pdf")

    def _next_free_invoice_index(self, prefix, file_prefix, start):
        """Premier index dont aucun PDF (vente ou achat) n'existe déjà, pour ne rien écraser."""
        idx = start
        while any(
            os.path.exists(self._invoice_filename(file_prefix, generate_invoice_number(prefix, idx), t))
            for t in ("700", "600")
        ):
            idx += 1
        return idx

    def generate_invoices(self):
        key = "facture"
        account_types = [t for t, var in (("700", self.vente_700_var), ("600", self.achat_600_var)) if var.get()]
        if not account_types:
            self._set_status(key, "✗ Coche au moins un type d'opération (Vente ou Achat).", "error")
            return
        if not self._validate(key, self._invoice_fields()):
            return

        n = self._invoice_count()
        cards = self.invoice_cards[:n]
        if self.micro_var.get():
            vat_rates = [Decimal("0")]
        elif self.vat_mode_var.get() == "multi":
            vat_rates = parse_rate_list(self.vat_multi_var.get())
        else:
            vat_rates = [parse_decimal(self.vat_var.get())]
        vat_rate = vat_rates[0]
        max_total_ttc = decimal_round(parse_decimal(self.max_total_var.get()))
        # Plafond HT calculé avec le taux le plus élevé, pour rester sous le plafond TTC.
        max_total_ht = decimal_round(max_total_ttc / ((Decimal("100") + max(vat_rates)) / Decimal("100")))
        prefix = self.prefix_var.get().strip() or "FAC-"
        file_prefix = self.file_prefix_var.get().strip()
        companies, clients = (
            self._build_party_list(party, pool, fallback, n, cards)
            for party, _, _, pool, fallback in PARTIES
        )

        custom_lines = self.custom_lines_var.get()
        custom_dates = self.custom_dates_var.get()
        today = datetime.date.today()
        plan = []
        for i, card in enumerate(cards):
            lines = self._card_lines(card) if custom_lines else []
            inv_raw = card.inv_date_var.get().strip() if custom_dates else ""
            due_raw = card.due_date_var.get().strip() if custom_dates else ""
            inv_date = parse_date(inv_raw) if inv_raw else random_date_between(
                today - datetime.timedelta(days=90), today
            )
            due_date = parse_date(due_raw) if due_raw else inv_date + datetime.timedelta(days=30)
            if due_date < inv_date:
                self._set_status(
                    key, f"✗ Facture {i + 1} : la date d'échéance est avant la date de facture.", "error"
                )
                return
            plan.append((companies[i], clients[i], lines, inv_date, due_date))

        ensure_output_dir()
        generated = []
        numbers = []
        idx = 0
        self._busy(True)
        try:
            for company, client, lines, inv_date, due_date in plan:
                idx = self._next_free_invoice_index(prefix, file_prefix, idx + 1)
                inv_no = generate_invoice_number(prefix, idx)
                numbers.append(inv_no)
                for account_type in account_types:
                    if lines:
                        # Lignes saisies : reprises telles quelles, sans application du plafond.
                        descriptions = ITEM_DESCRIPTIONS_BY_ACCOUNT[account_type]
                        items = [
                            {"desc": desc or random.choice(descriptions), "qty": qty, "unit": unit,
                             "total": decimal_round(qty * unit), "vat": rate}
                            for desc, qty, unit, rate in lines
                        ]
                    else:
                        items = generate_items(
                            max_total_ht=max_total_ht, account_type=account_type, min_lines=len(vat_rates)
                        )
                        self._assign_vat_rates(items, vat_rates)
                    filename = self._invoice_filename(file_prefix, inv_no, account_type)
                    draw_invoice_pdf(
                        filename, company, inv_no, inv_date, due_date, items, vat_rate, CURRENCY,
                        micro_entrepreneur=self.micro_var.get(),
                        account_type=account_type,
                        client=client,
                    )
                    generated.append(filename)
        except OSError as exc:
            self._write_error(key, exc, len(generated))
            return
        finally:
            self._busy(False)

        count = len(generated)
        range_text = numbers[0] if len(numbers) == 1 else f"{numbers[0]} à {numbers[-1]}"
        self._set_status(
            key,
            f"✓ {count} PDF {plural(count, 'créé', 'créés')} ({range_text}) "
            f"dans « {os.path.basename(OUTPUT_DIR)} ».",
            "ok",
        )

    # ------------------------------------------------------------------
    # Onglet Z de caisse
    # ------------------------------------------------------------------

    def _build_z_caisse_ui(self):
        body = self._make_tab("z", "Z de caisse", "Générer les Z", self.generate_z_caisse, Z_CAISSE_OUTPUT_DIR)
        reg = self.fields["z"]

        sec = self._section(body, 0, "Z de caisse à générer")
        spin = ttk.Spinbox(sec, from_=1, to=MAX_Z, textvariable=self.z_n_var, width=6)
        self._add_field(reg, sec, 0, "Nombre de Z", self.z_n_var, check_count(MAX_Z), widget=spin)
        company_combo = ttk.Combobox(
            sec, textvariable=self.z_company_var, state="readonly", width=30,
            values=[RANDOM_COMPANY_LABEL] + [c["name"] for c in SAMPLE_COMPANIES],
        )
        self._add_field(None, sec, 1, "Établissement", self.z_company_var, widget=company_combo)
        profile_combo = ttk.Combobox(
            sec, textvariable=self.z_profile_var, state="readonly", width=30,
            values=list(self.z_profile_by_label),
        )
        self._add_field(None, sec, 2, "Type de commerce", self.z_profile_var, widget=profile_combo)
        profile_combo.bind("<<ComboboxSelected>>", lambda e: self._on_z_profile_change())
        sec = self._section(body, 1, "Identification")
        self._add_field(reg, sec, 0, "Date de clôture", self.z_date_var, check_date, width=14)
        self._add_field(None, sec, 1, "Numéro de caisse", self.z_caisse_var, width=14)
        self._add_field(None, sec, 2, "Préfixe du n° de Z", self.z_numero_var, width=14)

        sec = self._section(body, 2, "TVA")
        modes = ttk.Frame(sec)
        modes.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        for value, text in (("1_rate", "Un taux"), ("2_rates", "Deux taux"), ("no_vat", "Sans TVA (0 %)")):
            ttk.Radiobutton(
                modes, text=text, value=value, variable=self.z_tva_mode_var,
                command=self._update_z_tva_fields_visibility,
            ).pack(side="left", padx=(0, 18))
        self.z_tva1_row, _ = self._add_field(
            reg, sec, 1, "Taux principal (%)", self.z_tva1_var, check_decimal(0, 100), width=10,
            is_active=lambda: self.z_tva_mode_var.get() != "no_vat",
        )
        self.z_tva2_row, _ = self._add_field(
            reg, sec, 2, "Taux secondaire (%)", self.z_tva2_var, check_decimal(0, 100), width=10,
            is_active=lambda: self.z_tva_mode_var.get() == "2_rates",
        )

        sec = self._section(body, 3, "Montants")
        modes = ttk.Frame(sec)
        modes.grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(
            modes, text=f"Au hasard (500 à 5 000 {CURRENCY} TTC)", value=True,
            variable=self.z_random_amounts_var, command=self._update_z_paiements,
        ).pack(side="left", padx=(0, 18))
        ttk.Radiobutton(
            modes, text="Saisir par mode de paiement", value=False,
            variable=self.z_random_amounts_var, command=self._update_z_paiements,
        ).pack(side="left")
        self.z_paiements_container = ttk.Frame(sec)
        self.z_paiements_container.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.z_paiements_container.columnconfigure(2, weight=1)

        sec = self._section(body, 4, "Écart de caisse")
        ttk.Checkbutton(
            sec, text="Ajouter un écart de caisse (cas de test)", variable=self.z_ecart_var,
            command=self._update_z_ecart_state,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        row, _ = self._add_field(
            reg, sec, 1, f"Montant de l'écart ({CURRENCY})", self.z_ecart_amount_var,
            check_decimal(non_zero=True), width=14, is_active=self.z_ecart_var.get,
        )
        self.z_ecart_entry = row[1]
        ttk.Frame(body, height=14).grid(row=5, column=0)

        self._on_z_profile_change()
        self._update_z_tva_fields_visibility()
        self._update_z_ecart_state()

    def _z_profile_key(self):
        return self.z_profile_by_label.get(self.z_profile_var.get())

    def _on_z_profile_change(self):
        key = self._z_profile_key()
        if key is None:
            return
        profile = SAMPLE_Z_PROFILES[key]
        rates = profile["tva_rates"]
        self.z_tva1_var.set(str(rates[0]))
        if len(rates) > 1:
            self.z_tva2_var.set(str(rates[1]))
        self._update_z_paiements()

    def _update_z_paiements(self):
        for widget in self.z_paiements_container.winfo_children():
            widget.destroy()
        self.z_payment_fields = []
        key = self._z_profile_key()
        manual = not self.z_random_amounts_var.get() and key is not None
        # Un conteneur grid vidé garde sa hauteur : on le masque quand il n'y a rien à saisir.
        self._show([self.z_paiements_container], manual)
        if not manual:
            return
        for i, paiement in enumerate(SAMPLE_Z_PROFILES[key]["paiements"]):
            # Une variable par mode de paiement, conservée d'un profil à l'autre.
            var = self.z_paiements_vars.get(paiement)
            if var is None:
                var = self.z_paiements_vars[paiement] = tk.StringVar(value="0,00")
            _, field = self._add_field(
                self.z_payment_fields, self.z_paiements_container, i, f"{paiement} ({CURRENCY})", var,
                check_decimal(0), width=14, name=f"Paiement {paiement}",
            )
            field.refresh()

    def _update_z_tva_fields_visibility(self):
        mode = self.z_tva_mode_var.get()
        self._show(self.z_tva1_row, mode != "no_vat")
        self._show(self.z_tva2_row, mode == "2_rates")
        for f in self.fields["z"]:
            f.refresh()

    def _update_z_ecart_state(self):
        self.z_ecart_entry.state(["!disabled"] if self.z_ecart_var.get() else ["disabled"])
        for f in self.fields["z"]:
            f.refresh()

    def _generate_z_amounts_random(self, categories, paiements):
        """Generate random amounts for categories and payments. Returns (categories_data, paiements_data, total_ttc)."""
        total_ttc = decimal_round(Decimal(random.uniform(500.0, 5000.0)))

        categories_data = {}
        remaining = total_ttc
        for j, cat in enumerate(categories):
            if j == len(categories) - 1:
                categories_data[cat] = remaining
            else:
                amount = decimal_round(total_ttc * Decimal(random.uniform(0.1, 0.4)))
                categories_data[cat] = amount
                remaining -= amount
        if remaining < 0:
            others_total = sum(v for k, v in categories_data.items() if k != categories[-1])
            categories_data[categories[-1]] = total_ttc - others_total

        paiements_data = {}
        remaining = total_ttc
        for j, paiement in enumerate(paiements):
            if j == len(paiements) - 1:
                paiements_data[paiement] = remaining
            else:
                amount = decimal_round(total_ttc * Decimal(random.uniform(0.2, 0.6)))
                paiements_data[paiement] = amount
                remaining -= amount
        if remaining < 0:
            others_total = sum(v for k, v in paiements_data.items() if k != paiements[-1])
            paiements_data[paiements[-1]] = total_ttc - others_total

        return categories_data, paiements_data, total_ttc

    def _generate_z_amounts_manual(self, categories, paiements):
        """Collect manually entered payment amounts and distribute evenly to categories.
        Returns (categories_data, paiements_data, total_ttc)."""
        paiements_data = {}
        total_ttc = Decimal("0.00")
        for paiement in paiements:
            var = self.z_paiements_vars.get(paiement)
            amount = decimal_round(parse_decimal(var.get())) if var else Decimal("0.00")
            paiements_data[paiement] = amount
            total_ttc += amount

        categories_data = {}
        if total_ttc > 0:
            ratio = Decimal("1.0") / Decimal(len(categories))
            for cat in categories:
                categories_data[cat] = decimal_round(total_ttc * ratio)
        else:
            for cat in categories:
                categories_data[cat] = Decimal("0.00")

        return categories_data, paiements_data, total_ttc

    def _compute_z_totals(self, total_ttc, tva_mode, tva1_rate, tva2_rate):
        """Compute HT, TVA and TTC totals dict for a Z de caisse."""
        if tva_mode == "no_vat":
            return {
                "ht": total_ttc,
                "tva1": Decimal("0.00"),
                "tva1_rate": Decimal("0"),
                "ttc": total_ttc,
                "no_vat": True,
            }
        if tva2_rate is not None:
            ratio_tva1 = Decimal("0.7")
            ratio_tva2 = Decimal("0.3")
            base_ht_tva1 = decimal_round(
                total_ttc / (Decimal("1") + tva1_rate / Decimal("100")) * ratio_tva1
            )
            base_ht_tva2 = decimal_round(
                total_ttc / (Decimal("1") + tva2_rate / Decimal("100")) * ratio_tva2
            )
            tva1 = decimal_round(base_ht_tva1 * tva1_rate / Decimal("100"))
            tva2 = decimal_round(base_ht_tva2 * tva2_rate / Decimal("100"))
            total_ht = base_ht_tva1 + base_ht_tva2
            total_ttc_recalc = decimal_round(total_ht + tva1 + tva2)
            diff = total_ttc - total_ttc_recalc
            if diff != 0:
                tva1 = decimal_round(tva1 + diff / Decimal("2"))
                tva2 = decimal_round(tva2 + diff / Decimal("2"))
                total_ht = decimal_round(total_ttc - tva1 - tva2)
            return {
                "ht": total_ht,
                "tva1": tva1,
                "tva1_rate": tva1_rate,
                "tva2": tva2,
                "tva2_rate": tva2_rate,
                "ttc": total_ttc,
                "no_vat": False,
            }
        total_ht = decimal_round(total_ttc / (Decimal("1") + tva1_rate / Decimal("100")))
        tva1 = decimal_round(total_ttc - total_ht)
        return {
            "ht": total_ht,
            "tva1": tva1,
            "tva1_rate": tva1_rate,
            "ttc": total_ttc,
            "no_vat": False,
        }

    def generate_z_caisse(self):
        key = "z"
        manual = not self.z_random_amounts_var.get()
        fields = self.fields["z"] + (self.z_payment_fields if manual else [])
        if not self._validate(key, fields):
            return
        profile_key = self._z_profile_key()
        if profile_key is None:
            self._set_status(key, "✗ Choisis un type de commerce.", "error")
            return

        n = parse_count(self.z_n_var.get(), MAX_Z)
        profile = SAMPLE_Z_PROFILES[profile_key]
        categories, paiements = profile["categories"], profile["paiements"]
        tva_mode = self.z_tva_mode_var.get()
        tva1_rate = Decimal("0") if tva_mode == "no_vat" else parse_decimal(self.z_tva1_var.get())
        tva2_rate = parse_decimal(self.z_tva2_var.get()) if tva_mode == "2_rates" else None
        z_caisse = self.z_caisse_var.get().strip() or "C001"
        z_prefix = self.z_numero_var.get().strip() or "Z-"
        ecart = decimal_round(parse_decimal(self.z_ecart_amount_var.get())) if self.z_ecart_var.get() else None
        z_date_str = self.z_date_var.get().strip()
        fixed_date = (
            datetime.datetime.combine(parse_date(z_date_str), datetime.datetime.now().time())
            if z_date_str else None
        )
        selected = next((c for c in SAMPLE_COMPANIES if c["name"] == self.z_company_var.get()), None)

        ensure_z_caisse_output_dir()
        generated = []
        seq = 1
        self._busy(True)
        try:
            for _ in range(n):
                company = selected or random.choice(SAMPLE_COMPANIES)
                z_date = fixed_date or datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 90))
                safe_name = safe_filename(company["name"])
                while True:
                    z_numero = f"{z_prefix}{z_date.strftime('%Y%m%d')}-{seq:04d}"
                    filename = os.path.join(
                        Z_CAISSE_OUTPUT_DIR,
                        f"Z_{safe_name}_{z_date.strftime('%Y%m%d')}_{z_numero.replace('-', '_')}.pdf",
                    )
                    seq += 1
                    if not os.path.exists(filename):
                        break

                if manual:
                    amounts = self._generate_z_amounts_manual(categories, paiements)
                else:
                    amounts = self._generate_z_amounts_random(categories, paiements)
                categories_data, paiements_data, total_ttc = amounts
                totals = self._compute_z_totals(total_ttc, tva_mode, tva1_rate, tva2_rate)
                draw_z_caisse_pdf(
                    filename, company, z_date, z_caisse, z_numero,
                    categories_data, paiements_data, totals, ecart,
                )
                generated.append(filename)
        except OSError as exc:
            self._write_error(key, exc, len(generated))
            return
        finally:
            self._busy(False)

        count = len(generated)
        self._set_status(
            key,
            f"✓ {count} {plural(count, 'Z de caisse créé', 'Z de caisse créés')} "
            f"dans « {os.path.basename(Z_CAISSE_OUTPUT_DIR)} ».",
            "ok",
        )

    # ------------------------------------------------------------------
    # Onglet RIB
    # ------------------------------------------------------------------

    def _build_rib_ui(self):
        body = self._make_tab("rib", "RIB", "Générer le PDF", self.generate_rib_pdf, RIB_OUTPUT_DIR)

        sec = self._section(body, 0, "Banque")
        prov_combo = ttk.Combobox(
            sec, textvariable=self.rib_provenance_var, state="readonly", width=30,
            values=list(self.rib_key_by_label),
        )
        self._add_field(None, sec, 0, "Utilisé pour", self.rib_provenance_var, widget=prov_combo)
        prov_combo.bind("<<ComboboxSelected>>", lambda e: self._on_rib_provenance_change())
        self.rib_bank_combo = ttk.Combobox(sec, textvariable=self.rib_bank_var, state="readonly", width=30)
        self._add_field(None, sec, 1, "Banque", self.rib_bank_var, widget=self.rib_bank_combo)
        self.rib_bank_combo.bind("<<ComboboxSelected>>", lambda e: self.generate_rib())

        sec = self._section(body, 1, "Coordonnées générées")
        mono = ("Consolas", 11)
        for row, (label, title, var) in enumerate(
            (("IBAN", "IBAN", self.rib_iban_var), ("BIC", "BIC / SWIFT", self.rib_bic_var))
        ):
            entry = ttk.Entry(sec, textvariable=var, width=36, state="readonly", font=mono)
            widgets, _ = self._add_field(None, sec, row, title, var, widget=entry)
            widgets[2].destroy()
            ttk.Button(
                sec, text="Copier", command=lambda l=label, v=var: self._copy_to_clipboard(l, v.get()),
            ).grid(row=row, column=2, sticky="w", padx=(10, 0))

        actions = ttk.Frame(sec)
        actions.grid(row=2, column=1, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Nouveau RIB", command=self._on_new_rib).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(
            actions, text="IBAN par blocs de 4", variable=self.rib_spaces_var,
            command=self._refresh_rib_display,
        ).pack(side="left")

        self._update_rib_bank_choices()
        self.generate_rib()

    def _rib_provenance_key(self):
        return self.rib_key_by_label.get(self.rib_provenance_var.get(), "CLIENT")

    def _on_rib_provenance_change(self):
        self._update_rib_bank_choices()
        self.generate_rib()

    def _on_new_rib(self):
        self.generate_rib()
        self._set_status("rib", "Nouveau RIB généré.", "info")

    def _update_rib_bank_choices(self):
        banks = SAMPLE_BANKS_BY_RIB_PROVENANCE.get(self._rib_provenance_key(), [])
        names = [b.get("name", "") for b in banks if b.get("name")]
        self.rib_bank_combo["values"] = names
        if names and self.rib_bank_var.get() not in names:
            self.rib_bank_var.set(names[0])

    def _copy_to_clipboard(self, label, text):
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._set_status("rib", f"{label} copié dans le presse-papiers.", "info")

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
        banks = SAMPLE_BANKS_BY_RIB_PROVENANCE.get(self._rib_provenance_key(), [])
        bank = next((b for b in banks if b.get("name") == self.rib_bank_var.get()), None) or (
            banks[0] if banks else None
        )
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
        key = "rib"
        prov = self._rib_provenance_key()
        prov_label = RIB_PROVENANCE_LABELS.get(prov, prov)
        bank_name = self.rib_bank_var.get() or "Banque"
        if not self.rib_iban_var.get() or not self.rib_bic_var.get():
            self.generate_rib()
        iban, bic = self.rib_iban_var.get(), self.rib_bic_var.get()

        ensure_rib_output_dir()
        filename = unique_path(os.path.join(
            RIB_OUTPUT_DIR,
            f"RIB_{safe_filename(bank_name, 'banque')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        ))
        try:
            draw_rib_pdf(filename, prov_label, bank_name, iban, bic)
        except OSError as exc:
            self._write_error(key, exc, 0)
            return
        self._set_status(
            key, f"✓ {os.path.basename(filename)} créé dans « {os.path.basename(RIB_OUTPUT_DIR)} ».", "ok"
        )


def main():
    root = tk.Tk()
    InvoiceGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
