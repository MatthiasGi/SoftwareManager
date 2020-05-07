import os
import yaml


class Config:
    """
    Wrapper for configuration of the project.
    """

    # Path to the config-file
    filename = 'config.yml'

    def __init__(self):
        # If the file is non existent, create it as empty (values will be
        # inserted later on)
        if not os.path.exists(Config.filename):
            with open(Config.filename, 'w'):
                pass

        # Load the config and save it to an instance variable
        with open(Config.filename, 'r') as f:
            self.config = yaml.full_load(f) or {}

    def save(self):
        """
        Saves the configuration to the specified file.
        """
        with open(Config.filename, 'w') as f:
            yaml.dump(self.config, f)

    def get(self, param):
        """
        Retrieves a parameter from the config or None if it doesn't exist.

        Parameters
        ----------
        param : str
            Name of the parameter to return.

        Returns
        -------
        The value of the parameter or None if it doesn't exist.
        """
        if param in self.config:
            return self.config[param]
        return None

    def checkParams(self, *params):
        """
        Assures, that the given parameters are contained in the config. If
        they're not, the program will abort with a corresponding message and
        prepare the config-file to contain the parameters.

        Attributes
        ----------
        *params : list(str)
            Names of the parameters that should be contained in the
            config-file.
        """
        missing = []
        for p in params:
            if p in self.config and self.config[p] is not None:
                continue
            missing.append(p)
            self.config[p] = None

        if len(missing) > 0:
            self.save()
            print('ERROR: Missing config options:', ', '.join(missing))
            exit()
