import datetime
import json
import os

# Onglets qui ont leurs propres modèles.
TABS = ("facture", "z", "rib")
FORMAT_VERSION = 1


class TemplateStore:
    """Modèles enregistrés et dernière session, dans un fichier JSON à côté de l'exe.

    Structure : {"version": 1, "modeles": {onglet: {nom: état}}, "derniere_session": {onglet: état}}.
    Le fichier est relu avant chaque écriture : deux fenêtres ouvertes ne s'écrasent pas leurs modèles.
    """

    def __init__(self, path):
        self.path = path
        self.templates = {tab: {} for tab in TABS}
        self.last_session = {}
        # Nom de la copie de sauvegarde si le fichier était illisible au chargement.
        self.backup_name = None
        self._load()

    def _load(self):
        self.templates = {tab: {} for tab in TABS}
        self.last_session = {}
        try:
            with open(self.path, encoding="utf-8") as f:
                content = json.load(f)
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            content = None
        if not isinstance(content, dict):
            self._backup_unreadable()
            return
        templates = content.get("modeles")
        if isinstance(templates, dict):
            for tab in TABS:
                by_name = templates.get(tab)
                if isinstance(by_name, dict):
                    self.templates[tab] = {
                        str(name): state for name, state in by_name.items() if isinstance(state, dict)
                    }
        session = content.get("derniere_session")
        if isinstance(session, dict):
            self.last_session = {tab: state for tab, state in session.items() if tab in TABS and isinstance(state, dict)}

    def _backup_unreadable(self):
        """Met de côté un fichier corrompu plutôt que de l'écraser à la prochaine sauvegarde."""
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"{os.path.splitext(self.path)[0]}_illisible_{stamp}.json"
        try:
            os.replace(self.path, backup)
            self.backup_name = os.path.basename(backup)
        except OSError:
            pass

    def _write(self):
        content = {"version": FORMAT_VERSION, "modeles": self.templates, "derniere_session": self.last_session}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def names(self, tab):
        return sorted(self.templates[tab], key=str.casefold)

    def get(self, tab, name):
        return self.templates[tab].get(name)

    def save(self, tab, name, state):
        self._load()
        self.templates[tab][name] = state
        self._write()

    def delete(self, tab, name):
        self._load()
        self.templates[tab].pop(name, None)
        self._write()

    def save_session(self, states):
        self._load()
        self.last_session = states
        self._write()
