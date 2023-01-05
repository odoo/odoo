# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class EventConfiguratorLine(models.TransientModel):
    """Event Configuration"""
    _name = "event.editor.line"
    _description = 'Edit Event Lines on Sales Confirmation'
    _order = "id desc"

    editor_id = fields.Many2one('event.event.configurator.batch', string="Editor")
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    event_ticket_id = fields.Many2one('event.event.ticket', string="Event Ticket",
        compute='_compute_event_ticket_ids', readonly=False, store=True)
    event_id = fields.Many2one('event.event', string="Event")
    order_id = fields.Many2many('sale.order', string="Sale order")
    sale_order_line_id = fields.Many2many('sale.order.line', string="Sale Order Line")

    @api.depends('event_id')
    def _compute_event_ticket_ids(self):
        # Once event is changed, ticket category should reset
        self.event_ticket_id = False

    def _get_event_data(self):
        self.ensure_one()
        lines = self.sale_order_line_id.filtered(
            lambda line: line.product_type == 'event' and not line.event_id.id)
        lines.write({
                'event_id': self.event_id.id,
                'event_ticket_id': self.event_ticket_id.id,
                'order_id': self.order_id.id,
            })
