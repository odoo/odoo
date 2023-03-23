# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class EventConfigurator(models.TransientModel):
    _name = 'event.event.configurator'
    _description = 'Event Configurator'

    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    event_id = fields.Many2one('event.event', string="Event")
    event_ticket_id = fields.Many2one('event.event.ticket', string="Event Ticket")

    @api.constrains('event_id', 'event_ticket_id')
    def check_event_id(self):
        error_messages = []
        for record in self:
            if record.event_id.id != record.event_ticket_id.event_id.id:
                error_messages.append(
                    _('Invalid ticket choice "%(ticket_name)s" for event "%(event_name)s".'))
        if error_messages:
            raise ValidationError('\n'.join(error_messages))

    def action_configure_event(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window_close",
            "infos": {
                "eventConfiguration": {
                    "event_id": [
                        self.event_id.id,
                        self.event_id.display_name],
                    "event_ticket_id": [
                        self.event_ticket_id.id,
                        self.event_ticket_id.display_name],
                },
            },
        }
