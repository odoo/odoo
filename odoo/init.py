# ruff: noqa: E402, F401
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Odoo initialization. """

import sys
from .release import MIN_PY_VERSION
assert sys.version_info > MIN_PY_VERSION, f"Outdated python version detected, Odoo requires Python >= {'.'.join(map(str, MIN_PY_VERSION))} to run."

# ----------------------------------------------------------
# Import tools to patch code and libraries
# required to do as early as possible for evented and timezone
# ----------------------------------------------------------
from . import _monkeypatches
_monkeypatches.patch_init()

# ----------------------------------------------------------
# Shortcuts
# Expose them at the `odoo` namespace level
# ----------------------------------------------------------
import odoo
from .orm.commands import Command
from .orm.utils import SUPERUSER_ID
from .tools.translate import _, _lt

odoo.SUPERUSER_ID = SUPERUSER_ID
odoo._ = _
odoo._lt = _lt
odoo.Command = Command
