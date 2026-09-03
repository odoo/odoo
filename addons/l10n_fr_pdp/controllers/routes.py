import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class IapAuthenticationWebhook(http.Controller):

    @http.route(['/api/signaturit_authentication_status/1/webhooks'], type='http', auth='public', csrf=False, methods=['POST'])
    def notify_authentication_status(self):
        data = request.get_json_data()
        object_uuid = data.get('object_uuid')
        auth_status = data.get('auth_status')

        if not object_uuid or not auth_status:
            _logger.warning("Signaturit - Notification received without info.")
            return request.make_response(
                json.dumps({'status': 'failed', 'message': 'Missing object_uuid or kyc_status'}),
                headers=[('Content-Type', 'application/json')],
                status=400,
            )

        if auth_status == 'done':
            company_id = request.env['res.company'].sudo().search([
                ('pdp_authentication_uuid', '=', object_uuid),
            ], limit=1)

            if not company_id:
                _logger.warning("Signaturit - Notification : no company matching object_uuid=%s", object_uuid)
                return request.make_response(
                    json.dumps({'status': 'failed', 'message': 'Authentication record not found'}),
                    headers=[('Content-Type', 'application/json')],
                    status=404,
                )
            company_id.sudo()._refresh_pdp_authentication_status()

        _logger.info("Signaturit - Notification for %s: auth_status=%s", object_uuid, auth_status)
        return request.make_response(
            json.dumps({'status': 'ok'}),
            headers=[('Content-Type', 'application/json')],
            status=200,
        )
