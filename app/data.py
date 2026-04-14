import os
from decimal import Decimal, ROUND_HALF_UP

from reportlab.lib.pagesizes import A4

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "factures_sortie")
Z_CAISSE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "z_caisse_sortie")
RIB_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "rib_sortie")
FONT_SIZE = 11
PAGE_WIDTH, PAGE_HEIGHT = A4
CURRENCY = "€"

CLIENT_NAME = "test test"
CLIENT_ADDRESS = ["12 rue Fictive", "75000 Faillotte", "France"]

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
DEFAULT_MAX_TOTAL_TTC = Decimal("5000")

SAMPLE_Z_PROFILES = {
    "BOUTIQUE": {
        "categories": ["Prêt-à-porter", "Accessoires", "Chaussures"],
        "paiements": ["Espèces", "CB"],
        "tva_rates": [Decimal("20"), Decimal("10")],
    },
    "RESTAURANT": {
        "categories": ["Sur place", "À emporter", "Boissons"],
        "paiements": ["Espèces", "CB", "Tickets resto"],
        "tva_rates": [Decimal("10"), Decimal("20")],
    },
    "BAR": {
        "categories": ["Boissons chaudes", "Boissons fraîches", "Alcool"],
        "paiements": ["Espèces", "CB"],
        "tva_rates": [Decimal("10"), Decimal("20")],
    },
}

ITEM_DESCRIPTIONS_BY_ACCOUNT = {
    "700": [
        "Vente de marchandises",
        "Prestation de services",
        "Abonnement mensuel",
        "Frais de livraison",
        "Support / assistance",
        "Licence / accès logiciel",
        "Consultation",
        "Développement",
        "Maintenance",
        "Formation",
    ],
    "600": [
        "Achat de marchandises",
        "Fournitures administratives",
        "Petit matériel",
        "Prestation externe",
        "Frais de transport",
        "Frais de déplacement",
        "Sous-traitance",
        "Location",
        "Assurance",
        "Entretien et réparation",
    ],
}


RIB_PROVENANCE_LABELS = {
    "CLIENT": "Factures (Vente / Client)",
    "FOURNISSEUR": "Factures (Achat / Fournisseur)",
    "CAISSE": "Z de caisse",
}

SAMPLE_BANKS_BY_RIB_PROVENANCE = {
    "CLIENT": [
        {"name": "BNP Paribas", "iban": "FR76 3000 6000 0112 3456 7890 189", "bic": "BNPAFRPPXXX"},
        {"name": "Crédit Agricole", "iban": "FR76 2000 3000 0123 4567 8901 234", "bic": "AGRIFRPPXXX"},
        {"name": "Société Générale", "iban": "FR76 1000 4000 0708 0000 1234 567", "bic": "SOGEFRPPXXX"},
    ],
    "FOURNISSEUR": [
        {"name": "BNP Paribas", "iban": "FR76 3000 6000 0212 3456 7890 189", "bic": "BNPAFRPPXXX"},
        {"name": "Crédit Agricole", "iban": "FR76 2000 3000 0223 4567 8901 234", "bic": "AGRIFRPPXXX"},
        {"name": "La Banque Postale", "iban": "FR76 4000 6000 0112 3456 7890 123", "bic": "PSSTFRPPPAR"},
    ],
    "CAISSE": [
        {"name": "La Banque Postale", "iban": "FR76 4000 6000 0312 3456 7890 123", "bic": "PSSTFRPPPAR"},
        {"name": "Société Générale", "iban": "FR76 1000 4000 0908 0000 1234 567", "bic": "SOGEFRPPXXX"},
        {"name": "Crédit Agricole", "iban": "FR76 2000 3000 0323 4567 8901 234", "bic": "AGRIFRPPXXX"},
    ],
}


def decimal_round(v):
    return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

