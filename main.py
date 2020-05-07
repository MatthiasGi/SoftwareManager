import os
import subprocess
import sys

# Startet das eigentliche Skript nachdem die Repository geupdated wurde.
def main():
    dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.check_call(['git', 'pull'], cwd=dir)
    subprocess.check_call([sys.executable, 'SoftwareManager.py'], cwd=dir)

if __name__ == '__main__':
    main()
