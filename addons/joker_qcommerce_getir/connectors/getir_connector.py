"""
Getir Partner API Connector

Getir Çarşı ve Getir Yemek entegrasyonu
Documentation: https://integrations.getir.com/
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from odoo.addons.joker_qcommerce_core.connectors.base_connector import (
    BaseQCommerceConnector,
)

_logger = logging.getLogger(__name__)


class GetirConnector(BaseQCommerceConnector):
    """Getir Partner API Connector"""

    API_BASE_URL = "https://integrations.getir.com/api"

    # Getir varsayılan ayarları
    DEFAULT_PREPARATION_TIME = 15  # dakika
    DEFAULT_MAX_DELIVERY_TIME = 30  # dakika

    def __init__(self, channel_record):
        """Getir connector'ı başlat"""
        super().__init__(channel_record)
        self.api_key = channel_record.api_key
        self.merchant_id = channel_record.merchant_id

        self._configure_session()

    def _configure_session(self):
        """Getir session'ını yapılandır"""
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
        """Getir API bağlantısını test et"""
        try:
            _logger.info(f"Testing Getir connection for merchant {self.merchant_id}")

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
            _logger.error(f"Getir connection test failed: {str(e)}")
            return False

    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """
        Getir'den siparişleri senkronize et

        Son senkronizasyondan beri gelen tüm siparişleri getir
        """
        sync_log = self._create_sync_log("sync_orders")
        created_count = 0
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Getir order sync")

            if not last_sync:
                last_sync = datetime.now() - timedelta(hours=24)

            # Getir'den siparişleri getir
            orders = self._fetch_getir_orders(last_sync)

            for order_data in orders:
                try:
                    # Sipariş bilgilerini hazırla
                    order_dict = {
                        "name": f"GR-{order_data.get('id')}",
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
                        "delivery_zone": order_data.get("deliveryZone", ""),
                        "latitude": order_data.get("location", {}).get("latitude"),
                        "longitude": order_data.get("location", {}).get("longitude"),
                        "amount_subtotal": float(order_data.get("subtotal", 0)),
                        "amount_delivery": float(order_data.get("deliveryFee", 0)),
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

                    # Getir otomatik sipariş kabulü aktifse, siparişi onayla
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
        Getir'den sipariş için kurye talep et

        Sipariş hazırlandıktan sonra kurye otomatik talep edilir
        """
        try:
            _logger.info(f"Requesting courier for order {order.name}")

            url = f"{self.API_BASE_URL}/couriers/request"

            payload = {
                "orderId": order.platform_order_id,
                "merchantId": self.merchant_id,
                "pickupAddress": self._format_address(self._get_pickup_address()),
                "deliveryAddress": order.delivery_address,
                "location": {
                    "latitude": order.latitude,
                    "longitude": order.longitude,
                },
                "estimatedDeliveryTime": self.channel.max_delivery_time_minutes,
                "specialRequests": order.special_requests or "",
            }

            response = self._make_api_call("POST", url, json=payload)

            if response.status_code == 200:
                data = response.json()

                # Teslimat kaydı oluştur
                QCommerceDelivery = self.env["qcommerce.delivery"]
                delivery = QCommerceDelivery.create(
                    {
                        "name": f"DEL-{data.get('courierId')}",
                        "platform_delivery_id": str(data.get("courierId")),
                        "order_id": order.id,
                        "status": "waiting",
                        "estimated_delivery_minutes": self.channel.max_delivery_time_minutes,
                        "requested_date": datetime.now(),
                    }
                )

                order.delivery_id = delivery.id
                _logger.info(f"Courier requested successfully: {data.get('courierId')}")
                return True
            else:
                _logger.error(f"Courier request failed: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Failed to request courier: {str(e)}")
            return False

    # ==================== Getir API Metodları ====================

    def _fetch_getir_orders(self, last_sync: datetime) -> list[dict]:
        """Getir'den siparişleri getir"""
        try:
            url = f"{self.API_BASE_URL}/merchants/{self.merchant_id}/orders"

            # Tarih formatını Getir beklentisine uyarla
            params = {
                "createdAfter": int(
                    last_sync.timestamp() * 1000
                ),  # Millisecond cinsinden
                "limit": 100,
                "offset": 0,
            }

            all_orders = []

            # Pagination
            while True:
                response = self._make_api_call("GET", url, params=params)
                data = response.json()

                orders = data.get("orders", [])
                if not orders:
                    break

                all_orders.extend(orders)

                # Daha fazla sayfa var mı?
                if len(orders) < params["limit"]:
                    break

                params["offset"] += params["limit"]

            _logger.info(f"Fetched {len(all_orders)} orders from Getir")
            return all_orders

        except Exception as e:
            _logger.error(f"Failed to fetch orders: {str(e)}")
            return []

    def _update_order_status(self, platform_order_id: str, status: str) -> bool:
        """Getir'de sipariş durumunu güncelle"""
        try:
            # Status mapping: Getir status'larını API'ye çevir
            status_map = {
                "confirmed": "ACCEPTED",
                "preparing": "PREPARING",
                "ready": "READY",
                "on_way": "PICKED_UP",
                "delivered": "DELIVERED",
                "cancelled": "CANCELLED",
            }

            getir_status = status_map.get(status, "PENDING")

            url = f"{self.API_BASE_URL}/orders/{platform_order_id}/status"

            payload = {
                "status": getir_status,
                "timestamp": int(datetime.now().timestamp() * 1000),
            }

            response = self._make_api_call("PUT", url, json=payload)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"Failed to update order status: {str(e)}")
            return False

    def _get_pickup_address(self) -> dict:
        """Teslim alma adresini al (mağaza adresi)"""
        company = self.env.company

        return {
            "fullName": company.name,
            "address": f"{company.street} {company.street2 or ''}",
            "city": company.city,
            "district": company.state_id.name if company.state_id else "",
            "zipCode": company.zip,
            "phoneNumber": company.phone or "",
            "latitude": company.partner_id.geo_lat if company.partner_id else 0,
            "longitude": company.partner_id.geo_lng if company.partner_id else 0,
        }

    def _format_address(self, address_data: dict) -> str:
        """Adres dict'ini string'e çevir"""
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

    def _map_payment_method(self, getir_method: str) -> str:
        """Getir ödeme yöntemini qcommerce payment method'a çevir"""
        method_map = {
            "cash": "cash",
            "creditCard": "card",
            "eWallet": "online",
            "bankTransfer": "online",
        }

        return method_map.get(getir_method, "cash")

    def _map_status(self, getir_status: str) -> str:
        """Getir sipariş durumunu qcommerce status'a çevir"""
        status_map = {
            "PENDING": "pending",
            "ACCEPTED": "confirmed",
            "PREPARING": "preparing",
            "READY": "ready",
            "PICKED_UP": "on_way",
            "IN_TRANSIT": "on_way",
            "DELIVERED": "delivered",
            "CANCELLED": "cancelled",
            "FAILED": "cancelled",
        }

        return status_map.get(getir_status, "pending")

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
        """Getir webhook'unu işle"""
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

            elif event_type == "courier.assigned":
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

            else:
                _logger.warning(f"Unknown webhook event: {event_type}")
                return {"status": "unknown_event"}

        except Exception as e:
            _logger.error(f"Webhook processing failed: {str(e)}")
            raise
