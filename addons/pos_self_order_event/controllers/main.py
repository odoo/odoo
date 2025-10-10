# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from werkzeug.exceptions import NotFound
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


class PosSelfEventController(PosSelfOrderController):

    @http.route('/pos-self-order/get-order-registrations-data', type='jsonrpc', auth='public')
    def get_order_registrations_data(self, access_token=None, order_id=None, event_ticket_id=None, **kwargs):
        pos_config = self._verify_pos_config(access_token)

        if not order_id or not event_ticket_id:
            raise NotFound()

        event_regs = pos_config.env['event.registration'].search([
            ('pos_order_id', '=', int(order_id)),
            ('event_ticket_id', '=', int(event_ticket_id)),
        ])
        if not event_regs:
            raise NotFound()

        event = event_regs.event_id.ensure_one()
        access_hash = event._get_tickets_access_hash(event_regs.ids)

        return {
            'event_id': event.id,
            'registration_ids': event_regs.ids,
            'tickets_hash': access_hash,
        }
