# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools import float_is_zero


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    pos_order_id = fields.Many2one(related='pos_order_line_id.order_id', string='PoS Order')
    pos_order_line_id = fields.Many2one('pos.order.line', string='PoS Order Line', ondelete='cascade', copy=False)

    @api.depends('pos_order_id.state', 'pos_order_line_id.currency_id', 'pos_order_line_id.price_subtotal_incl')
    def _compute_registration_status(self):
        super()._compute_registration_status()

    def _get_order(self):
        if self.pos_order_line_id:
            return self.pos_order_line_id
        return super()._get_order()

    def _is_cancel(self):
        return self.pos_order_id.state == 'cancel'

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        self.updateAvailableSeats()
        return result

    def write(self, vals):
        result = super().write(vals)
        self.updateAvailableSeats()
        return result

    def updateAvailableSeats(self):
        pos_session = self.env['pos.session']
        #Here sudo is used in order for pos_event to update the available seats to all open pos session when a ticket is sold in website for example
        session_ids = pos_session.sudo().search([("state", "!=", "closed")])
        payload = self.env['event.event.ticket'].search_read(pos_session.get_domain_event_event_ticket(), ['seats_available'])
        if session_ids:
            messages = []
            config_ids = session_ids.config_id
            for config_id in config_ids:
                current_session = config_id.current_session_id
                if current_session:
                    messages.append((current_session._get_bus_channel_name(), 'EVENT_REGISTRATION', payload))
            self.env['bus.bus']._sendmany(messages)
