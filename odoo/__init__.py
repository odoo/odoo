# -*- coding: utf-8 -*-
# ruff: noqa: E402, F401
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" OpenERP core library."""

# ----------------------------------------------------------
# odoo must be a namespace package for odoo.addons to become one too
# https://packaging.python.org/guides/packaging-namespace-packages/
# ----------------------------------------------------------
import pkgutil
import os.path
__path__ = [
    os.path.abspath(path)
    for path in pkgutil.extend_path(__path__, __name__)
]

import sys
MIN_PY_VERSION = (3, 10)
MAX_PY_VERSION = (3, 12)
assert sys.version_info > MIN_PY_VERSION, f"Outdated python version detected, Odoo requires Python >= {'.'.join(map(str, MIN_PY_VERSION))} to run."

# ----------------------------------------------------------
# Shortcuts
# ----------------------------------------------------------
# store file names from which the warning was raised
# used to stop raising warnings after X times
_GLOBAL_VARIABLE_WARNING = set()


def __getattr__(name: str):
    """Get variables from the odoo module and show warnings"""
    match name:
        case 'SUPERUSER_ID':
            module_name = 'odoo.api'
        case _:
            raise AttributeError(f"Module {__name__!r} has not attribute {name!r}.")

    # import the specific package (not just odoo)
    module = __import__(module_name, fromlist=module_name.split('.'))

    import inspect  # noqa: PLC0415
    import warnings  # noqa: PLC0415

    if len(_GLOBAL_VARIABLE_WARNING) < 10:
        # cannot import odoo.tools.lazy here (results in circular dependency)
        warnings.warn(f"You'll find {name!r} at {module.__name__!r}", DeprecationWarning)
        frame = inspect.currentframe().f_back
        _GLOBAL_VARIABLE_WARNING.add(frame.f_code.co_filename)
    return getattr(module, name)


def registry(database_name=None):
    """
    Return the model registry for the given database, or the database mentioned
    on the current thread. If the registry does not exist yet, it is created on
    the fly.
    """
    import warnings  # noqa: PLC0415
    warnings.warn("Since 18.0: call odoo.modules.registry.Registry directly", DeprecationWarning, stacklevel=2)
    if database_name is None:
        import threading
        database_name = threading.current_thread().dbname
    return modules.registry.Registry(database_name)


# ----------------------------------------------------------
# Import tools to patch code and libraries
# required to do as early as possible for evented and timezone
# ----------------------------------------------------------
from . import _monkeypatches
_monkeypatches.patch_all()


# ----------------------------------------------------------
# Imports
# ----------------------------------------------------------
from . import upgrade  # this namespace must be imported first
from . import addons
from . import conf
from . import loglevels
from . import modules
from . import netsvc
from . import osv
from . import release
from . import service
from . import sql_db
from . import tools

# ----------------------------------------------------------
# Model classes, fields, api decorators, and translations
# ----------------------------------------------------------
from . import models
from . import fields
from . import api
from odoo.tools.translate import _, _lt
from odoo.fields import Command
