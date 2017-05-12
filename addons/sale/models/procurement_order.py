# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
