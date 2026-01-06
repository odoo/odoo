"""
Q-Commerce Teslimat Takibi

Hızlı teslimat siparişlerinin teslimat aşamalarını takip eder.
"""

from datetime import datetime
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class QCommerceDelivery(models.Model):
    """Q-Commerce Teslimat"""

    _name = "qcommerce.delivery"
    _description = "Q-Commerce Delivery"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    # ==================== Temel Alanlar ====================

    name = fields.Char("Teslimat No", required=True)
    platform_delivery_id = fields.Char("Platform Teslimat ID", unique=True)

    # ==================== Durum ====================

    status = fields.Selection(
        [
            ("waiting", "Kurye Bekleniyor"),
            ("assigned", "Kurye Atandı"),
            ("arrived", "Gitti"),
            ("in_progress", "Yolda"),
            ("delivered", "Teslim Edildi"),
            ("cancelled", "İptal Edildi"),
        ],
        "Durum",
        default="waiting",
        tracking=True,
    )

    # ==================== Teslimat Bilgileri ====================

    courier_name = fields.Char("Kurye Adı", tracking=True)
    courier_phone = fields.Char("Kurye Telefonu")
    courier_vehicle = fields.Char("Araç Bilgisi")
    courier_latitude = fields.Float("Kurye Enlem")
    courier_longitude = fields.Float("Kurye Boylam", help="Real-time konum")

    # ==================== Tarihler ====================

    requested_date = fields.Datetime("Talep Tarihi")
    assigned_date = fields.Datetime("Atanma Tarihi")
    pickup_date = fields.Datetime("Kargo Alma Tarihi")
    delivered_date = fields.Datetime("Teslimat Tarihi")

    # ==================== Süreler ====================

    estimated_delivery_minutes = fields.Integer("Tahmini Teslimat (Dakika)")
    actual_delivery_minutes = fields.Integer(
        "Gerçek Teslimat (Dakika)",
        compute="_compute_actual_delivery_minutes",
        store=True,
    )

    # ==================== İlişkiler ====================

    order_id = fields.Many2one("qcommerce.order", "Sipariş", required=True)
    channel_id = fields.Many2one(
        "qcommerce.channel", "Kanal", related="order_id.channel_id", store=True
    )

    company_id = fields.Many2one(
        "res.company", "Şirket", default=lambda self: self.env.company
    )

    # ==================== Hesaplama Alanları ====================

    @api.depends("delivered_date", "requested_date")
    def _compute_actual_delivery_minutes(self):
        """Gerçek teslimat süresini hesapla"""
        for delivery in self:
            if delivery.delivered_date and delivery.requested_date:
                delta = delivery.delivered_date - delivery.requested_date
                delivery.actual_delivery_minutes = int(delta.total_seconds() / 60)
            else:
                delivery.actual_delivery_minutes = 0

    # ==================== Durum Değişiklikleri ====================

    def action_assign_courier(self, courier_data: dict):
        """Kurye ata"""
        self.write(
            {
                "status": "assigned",
                "assigned_date": datetime.now(),
                "courier_name": courier_data.get("name"),
                "courier_phone": courier_data.get("phone"),
                "courier_vehicle": courier_data.get("vehicle"),
            }
        )

    def action_pickup(self):
        """Kargoya çıktı olarak işaretle"""
        self.write(
            {
                "status": "in_progress",
                "pickup_date": datetime.now(),
            }
        )

    def action_delivered(self):
        """Teslim edildi olarak işaretle"""
        self.write(
            {
                "status": "delivered",
                "delivered_date": datetime.now(),
            }
        )

        # Sipariş durumunu güncelle
        self.order_id.action_mark_delivered()

    def action_cancel(self):
        """Teslimatı iptal et"""
        self.write({"status": "cancelled"})

    # ==================== Yardımcı Metodlar ====================

    def update_courier_location(self, latitude: float, longitude: float):
        """Kurye konumunu güncelle (Real-time tracking)"""
        self.write(
            {
                "courier_latitude": latitude,
                "courier_longitude": longitude,
            }
        )

    def get_delivery_time_remaining(self) -> int:
        """Kalan teslimat süresini dakika cinsinden döndür"""
        if self.delivered_date:
            return 0

        if self.estimated_delivery_minutes:
            elapsed = (
                datetime.now() - (self.requested_date or datetime.now())
            ).total_seconds() / 60
            remaining = max(0, self.estimated_delivery_minutes - int(elapsed))
            return remaining

        return self.estimated_delivery_minutes or 0

    def is_delayed(self) -> bool:
        """Teslimat gecikmiş mi?"""
        if self.delivered_date:
            return self.actual_delivery_minutes > (self.estimated_delivery_minutes or 0)

        remaining = self.get_delivery_time_remaining()
        return remaining <= 0
