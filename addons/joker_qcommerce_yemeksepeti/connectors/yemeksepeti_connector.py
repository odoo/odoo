"""
Yemeksepeti Delivery Hero API Connector

Yemeksepeti restoran teslimatı entegrasyonu
Documentation: https://developer.deliveryhero.com/
"""

from datetime import datetime, timedelta
import json
import logging
from typing import Any, Dict, List, Optional

from odoo.addons.joker_qcommerce_core.connectors.base_connector import (
    BaseQCommerceConnector,
)

_logger = logging.getLogger(__name__)


class YemeksepetiConnector(BaseQCommerceConnector):
    """Yemeksepeti (Delivery Hero) API Connector"""

    API_BASE_URL = "https://api.deliveryhero.io/api/v1"

    # Yemeksepeti varsayılan ayarları
    DEFAULT_PREPARATION_TIME = 30  # dakika
    DEFAULT_MAX_DELIVERY_TIME = 45  # dakika

    def __init__(self, channel_record):
        """Yemeksepeti connector'ı başlat"""
        super().__init__(channel_record)
        self.api_key = channel_record.api_key
        self.merchant_id = channel_record.merchant_id
        self.shop_id = channel_record.shop_id

        self._configure_session()

    def _configure_session(self):
        """Yemeksepeti session'ını yapılandır"""
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
        """Yemeksepeti API bağlantısını test et"""
        try:
            _logger.info(
                f"Testing Yemeksepeti connection for merchant {self.merchant_id}"
            )

            url = f"{self.API_BASE_URL}/merchants/{self.merchant_id}"
            response = self._make_api_call("GET", url)

            if response.status_code == 200:
                data = response.json()
                _logger.info(f"Connection successful. Restaurant: {data.get('name')}")
                return True
            else:
                _logger.error(f"Connection failed: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Yemeksepeti connection test failed: {str(e)}")
            return False

    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """
        Yemeksepeti'den siparişleri senkronize et

        Son senkronizasyondan beri gelen tüm siparişleri getir
        """
        sync_log = self._create_sync_log("sync_orders")
        created_count = 0
        updated_count = 0
        failed_count = 0

        try:
            _logger.info("Starting Yemeksepeti order sync")

            if not last_sync:
                last_sync = datetime.now() - timedelta(hours=24)

            # Yemeksepeti'den siparişleri getir
            orders = self._fetch_yemeksepeti_orders(last_sync)

            for order_data in orders:
                try:
                    # Sipariş bilgilerini hazırla
                    order_dict = {
                        "name": f"YS-{order_data.get('id')}",
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
                        "latitude": order_data.get("deliveryLocation", {}).get(
                            "latitude"
                        ),
                        "longitude": order_data.get("deliveryLocation", {}).get(
                            "longitude"
                        ),
                        "amount_subtotal": float(order_data.get("subtotal", 0)),
                        "amount_delivery": float(order_data.get("deliveryFee", 0)),
                        "amount_discount": float(order_data.get("discount", 0)),
                        "amount_total": float(order_data.get("total", 0)),
                        "payment_method": self._map_payment_method(
                            order_data.get("paymentMethod")
                        ),
                        "notes": order_data.get("specialInstructions", "")
                        or order_data.get("notes", ""),
                        "special_requests": self._format_special_requests(
                            order_data.get("items", [])
                        ),
                        "status": self._map_status(order_data.get("status")),
                    }

                    # Siparişi işle
                    marketplace_order = self._process_qcommerce_order(order_dict)

                    # Sipariş hatlarını oluştur (Restaurant özel alanları ile)
                    self._create_order_lines(
                        marketplace_order, order_data.get("items", [])
                    )

                    # Yemeksepeti otomatik sipariş kabulü aktifse, siparişi onayla
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
        Yemeksepeti'den sipariş için kurye talep et

        Sipariş hazırlandıktan sonra kurye otomatik talep edilir
        """
        try:
            _logger.info(f"Requesting courier for order {order.name}")

            url = f"{self.API_BASE_URL}/couriers/request"

            pickup_address = self._get_pickup_address()

            payload = {
                "orderId": order.platform_order_id,
                "merchantId": self.merchant_id,
                "pickupAddress": pickup_address,
                "deliveryAddress": {
                    "address": order.delivery_address,
                    "latitude": order.latitude,
                    "longitude": order.longitude,
                },
                "estimatedDeliveryTime": self.channel.max_delivery_time_minutes,
                "specialInstructions": order.special_requests or "",
                "restaurantName": self.env.company.name,
            }

            response = self._make_api_call("POST", url, json=payload)

            if response.status_code == 200 or response.status_code == 201:
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

    # ==================== Yemeksepeti API Metodları ====================

    def _fetch_yemeksepeti_orders(self, last_sync: datetime) -> list[dict]:
        """Yemeksepeti'den siparişleri getir"""
        try:
            url = f"{self.API_BASE_URL}/restaurants/{self.merchant_id}/orders"

            params = {
                "createdAfter": int(last_sync.timestamp()),
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

            _logger.info(f"Fetched {len(all_orders)} orders from Yemeksepeti")
            return all_orders

        except Exception as e:
            _logger.error(f"Failed to fetch orders: {str(e)}")
            return []

    def _update_order_status(self, platform_order_id: str, status: str) -> bool:
        """Yemeksepeti'de sipariş durumunu güncelle"""
        try:
            # Status mapping: qcommerce status'larını Delivery Hero status'larına çevir
            status_map = {
                "confirmed": "ACCEPTED",
                "preparing": "PREPARING",
                "ready": "READY_FOR_PICKUP",
                "on_way": "PICKED_UP",
                "delivered": "DELIVERED",
                "cancelled": "CANCELLED",
            }

            dh_status = status_map.get(status, "PENDING")

            url = f"{self.API_BASE_URL}/orders/{platform_order_id}/status"

            payload = {
                "status": dh_status,
                "timestamp": int(datetime.now().timestamp()),
            }

            response = self._make_api_call("PUT", url, json=payload)
            return response.status_code == 200

        except Exception as e:
            _logger.error(f"Failed to update order status: {str(e)}")
            return False

    def _get_pickup_address(self) -> dict:
        """Teslim alma adresini al (restoran adresi)"""
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

    def _format_special_requests(self, items: list[dict]) -> str:
        """Ürün modifikasyonlarını özel istekler olarak format et"""
        special = []

        for item in items:
            mods = item.get("modifications", [])
            if mods:
                item_name = item.get("name", "Ürün")
                mod_str = ", ".join([m.get("name", "") for m in mods])
                special.append(f"{item_name}: {mod_str}")

        return "\n".join(special) if special else ""

    def _map_payment_method(self, dh_method: str) -> str:
        """Delivery Hero ödeme yöntemini qcommerce payment method'a çevir"""
        method_map = {
            "cash": "cash",
            "creditCard": "card",
            "card": "card",
            "eWallet": "online",
            "online": "online",
        }

        return method_map.get(dh_method, "cash")

    def _map_status(self, dh_status: str) -> str:
        """Delivery Hero sipariş durumunu qcommerce status'a çevir"""
        status_map = {
            "PENDING": "pending",
            "ACCEPTED": "confirmed",
            "PREPARING": "preparing",
            "READY_FOR_PICKUP": "ready",
            "PICKED_UP": "on_way",
            "IN_TRANSIT": "on_way",
            "DELIVERED": "delivered",
            "CANCELLED": "cancelled",
            "FAILED": "cancelled",
            "REJECTED": "cancelled",
        }

        return status_map.get(dh_status, "pending")

    def _create_order_lines(self, order: Any, items: list[dict]):
        """Sipariş hatlarını oluştur (Restaurant modifikasyonları ile)"""
        QCommerceOrderLine = self.env["qcommerce.order.line"]

        for item in items:
            try:
                # Modifikasyonları not olarak ekle
                mods = item.get("modifications", [])
                mod_str = ", ".join([m.get("name", "") for m in mods]) if mods else ""

                QCommerceOrderLine.create(
                    {
                        "order_id": order.id,
                        "product_name": item.get("name", ""),
                        "platform_product_id": str(item.get("productId", "")),
                        "quantity": int(item.get("quantity", 1)),
                        "unit_price": float(item.get("price", 0)),
                        "notes": mod_str,  # Modifikasyonları note'ta sakla
                    }
                )
            except Exception as e:
                _logger.error(f"Failed to create order line: {str(e)}")

    def _process_webhook(self, webhook_data: dict) -> dict:
        """Yemeksepeti webhook'unu işle"""
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
