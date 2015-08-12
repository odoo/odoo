# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class Stok_Move(models.Model):
    _inherit = 'stock.move'

    subproduct_id = fields.Many2one('mrp.subproduct', 'Subproduct',
        help="Subproduct line that generated the move in a manufacturing order")
