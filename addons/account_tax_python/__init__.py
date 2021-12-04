# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    code_taxes = env['account.tax'].search([('amount_type', '=', 'code')])
    code_taxes.write({'amount_type': 'percent', 'active': False})

    _logger.warning("The following taxes have been archived following 'account_tax_python' module uninstallation: %s" % code_taxes.ids)
