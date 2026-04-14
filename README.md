# Générateur de Factures PDF

Outil de génération de factures PDF avec interface graphique permettant de créer plusieurs factures en une seule opération.

## Fonctionnalités

- **Génération multiple** : Création de 1 à 10 factures simultanément
- **Personnalisation complète** :
  - Informations de la société émettrice (nom, adresse, SIRET)
  - Montants personnalisés ou génération aléatoire
  - Dates de facturation et d'échéance personnalisées ou aléatoires
  - Taux de TVA configurable
  - Mode micro-entreprise (TVA non applicable)
  - Préfixe pour les numéros de facture
  - Plafond TTC pour limiter les montants
- **Génération automatique** : Utilisation de sociétés d'exemple si aucune information n'est fournie
- **Format PDF professionnel** : Factures au format A4 avec mise en page structurée

## Prérequis

- Python 3.x
- Bibliothèques Python :
  - `tkinter` (généralement inclus avec Python)
  - `reportlab`

## Installation

```bash
pip install reportlab
```

## Utilisation

Lancer l'application :

```bash
python "generateur de facture.py"
```

### Interface

1. **Nombre de factures** : Sélectionner le nombre de factures à générer (1-10)
2. **Même société** : Cocher pour utiliser les mêmes informations pour toutes les factures
3. **Informations société** :
   - Nom de la société
   - Adresse (séparer les lignes par `;`)
   - SIRET
4. **Personnalisation** :
   - **Montants personnalisés** : Permet de saisir des montants spécifiques par facture (séparés par `;`)
   - **Dates personnalisées** : Permet de définir les dates de facturation et d'échéance (format JJ-MM-AAAA)
5. **Paramètres généraux** :
   - TVA (%) : Taux de TVA à appliquer
   - Micro-entreprise : Active le mode sans TVA
   - Préfixe numéro : Préfixe pour les numéros de facture (ex: "FAC-")
   - Préfixe fichier : Préfixe pour les noms de fichiers PDF
   - Plafond TTC : Montant maximum TTC par facture

### Génération

Cliquer sur le bouton **"Générer"** pour créer les factures PDF. Les fichiers sont sauvegardés dans le dossier `factures_sortie` à la racine du projet.

## Format des factures

Chaque facture PDF contient :
- En-tête avec les informations de la société émettrice
- Numéro de facture (format : `PRÉFIXE-AAAAMMJJ-NNNN`)
- Date de facturation et date d'échéance
- Informations du client (configurées dans le code)
- Tableau des lignes de facturation avec :
  - Description
  - Quantité
  - Prix unitaire
  - Total
- Sous-total HT
- Montant de la TVA
- Total TTC
- Mention légale pour micro-entreprise si applicable

## Structure du projet

```
generateur de facture/
├── app/
│   └── generateur de facture.py
└── factures_sortie/          (créé automatiquement)
    └── facture_*.pdf
```

## Notes

- Les montants sont arrondis à 2 décimales selon la méthode d'arrondi bancaire
- Si aucun montant personnalisé n'est fourni, des montants aléatoires sont générés dans la limite du plafond TTC
- Les dates aléatoires sont générées sur les 90 derniers jours si non spécifiées
- L'échéance par défaut est fixée à 30 jours après la date de facturation
- 10 sociétés d'exemple sont disponibles si aucune information n'est fournie
