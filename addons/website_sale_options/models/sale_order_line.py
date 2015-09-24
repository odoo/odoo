# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    linked_line_id = fields.Many2one('sale.order.line', string='Linked Order Line', domain="[('order_id', '!=', order_id)]", ondelete='cascade')
    option_line_ids = fields.One2many('sale.order.line', 'linked_line_id', string='Options Linked')
