"""
N11 Marketplace Connector

N11 SOAP/REST API hybrid entegrasyonu
Documentation: https://www.n11.com/tools-detail/api
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from lxml import etree
import requests
from zeep import Client as SoapClient
from zeep.exceptions import Fault as SoapFault

from odoo.addons.joker_marketplace_core.connectors.base_connector import (
    BaseMarketplaceConnector,
)

_logger = logging.getLogger(__name__)


class N11Connector(BaseMarketplaceConnector):
    """N11 API Connector (SOAP + REST Hybrid)"""

    SOAP_WSDL = "https://soap.n11.com/gateway/slave/RssFeedService"
    REST_API_BASE = "https://api.n11.com/v1"

    def __init__(self, channel_record):
        """Initialize N11 connector"""
        super().__init__(channel_record)
        self.merchant_id = channel_record.merchant_id  # N11 seller ID
        self.api_key = channel_record.api_key  # API key
        self.api_secret = channel_record.api_secret  # API secret (for signature)

        # Initialize SOAP client
        self.soap_client = None
        self._init_soap_client()

        self._configure_session()

    def _init_soap_client(self):
        """Initialize ZEEP SOAP client"""
        try:
            self.soap_client = SoapClient(wsdl=self.SOAP_WSDL)
            _logger.info("SOAP client initialized successfully")
        except Exception as e:
            _logger.error(f"Failed to initialize SOAP client: {str(e)}")
            self.soap_client = None

    def _configure_session(self):
        """Configure requests session with N11 headers"""
        super()._configure_session()

        self.session.headers.update(
            {
                "Content-Type": "application/xml",
            }
        )

    def test_connection(self) -> bool:
        """Test N11 API connection via SOAP"""
        try:
            _logger.info(f"Testing N11 connection for seller {self.merchant_id}")

            if not self.soap_client:
                _logger.error("SOAP client not initialized")
                return False

            # Simple SOAP call to test connection
            # N11 SOAP service doesn't have a simple "ping" so we test with GetServiceFields
            try:
                response = self.soap_client.service.GetServiceFields(
                    request={
                        "authentication": {
                            "userName": self.merchant_id,
                            "userPassword": self.api_key,
                        },
                        "service": "ProductService",
                    }
                )
                _logger.info("SOAP connection test successful")
                return True
            except SoapFault as e:
                _logger.error(f"SOAP call failed: {str(e)}")
                # Try alternative: REST API test
                return self._test_rest_connection()

        except Exception as e:
            _logger.error(f"N11 connection test failed: {str(e)}")
            return False

    def _test_rest_connection(self) -> bool:
        """Test N11 REST API connection as fallback"""
        try:
            url = f"{self.REST_API_BASE}/account"

            # N11 REST uses signature-based auth
            timestamp = str(int(datetime.now().timestamp() * 1000))
            headers = self._get_rest_headers(timestamp)

            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"REST connection test failed: {str(e)}")
            return False

    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """
        Sync orders from N11

        N11 uses RSS feed for order data
        """
        sync_log = self._create_sync_log("sync_orders")
        created_count = 0
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting N11 order sync")

            if not last_sync:
                last_sync = datetime.now() - timedelta(hours=24)

            # Fetch orders via SOAP
            orders = self._fetch_n11_orders(last_sync)

            for order_data in orders:
                try:
                    marketplace_order = self._process_marketplace_order(
                        {
                            "channel_order_id": str(order_data.get("orderId")),
                            "order_date": self._parse_datetime(
                                order_data.get("createdDate", "")
                            ),
                            "partner_name": order_data.get("customerName", ""),
                            "partner_email": order_data.get("customerEmail", ""),
                            "partner_phone": order_data.get("customerPhone", ""),
                            "shipping_address": self._format_address(
                                order_data.get("shippingAddress")
                            ),
                            "amount_total": float(order_data.get("totalPrice", 0)),
                        }
                    )

                    # Create order lines from products
                    self._create_order_lines(
                        marketplace_order, order_data.get("products", [])
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
        Sync inventory to N11

        Update product stock on N11 based on Odoo inventory
        """
        sync_log = self._create_sync_log("sync_inventory")
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting N11 inventory sync")

            products = self.env["marketplace.product"].search(
                [
                    ("channel_id", "=", self.channel.id),
                    ("active", "=", True),
                ]
            )

            for marketplace_product in products:
                try:
                    qty = int(marketplace_product.product_id.qty_available)

                    # Update stock via SOAP
                    self._update_n11_stock(marketplace_product.channel_product_id, qty)

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
        Sync prices to N11

        Update product prices on N11 based on Odoo prices
        """
        sync_log = self._create_sync_log("sync_prices")
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting N11 price sync")

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

                    # Update price via SOAP
                    self._update_n11_price(
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

    # ==================== N11 SOAP API Methods ====================

    def _fetch_n11_orders(self, last_sync: datetime) -> list[dict]:
        """
        Fetch orders from N11 via SOAP

        N11 provides orders via RSS feed in SOAP response
        """
        try:
            if not self.soap_client:
                _logger.error("SOAP client not available")
                return []

            # Request orders created after last_sync
            start_date = self._format_datetime(last_sync)

            # N11 GetOrders SOAP call
            response = self.soap_client.service.GetOrders(
                request={
                    "authentication": {
                        "userName": self.merchant_id,
                        "userPassword": self.api_key,
                    },
                    "pagingData": {
                        "pageNumber": 1,
                        "pageSize": 100,
                    },
                    "orderFilter": {
                        "startDate": start_date,
                    },
                }
            )

            orders = []

            # Parse SOAP response
            if hasattr(response, "orders") and response.orders:
                orders = self._parse_soap_orders(response.orders)

            _logger.info(f"Fetched {len(orders)} orders from N11")
            return orders

        except SoapFault as e:
            _logger.error(f"SOAP fault: {str(e)}")
            return []
        except Exception as e:
            _logger.error(f"Failed to fetch orders: {str(e)}")
            return []

    def _update_n11_stock(self, product_id: str, quantity: int) -> bool:
        """Update product stock on N11 via SOAP"""
        try:
            if not self.soap_client:
                return False

            response = self.soap_client.service.SetProductInventory(
                request={
                    "authentication": {
                        "userName": self.merchant_id,
                        "userPassword": self.api_key,
                    },
                    "product": {
                        "productId": product_id,
                        "inventory": quantity,
                    },
                }
            )

            # Check response status
            if hasattr(response, "isSuccessful") and response.isSuccessful:
                return True

            _logger.warning(f"Stock update not successful for {product_id}")
            return False

        except Exception as e:
            _logger.error(f"Failed to update stock: {str(e)}")
            return False

    def _update_n11_price(self, product_id: str, price: float) -> bool:
        """Update product price on N11 via SOAP"""
        try:
            if not self.soap_client:
                return False

            response = self.soap_client.service.SetProductPrice(
                request={
                    "authentication": {
                        "userName": self.merchant_id,
                        "userPassword": self.api_key,
                    },
                    "product": {
                        "productId": product_id,
                        "price": price,
                    },
                }
            )

            if hasattr(response, "isSuccessful") and response.isSuccessful:
                return True

            _logger.warning(f"Price update not successful for {product_id}")
            return False

        except Exception as e:
            _logger.error(f"Failed to update price: {str(e)}")
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

    def _parse_soap_orders(self, orders_response) -> list[dict]:
        """Parse SOAP orders response"""
        orders = []

        try:
            # Convert ZEEP response to dict
            if hasattr(orders_response, "__iter__"):
                for order in orders_response:
                    orders.append(self._soap_object_to_dict(order))
            else:
                orders.append(self._soap_object_to_dict(orders_response))
        except Exception as e:
            _logger.error(f"Failed to parse SOAP orders: {str(e)}")

        return orders

    def _soap_object_to_dict(self, obj) -> dict:
        """Convert ZEEP SOAP object to dictionary"""
        if isinstance(obj, dict):
            return obj

        result = {}

        try:
            # Get all attributes from ZEEP object
            for key in dir(obj):
                if not key.startswith("_"):
                    value = getattr(obj, key, None)
                    if value and not callable(value):
                        result[key] = value
        except Exception as e:
            _logger.error(f"Failed to convert SOAP object: {str(e)}")

        return result

    def _get_rest_headers(self, timestamp: str) -> dict[str, str]:
        """
        Generate REST API headers with signature

        N11 REST API requires signed requests
        """
        import base64
        import hashlib
        import hmac

        # Create signature: HMAC-SHA256 of timestamp
        message = f"{self.api_key}{timestamp}"
        signature = hmac.new(
            self.api_secret.encode(), message.encode(), hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode()

        return {
            "X-Ticimax-Api-Key": self.api_key,
            "X-Ticimax-Api-Signature": signature_b64,
            "X-Ticimax-Api-Timestamp": timestamp,
            "Content-Type": "application/json",
        }

    def _process_webhook(self, webhook_data: dict) -> dict:
        """Process webhook from N11"""
        try:
            event_type = webhook_data.get("eventType")

            if event_type == "OrderCreated":
                # Fetch new orders
                self.sync_orders()
                return {"status": "processed"}

            elif event_type == "ProductInventoryChanged":
                # Sync affected product inventory
                self.sync_inventory()
                return {"status": "processed"}

            else:
                _logger.warning(f"Unknown webhook event: {event_type}")
                return {"status": "unknown_event"}

        except Exception as e:
            _logger.error(f"Webhook processing failed: {str(e)}")
            raise

    def _map_status(self, n11_status: str) -> str:
        """Map N11 order status to marketplace.order status"""
        status_map = {
            "New": "pending",
            "Approved": "confirmed",
            "Processing": "confirmed",
            "Shipped": "shipped",
            "Delivered": "delivered",
            "Cancelled": "cancelled",
        }

        return status_map.get(n11_status, "pending")
