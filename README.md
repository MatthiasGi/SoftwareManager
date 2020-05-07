# SoftwareManager
Tool, das Skripte automatisiert installieren und ausführen kann. Zum Ausführen
`SoftwareManager.py` starten, `main.py` führt vorher noch ein `git pull` durch.

## Voraussetzungen
Damit dieses Programm vernünftig laufen kann, benötigt es eine Python-Umgebung.

## Repository
Das Skript benötigt genau eine Repository. Diese ist im Idealfall ein
Verzeichnis, das sich in einer Git-Repository befindet. Der Aufbau ist
bespielhaft dem Ordner `repository` zu entnehmen: Jede Software erhält einen
eigenen Ordner, der als Namen ein sogenanntes *Slug* erhält: Ein eindeutiger
String, der die Software auszeichnet.

In dem Repository gibt es nun eine Ansammlung von Dateien, die eigene Zwecke
erfüllen. Dies sind im Einzelnen:

### Allgemeine Informationen: config.yml
Die Konfigurationsdatei enthält wichtige Informationen für den Programmfluss.
Es handelt sich um eine einfache YAML-Datei beispielsweise mit diesem Inhalt:
```YAML
name: 'Testsoftware'
version: '1.0.0'
pip: ['numpy', 'scipy']
dependencies: ['testdependency']
```
Folgende Bedeutung haben die einzelnen Werte:
- **name**: Ein lesbarer Name, der dem Nutzer statt des Slugs angezeigt werden
  kann
- **version**: Eine Versionsnummer nach
  [Semantic Versioning 2.0.0](https://semver.org/lang/de/spec/v2.0.0.html), die
  zur Versionierung der Software genutzt werden kann. Steht in der Repository
  eine aktuellere Version als in der Datenbank zur Verfügung, wird sie
  geupdatet.
- **pip**: Liste von PIP-Paketen, von der die Software abhängt. Werden vor der
  Ausführung des Installationsskripts installiert und können daher auch
  Abhängigkeiten dieses Skripts enthalten.
- **dependencies**: Liste von Software-Slugs, von der diese Software abhängt.
  Werden vor der Ausführung des Installationsskripts installiert.

### Installationsskript: install.py
Das Installationsskript soll die Installation der eigentlichen Software
vornehmen. Es bekommt dafür als Kommandozeilenparameter das Verzeichnis
übergeben, in das die Installation vorgenommen werden soll. Als
Ausführungsverzeichnis wird der Unterordner der Software innerhalb der
Repository genutzt.

### Deinstallationsskript: uninstall.py
Soll die Software restlos löschen. Dieses Skript wird bei der Installation in
einen Ordner der Datenbank kopiert, um ggf. die Deinstallation der Software
durchführen zu können, die nötig wird, wenn sich eine Software plötzlich nicht
mehr in der Repository befindet. Das Ausführungsverzeichnis ist immer der
Ordner mit den gecachten Deinstallationsskripten.

### Updateskript: update.py (optional)
Ist dieses Skript vorhanden, wird es genutzt, um eine Software zu updaten.
Dafür wird im das Zielverzeichnis und die Versionsnummer der aktuell
installierten Software als Parameter übergeben. Um die Verwaltung des
Deinstallationsskripts muss sich das Update-Skript keine Gedanken machen.

Ist das Skript nicht vorhanden, wird die Software erst deinstalliert und
anschließend erneut installiert.
