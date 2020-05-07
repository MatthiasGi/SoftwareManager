from colorama import Fore, Style
import colorama
import os
import subprocess

from config import Config
from database import Database
from software import Software

"""
Zusammenfassung von Funktionen, die sich mit der Ausgabe von Informationen auf
der Konsole beschäftigen. Dabei wird hier im Wesentlichen der gesamte
Kontrollfluss des Programms abgehandelt.
"""


def init():
    """
    Bereitet die Ausgabe vor, indem es dem `colorama`-Modul die
    platformunabhängige Ausführung ermöglicht.
    """
    colorama.init()


def deinit():
    """
    Setzt die Ausgabe zurück, indem es dem `colorama`-Modul einen
    entsprechenden Befehl gibt.
    """
    colorama.deinit()


def clear():
    """
    Bereinigt die Konsole vollständig.
    """
    os.system('cls||clear')


def header(headline):
    """
    Gibt eine Überschrift aus, die zentriert dargestellt wird.

    Parameters
    ----------
    headline : str
        Auszugebene Überschrift (sollte im Idealfall nicht länger als 78
        Character sein).
    """
    print(Fore.BLUE + '*' * 80)
    print('*{:^78}*'.format(headline))
    print('*' * 80)
    print(Style.RESET_ALL)


def loadSoftware():
    """
    Lädt Konfiguration und Softwareliste ein.
    """
    print('Lade Konfiguration: ', end='')
    config = Config()
    # Die Konfigurationsparameter `repository` und `target` bestimmen, in
    # welchem Ordner sich die Quelle (Repository) und in welcher sich die
    # Installationen (Target) befinden.
    config.checkParams('repository', 'target')
    Software.setTargetDir(config.get('target'))
    print(Fore.GREEN + 'Ok' + Style.RESET_ALL)

    # Repository aktualisieren
    print('Aktualisiere Repository…')
    subprocess.check_call(['git', 'pull'], cwd=config.get('repository'))

    # Nun die Software einlesen
    print('Lese Software ein: ', end='')
    Database.readSoftware(config.get('repository'))
    # Damit der Nutzer auf der Konsole über Statusänderungen informiert werden
    # kann, wird hier eine Ausgabefunktion für die Information über
    # Statusänderungen registriert.
    Software.registerStateListener(updateSoftware)
    print(Fore.GREEN + 'Ok' + Style.RESET_ALL)

    print()


def updateSoftware(software):
    """
    Reagiert auf die Statusänderung einer Software mit einer entsprechenden
    Ausgabe.

    Parameters
    ----------
    software : Software
        Gibt eine Information über die Statusänderung der Software aus, bei
        Fehler-Zustand mit entsprechender Nachricht.
    """
    print(software.getName() + ': ' + getSoftwareState(software))
    if software.hasError():
        print(Fore.RED + software.error_msg + Style.RESET_ALL)
        exit()


def printSoftwareTable():
    """
    Gibt eine Tabelle mit aller in der Repository befindlichen Software mit
    ihrem jeweiligen Zustand aus.
    """
    print()
    print('{:^50}'.format('Software') + Style.DIM + '|' + Style.NORMAL
          + '{:^29}'.format('Status'))
    print(Style.DIM + '-' * 50 + '|' + '-' * 29 + Style.NORMAL)
    for slug, software in Database.software.items():
        print(' {:<49}'.format(software.getName()) + Style.DIM + '|'
              + Style.NORMAL + ' {:<28}'.format(getSoftwareState(software)))


def getSoftwareState(software):
    """
    Ermittelt den Status einer Software als ausgebbaren String mit ggf.
    hilfreicher Farbcodierung.

    Parameters
    ----------
    software : Software
        Software, deren Status überprüft werden soll.

    Returns
    -------
    String, der per `print()` ausgebbar ist und den Status der übergebenen
    Software repräsentiert.
    """
    names = {
        Software.UNKNOWN: 'UNBEKANNT',
        Software.UNINSTALLED: 'Nicht installiert',
        Software.INSTALLING_PIP_DEPENDENCIES:
            'Installiere PIP-Abhängigkeiten…',
        Software.INSTALLING_DEPENDENCIES: 'Installiere Abhängigkeiten…',
        Software.INSTALLING: 'Installiere…',
        Software.INSTALLED: 'Installiert',
        Software.UPDATING: 'Aktualisiere…',
        Software.UPDATED: 'Aktualisiert',
        Software.AUTOSTARTED: 'Automatisch gestartet',
        Software.REPEATEDRUN: 'Wird wiederholt gestartet',
        Software.ERROR: 'FEHLER',
    }

    state = names[software.state]
    if software.hasError(): state = Fore.RED + state + Style.RESET_ALL
    return state


def startInstalls():
    """
    Startet die Installationen der nicht installierten Software begleitet mit
    entsprechender Ausgabe.
    """
    # Zu installierende Software ermitteln. Falls keine vorhanden, gibt es auch
    # nichts zu tun.
    software = [s for _, s in Database.software.items() if not s.isInstalled()]
    if len(software) < 1: return

    # Ausgabe einer kurzen Information und Installation aller betroffenen
    # Software.
    print()
    print('{:*^80}'.format(' Starte Installationen… '))
    for s in software: s.install()
    print('{:*^80}'.format(' Installationen abgeschlossen '))

    # Softwaretabelle nachher noch einmal ausgeben.
    printSoftwareTable()


def startUpdates():
    """
    Startet die Aktualisierungen aller betoffenen Software.
    """
    print()
    print('{:*^80}'.format(' Starte Aktualisierungen… '))
    print(Fore.BLUE + 'Überprüfe einzelne Einträge…' + Style.RESET_ALL)
    Database.updateSoftware()
    print('{:*^80}'.format(' Aktualisierungen abgeschlossen '))
    printSoftwareTable()
