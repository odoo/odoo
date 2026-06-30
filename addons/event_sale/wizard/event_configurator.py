# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class EventEventConfigurator(models.TransientModel):
    _name = 'event.event.configurator'
    _description = 'Event Configurator'

    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    event_id = fields.Many2one('event.event', string="Event")
    event_slot_id = fields.Many2one('event.slot', string="Slot", domain="[('event_id', '=', event_id)]",
        compute="_compute_event_slot_id", readonly=False, store=True)
    event_ticket_id = fields.Many2one('event.event.ticket', string="Ticket Type", domain="[('event_id', '=', event_id)]",
        compute="_compute_event_ticket_id", readonly=False, store=True)
    is_multi_slots = fields.Boolean(related="event_id.is_multi_slots")
    has_available_tickets = fields.Boolean("Has Available Tickets", compute="_compute_has_available_tickets")

    @api.constrains('event_id', 'event_slot_id', 'event_ticket_id')
    def check_event_id(self):
        error_messages = []
        for record in self:
            if record.event_id.id != record.event_ticket_id.event_id.id:
                error_messages.append(
                    _('Invalid ticket choice "%(ticket_name)s" for event "%(event_name)s".'))
            if record.event_slot_id and record.event_id.id != record.event_slot_id.event_id.id:
                error_messages.append(
                    _('Invalid slot choice "%(slot_name)s" for event "%(event_name)s".'))
        if error_messages:
            raise ValidationError('\n'.join(error_messages))

    @api.depends('product_id')
    def _compute_has_available_tickets(self):
        product_ticket_data = self.env['event.event.ticket']._read_group([
            ('product_id', 'in', self.product_id.ids),
            ('event_id.date_end', '>=', fields.Date.today())],
            ['product_id'],
            ['__count'])
        mapped_data = {product: ticket_count for product, ticket_count in product_ticket_data}
        for configurator in self:
            configurator.has_available_tickets = bool(mapped_data.get(configurator.product_id, 0))

    @api.depends("is_multi_slots")
    def _compute_event_slot_id(self):
        """ Pre-select the slot of the multi slots event selected if it is the only one """
        for configurator in self:
            if not configurator.is_multi_slots:
                configurator.event_slot_id = False
            else:
                event_slot_ids = self.env['event.slot'].search([
                    ('event_id', '=', configurator.event_id.id)], limit=2)
                configurator.event_slot_id = event_slot_ids if len(event_slot_ids) == 1 else False

    @api.depends('event_id')
    def _compute_event_ticket_id(self):
        """ Pre-select the ticket of the event selected if it is the only one """
        for configurator in self:
            event_ticket_ids = self.env['event.event.ticket'].search([
                ('event_id', '=', configurator.event_id.id),
                ('product_id', '=', configurator.product_id.id)], limit=2)
            configurator.event_ticket_id = event_ticket_ids if len(event_ticket_ids) == 1 else False
