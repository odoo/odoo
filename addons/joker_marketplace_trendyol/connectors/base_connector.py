"""
Trendyol Marketplace Connector

Trendyol REST API v2.0 entegrasyonu
Documentation: https://developer.trendyol.com/
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

import requests

from odoo.addons.joker_marketplace_core.connectors.base_connector import (
    BaseMarketplaceConnector,
)

_logger = logging.getLogger(__name__)


class TrendyolConnector(BaseMarketplaceConnector):
    """Trendyol API Connector"""

    API_BASE_URL = "https://api.trendyol.com/v2"

    def __init__(self, channel_record):
        """Initialize Trendyol connector"""
        super().__init__(channel_record)
        self.merchant_id = channel_record.merchant_id
        self.api_key = channel_record.api_key
        self.api_secret = channel_record.api_secret

        # Configure session with Trendyol headers
        self._configure_session()

    def _configure_session(self):
        """Configure requests session with Trendyol auth"""
        super()._configure_session()

        # Trendyol uses Basic Auth with merchant_id:api_key
        import base64

        auth_string = f"{self.merchant_id}:{self.api_key}"
        auth_bytes = auth_string.encode("utf-8")
        auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

        self.session.headers.update(
            {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
            }
        )

    def test_connection(self) -> bool:
        """Test Trendyol API connection"""
        try:
            _logger.info(f"Testing Trendyol connection for merchant {self.merchant_id}")

            url = f"{self.API_BASE_URL}/merchant/{self.merchant_id}"
            response = self._make_api_call("GET", url)

            if response.status_code == 200:
                data = response.json()
                _logger.info(f"Connection successful. Shop: {data.get('shopName')}")
                return True
            else:
                _logger.error(f"Connection failed: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Trendyol connection test failed: {str(e)}")
            return False

    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """
        Sync orders from Trendyol

        Fetch all orders since last sync and create marketplace.order records
        """
        sync_log = self._create_sync_log("sync_orders")
        created_count = 0
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Trendyol order sync")

            if not last_sync:
                last_sync = datetime.now() - timedelta(hours=24)

            # Fetch orders from Trendyol API
            orders = self._fetch_trendyol_orders(last_sync)

            for order_data in orders:
                try:
                    # Process each order
                    marketplace_order = self._process_marketplace_order(
                        {
                            "channel_order_id": str(order_data.get("orderId")),
                            "order_date": self._parse_datetime(
                                order_data.get("createdDate", "")
                            ),
                            "partner_name": order_data.get("invoiceAddress", {}).get(
                                "fullName", ""
                            ),
                            "partner_email": order_data.get("invoiceAddress", {}).get(
                                "email", ""
                            ),
                            "partner_phone": order_data.get("invoiceAddress", {}).get(
                                "phoneNumber", ""
                            ),
                            "shipping_address": self._format_address(
                                order_data.get("shippingAddress")
                            ),
                            "amount_total": float(order_data.get("totalPrice", 0)),
                        }
                    )

                    # Create order lines
                    self._create_order_lines(
                        marketplace_order, order_data.get("lines", [])
                    )

                    created_count += 1

                except Exception as e:
                    _logger.error(
                        f"Failed to process order {order_data.get('orderId')}: {str(e)}"
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
        Sync inventory to Trendyol

        Update product stock on Trendyol based on Odoo inventory
        """
        sync_log = self._create_sync_log("sync_inventory")
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Trendyol inventory sync")

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

                    # Update stock on Trendyol
                    self._update_trendyol_stock(
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
        Sync prices to Trendyol

        Update product prices on Trendyol based on Odoo prices
        """
        sync_log = self._create_sync_log("sync_prices")
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Trendyol price sync")

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

                    # Update price on Trendyol
                    self._update_trendyol_price(
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

    # ==================== Trendyol API Methods ====================

    def _fetch_trendyol_orders(self, last_sync: datetime) -> list[dict]:
        """Fetch orders from Trendyol API"""
        try:
            # Format date for API
            start_date = self._format_datetime(last_sync)

            # Build request
            url = f"{self.API_BASE_URL}/merchant/{self.merchant_id}/orders"
            params = {
                "startDate": start_date,
                "size": 200,
            }

            all_orders = []
            page = 0

            # Pagination loop
            while True:
                params["page"] = page
                response = self._make_api_call("GET", url, params=params)
                data = response.json()

                orders = data.get("content", [])
                if not orders:
                    break

                all_orders.extend(orders)

                # Check if there are more pages
                if not data.get("hasNext", False):
                    break

                page += 1

            _logger.info(f"Fetched {len(all_orders)} orders from Trendyol")
            return all_orders

        except Exception as e:
            _logger.error(f"Failed to fetch orders: {str(e)}")
            raise

    def _update_trendyol_stock(self, product_id: str, quantity: int) -> bool:
        """Update product stock on Trendyol"""
        try:
            url = f"{self.API_BASE_URL}/merchant/{self.merchant_id}/products/{product_id}/stock"

            payload = {
                "quantity": quantity,
            }

            response = self._make_api_call("PUT", url, json=payload)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"Failed to update stock for {product_id}: {str(e)}")
            raise

    def _update_trendyol_price(self, product_id: str, price: float) -> bool:
        """Update product price on Trendyol"""
        try:
            url = f"{self.API_BASE_URL}/merchant/{self.merchant_id}/products/{product_id}/price"

            payload = {
                "salePrice": price,
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
            address_data.get("fullName"),
            address_data.get("address"),
            address_data.get("city"),
            address_data.get("district"),
            address_data.get("postalCode"),
        ]

        return ", ".join(str(p) for p in parts if p)

    def _prepare_order_vals(self, order_data: dict) -> dict:
        """Prepare values for marketplace.order creation"""
        vals = super()._prepare_order_vals(order_data)

        # Add Trendyol-specific fields
        vals.update(
            {
                "shipping_method": "Trendyol Default",
                "extra_data": str(order_data),  # Store original data
            }
        )

        return vals

    def _process_webhook(self, webhook_data: dict) -> dict:
        """Process webhook from Trendyol"""
        try:
            event_type = webhook_data.get("eventType")

            if event_type == "OrderCreated":
                # Fetch and process new order
                order_id = webhook_data.get("orderId")
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

    def _map_status(self, trendyol_status: str) -> str:
        """Map Trendyol order status to marketplace.order status"""
        status_map = {
            "New": "pending",
            "Confirmed": "confirmed",
            "Preparing": "confirmed",
            "Shipped": "shipped",
            "Delivered": "delivered",
            "Cancelled": "cancelled",
            "Returned": "returned",
        }

        return status_map.get(trendyol_status, "pending")
