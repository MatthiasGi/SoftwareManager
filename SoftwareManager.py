from software import Software
from config import Config
import time
import output

def main():
    output.header('SoftwareManager')
    output.loadSoftware()
    output.printSoftwareTable()
    output.uninstallOldSoftware()
    output.startInstalls()
    output.startUpdates()

if __name__ == '__main__':
    output.init()
    main()
    output.deinit()
