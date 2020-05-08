import output


def main():
    output.header('SoftwareManager')
    output.loadSoftware()
    output.printSoftwareTable()
    output.uninstallOldSoftware()
    output.startInstalls()
    output.startUpdates()
    output.autostartSoftware()
    output.printSoftwareTable()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('Beende…')
        pass


if __name__ == '__main__':
    output.init()
    main()
    output.deinit()
    exit(0)
