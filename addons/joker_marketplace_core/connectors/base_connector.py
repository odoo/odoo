"""
Base Connector Class for Marketplace Integrations

All marketplace connectors should inherit from this class and implement
the required abstract methods.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

import requests

_logger = logging.getLogger(__name__)


class BaseMarketplaceConnector(ABC):
    """Base class for all marketplace connectors"""

    def __init__(self, channel_record):
        """
        Initialize connector with marketplace channel record

        Args:
            channel_record: marketplace.channel record
        """
        self.channel = channel_record
        self.env = channel_record.env
        self.company = channel_record.company_id
        self.warehouse = (
            channel_record.warehouse_id or channel_record.company_id.warehouse_ids[0]
        )

        self.api_key = channel_record.api_key
        self.api_secret = channel_record.api_secret
        self.merchant_id = channel_record.merchant_id
        self.shop_id = channel_record.shop_id

        # Session for API calls
        self.session = requests.Session()
        self._configure_session()

        # Sync log
        self.sync_log = None
        self.api_call_count = 0

    def _configure_session(self):
        """Configure requests session (override in subclass if needed)"""
        self.session.headers.update(
            {
                "User-Agent": "JOKER-Marketplace-Connector/1.0",
            }
        )

    @abstractmethod
    def test_connection(self) -> bool:
        """Test API connection. Must be implemented by subclass"""
        pass

    @abstractmethod
    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """
        Sync orders from marketplace

        Args:
            last_sync: Only fetch orders after this datetime

        Returns:
            Dict with sync results
        """
        pass

    @abstractmethod
    def sync_inventory(self) -> dict[str, Any]:
        """
        Sync inventory to marketplace

        Returns:
            Dict with sync results
        """
        pass

    @abstractmethod
    def sync_prices(self) -> dict[str, Any]:
        """
        Sync prices to marketplace

        Returns:
            Dict with sync results
        """
        pass

    # ==================== Helper Methods ====================

    def _create_sync_log(self, operation: str) -> "marketplace.sync.log":
        """Create a sync log record"""
        SyncLog = self.env["marketplace.sync.log"]
        self.sync_log = SyncLog.create(
            {
                "channel_id": self.channel.id,
                "operation": operation,
                "status": "processing",
            }
        )
        return self.sync_log

    def _update_sync_log(self, status: str, **kwargs):
        """Update sync log with results"""
        if self.sync_log:
            update_vals = {
                "status": status,
                "end_time": datetime.now(),
                "api_call_count": self.api_call_count,
            }
            update_vals.update(kwargs)
            self.sync_log.write(update_vals)

    def _log_error(self, error_msg: str, error_details: dict = None):
        """Log an error"""
        _logger.error(f"[{self.channel.name}] {error_msg}")
        if error_details:
            _logger.error(f"Details: {error_details}")

        if self.sync_log:
            self.sync_log.write(
                {
                    "error_message": error_msg,
                    "status": "error",
                }
            )
            if error_details:
                self.sync_log.set_error_details(error_details)

    def _make_api_call(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP API call with error handling

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            **kwargs: Additional arguments for requests

        Returns:
            Response object
        """
        self.api_call_count += 1

        try:
            _logger.info(f"API Call: {method} {url}")
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self._log_error(f"API call failed: {str(e)}")
            raise

    # ==================== Order Processing ====================

    def _process_marketplace_order(self, order_data: dict) -> "marketplace.order":
        """
        Process marketplace order data and create/update order record

        Args:
            order_data: Dict containing order information

        Returns:
            marketplace.order record
        """
        MarketplaceOrder = self.env["marketplace.order"]

        # Check if order already exists
        existing = MarketplaceOrder.search(
            [
                ("channel_id", "=", self.channel.id),
                ("channel_order_id", "=", order_data["channel_order_id"]),
            ]
        )

        if existing:
            # Update existing order
            existing.write(self._prepare_order_vals(order_data))
            return existing
        else:
            # Create new order
            return MarketplaceOrder.create(self._prepare_order_vals(order_data))

    def _prepare_order_vals(self, order_data: dict) -> dict:
        """Prepare values dict for marketplace.order creation/update"""
        return {
            "channel_id": self.channel.id,
            "channel_order_id": order_data["channel_order_id"],
            "order_date": order_data.get("order_date"),
            "partner_name": order_data.get("partner_name"),
            "partner_email": order_data.get("partner_email"),
            "partner_phone": order_data.get("partner_phone"),
            "shipping_address": order_data.get("shipping_address"),
            "amount_total": order_data.get("amount_total", 0),
            "status": "pending",
        }

    def _create_order_lines(self, order: "marketplace.order", lines_data: list[dict]):
        """Create order lines from marketplace data"""
        OrderLine = self.env["marketplace.order.line"]

        for line_data in lines_data:
            product = self._get_or_create_product(line_data)

            OrderLine.create(
                {
                    "order_id": order.id,
                    "product_id": product.id,
                    "qty": line_data.get("qty", 1),
                    "price": line_data.get("price", 0),
                    "discount": line_data.get("discount", 0),
                }
            )

    # ==================== Product Processing ====================

    def _get_or_create_product(self, product_data: dict) -> "product.product":
        """
        Get or create product from marketplace data

        Args:
            product_data: Dict containing product information

        Returns:
            product.product record
        """
        Product = self.env["product.product"]

        # Try to find by SKU or product ID
        product = Product.search(
            [
                "|",
                ("barcode", "=", product_data.get("sku")),
                ("default_code", "=", product_data.get("sku")),
            ],
            limit=1,
        )

        if product:
            return product

        # Create new product
        return Product.create(
            {
                "name": product_data.get("name", "Untitled Product"),
                "type": "product",
                "categ_id": self._get_product_category(product_data).id,
                "default_code": product_data.get("sku"),
                "list_price": product_data.get("price", 0),
            }
        )

    def _get_product_category(self, product_data: dict):
        """Get or create product category"""
        ProductCategory = self.env["product.category"]

        category_name = product_data.get("category", "Marketplace Products")
        category = ProductCategory.search([("name", "=", category_name)], limit=1)

        if not category:
            category = ProductCategory.create({"name": category_name})

        return category

    # ==================== Inventory Processing ====================

    def _update_product_inventory(
        self, marketplace_product: "marketplace.product", qty: float
    ):
        """Update product inventory based on marketplace data"""
        StockMove = self.env["stock.move"]

        current_qty = marketplace_product.product_id.qty_available
        qty_diff = qty - current_qty

        if qty_diff > 0:
            # Add stock
            move = StockMove.create(
                {
                    "name": f"Inventory adjustment from {self.channel.name}",
                    "product_id": marketplace_product.product_id.id,
                    "product_uom_qty": qty_diff,
                    "quantity": qty_diff,
                    "product_uom": marketplace_product.product_id.uom_id.id,
                    "location_id": self.env.ref("stock.stock_location_suppliers").id,
                    "location_dest_id": self.warehouse.lot_stock_id.id,
                }
            )
            move._action_confirm()
            move._action_done()

        elif qty_diff < 0:
            # Remove stock
            move = StockMove.create(
                {
                    "name": f"Inventory adjustment from {self.channel.name}",
                    "product_id": marketplace_product.product_id.id,
                    "product_uom_qty": abs(qty_diff),
                    "quantity": abs(qty_diff),
                    "product_uom": marketplace_product.product_id.uom_id.id,
                    "location_id": self.warehouse.lot_stock_id.id,
                    "location_dest_id": self.env.ref(
                        "stock.stock_location_inventory"
                    ).id,
                }
            )
            move._action_confirm()
            move._action_done()

    # ==================== Utility Methods ====================

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for API"""
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    def _parse_datetime(self, dt_string: str) -> datetime:
        """Parse datetime from API response"""
        # Try different common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_string, fmt)
            except ValueError:
                continue

        raise ValueError(f"Cannot parse datetime: {dt_string}")

    def _sanitize_phone(self, phone: str) -> str:
        """Sanitize phone number"""
        if not phone:
            return ""
        # Remove non-digit characters except + and -
        return "".join(c for c in phone if c.isdigit() or c in "+-")

    def __del__(self):
        """Clean up session"""
        if hasattr(self, "session"):
            self.session.close()
