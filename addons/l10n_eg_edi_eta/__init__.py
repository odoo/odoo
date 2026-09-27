# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools
from . import wizards


def _l10n_eg_edi_eta_post_init(env):
    """Post init hook to set the default invoicing threshold for Egypt."""
    env['ir.config_parameter'].sudo().set_float('l10n_eg_edi_eta.invoicing_threshold', 150000.0)
