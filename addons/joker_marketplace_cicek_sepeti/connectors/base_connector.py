"""
Çiçek Sepeti Marketplace Connector

Çiçek Sepeti REST API entegrasyonu
Documentation: https://bayi-api.ciceksepeti.com/
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

import requests

from odoo.addons.joker_marketplace_core.connectors.base_connector import (
    BaseMarketplaceConnector,
)

_logger = logging.getLogger(__name__)


class CicekSepetiConnector(BaseMarketplaceConnector):
    """Çiçek Sepeti API Connector"""

    API_BASE_URL = "https://bayi-api.ciceksepeti.com/api"

    def __init__(self, channel_record):
        """Initialize Çiçek Sepeti connector"""
        super().__init__(channel_record)
        self.shop_id = channel_record.shop_id or channel_record.merchant_id
        self.api_key = channel_record.api_key

        self._configure_session()

    def _configure_session(self):
        """Configure requests session with Çiçek Sepeti auth"""
        super()._configure_session()

        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def test_connection(self) -> bool:
        """Test Çiçek Sepeti API connection"""
        try:
            _logger.info(f"Testing Çiçek Sepeti connection for shop {self.shop_id}")

            url = f"{self.API_BASE_URL}/shop/info"
            response = self._make_api_call("GET", url)

            if response.status_code == 200:
                data = response.json()
                _logger.info(f"Connection successful. Shop: {data.get('shopName')}")
                return True
            else:
                _logger.error(f"Connection failed: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Çiçek Sepeti connection test failed: {str(e)}")
            return False

    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """
        Sync orders from Çiçek Sepeti

        Fetch all orders since last sync and create marketplace.order records
        """
        sync_log = self._create_sync_log("sync_orders")
        created_count = 0
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Çiçek Sepeti order sync")

            if not last_sync:
                last_sync = datetime.now() - timedelta(hours=24)

            # Fetch orders from Çiçek Sepeti API
            orders = self._fetch_cicek_sepeti_orders(last_sync)

            for order_data in orders:
                try:
                    # Çiçek Sepeti has special fields for gift orders
                    shipping_addr = order_data.get("shippingAddress", {})

                    marketplace_order = self._process_marketplace_order(
                        {
                            "channel_order_id": str(order_data.get("orderId")),
                            "order_date": self._parse_datetime(
                                order_data.get("orderDate", "")
                            ),
                            "partner_name": shipping_addr.get("fullName", ""),
                            "partner_email": order_data.get("customerEmail", ""),
                            "partner_phone": shipping_addr.get("phoneNumber", ""),
                            "shipping_address": self._format_address(shipping_addr),
                            "amount_total": float(order_data.get("totalPrice", 0)),
                        }
                    )

                    # Create order lines
                    self._create_order_lines(
                        marketplace_order, order_data.get("items", [])
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
        Sync inventory to Çiçek Sepeti

        Update product stock on Çiçek Sepeti based on Odoo inventory
        """
        sync_log = self._create_sync_log("sync_inventory")
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Çiçek Sepeti inventory sync")

            # Get all products for this channel
            products = self.env["marketplace.product"].search(
                [
                    ("channel_id", "=", self.channel.id),
                    ("active", "=", True),
                ]
            )

            for marketplace_product in products:
                try:
                    qty = int(marketplace_product.product_id.qty_available)

                    # Update stock on Çiçek Sepeti
                    self._update_cicek_sepeti_stock(
                        marketplace_product.channel_product_id, qty
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
        Sync prices to Çiçek Sepeti

        Update product prices on Çiçek Sepeti based on Odoo prices
        """
        sync_log = self._create_sync_log("sync_prices")
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Çiçek Sepeti price sync")

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

                    # Update price on Çiçek Sepeti
                    self._update_cicek_sepeti_price(
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

    # ==================== Çiçek Sepeti API Methods ====================

    def _fetch_cicek_sepeti_orders(self, last_sync: datetime) -> list[dict]:
        """Fetch orders from Çiçek Sepeti API"""
        try:
            # Format date for API
            start_date = self._format_datetime(last_sync)

            url = f"{self.API_BASE_URL}/orders"
            params = {
                "fromDate": start_date,
                "pageSize": 100,
            }

            all_orders = []
            page = 1

            # Pagination loop
            while True:
                params["page"] = page
                response = self._make_api_call("GET", url, params=params)
                data = response.json()

                orders = data.get("orders", [])
                if not orders:
                    break

                all_orders.extend(orders)

                # Check if there are more pages
                if not data.get("hasMore", False):
                    break

                page += 1

            _logger.info(f"Fetched {len(all_orders)} orders from Çiçek Sepeti")
            return all_orders

        except Exception as e:
            _logger.error(f"Failed to fetch orders: {str(e)}")
            return []

    def _update_cicek_sepeti_stock(self, product_id: str, quantity: int) -> bool:
        """Update product stock on Çiçek Sepeti"""
        try:
            url = f"{self.API_BASE_URL}/products/{product_id}/stock"

            payload = {
                "quantity": quantity,
            }

            response = self._make_api_call("PUT", url, json=payload)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"Failed to update stock for {product_id}: {str(e)}")
            return False

    def _update_cicek_sepeti_price(self, product_id: str, price: float) -> bool:
        """Update product price on Çiçek Sepeti"""
        try:
            url = f"{self.API_BASE_URL}/products/{product_id}/price"

            payload = {
                "price": price,
            }

            response = self._make_api_call("PUT", url, json=payload)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"Failed to update price for {product_id}: {str(e)}")
            return False

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
            address_data.get("zipCode"),
        ]

        return ", ".join(str(p) for p in parts if p)

    def _process_webhook(self, webhook_data: dict) -> dict:
        """Process webhook from Çiçek Sepeti"""
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

    def _map_status(self, cs_status: str) -> str:
        """Map Çiçek Sepeti order status to marketplace.order status"""
        status_map = {
            "Pending": "pending",
            "Confirmed": "confirmed",
            "Processing": "confirmed",
            "Shipped": "shipped",
            "Delivered": "delivered",
            "Cancelled": "cancelled",
        }

        return status_map.get(cs_status, "pending")
