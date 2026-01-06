"""
Vigo API Connector

Vigo aynı gün teslimat hizmeti entegrasyonu
Documentation: https://api.vigox.com/
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from odoo.addons.joker_qcommerce_core.connectors.base_connector import (
    BaseQCommerceConnector,
)

_logger = logging.getLogger(__name__)


class VigoConnector(BaseQCommerceConnector):
    """Vigo API Connector - Same Day Delivery"""

    API_BASE_URL = "https://api.vigox.com/v1"

    # Vigo varsayılan ayarları
    DEFAULT_PREPARATION_TIME = 20  # dakika
    DEFAULT_MAX_DELIVERY_TIME = 60  # dakika

    def __init__(self, channel_record):
        """Vigo connector'ı başlat"""
        super().__init__(channel_record)
        self.api_key = channel_record.api_key
        self.merchant_id = channel_record.merchant_id

        self._configure_session()

    def _configure_session(self):
        """Vigo session'ını yapılandır"""
        super()._configure_session()

        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Merchant-ID": self.merchant_id,
            }
        )

    def test_connection(self) -> bool:
        """Vigo API bağlantısını test et"""
        try:
            _logger.info(f"Testing Vigo connection for merchant {self.merchant_id}")

            url = f"{self.API_BASE_URL}/merchants/{self.merchant_id}"
            response = self._make_api_call("GET", url)

            if response.status_code == 200:
                data = response.json()
                _logger.info(f"Connection successful. Merchant: {data.get('name')}")
                return True
            else:
                _logger.error(f"Connection failed: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Vigo connection test failed: {str(e)}")
            return False

    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """
        Vigo'dan siparişleri senkronize et

        Son senkronizasyondan beri gelen tüm siparişleri getir
        """
        sync_log = self._create_sync_log("sync_orders")
        created_count = 0
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Vigo order sync")

            if not last_sync:
                last_sync = datetime.now() - timedelta(hours=24)

            # Vigo'dan siparişleri getir
            orders = self._fetch_vigo_orders(last_sync)

            for order_data in orders:
                try:
                    # Sipariş bilgilerini hazırla
                    order_dict = {
                        "name": f"VG-{order_data.get('id')}",
                        "platform_order_id": str(order_data.get("id")),
                        "order_date": self._parse_datetime(
                            order_data.get("createdAt", "")
                        ),
                        "customer_name": order_data.get("customer", {}).get("name", ""),
                        "customer_phone": self._sanitize_phone(
                            order_data.get("customer", {}).get("phone", "")
                        ),
                        "customer_email": order_data.get("customer", {}).get(
                            "email", ""
                        ),
                        "delivery_address": self._format_address(
                            order_data.get("deliveryAddress", {})
                        ),
                        "delivery_zone": order_data.get("area", ""),
                        "latitude": order_data.get("deliveryLocation", {}).get(
                            "latitude"
                        ),
                        "longitude": order_data.get("deliveryLocation", {}).get(
                            "longitude"
                        ),
                        "amount_subtotal": float(order_data.get("subtotal", 0)),
                        "amount_delivery": float(order_data.get("deliveryCharge", 0)),
                        "amount_discount": float(order_data.get("discount", 0)),
                        "amount_total": float(order_data.get("total", 0)),
                        "payment_method": self._map_payment_method(
                            order_data.get("paymentMethod")
                        ),
                        "notes": order_data.get("notes", ""),
                        "special_requests": order_data.get("specialRequests", ""),
                        "status": self._map_status(order_data.get("status")),
                    }

                    # Siparişi işle
                    marketplace_order = self._process_qcommerce_order(order_dict)

                    # Sipariş hatlarını oluştur
                    self._create_order_lines(
                        marketplace_order, order_data.get("items", [])
                    )

                    # Vigo otomatik sipariş kabulü aktifse, siparişi onayla
                    if (
                        self.channel.auto_accept_orders
                        and marketplace_order.status == "pending"
                    ):
                        marketplace_order.action_confirm()
                        _logger.info(f"Order {marketplace_order.name} auto-confirmed")

                    created_count += 1

                except Exception as e:
                    _logger.error(
                        f"Failed to process order {order_data.get('id')}: {str(e)}"
                    )
                    failed_count += 1

            # Sync log'u güncelle
            sync_log.log_success(
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
            sync_log.log_error(f"Sipariş senkronizasyonu başarısız: {str(e)}")

    def request_courier(self, order: Any) -> bool:
        """
        Vigo'dan sipariş için kurye talep et

        Sipariş hazırlandıktan sonra kurye otomatik talep edilir
        """
        try:
            _logger.info(f"Requesting courier for order {order.name}")

            url = f"{self.API_BASE_URL}/deliveries/request"

            pickup_address = self._get_pickup_address()

            payload = {
                "orderId": order.platform_order_id,
                "merchantId": self.merchant_id,
                "pickupAddress": pickup_address,
                "deliveryAddress": {
                    "fullAddress": order.delivery_address,
                    "latitude": order.latitude,
                    "longitude": order.longitude,
                },
                "estimatedDeliveryMinutes": self.channel.max_delivery_time_minutes,
                "specialInstructions": order.special_requests or "",
                "packageDetails": {
                    "weight": 5,  # kg (default)
                    "value": order.amount_total,
                },
            }

            response = self._make_api_call("POST", url, json=payload)

            if response.status_code == 200 or response.status_code == 201:
                data = response.json()

                # Teslimat kaydı oluştur
                QCommerceDelivery = self.env["qcommerce.delivery"]
                delivery = QCommerceDelivery.create(
                    {
                        "name": f"DEL-{data.get('deliveryId')}",
                        "platform_delivery_id": str(data.get("deliveryId")),
                        "order_id": order.id,
                        "status": "waiting",
                        "estimated_delivery_minutes": self.channel.max_delivery_time_minutes,
                        "requested_date": datetime.now(),
                    }
                )

                order.delivery_id = delivery.id
                _logger.info(
                    f"Courier requested successfully: {data.get('deliveryId')}"
                )
                return True
            else:
                _logger.error(f"Courier request failed: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Failed to request courier: {str(e)}")
            return False

    # ==================== Vigo API Metodları ====================

    def _fetch_vigo_orders(self, last_sync: datetime) -> list[dict]:
        """Vigo'dan siparişleri getir"""
        try:
            url = f"{self.API_BASE_URL}/merchants/{self.merchant_id}/orders"

            params = {
                "createdAfter": last_sync.isoformat(),
                "limit": 50,
                "offset": 0,
            }

            all_orders = []

            # Pagination
            while True:
                response = self._make_api_call("GET", url, params=params)
                data = response.json()

                orders = data.get("data", [])
                if not orders:
                    break

                all_orders.extend(orders)

                # Daha fazla sayfa var mı?
                pagination = data.get("pagination", {})
                if pagination.get("hasMore") is False:
                    break

                params["offset"] += params["limit"]

            _logger.info(f"Fetched {len(all_orders)} orders from Vigo")
            return all_orders

        except Exception as e:
            _logger.error(f"Failed to fetch orders: {str(e)}")
            return []

    def _update_order_status(self, platform_order_id: str, status: str) -> bool:
        """Vigo'da sipariş durumunu güncelle"""
        try:
            # Status mapping
            status_map = {
                "confirmed": "ACCEPTED",
                "preparing": "PREPARING",
                "ready": "READY",
                "on_way": "PICKED_UP",
                "delivered": "DELIVERED",
                "cancelled": "CANCELLED",
            }

            vigo_status = status_map.get(status, "PENDING")

            url = f"{self.API_BASE_URL}/orders/{platform_order_id}/status"

            payload = {
                "status": vigo_status,
                "timestamp": int(datetime.now().timestamp()),
            }

            response = self._make_api_call("PUT", url, json=payload)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"Failed to update order status: {str(e)}")
            return False

    def _get_pickup_address(self) -> dict:
        """Teslim alma adresini al"""
        company = self.env.company

        return {
            "fullName": company.name,
            "fullAddress": f"{company.street} {company.street2 or ''}",
            "city": company.city,
            "zipCode": company.zip,
            "phoneNumber": company.phone or "",
            "latitude": company.partner_id.geo_lat if company.partner_id else 0,
            "longitude": company.partner_id.geo_lng if company.partner_id else 0,
        }

    def _format_address(self, address_data: dict) -> str:
        """Adres dict'ini string'e çevir"""
        if not address_data:
            return ""

        if "fullAddress" in address_data:
            return address_data.get("fullAddress", "")

        parts = [
            address_data.get("fullName"),
            address_data.get("address"),
            address_data.get("city"),
            address_data.get("zipCode"),
        ]

        return ", ".join(str(p) for p in parts if p)

    def _map_payment_method(self, vigo_method: str) -> str:
        """Vigo ödeme yöntemini qcommerce payment method'a çevir"""
        method_map = {
            "CASH": "cash",
            "CARD": "card",
            "WALLET": "online",
            "ONLINE": "online",
        }

        return method_map.get(vigo_method, "cash")

    def _map_status(self, vigo_status: str) -> str:
        """Vigo sipariş durumunu qcommerce status'a çevir"""
        status_map = {
            "PENDING": "pending",
            "CONFIRMED": "confirmed",
            "ACCEPTED": "confirmed",
            "PREPARING": "preparing",
            "READY": "ready",
            "PICKED_UP": "on_way",
            "IN_TRANSIT": "on_way",
            "DELIVERED": "delivered",
            "CANCELLED": "cancelled",
            "FAILED": "cancelled",
        }

        return status_map.get(vigo_status, "pending")

    def _create_order_lines(self, order: Any, items: list[dict]):
        """Sipariş hatlarını oluştur"""
        QCommerceOrderLine = self.env["qcommerce.order.line"]

        for item in items:
            try:
                QCommerceOrderLine.create(
                    {
                        "order_id": order.id,
                        "product_name": item.get("name", ""),
                        "platform_product_id": str(item.get("productId", "")),
                        "quantity": int(item.get("quantity", 1)),
                        "unit_price": float(item.get("price", 0)),
                        "notes": item.get("notes", ""),
                    }
                )
            except Exception as e:
                _logger.error(f"Failed to create order line: {str(e)}")

    def _process_webhook(self, webhook_data: dict) -> dict:
        """Vigo webhook'unu işle"""
        try:
            event_type = webhook_data.get("eventType")

            if event_type == "order.created":
                # Yeni sipariş oluşturuldu
                self.sync_orders()
                return {"status": "processed"}

            elif event_type == "order.status_changed":
                # Sipariş durumu değişti
                order_id = webhook_data.get("orderId")
                new_status = webhook_data.get("status")

                QCommerceOrder = self.env["qcommerce.order"]
                order = QCommerceOrder.search(
                    [("platform_order_id", "=", str(order_id))]
                )

                if order:
                    order.write({"status": self._map_status(new_status)})

                return {"status": "processed"}

            elif event_type == "delivery.assigned":
                # Kurye atandı
                order_id = webhook_data.get("orderId")
                courier_data = webhook_data.get("courier", {})

                QCommerceOrder = self.env["qcommerce.order"]
                order = QCommerceOrder.search(
                    [("platform_order_id", "=", str(order_id))]
                )

                if order and order.delivery_id:
                    order.delivery_id.action_assign_courier(
                        {
                            "name": courier_data.get("name"),
                            "phone": courier_data.get("phone"),
                            "vehicle": courier_data.get("vehicle"),
                        }
                    )

                return {"status": "processed"}

            elif event_type == "delivery.location_updated":
                # Kurye konumu güncellendi
                order_id = webhook_data.get("orderId")
                location = webhook_data.get("location", {})

                QCommerceOrder = self.env["qcommerce.order"]
                order = QCommerceOrder.search(
                    [("platform_order_id", "=", str(order_id))]
                )

                if order and order.delivery_id:
                    order.delivery_id.update_courier_location(
                        location.get("latitude", 0), location.get("longitude", 0)
                    )

                return {"status": "processed"}

            elif event_type == "delivery.completed":
                # Teslimat tamamlandı
                order_id = webhook_data.get("orderId")

                QCommerceOrder = self.env["qcommerce.order"]
                order = QCommerceOrder.search(
                    [("platform_order_id", "=", str(order_id))]
                )

                if order:
                    order.action_mark_delivered()

                return {"status": "processed"}

            else:
                _logger.warning(f"Unknown webhook event: {event_type}")
                return {"status": "unknown_event"}

        except Exception as e:
            _logger.error(f"Webhook processing failed: {str(e)}")
            raise
