"""WooCommerce incoming webhook handler.

WooCommerce POSTs JSON payloads to this endpoint when configured.
Each request is verified by HMAC-SHA256 signature before processing.

Topics handled:
- order.created / order.updated
- product.created / product.updated / product.deleted
- customer.created / customer.updated

Security:
- Signature verification using X-WC-Webhook-Signature header
- Token-based backend routing (URL contains backend-specific token)
- Public route (no Odoo authentication required)
- CSRF disabled (external webhook)
"""

import json
import logging
import pprint

from odoo import http
from odoo.http import request

from ..api import WooCommerceClient

_logger = logging.getLogger(__name__)


class WooCommerceWebhookController(http.Controller):

    @http.route(
        '/woocommerce/webhook/<string:token>',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def woocommerce_webhook(self, token, **kwargs):
        """Receive and dispatch WooCommerce webhook notifications.

        URL: POST /woocommerce/webhook/<backend_token>

        Headers expected:
        - X-WC-Webhook-Topic: e.g. 'order.created'
        - X-WC-Webhook-Source: store URL
        - X-WC-Webhook-Signature: HMAC-SHA256 base64 of raw body
        - X-WC-Webhook-ID: webhook ID on WooCommerce
        - Content-Type: application/json
        """
        http_request = request.httprequest
        topic = http_request.headers.get('X-WC-Webhook-Topic', '')
        source = http_request.headers.get('X-WC-Webhook-Source', '')
        signature = http_request.headers.get('X-WC-Webhook-Signature', '')

        _logger.info('[WooCommerce Webhook] topic=%s source=%s token=%s', topic, source, token)

        # ── 1. Find the backend for this token ────────────────────────────────
        Backend = request.env['woocommerce.backend'].sudo()
        backend = Backend._find_by_webhook_token(token)
        if not backend:
            _logger.warning('[WooCommerce Webhook] Unknown token: %s', token)
            return request.make_response('', status=404)

        # ── 2. Verify signature ───────────────────────────────────────────────
        raw_body = http_request.get_data()
        if backend.webhook_secret:
            valid = WooCommerceClient.verify_webhook_signature(
                raw_body, backend.webhook_secret, signature
            )
            if not valid:
                _logger.warning(
                    '[WooCommerce Webhook] Invalid signature for backend %s, topic=%s',
                    backend.name, topic,
                )
                return request.make_response('', status=401)

        # ── 3. Parse payload ──────────────────────────────────────────────────
        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, ValueError) as exc:
            _logger.error('[WooCommerce Webhook] Invalid JSON payload: %s', exc)
            return request.make_response('', status=400)

        _logger.debug('[WooCommerce Webhook] Payload:\n%s', pprint.pformat(payload))

        # ── 4. Dispatch by topic ──────────────────────────────────────────────
        try:
            self._dispatch(backend, topic, payload)
        except Exception as exc:
            _logger.error(
                '[WooCommerce Webhook] Error processing topic %s: %s',
                topic, exc, exc_info=True,
            )
            # Return 200 anyway to prevent WooCommerce from disabling the webhook
            # (WC disables webhooks after too many failures)

        # ── 5. Acknowledge ────────────────────────────────────────────────────
        return request.make_response('', status=200)

    def _dispatch(self, backend, topic, payload):
        """Route the webhook payload to the appropriate handler."""
        handlers = {
            'order.created': self._handle_order,
            'order.updated': self._handle_order,
            'order.deleted': self._handle_order_deleted,
            'product.created': self._handle_product,
            'product.updated': self._handle_product,
            'product.deleted': self._handle_product_deleted,
            'customer.created': self._handle_customer,
            'customer.updated': self._handle_customer,
        }
        handler = handlers.get(topic)
        if handler:
            handler(backend, payload, topic)
        else:
            _logger.debug('[WooCommerce Webhook] No handler for topic: %s', topic)

    # ── Order Handlers ────────────────────────────────────────────────────────

    def _handle_order(self, backend, payload, topic):
        """Process order.created / order.updated webhook."""
        wc_id = str(payload.get('id', ''))
        if not wc_id:
            _logger.warning('[WooCommerce Webhook] Order payload missing id')
            return

        OrderBinding = request.env['woocommerce.order.binding'].sudo()
        binding = OrderBinding._get_binding(backend, wc_id)

        if binding:
            # Update status
            wc_status = payload.get('status', '')
            if wc_status and wc_status != binding.wc_status:
                OrderBinding._update_existing_order(binding, payload, wc_status)
                _logger.info(
                    '[WooCommerce Webhook] Updated order #%s status → %s', wc_id, wc_status
                )
        else:
            # Import the new order
            _logger.info('[WooCommerce Webhook] Importing new order #%s', wc_id)
            OrderBinding._import_one_order(backend, payload)

    def _handle_order_deleted(self, backend, payload, topic):
        """Process order.deleted webhook — cancel the Odoo sale order."""
        wc_id = str(payload.get('id', ''))
        if not wc_id:
            return
        OrderBinding = request.env['woocommerce.order.binding'].sudo()
        binding = OrderBinding._get_binding(backend, wc_id)
        if binding and binding.odoo_id.state not in ('cancel',):
            try:
                binding.odoo_id.action_cancel()
                _logger.info('[WooCommerce Webhook] Cancelled order %s (WC #%s)',
                             binding.odoo_id.name, wc_id)
            except Exception as exc:
                _logger.warning('[WooCommerce Webhook] Cannot cancel order %s: %s',
                                binding.odoo_id.name, exc)

    # ── Product Handlers ──────────────────────────────────────────────────────

    def _handle_product(self, backend, payload, topic):
        """Process product.created / product.updated webhook."""
        wc_id = str(payload.get('id', ''))
        if not wc_id:
            return
        _logger.info('[WooCommerce Webhook] Processing product #%s', wc_id)
        # Delegate to full product import (handles create/update idempotently)
        ProductBinding = request.env['woocommerce.product.binding'].sudo()
        client = backend._get_client()
        ProductBinding._import_one_product(backend, payload, client)

    def _handle_product_deleted(self, backend, payload, topic):
        """Process product.deleted — archive the Odoo product."""
        wc_id = str(payload.get('id', ''))
        if not wc_id:
            return
        ProductBinding = request.env['woocommerce.product.binding'].sudo()
        binding = ProductBinding._get_binding(backend, wc_id)
        if binding:
            binding.odoo_id.write({'active': False})
            binding.write({'sync_state': 'outdated'})
            _logger.info('[WooCommerce Webhook] Archived product (WC #%s)', wc_id)

    # ── Customer Handlers ─────────────────────────────────────────────────────

    def _handle_customer(self, backend, payload, topic):
        """Process customer.created / customer.updated webhook."""
        wc_id = str(payload.get('id', ''))
        if not wc_id:
            return
        _logger.info('[WooCommerce Webhook] Processing customer #%s', wc_id)
        CustomerBinding = request.env['woocommerce.customer.binding'].sudo()
        CustomerBinding._import_one_customer(backend, payload)
