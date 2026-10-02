# Générateur de documents de test

Application Windows qui génère des **factures**, des **Z de caisse** et des **RIB** fictifs au format PDF, pour alimenter des tests (saisie, OCR, rapprochements…).

## Installation

Quatre façons de faire, au choix. Pour les options 1 à 3, pas besoin de Python : l'exe est autonome.
Les options 2 et 3 font exactement la même chose : elles installent l'exe dans **`Documents\Generateur de factures\`** et créent le raccourci **« Generateur de factures »** sur le Bureau.

### Option 1 : téléchargement manuel

1. Télécharge **`Generateur_Factures.exe`** depuis la [dernière Release](https://github.com/Dominik4848/generateur-facture-test/releases/latest).
2. Crée un dossier à toi pour l'application, par exemple `Documents\Generateur de factures\`, et mets l'exe dedans.
   Les PDF seront créés dans ce même dossier : évite donc le dossier Téléchargements et les partages réseau.
3. Clic droit sur l'exe → **Envoyer vers** → **Bureau (créer un raccourci)**.
   Sous Windows 11, passe d'abord par **Afficher d'autres options**.

Au premier lancement, Windows SmartScreen affiche « Windows a protégé votre ordinateur » : clique sur **Informations complémentaires** → **Exécuter quand même**.
L'exe n'est pas signé, d'où l'avertissement. Il ne s'affiche qu'une fois.

### Option 2 : une commande à copier-coller

Ouvre **PowerShell** (touche Windows, tape `PowerShell`, Entrée), colle la commande ci-dessous et valide avec Entrée :

```powershell
$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $d=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Generateur de factures'; $exe=Join-Path $d 'Generateur_Factures.exe'; New-Item -ItemType Directory -Force $d | Out-Null; Invoke-WebRequest 'https://github.com/Dominik4848/generateur-facture-test/releases/latest/download/Generateur_Factures.exe' -OutFile ($exe + '.part') -UseBasicParsing; Move-Item -Force ($exe + '.part') $exe; Unblock-File $exe; $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Generateur de factures.lnk')); $s.TargetPath=$exe; $s.WorkingDirectory=$d; $s.IconLocation=$exe; $s.Save(); Write-Host ('Installe dans ' + $d + ' - raccourci cree sur le Bureau.')
```

La commande télécharge la dernière version, la débloque (pas d'avertissement SmartScreen), puis crée le raccourci.

### Option 3 : le script `installer.bat`

Télécharge [**`installer.bat`**](https://github.com/Dominik4848/generateur-facture-test/releases/latest/download/installer.bat) et double-clique dessus.
Il lance exactement la commande de l'option 2. Windows peut demander une confirmation la première fois, car le fichier vient d'Internet.

### Option 4 : construire l'exe soi-même

Prérequis : [Python 3.10+](https://www.python.org/downloads/) installé en cochant **« Add python.exe to PATH »**, et Git.

```
git clone https://github.com/Dominik4848/generateur-facture-test.git
cd generateur-facture-test
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm Generateur_Factures.spec
```

L'exe est créé dans `dist\Generateur_Factures.exe`. Range-le ensuite dans un dossier à toi, comme à l'option 1.
Le script **`build.bat`** enchaîne ces étapes (dépendances, build, raccourci sur le Bureau) en un double-clic.

### Mettre à jour

- **Options 2 et 3** : relance la commande ou `installer.bat`, application fermée. L'exe est remplacé, le raccourci et les PDF sont conservés.
- **Options 1 et 4** : remplace l'exe **dans le même dossier**, application fermée.

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

Double-clic sur **`build.bat`** (voir aussi l'option 4 de l'installation) : le script installe les dépendances, construit `dist\Generateur_Factures.exe` et crée un raccourci vers cet exe sur ton Bureau.

L'icône vient de `app/icon.ico` : elle est intégrée à l'exe (raccourcis, barre des tâches, fenêtre) si le fichier existe.

Pour publier une nouvelle version : sur GitHub, **Releases** → **Draft a new release**, crée un tag (`v1.1`, etc.) et joins **deux fichiers** : `dist\Generateur_Factures.exe` et `installer.bat`.
Garde exactement ces noms : les options 2 et 3 téléchargent `releases/latest/download/Generateur_Factures.exe`, et le lien de l'option 3 pointe vers `releases/latest/download/installer.bat`.

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
├── installer.bat                  # installation depuis la dernière Release (options 2 et 3)
├── build.bat                      # build de l'exe + raccourci Bureau (option 4)
├── lancer_factures.bat            # lancement depuis les sources
└── requirements.txt
```

Les données fictives (sociétés, clients, banques, libellés de lignes) se modifient dans `app/data.py`.

## Dépannage

- **« Windows a protégé votre ordinateur »** : Informations complémentaires → Exécuter quand même. L'exe n'est pas signé, d'où cet avertissement. Les options 2 et 3 l'évitent.
- **Option 2 ou 3 : « Le Generateur de factures est ouvert » ou erreur de téléchargement** : ferme l'application et relance. Si l'erreur persiste, passe par l'option 1.
- **« Impossible d'écrire … ouvert dans un lecteur PDF »** : ferme le PDF concerné dans Acrobat ou Edge, puis relance la génération.
- **Rien ne se crée / erreur d'écriture** : l'exe est sans doute dans un dossier en lecture seule (partage réseau, Program Files). Déplace-le dans un dossier à toi.
- **`build.bat` : « Python est introuvable »** (option 4) : installe Python en cochant « Add python.exe to PATH », puis relance le script.
