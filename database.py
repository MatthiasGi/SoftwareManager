import os
import semver
import subprocess
import sys
import yaml

from software import Software


class Database:
    """
    Wrapper der als Container für die verwaltete Software dient. Statische
    Methoden hier ermöglichen die Verwaltung der enthaltenen Software.
    """

    # Pfad zur Datenbankdatei, in der sich der aktuelle Stand der Datenbank
    # befinden soll.
    file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'database.yml')

    # Eigentliche Datenbank. Ein Dictionary, das zu jeder Software (Bezeichner:
    # Slug der Software) ein weiteres Dictionary enthält. Darin wird die
    # aktuell installierte Version unter `version` gespeichert. So ist ein
    # Update-Mechanismus möglich. Alle weiteren Informationen werden aus der
    # Repository gelesen.
    database = None

    # Dictionary der aktuell in der Repository enthaltenen Software. Dabei wird
    # als Key der Slug der Software genutzt, als Value das Softwareobjekt
    # selbst. Software die hier, aber nicht in der `database` enthalten ist,
    # muss folglich noch installiert werden.
    software = {}

    # Ordner der Repository. In diesem befinden sich die einzelnen Software-
    # Deskriptoren.
    repository = None

    @staticmethod
    def init():
        """
        Initialisiert die Datenbank, sofern das noch nicht geschehen ist und
        muss im Idealfall sofort aufgerufen werden.
        """
        if Database.database is not None: return
        if not os.path.exists(Database.file):
            with open(Database.file, 'w'): pass
        Database.load()

        # Melde die Datenbank für Statusänderungen der enthaltenen Software bei
        # der Klasse an. So können Installations-, Deinstallations- und Update-
        # Events abgegriffen werden.
        Software.registerStateListener(Database.softwareUpdated)

    @staticmethod
    def readSoftware(repository):
        """
        Liest die Software in einer Repository ein und speichert das übergebene
        Verzeichnis für spätere Verwendung zwischen.

        Parameters
        ----------
        repository : str
            Pfad zum Verzeichnis mit allen Softwaredeskriptoren.
        """
        Database.repository = repository
        dirs = [f.path for f in os.scandir(repository) if f.is_dir()]
        for d in dirs:
            s = Software(d)
            s.setState(Software.INSTALLED if Database.hasSoftware(s) else
                       Software.UNINSTALLED)
            Database.software[s.slug] = s

    @staticmethod
    def load():
        """
        Lädt die Datenbank neu ein.
        """
        with open(Database.file, 'r') as f:
            Database.database = yaml.full_load(f) or {}

    @staticmethod
    def save():
        """
        Speichert die Datenbank in der entsprechenden Datei.
        """
        with open(Database.file, 'w') as f:
            yaml.dump(Database.database, f)

    @staticmethod
    def softwareUpdated(software):
        """
        Reagiert auf eine Statusänderung einer Software.

        Parameters
        ----------
        software : Software
            Das Software-Objekt, das seinen Status geändert hat.
        """
        if software.state == Software.INSTALLED \
                and not Database.hasSoftware(software):
            # Software wurde neu installiert und muss der Datenbank hinzugefügt
            # werden.
            Database.database[software.slug] = {
                'version': str(software.getVersion()),
            }

        elif software.state == Software.UNINSTALLED \
                and Database.hasSoftware(software):
            # Software wurde deinstalliert und muss der Datenbank entfernt
            # werden.
            del Database.database[software.slug]

        elif software.state == Software.UPDATED:
            # Software hat die Version geändert.
            Database.database[software.slug]['version'] = \
                str(software.getVersion())

        else: return

        # Sollte eine Änderung an der Datenbank vorgenommen worden sein, muss
        # diese gespeichert werden.
        Database.save()

    @staticmethod
    def hasSoftware(software):
        """
        Ermittelt, ob die übergebene Software in der Datenbank vorhanden ist.

        Parameters
        ----------
        software : Software
            Das Software-Objekt, dessen Existenz in der Datenbank überprüft
            werden soll.

        Returns
        -------
        Ob die übergebene Software in der Datenbank vorhanden ist.
        """
        return software.slug in Database.database

    @staticmethod
    def updateSoftware():
        """
        Löst die Update-Sequenz für die Software aus, deren Version aktueller
        als die in der Datenbank hinterlegten ist.
        """
        for slug, software in Database.software.items():
            currVer = Database.database[slug].get('version') or '0.0.0'
            if software.getVersion() > semver.VersionInfo.parse(currVer):
                software.update(currVer)

    @staticmethod
    def getOldSoftware():
        """
        Gibt die Slugs veralteter Software zurück, die nicht mehr in der
        Repository ist, aber noch in der Datenbank.
        """
        return [s for s in Database.database.keys()
                if s not in Database.software]

    @staticmethod
    def isSlugSafeToUninstall(slug):
        """
        Ermittelt, ob die mit dem entsprechenden Slug bezeichneten Software
        deinstalliert werden kann, oder ob es Abhängigkeiten gibt.

        Parameters
        ----------
        slug : str
            Slug der zu überprüfenden Software.

        Returns
        -------
        False, sofern es mindestens eine Abhängigkeit in der noch installierten
        und nicht veralteten Software gibt. True, falls dies nicht der Fall ist
        und die Software damit sicher deinstalliert werden kann.
        """
        for software in Database.software.values():
            if slug in software.getDependencies(): return False
        return True

    @staticmethod
    def uninstallOldSlug(slug):
        """
        Deinstalliert veraltete Software nach Slug. Wenn es Abhängigkeiten von
        dieser Software gibt, wird der Vorgang abgebrochen.
        """
        if slug in Database.software: return
        if not Database.isSlugSafeToUninstall(slug): return
        uninstaller = os.path.join(Software.dirUninstaller, slug + '.py')
        if os.path.exists(uninstaller):
            subprocess.check_call([sys.executable, slug + '.py',
                                   Software.dirTarget],
                                  cwd=Software.dirUninstaller)
            os.remove(uninstaller)
        del Database.database[slug]
        Database.save()


Database.init()
