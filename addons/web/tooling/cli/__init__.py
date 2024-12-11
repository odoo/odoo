import os
from pathlib import Path

TOOLING_PATH = Path(os.path.abspath(__file__)).parent.parent
ODOO_PATH = TOOLING_PATH.parent.parent.parent
CONFIG = {
    "odoo": ODOO_PATH,
}


def get_absolute_path(path):
    path_path = Path(path).expanduser()
    if path_path.is_absolute():
        return path_path
    return ODOO_PATH.joinpath(path)


commands = {}


def defineCommand(cls):
    name = cls.__name__.lower()
    commands[name] = cls
    return cls


def get_tooling(odoo=None):
    if odoo is None:
        odoo = CONFIG["odoo"]
    return odoo.joinpath("addons/web/tooling")


from . import jsconfig_command  # noqa: E402,F401
from . import jslint_command  # noqa: E402,F401
