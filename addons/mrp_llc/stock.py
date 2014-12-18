# -*- coding: utf-8 -*-
# See __openerp__.py file for full copyright and licensing details.

from openerp import fields, models


class stock_warehouse_orderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'
    _order = 'sequence'

    sequence = fields.Integer(string='Low Level Code', readonly=True)
