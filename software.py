import os
import semver
import subprocess
import sys
import yaml


class Software:
    """
    Objekt, das eine Software in der Repository (bewusst: nicht in der
    Datenbank) repräsentiert. Methoden zur Verwaltung dieser Software werden
    hier zur Verfügung gestellt.

    Attributes
    ----------
    path : str
        Pfad zum Repository-Ordner, in dem sich die Deskriptoren für diese
        Software befinden.
    slug : str
        Eindeutige Kurzbezeichnung für diese Software, über die sie auch immer
        wieder identifiziert wird.
    config : dict
        Enthält Konfigurationsparameter aus der Repository.
    state : int
        Aktueller Status der Software, kodiert durch statische Konstanten
        (s.u.).
    error_msg : str
        Fehlermeldung, die beim Setzen des Fehlerstatus mit Informationen
        befüllt wird.
    """

    # Liste mit methoden, die über Änderungen eines Softwarestatus informiert
    # werden wollen.
    stateListeners = []

    # Kodierung der verschiedenen, zur Verfügung stehenden Status, die die
    # Software annehmen kann.
    UNKNOWN = -1
    UNINSTALLED = 0
    INSTALLING_PIP_DEPENDENCIES = 2
    INSTALLING_DEPENDENCIES = 4
    INSTALLING = 5
    INSTALLED = 10
    UPDATING = 15
    UPDATED = 20
    AUTOSTARTED = 30
    REPEATEDRUN = 40
    ERROR = -2

    def __init__(self, path):
        """
        Erstellt das Software-Objekt, das sich am entsprechenden Pfad befindet.

        Parameters
        ----------
        path : str
            Pfad, in dem sich die zu verwaltende Software befindet.
        """
        self.path = path
        self.slug = os.path.basename(os.path.normpath(self.path))
        with open(os.path.join(self.path, 'config.yml'), 'r') as f:
            self.config = yaml.full_load(f) or {}
        self.state = Software.UNKNOWN

    @staticmethod
    def setTargetDir(dirTarget):
        """
        Setzt das Zielverzeichnis als statische Variable, in die die Software
        später installiert werden soll. Die Repository dient hier tatsächlich
        nur zur Verwaltung. Das Verzeichnis wird später den relevanten Skripten
        übergeben.

        Parameters
        ----------
        dirTarget : str
            Verzeichnis, in dem Software installiert werden soll.
        """
        Software.dirTarget = dirTarget

    def getName(self):
        """
        Ermittelt einen Namen für die Software: Falls vorhanden wird dieser aus
        der Konfiguration übernommen, ansonsten wird der Slug genutzt.

        Returns
        -------
        Einen Namen für die Software.
        """
        return self.config.get('name') or self.slug

    def getDependencies(self):
        """
        Gibt an, von welcher Software diese hier abhängig ist, welche also
        zuerst installiert sein müssen.

        Returns
        -------
        Liste der Slugs von Software, die vor dieser hier installiert sein
        muss.
        """
        return self.config.get('dependencies') or []

    def getPipDependencies(self):
        """
        Gibt an, welche Pip-Pakete für diese Software installiert sein müssen.

        Returns
        -------
        Namen der Pip-Pakete, von der diese Software abhängig ist.
        """
        return self.config.get('pip') or []

    def setState(self, state):
        """
        Setzt den Status der Software neu. Ferner werden alle Methoden über
        diese Änderungen informiert, die zuvor registriert wurden.

        Parameters
        ----------
        state : int
            Neuer Status der Software.
        """
        self.state = state
        for method in Software.stateListeners: method(self)

    def install(self):
        """
        Installiert eine Software mithilfe des Installationsskripts in der
        Repository und versucht gleichzeitig, die Abhängigkeiten zu
        befriedigen.
        """
        if self.state != Software.UNINSTALLED: return
        from database import Database

        # PIP-Dependencies
        self.setState(Software.INSTALLING_PIP_DEPENDENCIES)
        for d in self._getDeps('pip'):
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', d])

        # Dependencies
        self.setState(Software.INSTALLING_DEPENDENCIES)
        for d in self._getDeps('dependencies'):
            software = Database.software.get(d)
            if software is None:
                return self.setError('Abhängigkeit ist nicht in der '
                                     'Repository.')
            software.install()
            if not software.isInstalled():
                return self.setError('Installation konnte nicht abgeschlossen '
                                     'werden.')

        # Installing
        if not os.path.exists(os.path.join(self.path, 'install.py')):
            return self.setError('Kein Installationsskript vorhanden.')
        self.setState(Software.INSTALLING)
        subprocess.check_call([sys.executable, 'install.py',
                               Software.dirTarget], cwd=self.path)

        # Fertig installiert
        self.setState(Software.INSTALLED)

    def update(self, currentVersion):
        """
        Updatet die Software mithilfe des Update-Skripts oder wenn dieses nicht
        vorhanden ist einer Neuinstallation.

        Parameters
        ----------
        currentVersion : semver.VersionInfo
            Version der Software, wie sie gerade laut Datenbank installiert
            ist. Diese nützliche Information wird an das Update-Skript
            übergeben, damit es versionsabhängige Aktionen durchführen kann.
        """

        if not self.isInstalled(): return
        self.setState(Software.UPDATING)

        if os.path.exists(os.path.join(self.path, 'update.py')):
            # Wenn es ein Updateskript gibt: Ausführen
            subprocess.check_call([sys.executable, 'update.py',
                                   Software.dirTarget, str(currentVersion)],
                                  cwd=self.path)
        else:
            # Wenn es kein Updateskript gibt, dann eben löschen und neu
            # installieren
            self.uninstall()
            if self.isInstalled():
                return self.setError('Deinstallierskript hat nicht '
                                     'funktioniert.')
            self.install()

        self.setState(Software.UPDATED)

    def uninstall(self):
        """
        Deinstalliert die Software anhand des Deinstallationsskripts.
        """
        if not self.isInstalled(): return
        if not os.path.exists(os.path.join(self.path, 'uninstall.py')): return
        subprocess.check_call([sys.executable, 'uninstall.py',
                               Software.dirTarget], cwd=self.path)
        self.setState(Software.UNINSTALLED)

    def setError(self, msg):
        """
        Setzt eine Fehlermeldung und den Fehlerstatus der Software.

        Parameters
        ----------
        msg : str
            Nachricht, die als Fehlergrund hinterlegt werden soll.
        """
        self.error_msg = msg
        self.setState(Software.ERROR)

    def isInstalled(self):
        """
        Ermittelt, ob die Software aktuell installiert ist.

        Returns
        -------
        Ob die Software laut Status installiert ist.
        """
        return self.state >= Software.INSTALLED

    @staticmethod
    def registerStateListener(method):
        """
        Statische Methode, die eine andere Methode registriert. Diese wird dann
        immer über Statusänderungen aller Software-Instanzen informiert.

        Parameters
        ----------
        method : func(Software)
            Eine Methode, die über Statusänderungen informiert wird, indem sie
            als Parameter das betroffene Softwareobjekt übergeben bekommt.
        """
        Software.stateListeners.append(method)

    def hasError(self):
        """
        Ermittelt, ob sich die Software in einem Fehlerzustand befindet.

        Returns
        -------
        Ob sich die Software in einem Fehlerstatus befindet.
        """
        return self.state in [Software.ERROR, Software.UNKNOWN]

    def getVersion(self):
        """
        Ermittelt die Version der Software in der Repository (also ausdrücklich
        nicht die der ggf. aktuell installierten).

        Returns
        -------
        semver.VersionInfo-Objekt mit der aktuell verfügbaren Versionsnummer
        laut Repository.
        """
        return semver.VersionInfo.parse(self.config.get('version', '0.0.0'))
