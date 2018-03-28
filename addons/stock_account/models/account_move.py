# -*- coding: utf-8 -*-

from odoo import fields, models, _

from odoo.tools.float_utils import float_is_zero

from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_id = fields.Many2one('stock.move', string='Stock Move')
