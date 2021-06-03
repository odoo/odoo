# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class EventBoothConfigurator(models.TransientModel):
    _name = 'event.booth.configurator'
    _description = 'Event Booth Configurator'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', readonly=True)
    event_id = fields.Many2one('event.event', string='Event', required=True)
    event_booth_category_ids = fields.Many2many(related='event_id.event_booth_category_ids', readonly=True)
    event_booth_category_id = fields.Many2one('event.booth.category', string='Booth Category', required=True)
    event_booth_ids = fields.Many2many('event.booth', string='Booth', required=True)

    @api.onchange('event_id')
    def _onchange_event_id(self):
        if not self.env.context.get('default_event_id'):
            self.event_booth_category_id = False

    @api.onchange('event_booth_category_id')
    def _onchange_event_booth_category_id(self):
        if not self.env.context.get('default_event_booth_category_id'):
            self.event_booth_ids = False
