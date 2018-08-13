# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from odoo import api, SUPERUSER_ID


def set_transfer_so_reference(cr, registry):
    # so_reference_type default values is 'none' except for wire transfer.
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.acquirer'].search([('provider', '=', 'transfer')]).write({'so_reference_type': 'so_name'})
