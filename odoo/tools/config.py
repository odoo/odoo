#odoo.loggers.handlers. -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import warnings
warnings.warn(
    "The configuration have been moved from odoo.tools.config to "
    "odoo.config. Please import the later.",
    DeprecationWarning,
)

from odoo.config import config
