# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Event(models.Model):
    _inherit = 'event.event'

    sale_order_lines_ids = fields.One2many(
        'sale.order.line', 'event_id',
        string='All sale order lines pointing to this event')
    sale_price_subtotal = fields.Monetary(string='Sales (Tax Excluded)', compute='_compute_sale_price_subtotal')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', readonly=True)

    @api.depends('company_id.currency_id',
                 'sale_order_lines_ids.price_subtotal', 'sale_order_lines_ids.currency_id',
                 'sale_order_lines_ids.company_id', 'sale_order_lines_ids.order_id.date_order')
    def _compute_sale_price_subtotal(self):
        for event in self:
            event.sale_price_subtotal = sum([
                event.currency_id._convert(
                    sale_order_line_id.price_subtotal,
                    sale_order_line_id.currency_id,
                    sale_order_line_id.company_id,
                    sale_order_line_id.order_id.date_order)
                for sale_order_line_id in event.sale_order_lines_ids
            ])

    def action_view_linked_orders(self):
        """ Redirects to the orders linked to the current events """
        sale_order_action = self.env.ref('sale.action_orders').read()[0]
        sale_order_action.update({
            'domain': [('state', '!=', 'cancel'), ('order_line.event_id', 'in', self.ids)],
            'context': {'create': 0},
        })
        return sale_order_action
