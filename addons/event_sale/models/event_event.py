# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventType(models.Model):
    _inherit = 'event.type'

    @api.model
    def _get_default_event_ticket_ids(self):
        product = self.env.ref('event_sale.product_product_event', raise_if_not_found=False)
        if not product:
            return False
        return [(0, 0, {
            'name': _('Registration'),
            'product_id': product.id,
            'price': 0,
        })]

    use_ticketing = fields.Boolean('Ticketing')
    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_type_id',
        string='Tickets', default=_get_default_event_ticket_ids)

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            self.event_ticket_ids.filtered(lambda ticket: ticket.name == _('Registration')).update({
                'name': _('Registration for %s') % self.name
            })


class Event(models.Model):
    _inherit = 'event.event'

    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_id', string='Event Ticket',
        copy=True)
    sale_order_lines_ids = fields.One2many(
        'sale.order.line', 'event_id',
        string='All sale order lines pointing to this event')
    sale_price_subtotal = fields.Monetary(string='Sales (Tax Excluded)', compute='_compute_sale_price_subtotal')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', readonly=True)
    start_sale_date = fields.Date('Start sale date', compute='_compute_start_sale_date')

    @api.onchange('event_type_id')
    def _onchange_type(self):
        super(Event, self)._onchange_type()
        if self.event_type_id.use_ticketing:
            self.event_ticket_ids = [(5, 0, 0)] + [
                (0, 0, {
                    'name': self.name and _('Registration for %s') % self.name or ticket.name,
                    'product_id': ticket.product_id.id,
                    'price': ticket.price,
                })
                for ticket in self.event_type_id.event_ticket_ids]

    @api.depends('event_ticket_ids.start_sale_date')
    def _compute_start_sale_date(self):
        for event in self:
            start_dates = [ticket.start_sale_date for ticket in event.event_ticket_ids if ticket.start_sale_date]
            event.start_sale_date = min(start_dates) if start_dates else False

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

    @api.depends('event_ticket_ids.sale_available')
    def _compute_event_registrations_open(self):
        non_open_events = self.filtered(lambda event: not any(event.event_ticket_ids.mapped('sale_available')))
        non_open_events.event_registrations_open = False
        super(Event, self - non_open_events)._compute_event_registrations_open()
