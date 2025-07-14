# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import utils
from . import action
from . import binary
from . import database
from . import dataset
from . import domain
from . import export
from . import json
from . import home
from . import model
from . import pivot
from . import profiling
from . import report
from . import session
from . import vcard
from . import view
from . import webclient
from . import webmanifest


def __getattr__(attr):
    if attr != 'main':
        raise AttributeError(f"Module {__name__!r} has not attribute {attr!r}.")

    import sys  # noqa: PLC0415
    mod = __name__ + '.main'
    if main := sys.modules.get(mod):
        return main

    # can't use relative import as that triggers a getattr first
    import odoo.addons.web.controllers.main as main  # noqa: PLC0415
    return main
