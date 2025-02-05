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
from odoo.release import MIN_PY_VERSION
assert sys.version_info > MIN_PY_VERSION, f"Outdated python version detected, Odoo requires Python >= {'.'.join(map(str, MIN_PY_VERSION))} to run."

# ----------------------------------------------------------
# Shortcuts
# ----------------------------------------------------------

def registry(database_name=None):
    """
    Return the model registry for the given database, or the database mentioned
    on the current thread. If the registry does not exist yet, it is created on
    the fly.
    """
    import warnings  # noqa: PLC0415
    warnings.warn("Since 18.0: call odoo.modules.registry.Registry directly", DeprecationWarning, stacklevel=2)
    from . import modules  # noqa: PLC0415
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
# Export admin user constant
from .orm.utils import SUPERUSER_ID

# ----------------------------------------------------------
# Imports of directly exposed variables
# ----------------------------------------------------------
from odoo.tools.translate import _, _lt
from odoo.fields import Command
