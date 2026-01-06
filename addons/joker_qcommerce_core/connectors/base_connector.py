"""
Q-Commerce Base Connector - Abstract Sınıfı

Tüm hızlı teslimat platformları için base connector.
"""

from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

import requests

from odoo import fields

_logger = logging.getLogger(__name__)


class BaseQCommerceConnector(ABC):
    """Q-Commerce Platform Connector Base Sınıfı"""

    def __init__(self, channel_record):
        """Connector'ı başlat"""
        self.env = channel_record.env
        self.channel = channel_record
        self.session = None

        self._configure_session()

    def _configure_session(self):
        """HTTP session'ı yapılandır"""
        self.session = requests.Session()
        self.session.timeout = 30
        self.session.headers.update(
            {
                "User-Agent": "JOKER QCommerce/1.0",
            }
        )

    # ==================== Abstract Metodlar ====================

    @abstractmethod
    def test_connection(self) -> bool:
        """Platform API bağlantısını test et"""
        pass

    @abstractmethod
    def sync_orders(self, last_sync: datetime | None = None) -> dict[str, Any]:
        """Platformdan siparişleri senkronize et"""
        pass

    @abstractmethod
    def request_courier(self, order: Any) -> bool:
        """Platformdan kurye talep et"""
        pass

    # ==================== Yardımcı Metodlar ====================

    def _make_api_call(self, method: str, url: str, **kwargs) -> requests.Response:
        """API çağrısı yap"""
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            _logger.error(f"API çağrısı başarısız: {str(e)}")
            raise

    def _create_sync_log(self, operation_type: str):
        """Senkronizasyon logu oluştur"""
        QCommerceSyncLog = self.env["qcommerce.sync.log"]
        return QCommerceSyncLog.create_sync_log(self.channel, operation_type)

    def _update_sync_log(self, log_record, status: str, **kwargs):
        """Senkronizasyon logunu güncelle"""
        if status == "success":
            log_record.log_success(**kwargs)
        else:
            log_record.log_error(**kwargs)

    def _process_qcommerce_order(self, order_data: dict) -> Any:
        """Platform siparişini qcommerce.order olarak oluştur"""
        QCommerceOrder = self.env["qcommerce.order"]

        platform_order_id = str(order_data.get("id") or order_data.get("orderId"))

        # Varsa güncelle, yoksa oluştur
        order = QCommerceOrder.search([("platform_order_id", "=", platform_order_id)])

        if order:
            order.write(order_data)
            return order

        order = QCommerceOrder.create(
            {
                "name": f"QC-{self.channel.name[:3]}-{platform_order_id}",
                "platform_order_id": platform_order_id,
                "channel_id": self.channel.id,
                **order_data,
            }
        )

        return order

    def _parse_datetime(self, date_str: str) -> datetime | None:
        """String tarihini datetime'a çevir"""
        if not date_str:
            return None

        try:
            # ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            try:
                # Unix timestamp
                return datetime.fromtimestamp(int(date_str))
            except:
                return None

    def _format_datetime(self, dt: datetime) -> str:
        """Datetime'ı API formatına çevir (ISO 8601)"""
        if not dt:
            return ""

        return dt.isoformat()

    def _sanitize_phone(self, phone: str) -> str:
        """Telefon numarasını temizle"""
        if not phone:
            return ""

        # Sadece rakamları tut
        phone = "".join(filter(str.isdigit, phone))

        # Türkiye numaraları: +90 ile başlayan veya 0 ile başlayan
        if phone.startswith("90"):
            phone = "+" + phone
        elif phone.startswith("0"):
            phone = "+90" + phone[1:]
        elif not phone.startswith("+"):
            phone = "+90" + phone

        return phone

    def _log_error(self, error_msg: str):
        """Hata logla"""
        _logger.error(f"[{self.channel.platform_type}] {error_msg}")
