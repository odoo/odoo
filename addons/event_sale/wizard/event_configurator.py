# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import models, fields, api


class EventConfigurator(models.TransientModel):
    _name = 'event.event.configurator'
    _description = 'Event Configurator'

    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    event_id = fields.Many2one('event.event', string="Event")
    event_ticket_id = fields.Many2one('event.event.ticket', string="Event Ticket")
    has_available_events = fields.Boolean(
        "Has Available Events",
        compute="_compute_has_available_events",
        help="Technical field used to know if the user has at least one event that can be selected and used to configure event tickets on sale order lines")

    @api.model
    def default_get(self, fields):
        res = super(EventConfigurator, self).default_get(fields)
        if 'event_id' in fields and res.get('product_id'):
            upcoming_events = self.env['event.event'].search(
                [('event_ticket_ids.product_id', '=', res['product_id']),
                 ('date_end', '>=',
                  date.today().strftime('%Y-%m-%d 00:00:00')),
                 ('stage_id.pipe_end', '=', False), ], limit=2)
            if len(upcoming_events) == 1:
                res['event_id'] = upcoming_events
                if 'event_ticket_id' in fields and len(upcoming_events.event_ticket_ids) == 1:
                    res['event_ticket_id'] = upcoming_events.event_ticket_ids
        return res

    @api.depends("product_id")
    def _compute_has_available_events(self):
        self.has_available_events = self.env['event.event'].search_count(
            [('event_ticket_ids.product_id', '=', self.product_id.id),
             ('date_end', '>=', date.today().strftime('%Y-%m-%d 00:00:00')),
             ('stage_id.pipe_end', '=', False), ]) > 0

    @api.onchange("event_id")
    def _onchange_event_id(self):
        self.ensure_one()
        if len(self.event_id.event_ticket_ids) == 1:
            self.event_ticket_id = self.event_id.event_ticket_ids
