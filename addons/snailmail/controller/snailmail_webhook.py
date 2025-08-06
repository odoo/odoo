from odoo import http
from odoo.http import request

LETTER_STATUS_MAPPING = {
    'undeliverable': 'Letter was unable to be delivered',
    'delivered': 'Letter is delivered successfully'
}


class SnailmailWebhookController(http.Controller):
    @http.route('/webhook/snailmail/<string:event_type>', type='jsonrpc', auth='public', save_session=False)
    def snailmail_webhook(self, event_type):
        """ Receive and process letter sent by IAP pingen webhook. """

        event = request.httprequest.json or {}
        if not event or event_type not in LETTER_STATUS_MAPPING:
            return
        pingen_letter_id = event.get('letter_id')
        letter_status = event.get('status')
        letter = request.env['snailmail.letter'].sudo().search([('document_id', '=', pingen_letter_id)], limit=1)

        if not letter:
            return
        letter.state = letter_status
        msg = LETTER_STATUS_MAPPING.get(letter_status)

        model_name, record_id = letter.reference.split(',')
        record = request.env[model_name].browse(int(record_id))
        if record:
            record.sudo().message_post(
                body=msg,
                message_type='snailmail',
                subtype_xmlid='mail.mt_note',
                author_id=request.env.ref('base.partner_root').id
            )
        return request.make_json_response('[accepted]')
