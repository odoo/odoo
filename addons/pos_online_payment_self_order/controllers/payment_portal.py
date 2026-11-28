# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlsplit

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal
from odoo.addons.pos_online_payment_self_order.models.pos_order import PresetSlotUnavailableError

class PaymentPortalSelfOrder(PaymentPortal):
    @staticmethod
    def _get_reschedule_route(exit_route):
        """ Route back to the self order cart, to select another timing slot.
        The fragment is only read by the self order app, it is not sent to the server.
        """
        return urlsplit(exit_route)._replace(fragment='reschedule').geturl()

    @http.route()
    def pos_order_pay(self, pos_order_id, access_token=None, exit_route=None):
        pos_order = request.env['pos.order'].sudo().browse(pos_order_id)
        pos_order._send_notification_online_payment_status('progress')
        try:
            return super().pos_order_pay(pos_order_id, access_token=access_token, exit_route=exit_route)
        except PresetSlotUnavailableError:
            if not exit_route:
                raise
            return request.redirect(self._get_reschedule_route(exit_route))

    def _check_additional_payment_guards(self, pos_order_sudo):
        super()._check_additional_payment_guards(pos_order_sudo)
        try:
            pos_order_sudo._check_preset_slot_availability()
        except ValidationError:
            pos_order_sudo._send_notification_online_payment_status('fail')
            raise

    @http.route()
    def pos_order_pay_transaction(self, pos_order_id, access_token=None, **kwargs):
        try:
            return super().pos_order_pay_transaction(pos_order_id, access_token=access_token, **kwargs)
        except PresetSlotUnavailableError as error:
            exit_route = request.httprequest.args.get('exit_route')
            if not exit_route:
                raise
            return {
                'state': 'error',
                'state_message': error.args[0],
                'pos_online_payment_slot_unavailable': True,
                'exit_route': self._get_reschedule_route(exit_route),
            }

    @http.route()
    def pos_order_pay_confirmation(self, pos_order_id, tx_id=None, access_token=None, exit_route=None, **kwargs):
        result = super().pos_order_pay_confirmation(pos_order_id, tx_id=tx_id, access_token=access_token, exit_route=exit_route, **kwargs)
        tx_sudo = request.env['payment.transaction'].sudo().search([('id', '=', tx_id)])

        if tx_sudo.state not in ('authorized', 'done'):
            pos_order = request.env['pos.order'].sudo().browse(pos_order_id)
            pos_order._send_notification_online_payment_status('fail')

        return result
