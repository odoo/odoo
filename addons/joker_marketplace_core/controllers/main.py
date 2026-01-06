"""
Marketplace API Controllers

RESTful API endpoints for marketplace operations
"""

import json
import logging

from odoo import http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


class MarketplaceController(http.Controller):
    """Main marketplace API controller"""

    @http.route("/api/marketplace/channels", type="json", auth="user", methods=["GET"])
    def get_channels(self, **kw):
        """Get all marketplace channels"""
        try:
            channels = request.env["marketplace.channel"].search([])
            return {
                "status": "success",
                "data": [
                    {
                        "id": ch.id,
                        "name": ch.name,
                        "type": ch.channel_type,
                        "active": ch.active,
                        "last_sync": ch.last_sync.isoformat() if ch.last_sync else None,
                        "total_products": ch.total_products,
                        "total_orders": ch.total_orders,
                    }
                    for ch in channels
                ],
            }
        except Exception as e:
            _logger.error(f"Error fetching channels: {str(e)}")
            return {"status": "error", "message": str(e)}, 500

    @http.route(
        "/api/marketplace/channels/<int:channel_id>",
        type="json",
        auth="user",
        methods=["GET"],
    )
    def get_channel(self, channel_id, **kw):
        """Get channel details"""
        try:
            channel = request.env["marketplace.channel"].browse(channel_id)
            if not channel.exists():
                return {"status": "error", "message": "Channel not found"}, 404

            return {
                "status": "success",
                "data": {
                    "id": channel.id,
                    "name": channel.name,
                    "type": channel.channel_type,
                    "active": channel.active,
                    "last_sync": (
                        channel.last_sync.isoformat() if channel.last_sync else None
                    ),
                    "total_products": channel.total_products,
                    "total_orders": channel.total_orders,
                    "pending_orders": channel.pending_orders,
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

    @http.route(
        "/api/marketplace/channels/<int:channel_id>/sync",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def sync_channel(self, channel_id, **kw):
        """Sync channel now"""
        try:
            channel = request.env["marketplace.channel"].browse(channel_id)
            if not channel.exists():
                return {"status": "error", "message": "Channel not found"}, 404

            channel.action_sync_now()

            return {
                "status": "success",
                "message": f"{channel.name} senkronizasyonu başlatıldı",
            }
        except Exception as e:
            _logger.error(f"Sync error: {str(e)}")
            return {"status": "error", "message": str(e)}, 500

    @http.route("/api/marketplace/orders", type="json", auth="user", methods=["GET"])
    def get_orders(self, **kw):
        """Get marketplace orders"""
        try:
            domain = []
            if "channel_id" in kw:
                domain.append(("channel_id", "=", int(kw["channel_id"])))
            if "status" in kw:
                domain.append(("status", "=", kw["status"]))

            orders = request.env["marketplace.order"].search(domain, limit=100)

            return {
                "status": "success",
                "data": [
                    {
                        "id": order.id,
                        "channel_order_id": order.channel_order_id,
                        "channel": order.channel_id.name,
                        "order_date": (
                            order.order_date.isoformat() if order.order_date else None
                        ),
                        "customer": order.partner_name,
                        "amount": order.amount_total,
                        "status": order.status,
                    }
                    for order in orders
                ],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

    @http.route(
        "/api/marketplace/orders/<int:order_id>",
        type="json",
        auth="user",
        methods=["GET"],
    )
    def get_order(self, order_id, **kw):
        """Get order details"""
        try:
            order = request.env["marketplace.order"].browse(order_id)
            if not order.exists():
                return {"status": "error", "message": "Order not found"}, 404

            return {
                "status": "success",
                "data": {
                    "id": order.id,
                    "channel_order_id": order.channel_order_id,
                    "channel": order.channel_id.name,
                    "order_date": (
                        order.order_date.isoformat() if order.order_date else None
                    ),
                    "customer": order.partner_name,
                    "email": order.partner_email,
                    "phone": order.partner_phone,
                    "amount": order.amount_total,
                    "status": order.status,
                    "lines": [
                        {
                            "product": line.product_id.name,
                            "qty": line.qty,
                            "price": line.price,
                        }
                        for line in order.line_ids
                    ],
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

    @http.route(
        "/api/marketplace/orders/<int:order_id>/confirm",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def confirm_order(self, order_id, **kw):
        """Confirm order and create sale order"""
        try:
            order = request.env["marketplace.order"].browse(order_id)
            if not order.exists():
                return {"status": "error", "message": "Order not found"}, 404

            order.action_confirm()

            return {
                "status": "success",
                "message": f"Sipariş {order_id} onaylandı",
                "sale_order_id": order.sale_order_id.id,
            }
        except Exception as e:
            _logger.error(f"Order confirmation error: {str(e)}")
            return {"status": "error", "message": str(e)}, 500

    @http.route("/api/marketplace/products", type="json", auth="user", methods=["GET"])
    def get_products(self, **kw):
        """Get marketplace products"""
        try:
            domain = []
            if "channel_id" in kw:
                domain.append(("channel_id", "=", int(kw["channel_id"])))
            if "status" in kw:
                domain.append(("status", "=", kw["status"]))

            products = request.env["marketplace.product"].search(domain, limit=100)

            return {
                "status": "success",
                "data": [
                    {
                        "id": prod.id,
                        "channel_sku": prod.channel_sku,
                        "product_name": prod.product_id.name,
                        "price": prod.sale_price,
                        "qty": prod.qty_sellable,
                        "status": prod.status,
                    }
                    for prod in products
                ],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500


class WebhookController(http.Controller):
    """Webhook receivers for marketplace events"""

    @http.route(
        "/api/webhook/marketplace/<channel>",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def marketplace_webhook(self, channel, **kw):
        """
        Receive webhook from marketplace

        Each marketplace connector should implement specific webhook handling
        """
        try:
            _logger.info(f"Webhook received for channel: {channel}")
            _logger.info(f"Payload: {kw}")

            # Find channel
            Channel = http.request.env["marketplace.channel"]
            marketplace_channel = Channel.search(
                [("channel_type", "=", channel)], limit=1
            )

            if not marketplace_channel:
                return {"status": "error", "message": "Channel not found"}, 404

            # Get connector and process webhook
            connector = marketplace_channel._get_connector()
            result = connector._process_webhook(kw)

            return {
                "status": "success",
                "message": f"Webhook processed for {channel}",
                "result": result,
            }
        except Exception as e:
            _logger.error(f"Webhook error: {str(e)}")
            return {"status": "error", "message": str(e)}, 500
