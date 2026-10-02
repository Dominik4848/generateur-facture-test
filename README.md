# Générateur de documents de test

Application Windows qui génère des **factures**, des **Z de caisse** et des **RIB** fictifs au format PDF, pour alimenter des tests (saisie, OCR, rapprochements…).

## Installation

Pas besoin de Python : l'exécutable est autonome.

1. Télécharge **`Generateur_Factures.exe`** depuis la dernière
   [Release](https://github.com/Dominik4848/generateur-facture-test/releases/latest).
2. Crée un dossier à toi pour l'application, par exemple `Documents\Generateur de factures\`, et mets l'exe dedans.
   Les PDF seront créés dans ce même dossier : évite donc le dossier Téléchargements et les partages réseau.
3. Clic droit sur l'exe → **Envoyer vers** → **Bureau (créer un raccourci)**.
   Sous Windows 11, passe d'abord par **Afficher d'autres options**.

Au premier lancement, Windows SmartScreen peut afficher « Windows a protégé votre ordinateur » : clique sur **Informations complémentaires** → **Exécuter quand même**.

### Mettre à jour

Télécharge le nouvel exe depuis la Release et remplace l'ancien **dans le même dossier**, application fermée. Le raccourci et les PDF déjà générés sont conservés.

## Où sont les PDF ?

Dans des sous-dossiers créés automatiquement à côté de l'exe :

| Onglet      | Dossier             |
|-------------|---------------------|
| Factures    | `factures_sortie\`  |
| Z de caisse | `z_caisse_sortie\`  |
| RIB         | `rib_sortie\`       |

Le bouton **« Ouvrir le dossier »** de chaque onglet y mène directement. Les fichiers existants ne sont jamais écrasés : la numérotation continue (`FAC-20261002-0001`, `-0002`…).

## Utilisation

**Ctrl + Entrée** génère les documents de l'onglet affiché. Un champ mal rempli s'affiche en rouge, et le bouton Générer t'y emmène directement.

### Factures

- **Nombre** de factures (1 à 10) et **type** : Vente (700) et/ou Achat (600). Si les deux sont cochés, chaque facture est générée en deux versions, une de vente et une d'achat.
- **Société émettrice** et **Client / tiers** : au hasard, la même pour toutes, ou une par facture. Un champ vide donne une valeur au hasard. Pour l'adresse, sépare les lignes par `;`.
- **TVA** : un taux, plusieurs taux (`20 ; 10 ; 5,5`), ou micro-entreprise (TVA non applicable).
- **Détail par facture** :
  - *Saisir les lignes* : libellé, quantité, prix unitaire HT et taux de TVA ligne par ligne. Libellé vide = libellé au hasard, quantité vide = 1. « Copier vers les autres factures » duplique les lignes de la facture 1.
  - *Saisir les dates* : date de facture et date d'échéance (`JJ-MM-AAAA` ou `JJ/MM/AAAA`).
- **Options avancées** : préfixe du numéro, préfixe du nom de fichier, plafond TTC. Le plafond ne s'applique qu'aux lignes générées au hasard.

### Z de caisse

Établissement, type de commerce (boutique, restaurant, bar), date de clôture, TVA à un ou deux taux ou sans TVA, montants au hasard ou saisis par mode de paiement, et écart de caisse optionnel.

### RIB

IBAN français fictif mais valide (clé de contrôle correcte) et BIC de la banque choisie. Boutons « Copier » pour le presse-papiers, et génération d'un RIB en PDF.

## Développement

Prérequis : Python 3.10 ou plus récent, installé avec l'option « Add python.exe to PATH ».

Lancer depuis les sources :
```
python -m pip install -r requirements.txt
python "app/generateur de facture.py"
```
ou double-clic sur `lancer_factures.bat`. En mode développement, les PDF sont créés à la racine du projet.

### Construire l'exe et publier une Release

Double-clic sur **`installer.bat`** : le script installe les dépendances, construit `dist\Generateur_Factures.exe` et crée un raccourci sur ton Bureau. À la main :
```
python -m PyInstaller --noconfirm Generateur_Factures.spec
```

L'icône vient de `app/icon.ico` : elle est intégrée à l'exe (raccourcis, barre des tâches, fenêtre) si le fichier existe.

Pour publier une nouvelle version : sur GitHub, **Releases** → **Draft a new release**, crée un tag (`v1.1`, etc.) et joins `dist\Generateur_Factures.exe`.

### Structure

```
├── app/
│   ├── generateur de facture.py   # interface (tkinter)
│   ├── data.py                    # sociétés, clients, banques, profils de Z, dossiers de sortie
│   ├── invoice_pdf.py             # PDF facture
│   ├── z_caisse_pdf.py            # PDF Z de caisse
│   ├── rib_pdf.py                 # PDF RIB
│   ├── icon.ico                   # icône de l'application
│   └── Azure-ttk-theme/           # thème graphique (MIT, rdbende/Azure-ttk-theme)
├── Generateur_Factures.spec       # configuration PyInstaller
├── installer.bat                  # build de l'exe + raccourci Bureau (développeurs)
├── lancer_factures.bat            # lancement depuis les sources
└── requirements.txt
```

Les données fictives (sociétés, clients, banques, libellés de lignes) se modifient dans `app/data.py`.

## Dépannage

- **« Windows a protégé votre ordinateur »** : Informations complémentaires → Exécuter quand même. L'exe n'est pas signé, d'où cet avertissement.
- **« Impossible d'écrire … ouvert dans un lecteur PDF »** : ferme le PDF concerné dans Acrobat ou Edge, puis relance la génération.
- **Rien ne se crée / erreur d'écriture** : l'exe est sans doute dans un dossier en lecture seule (partage réseau, Program Files). Déplace-le dans un dossier à toi.
- **`installer.bat` : « Python est introuvable »** (développeurs) : installe Python en cochant « Add python.exe to PATH », puis relance le script.
