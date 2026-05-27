import json

from odoo import http
from odoo.http import request


class IapAuthenticationWebhook(http.Controller):

    @http.route(['/api/signaturit_authentication_status/1/webhooks'], type='http', auth='public', csrf=False, methods=['POST'])
    def notify_authentication_status(self):
        data = json.loads(request.httprequest.data)
        object_uuid = data.get('object_uuid')
        kyc_status = data.get('kyc_status')

        if not object_uuid or not kyc_status:
            return request.make_response(
                json.dumps({'status': 'failed', 'message': 'Missing object_uuid or kyc_status'}),
                headers=[('Content-Type', 'application/json')],
                status=400,
            )

        auth_record = request.env['pdp.registration'].sudo().search([
            ('authenticaton_uuid', '=', object_uuid),
        ], limit=1)

        if not auth_record:
            return request.make_response(
                json.dumps({'status': 'failed', 'message': 'Authentication record not found'}),
                headers=[('Content-Type', 'application/json')],
                status=404,
            )

        if kyc_status in ('success', 'fail'):
            auth_record.kyc_status = kyc_status

        return request.make_response(
            json.dumps({'status': 'ok'}),
            headers=[('Content-Type', 'application/json')],
            status=200,
        )
