# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class EventBoothConfigurator(models.TransientModel):
    _name = 'event.booth.configurator'
    _description = 'Event Booth Configurator'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', readonly=True)
    event_id = fields.Many2one('event.event', string='Event', required=True)
    event_booth_id = fields.Many2one('event.booth', string='Event Booth', required=True)
    event_booth_slot_ids = fields.Many2many('event.booth.slot', string='Booth Slot', required=True)
