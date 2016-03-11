# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp.addons.decimal_precision as dp
from openerp import api, fields, models
from openerp.tools.translate import _
from openerp.exceptions import UserError
from openerp.tools import float_round

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    priority = fields.Selection(AVAILABLE_PRIORITIES, help="Gives the sequence order when displaying a list of tasks.")