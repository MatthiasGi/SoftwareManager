from datetime import datetime, timedelta
from glob import glob
import os
import semver
import shutil
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
    process : subprocess
        Objekt, das mit einer subprocess-Instanz befüllt ist, wenn die Software
        läuft. Kann beispielsweise genutzt werden, um die Software zu beenden.
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
    ERROR = -2

    # Zielverzeichnis, in dem Software installiert werden soll.
    dirTarget = ''

    # Verzeichnis, in dem Logdateien abgelegt werden sollen.
    dirLog = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')

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
        self.process = None

    @staticmethod
    def deleteOldLogs():
        """
        Löscht veraltete Logdateien im geteilten Verzeichnis aller Software.
        """
        files = glob(os.path.join(Software.dirLog, '*', '*.log'))
        killtime = (datetime.now() - timedelta(days=7)).timestamp()
        filesOld = [f for f in files if os.path.getmtime(f) < killtime]
        for f in filesOld: os.remove(f)

        # Nun leere Verzeichnisse ebenfalls löschen – gehören nämlich bestimmt
        # zu deinstallierter Software
        folders = glob(os.path.join(Software.dirLog, '*'))
        for folder in folders:
            if not os.path.isdir(folder): continue
            if os.listdir(folder): continue
            os.rmdir(folder)

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

        # Überprüfung, ob Installations- und Deinstallationsskript vorhanden
        # sind, denn ansonsten schlägt die Installation später fehl.
        if not os.path.exists(os.path.join(self.path, 'install.py')):
            return self.setError('Kein Installationsskript vorhanden.')
        if not os.path.exists(os.path.join(self.path, 'uninstall.py')):
            return self.setError('Kein Deinstallationsskript vorhanden.')

        # PIP-Dependencies
        self.setState(Software.INSTALLING_PIP_DEPENDENCIES)
        for d in self.getPipDependencies():
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', d])

        # Dependencies
        self.setState(Software.INSTALLING_DEPENDENCIES)
        for d in self.getDependencies():
            software = Database.software.get(d)
            if software is None:
                return self.setError('Abhängigkeit ist nicht in der '
                                     'Repository.')
            software.install()
            if not software.isInstalled():
                return self.setError('Installation konnte nicht abgeschlossen '
                                     'werden.')

        # Installationsskript ausführen
        self.setState(Software.INSTALLING)
        subprocess.check_call([sys.executable, 'install.py',
                               self.getTargetDir()], cwd=self.path)

        # Deinstallationsskript cachen
        self.cacheUninstaller()

        # Fertig installiert
        self.setState(Software.INSTALLED)

    def cacheUninstaller(self):
        """
        Sichert das Deinstallationsskript, damit dieses später ausgeführt
        werden kann, wenn beispielsweise die Software nicht mehr in der
        Repository vorhanden ist.
        """
        shutil.copyfile(os.path.join(self.path, 'uninstall.py'),
                        self.getUninstaller())

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
                                   self.getTargetDir(), str(currentVersion)],
                                  cwd=self.path)
            self.cacheUninstaller()
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
        uninstaller = self.getUninstaller()
        subprocess.check_call([sys.executable, os.path.basename(uninstaller),
                               self.getTargetDir()],
                              cwd=os.path.dirname(uninstaller))
        os.remove(uninstaller)
        self.setState(Software.UNINSTALLED)

    def getUninstaller(self):
        """
        Gibt den Pfad zum Deinstallationsskript dieser Software zurück.

        Returns
        -------
        Pfad, an dessen Stelle sich das Deinstallationsskript befinden sollte.
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'uninstaller', self.slug + '.py')

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

    def getTargetDir(self):
        """
        Gibt das für die aktuelle Software spezifische Zielverzeichnis zurück.

        Returns
        -------
        Das für diese Software spezifische Zielverzeichnis: globales
        Zielverzeichnis mit angehängtem Slug.
        """
        return os.path.join(Software.dirTarget, self.slug)

    def isRunnable(self):
        """
        Überprüft, ob die aktuelle Software ausführbar ist, also ein Skript in
        der Konfiguration bezeichnet ist, das beim Start des Managers nach der
        Installation und Aktualisierung gestartet werden soll.

        Returns
        -------
        Ob die Software ausgeführt werden möchte.
        """
        return self.config.get('run')

    def run(self):
        """
        Führt das Skript aus, das in der Konfiguration für diese Software unter
        dem Schlüssel `key` bezeichnet ist.
        """
        if not self.isRunnable(): return

        logpath = os.path.join(Software.dirLog, self.slug)
        if not os.path.exists(logpath): os.makedirs(logpath)
        basetime = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        logStdout = os.path.join(logpath, basetime + '_stdout.log')
        logStderr = os.path.join(logpath, basetime + '_stderr.log')

        with open(logStdout, 'wb', encoding='utf-8') as out, \
                open(logStderr, 'wb', encoding='utf-8') as err:
            self.process = subprocess.Popen(
                [sys.executable, self.config.get('run')],
                cwd=self.getTargetDir(), stdout=out, stderr=err)

        self.setState(Software.AUTOSTARTED)
