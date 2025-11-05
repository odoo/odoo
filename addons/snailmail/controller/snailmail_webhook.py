import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.translate import LazyTranslate

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)

LETTER_STATUS_MAPPING = {
    'undeliverable': _lt('Letter was unable to be delivered'),
    'delivered': _lt('Letter is delivered successfully')
}


class SnailmailWebhookController(http.Controller):
    @http.route('/webhook/snailmail/1/<string:event_type>', type='http', auth='public', save_session=False, csrf=False)
    def snailmail_webhook(self, event_type):
        """ Receive and process letter sent by IAP pingen webhook. """

        event = request.get_json_data()
        if not event or event_type not in LETTER_STATUS_MAPPING:
            _logger.warning("[Snailmail] Webhook: Invalid request payload received")
            raise request.not_found()

        account_token = request.env['iap.account'].sudo().get('snailmail').account_token
        hashed_token = hashlib.sha1(account_token.encode('utf-8')).hexdigest()
        if not self._check_signature(hashed_token, event):
            _logger.warning("[Snailmail] Webhook: IAP signature does not match")
            raise request.not_found()

        pingen_letter_id = event.get('letter_id')
        letter_status = event.get('status')
        if not pingen_letter_id or not letter_status:
            _logger.warning("[Snailmail] Webhook: Invalid event payload received, missing letter_id or status")
            raise request.not_found()

        letter_su = request.env['snailmail.letter'].sudo().search([('document_id', '=', pingen_letter_id)], limit=1)

        if not letter_su:
            _logger.warning("[Snailmail] Webhook: could not find a matching letter with letter_id = %s", pingen_letter_id)
            raise request.not_found()

        record = request.env[letter_su.model].browse(int(letter_su.res_id))
        if not record.exists():
            _logger.warning("[Snailmail] Webhook: could not find a matching record for letter with letter_id = %s", pingen_letter_id)
            raise request.not_found()

        letter_data = {}
        notification_data = {}
        if letter_status == 'delivered':
            letter_data = {
                'state': 'sent',
                'error_code': False
            }
            notification_data = {
                'notification_status': 'sent',
                'failure_type': False,
                'failure_reason': False
            }
        elif letter_status == 'undeliverable':
            letter_data = {
                'state': 'error',
                'error_code': 'LETTER_UNDELIVERABLE',
                'info_msg': event.get('reason', LETTER_STATUS_MAPPING[letter_status])
            }
            notification_data = {
                'notification_status': 'bounce',
                'failure_type': 'sn_undeliverable',
                'failure_reason': 'Undeliverable letter'
            }
        letter_su.write(letter_data)
        letter_su.notification_ids.sudo().write(notification_data)
        letter_su.message_id._notify_message_notification_update()

        return request.make_json_response('[accepted]')

    def _check_signature(self, sign_token, data):
        """Verifying IAP signature."""
        signature = request.httprequest.headers.get('odoo-iap-signature')
        if not signature or len(signature) != 64:
            _logger.warning("[Snailmail] Webhook: Invalid signature header %r", signature)
            return False
        expected = hmac.new(key=sign_token.encode(), msg=json.dumps(data, sort_keys=True).encode(), digestmod=hashlib.sha256).hexdigest()
        return consteq(expected, signature)
