# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class L10nIdQrisController(http.Controller):

    @http.route('/l10n_id/qris/webhook/<int:bank_id>/<string:token>', type='http', methods=['POST'], auth='public', csrf=False, save_session=False)
    def l10n_id_qris_webhook(self, bank_id, token, **kwargs):
        """ Webhook to register the payment of an invoice as soon as its QR code is paid, notified by QRIS """
        bank_sudo = request.env['res.partner.bank'].sudo().browse(bank_id).exists()
        if not bank_sudo or not consteq(token, bank_sudo._l10n_id_get_qris_webhook_token()):
            raise Forbidden()

        data = request.get_json_data()
        _logger.info("Notification received from QRIS with data:\n%s", pprint.pformat(data))
        bank_sudo._l10n_id_qris_process_webhook(data)
        return request.make_json_response({'status': 'success'})
