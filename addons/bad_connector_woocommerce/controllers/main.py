import json
import logging

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WooWebhook(http.Controller):
    def _common_webhook_handler(self, access_token, model_name):
        """Common handler for processing WooCommerce webhooks."""
        job_options = {}
        if not access_token:
            _logger.error(
                "No Access Token found in WooCommerce backend. Please generate the "
                "Access Token!!"
            )
            raise Forbidden()
        backend = (
            request.env["woo.backend"]
            .sudo()
            .search(
                [
                    "|",
                    "&",
                    ("test_mode", "!=", True),
                    ("access_token", "=", access_token),
                    "&",
                    ("test_access_token", "=", access_token),
                    ("test_mode", "=", True),
                ],
                limit=1,
            )
        )
        if not backend:
            _logger.error(
                "No WooCommerce backend found. Check your Access Token and try again"
            )
            raise Forbidden()
        payload = json.loads(request.httprequest.data)
        payload_status = payload.get("status")
        if model_name == "woo.sale.order":
            status = backend.woo_sale_status_ids.mapped("code")
            if status and payload_status not in status:
                _logger.info(
                    "Skipping sale order import due to status %s is not configured for "
                    "import",
                    payload_status,
                )
                return True
        model = request.env[model_name]
        description = backend.get_queue_job_description(
            prefix=model.import_record.__doc__ or f"Record Import Of {model_name}",
            model=model._description,
        )
        job_options["description"] = description
        return model.with_delay(**job_options or {}).import_record(
            backend=backend, external_id=payload.get("id"), data=payload
        )

    @http.route(
        [
            "/create_product/woo_webhook/<access_token>",
            "/update_product/woo_webhook/<access_token>",
        ],
        methods=["POST"],
        type="json",
        auth="public",
        website=True,
    )
    def handle_product_webhook(self, access_token, **kwargs):
        """Handle WooCommerce product webhooks."""
        return self._common_webhook_handler(access_token, "woo.product.product")

    @http.route(
        [
            "/create_order/woo_webhook/<access_token>",
            "/update_order/woo_webhook/<access_token>",
        ],
        methods=["POST"],
        type="json",
        auth="public",
        website=True,
    )
    def handle_order_webhook(self, access_token, **kwargs):
        """Handle WooCommerce order webhooks."""
        return self._common_webhook_handler(access_token, "woo.sale.order")
