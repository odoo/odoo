"""
Hepsiburada Marketplace Connector

Hepsiburada REST API entegrasyonu
Documentation: https://developer.hepsiburada.com/
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

import requests

from odoo.addons.joker_marketplace_core.connectors.base_connector import (
    BaseMarketplaceConnector,
)

_logger = logging.getLogger(__name__)


class HepsiburadaConnector(BaseMarketplaceConnector):
    """Hepsiburada API Connector"""

    API_BASE_URL = "https://api.hepsiburada.com/api"

    def __init__(self, channel_record):
        """Initialize Hepsiburada connector"""
        super().__init__(channel_record)
        self.shop_id = channel_record.shop_id
        self.api_key = channel_record.api_key

        self._configure_session()

    def _configure_session(self):
        """Configure requests session with Hepsiburada auth"""
        super()._configure_session()

        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def test_connection(self) -> bool:
        """Test Hepsiburada API connection"""
        try:
            _logger.info(f"Testing Hepsiburada connection for shop {self.shop_id}")

            url = f"{self.API_BASE_URL}/shop/{self.shop_id}"
            response = self._make_api_call("GET", url)

            if response.status_code == 200:
                data = response.json()
                _logger.info("Connection successful")
                return True
            else:
                _logger.error(f"Connection failed: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Hepsiburada connection test failed: {str(e)}")
            return False

    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """
        Sync orders from Hepsiburada

        Fetch all orders since last sync and create marketplace.order records
        """
        sync_log = self._create_sync_log("sync_orders")
        created_count = 0
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Hepsiburada order sync")

            if not last_sync:
                last_sync = datetime.now() - timedelta(hours=24)

            # Fetch orders from Hepsiburada API
            orders = self._fetch_hepsiburada_orders(last_sync)

            for order_data in orders:
                try:
                    # Process each order
                    shipping_addr = order_data.get("shippingAddress", {})
                    invoice_addr = order_data.get("invoiceAddress", {})

                    marketplace_order = self._process_marketplace_order(
                        {
                            "channel_order_id": str(order_data.get("orderNumber")),
                            "order_date": self._parse_datetime(
                                order_data.get("createdDate", "")
                            ),
                            "partner_name": shipping_addr.get("name", ""),
                            "partner_email": order_data.get("customerEmail", ""),
                            "partner_phone": shipping_addr.get("phoneNumber", ""),
                            "shipping_address": self._format_address(shipping_addr),
                            "amount_total": float(
                                order_data.get("totalPrice", {}).get("value", 0)
                            ),
                        }
                    )

                    # Create order lines
                    self._create_order_lines(
                        marketplace_order, order_data.get("lineItems", [])
                    )

                    created_count += 1

                except Exception as e:
                    _logger.error(
                        f"Failed to process order {order_data.get('orderNumber')}: {str(e)}"
                    )
                    failed_count += 1

            self._update_sync_log(
                "success",
                records_processed=len(orders),
                records_created=created_count,
                records_updated=updated_count,
                records_failed=failed_count,
            )

            _logger.info(
                f"Order sync completed: {created_count} created, {failed_count} failed"
            )

        except Exception as e:
            _logger.error(f"Order sync failed: {str(e)}")
            self._log_error(f"Sipariş senkronizasyonu başarısız: {str(e)}")

    def sync_inventory(self) -> dict[str, Any]:
        """
        Sync inventory to Hepsiburada

        Update product stock on Hepsiburada based on Odoo inventory
        """
        sync_log = self._create_sync_log("sync_inventory")
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Hepsiburada inventory sync")

            # Get all products for this channel
            products = self.env["marketplace.product"].search(
                [
                    ("channel_id", "=", self.channel.id),
                    ("active", "=", True),
                ]
            )

            for marketplace_product in products:
                try:
                    qty = marketplace_product.product_id.qty_available

                    # Update stock on Hepsiburada
                    self._update_hepsiburada_stock(
                        marketplace_product.channel_product_id, int(qty)
                    )

                    marketplace_product.write(
                        {
                            "qty_available": qty,
                            "sync_status": "synced",
                        }
                    )

                    updated_count += 1

                except Exception as e:
                    _logger.error(
                        f"Failed to sync stock for {marketplace_product.channel_sku}: {str(e)}"
                    )
                    failed_count += 1

            self._update_sync_log(
                "success",
                records_processed=len(products),
                records_updated=updated_count,
                records_failed=failed_count,
            )

            _logger.info(f"Inventory sync completed: {updated_count} updated")

        except Exception as e:
            _logger.error(f"Inventory sync failed: {str(e)}")
            self._log_error(f"Stok senkronizasyonu başarısız: {str(e)}")

    def sync_prices(self) -> dict[str, Any]:
        """
        Sync prices to Hepsiburada

        Update product prices on Hepsiburada based on Odoo prices
        """
        sync_log = self._create_sync_log("sync_prices")
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Hepsiburada price sync")

            # Get all products for this channel
            products = self.env["marketplace.product"].search(
                [
                    ("channel_id", "=", self.channel.id),
                    ("active", "=", True),
                ]
            )

            for marketplace_product in products:
                try:
                    price = (
                        marketplace_product.sale_price
                        or marketplace_product.product_id.list_price
                    )

                    # Update price on Hepsiburada
                    self._update_hepsiburada_price(
                        marketplace_product.channel_product_id, float(price)
                    )

                    marketplace_product.write(
                        {
                            "sale_price": price,
                            "sync_status": "synced",
                        }
                    )

                    updated_count += 1

                except Exception as e:
                    _logger.error(
                        f"Failed to sync price for {marketplace_product.channel_sku}: {str(e)}"
                    )
                    failed_count += 1

            self._update_sync_log(
                "success",
                records_processed=len(products),
                records_updated=updated_count,
                records_failed=failed_count,
            )

            _logger.info(f"Price sync completed: {updated_count} updated")

        except Exception as e:
            _logger.error(f"Price sync failed: {str(e)}")
            self._log_error(f"Fiyat senkronizasyonu başarısız: {str(e)}")

    # ==================== Hepsiburada API Methods ====================

    def _fetch_hepsiburada_orders(self, last_sync: datetime) -> list[dict]:
        """Fetch orders from Hepsiburada API"""
        try:
            # Format date for API (ISO 8601)
            start_date = self._format_datetime(last_sync)

            url = f"{self.API_BASE_URL}/shop/{self.shop_id}/orders"
            params = {
                "createdDateFrom": start_date,
                "limit": 100,
            }

            all_orders = []
            offset = 0

            # Pagination loop
            while True:
                params["offset"] = offset
                response = self._make_api_call("GET", url, params=params)
                data = response.json()

                orders = data.get("orders", [])
                if not orders:
                    break

                all_orders.extend(orders)

                # Check if there are more orders
                if len(orders) < params["limit"]:
                    break

                offset += params["limit"]

            _logger.info(f"Fetched {len(all_orders)} orders from Hepsiburada")
            return all_orders

        except Exception as e:
            _logger.error(f"Failed to fetch orders: {str(e)}")
            raise

    def _update_hepsiburada_stock(self, product_id: str, quantity: int) -> bool:
        """Update product stock on Hepsiburada"""
        try:
            url = f"{self.API_BASE_URL}/products/{product_id}/inventory"

            payload = {
                "quantity": quantity,
            }

            response = self._make_api_call("PUT", url, json=payload)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"Failed to update stock for {product_id}: {str(e)}")
            raise

    def _update_hepsiburada_price(self, product_id: str, price: float) -> bool:
        """Update product price on Hepsiburada"""
        try:
            url = f"{self.API_BASE_URL}/products/{product_id}/price"

            payload = {
                "price": price,
            }

            response = self._make_api_call("PUT", url, json=payload)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"Failed to update price for {product_id}: {str(e)}")
            raise

    # ==================== Helper Methods ====================

    def _format_address(self, address_data: dict) -> str:
        """Format address dict to string"""
        if not address_data:
            return ""

        parts = [
            address_data.get("name"),
            address_data.get("address1"),
            address_data.get("city"),
            address_data.get("district"),
            address_data.get("postalCode"),
        ]

        return ", ".join(str(p) for p in parts if p)

    def _process_webhook(self, webhook_data: dict) -> dict:
        """Process webhook from Hepsiburada"""
        try:
            event_type = webhook_data.get("eventType")

            if event_type == "OrderCreated":
                # Fetch and process new order
                self.sync_orders()
                return {"status": "processed"}

            elif event_type == "OrderStatusChanged":
                # Update order status
                order_id = webhook_data.get("orderId")
                status = webhook_data.get("orderStatus")

                MarketplaceOrder = self.env["marketplace.order"]
                order = MarketplaceOrder.search(
                    [("channel_order_id", "=", str(order_id))]
                )

                if order:
                    order.write({"status": self._map_status(status)})

                return {"status": "processed"}

            else:
                _logger.warning(f"Unknown webhook event: {event_type}")
                return {"status": "unknown_event"}

        except Exception as e:
            _logger.error(f"Webhook processing failed: {str(e)}")
            raise

    def _map_status(self, hb_status: str) -> str:
        """Map Hepsiburada order status to marketplace.order status"""
        status_map = {
            "New": "pending",
            "Confirmed": "confirmed",
            "Preparing": "confirmed",
            "Shipped": "shipped",
            "Delivered": "delivered",
            "Cancelled": "cancelled",
        }

        return status_map.get(hb_status, "pending")
