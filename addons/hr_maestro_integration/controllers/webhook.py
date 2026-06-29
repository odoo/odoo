# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac
import json
import logging
import time

from datetime import datetime, timezone

from odoo import http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)

# Tolerância de relógio entre o Maestro e o Odoo (evita replay de assinaturas antigas)
SIGNATURE_TOLERANCE_SECONDS = 5 * 60


class MaestroWebhookController(http.Controller):

    def _get_secret(self):
        return request.env['ir.config_parameter'].sudo().get_param(
            'hr_maestro_integration.webhook_secret')

    def _verify_signature(self, raw_body, signature_header, secret):
        """Verifica o header `X-Maestro-Signature: t={ts},v1={sig}`.

        sig = HMAC-SHA256(secret, f"{ts}.{json.dumps(payload, sort_keys=True, separators=(',', ':'))}")
        """
        if not signature_header or not secret:
            return False
        parts = dict(
            item.split('=', 1) for item in signature_header.split(',') if '=' in item
        )
        ts, sig = parts.get('t'), parts.get('v1')
        if not ts or not sig:
            return False
        if abs(time.time() - int(ts)) > SIGNATURE_TOLERANCE_SECONDS:
            _logger.warning('Maestro webhook: assinatura fora da janela de tempo permitida.')
            return False

        try:
            payload = json.loads(raw_body)
        except ValueError:
            return False
        canonical_body = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        message = f"{ts}.{canonical_body}"
        expected_sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return consteq(expected_sig, sig)

    @http.route('/maestro/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def maestro_webhook(self, **kwargs):
        raw_body = request.httprequest.get_data()
        signature_header = request.httprequest.headers.get('X-Maestro-Signature')
        secret = self._get_secret()

        if not secret:
            _logger.error('Maestro webhook: hr_maestro_integration.webhook_secret não configurado.')
            return request.make_json_response({'error': 'not_configured'}, status=503)

        if not self._verify_signature(raw_body, signature_header, secret):
            _logger.warning('Maestro webhook: assinatura inválida.')
            return request.make_json_response({'error': 'invalid_signature'}, status=401)

        payload = json.loads(raw_body)
        event_id = payload.get('event_id')
        event_type = payload.get('event_type')
        maestro_company_id = payload.get('company_id')
        data = payload.get('data') or {}

        if not (event_id and event_type and maestro_company_id):
            return request.make_json_response({'error': 'invalid_payload'}, status=400)

        Event = request.env['hr.maestro.event'].sudo()
        if Event.search_count([('external_event_id', '=', event_id)]):
            # Idempotência: evento já processado, responde 200 sem duplicar.
            return request.make_json_response({'status': 'duplicate'}, status=200)

        try:
            event_date = datetime.fromisoformat(payload['timestamp']).astimezone(timezone.utc).replace(tzinfo=None)
        except (KeyError, ValueError):
            event_date = datetime.now(timezone.utc).replace(tzinfo=None)

        Event.create({
            'maestro_company_id': maestro_company_id,
            'event_type': event_type,
            'event_date': event_date,
            'external_event_id': event_id,
            'risk_level': data.get('risk_level'),
            'summary': data.get('summary') or data.get('description'),
            'data': json.dumps(data, ensure_ascii=False),
        })
        return request.make_json_response({'status': 'received'}, status=200)
