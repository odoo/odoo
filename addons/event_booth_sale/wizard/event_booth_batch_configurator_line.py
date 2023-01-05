# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class EventConfiguratorLine(models.TransientModel):
    """Event Booth Configuration"""
    _name = "event.booth.editor.line"
    _description = 'Edit Event Booth values on Sales Confirmation'
    _order = "id desc"

    editor_id = fields.Many2one('event.event.booth.configurator.batch')
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    event_booth_category_id = fields.Many2one(
        'event.booth.category', string='Booth Category', required=True,
        compute='_compute_event_booth_category_id', readonly=False, store=True)
    event_booth_ids = fields.Many2many(
        'event.booth', string='Booth', required=True,
        compute='_compute_event_booth_ids', readonly=False, store=True)
    event_id = fields.Many2one('event.event', string='Event', required=True)
    event_booth_category_available_ids = fields.Many2many(related='event_id.event_booth_category_available_ids', readonly=True)
    order_id = fields.Many2many('sale.order', string="Sale order")
    sale_order_line_id = fields.Many2many('sale.order.line', string="Sale Order Line")

    @api.depends('event_id')
    def _compute_event_booth_category_id(self):
        # Once event is changed, booth category field should reset
        self.event_booth_category_id = False

    @api.depends('event_id', 'event_booth_category_id')
    def _compute_event_booth_ids(self):
        # Once event or booth category is changed, booth field should reset
        self.event_booth_ids = False

    def _get_event_data(self):
        self.ensure_one()
        lines = self.sale_order_line_id.filtered(
             lambda line: line.product_type == 'event_booth' and not line.event_id.id)
        lines.write({
                'event_id': self.event_id.id,
                'order_id': self.order_id.id,
                'event_booth_ids': self.event_booth_ids.ids,
                'event_booth_category_id': self.event_booth_category_id.id,
            })
