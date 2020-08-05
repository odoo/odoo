#odoo.loggers.handlers. -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import warnings
import odoo
from .func import lazy


@lazy
def config():
    warnings.warn(
        "The configuration have been moved from odoo.tools.config to "
        "odoo.config. Please import the later.",
        DeprecationWarning, stacklevel=4,
    )
    return odoo.config
