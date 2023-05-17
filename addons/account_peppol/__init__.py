# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo.exceptions import UserError

def pre_init_hook(env):
    if env['ir.config_parameter'].get_param('account_peppol.edi.mode', False) != 'test':
        raise UserError("This module is not ready to be installed.")
