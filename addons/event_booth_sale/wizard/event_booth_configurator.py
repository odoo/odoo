# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class EventBoothConfigurator(models.TransientModel):
    _name = 'event.booth.configurator'
    _description = 'Event Booth Configurator'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', readonly=True)
    event_id = fields.Many2one('event.event', string='Event', required=True)
    event_booth_category_available_ids = fields.Many2many(related='event_id.event_booth_category_available_ids', readonly=True)
    event_booth_category_id = fields.Many2one(
        'event.booth.category', string='Booth Category', required=True,
        compute='_compute_event_booth_category_id', readonly=False, store=True)
    event_booth_ids = fields.Many2many(
        'event.booth', string='Booth', required=True,
        compute='_compute_event_booth_ids', readonly=False, store=True)

    @api.depends('event_id')
    def _compute_event_booth_category_id(self):
        self.event_booth_category_id = False

    @api.depends('event_id', 'event_booth_category_id')
    def _compute_event_booth_ids(self):
        self.event_booth_ids = False

    @api.constrains('event_booth_ids')
    def _check_if_no_booth_ids(self):
        if any(not wizard.event_booth_ids for wizard in self):
            raise ValidationError(_('You have to select at least one booth.'))
