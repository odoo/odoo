# coding: utf-8
import logging
import urllib.parse
import json
from odoo import http, _
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class PosVivaComController(http.Controller):
    @http.route('/pos_viva_com/notification', type='http', auth='none', csrf=False, readonly=False)
    def notification(self, company_id, token):
        _logger.info('notification received from Viva.com')

        viva_payment_methods = request.env['pos.payment.method'].sudo().search([
            ('use_payment_terminal', '=', 'viva_com'),
            ('company_id.id', '=', int(company_id))
        ])
        payment_method_sudo = next(
            (pm for pm in viva_payment_methods if consteq(pm.viva_com_webhook_verification_key, token)),
            None
        )

        if payment_method_sudo:
            if request.httprequest.data:
                data = request.get_json_data()
                terminal_id = data.get('EventData', {}).get('TerminalId', '')
                event_type = data.get('EventTypeId')
                data_webhook = data.get('EventData', {})
                if event_type != 1796:  # Transaction Payment Created
                    _logger.warning('received a message with an unknown event type "%s". See https://developer.viva.com/webhooks-for-payments/#webhook-events.', event_type)
                elif terminal_id:
                    payment_method_sudo = request.env['pos.payment.method'].sudo().search(
                        [('viva_com_terminal_id', '=', terminal_id)], limit=1
                    )
                    payment_method_sudo._retrieve_session_id(data_webhook)
                else:
                    _logger.error(_('received a message for a terminal not registered in Odoo: %s', terminal_id))
            return json.dumps({'Key': payment_method_sudo.viva_com_webhook_verification_key})
        else:
            _logger.error(_('received a message for a pos payment provider not registered.'))

    @http.route('/pos_viva_com/<int:config_id>/abort/<string:order_uuid>', type='http', auth='public', methods=['GET'])
    def viva_abort_callback(self, config_id, order_uuid, **kwargs):
        result = kwargs.get('status')
        _logger.info('received abort callback from Viva.com with result %s', result)

        dynamicLink = self._create_dynamic_link(f"/pos/ui/{config_id}/payment/{order_uuid}")
        return request.redirect(dynamicLink, local=False)

    @http.route('/pos_viva_com/<int:config_id>/payment/<string:order_uuid>', type='http', auth='public', methods=['GET'])
    def viva_payment_callback(self, config_id, order_uuid, **kwargs):
        result = kwargs.get('status')
        transaction_id = kwargs.get('transactionId')
        session_id = kwargs.get('clientTransactionId')

        _logger.info('received payment callback from Viva.com with result %s', result)

        pos_order = request.env['pos.order'].sudo().search([('uuid', '=', order_uuid)], limit=1)
        if not pos_order:
            return "Order not found"

        # Update payment line
        if not session_id:
            payment_line = pos_order.payment_ids.filtered(lambda p: p.payment_method_id.use_payment_terminal == 'viva_com')
        else:
            payment_line = pos_order.payment_ids.filtered(lambda p: p.payment_method_id.use_payment_terminal == 'viva_com' and p.viva_com_session_id == session_id)[-1:]

        if result == 'success':
            payment_line.write({
                'transaction_id': transaction_id,
                'payment_status': 'done',
            })
            if pos_order.amount_difference == 0 and all(p.payment_status == 'done' for p in pos_order.payment_ids):
                pos_order.write({'state': 'paid'})

                dynamicLink = self._create_dynamic_link(f"/pos/ui/{config_id}/resume/{order_uuid}")
                return request.redirect(dynamicLink, local=False)
        else:
            payment_line.write({'payment_status': 'error', 'transaction_id': transaction_id})

        dynamicLink = self._create_dynamic_link(f"/pos/ui/{config_id}/payment/{order_uuid}")
        return request.redirect(dynamicLink, local=False)

    # Create a redirect link which should open the Odoo mobile app if it is installed
    def _create_dynamic_link(self, redirect_path):
        base_url = request.env['ir.config_parameter'].sudo().get_str('web.base.url')
        original_link = f"{base_url}{redirect_path}"
        redirect_base = "https://redirect-url.email/"
        url_params = urllib.parse.urlencode({
            'link': original_link,
        })
        return f"{redirect_base}?{url_params}"
