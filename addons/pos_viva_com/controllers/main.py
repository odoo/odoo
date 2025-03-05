# coding: utf-8
import logging
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
            ('company_id.id', '=', company_id)
        ])
        payment_method_sudo = next(
            (pm for pm in viva_payment_methods if consteq(pm.viva_com_webhook_verification_key, token)),
            None
        )

        if payment_method_sudo:
            if request.httprequest.data:
                data = request.get_json_data()
                terminal_id = data.get('EventData', {}).get('TerminalId', '')
                data_webhook = data.get('EventData', {})
                if terminal_id:
                    payment_method_sudo = request.env['pos.payment.method'].sudo().search(
                        [('viva_com_terminal_id', '=', terminal_id)], limit=1
                    )
                    payment_method_sudo._retrieve_session_id(data_webhook)
                else:
                    _logger.error(_('received a message for a terminal not registered in Odoo: %s', terminal_id))
            return json.dumps({'Key': payment_method_sudo.viva_com_webhook_verification_key})
        else:
            _logger.error(_('received a message for a pos payment provider not registered.'))
