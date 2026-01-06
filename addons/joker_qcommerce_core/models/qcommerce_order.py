"""
Q-Commerce Hızlı Teslimat Siparişi

Getir, Yemeksepeti, Vigo gibi platformlardan gelen siparişleri temsil eder.
"""

from datetime import datetime
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class QCommerceOrder(models.Model):
    """Q-Commerce Siparişi"""

    _name = "qcommerce.order"
    _description = "Q-Commerce Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    # ==================== Temel Alanlar ====================

    name = fields.Char("Sipariş No", required=True, tracking=True)
    platform_order_id = fields.Char("Platform Sipariş ID", required=True, unique=True)

    # ==================== Durum ====================

    status = fields.Selection(
        [
            ("pending", "Beklemede"),
            ("confirmed", "Onaylandı"),
            ("preparing", "Hazırlanıyor"),
            ("ready", "Hazır"),
            ("on_way", "Yolda"),
            ("delivered", "Teslim Edildi"),
            ("cancelled", "İptal Edildi"),
        ],
        "Durum",
        default="pending",
        tracking=True,
    )

    # ==================== Tarihler ====================

    order_date = fields.Datetime("Sipariş Tarihi", required=True)
    confirmed_date = fields.Datetime("Onay Tarihi")
    ready_date = fields.Datetime("Hazır Tarihi")
    delivered_date = fields.Datetime("Teslimat Tarihi")

    # ==================== Müşteri Bilgileri ====================

    customer_name = fields.Char("Müşteri Adı", required=True)
    customer_phone = fields.Char("Müşteri Telefonu", required=True)
    customer_email = fields.Char("Müşteri E-posta")

    # ==================== Adres Bilgileri ====================

    delivery_address = fields.Text("Teslimat Adresi", required=True)
    delivery_zone = fields.Char("Teslimat Bölgesi")
    latitude = fields.Float("Enlem")
    longitude = fields.Float("Boylam")

    # ==================== Sipariş Detayları ====================

    amount_subtotal = fields.Float("Ürün Toplamı")
    amount_delivery = fields.Float("Teslimat Ücreti")
    amount_discount = fields.Float("İndirim")
    amount_total = fields.Float("Toplam Tutar", required=True)

    payment_method = fields.Selection(
        [
            ("cash", "Nakit"),
            ("card", "Kart"),
            ("online", "Online"),
        ],
        "Ödeme Yöntemi",
    )

    notes = fields.Text("Notlar")
    special_requests = fields.Text("Özel İstekler")

    # ==================== Hat Detayları ====================

    line_ids = fields.One2many("qcommerce.order.line", "order_id", "Ürünler")

    # ==================== İlişkiler ====================

    channel_id = fields.Many2one("qcommerce.channel", "Kanal", required=True)
    sale_order_id = fields.Many2one("sale.order", "Satış Siparişi")
    delivery_id = fields.Many2one("qcommerce.delivery", "Teslimat")

    partner_id = fields.Many2one(
        "res.partner", "Müşteri", compute="_compute_partner_id", store=True
    )

    company_id = fields.Many2one(
        "res.company", "Şirket", default=lambda self: self.env.company
    )

    # ==================== Hesaplama Alanları ====================

    @api.depends("customer_name", "customer_phone")
    def _compute_partner_id(self):
        """Müşteri partner kaydını otomatik oluştur/bul"""
        for order in self:
            if not order.customer_name:
                order.partner_id = None
                continue

            partner = self.env["res.partner"].search(
                [
                    ("name", "=", order.customer_name),
                    ("phone", "=", order.customer_phone),
                ],
                limit=1,
            )

            if not partner:
                partner = self.env["res.partner"].create(
                    {
                        "name": order.customer_name,
                        "phone": order.customer_phone,
                        "email": order.customer_email,
                    }
                )

            order.partner_id = partner

    # ==================== Durum Değişiklikleri ====================

    def action_confirm(self):
        """Siparişi onayla"""
        self.write(
            {
                "status": "confirmed",
                "confirmed_date": datetime.now(),
            }
        )
        _logger.info(f"Sipariş {self.name} onaylandı")

    def action_mark_preparing(self):
        """Siparişi hazırlanıyor olarak işaretle"""
        self.write({"status": "preparing"})

    def action_mark_ready(self):
        """Siparişi hazır olarak işaretle"""
        self.write(
            {
                "status": "ready",
                "ready_date": datetime.now(),
            }
        )

        # Otomatik kurye talebini gönder
        if self.channel_id.auto_request_courier:
            self._request_courier()

    def action_mark_on_way(self):
        """Siparişi yolda olarak işaretle"""
        self.write({"status": "on_way"})

    def action_mark_delivered(self):
        """Siparişi teslim edildi olarak işaretle"""
        self.write(
            {
                "status": "delivered",
                "delivered_date": datetime.now(),
            }
        )

        # Satış siparişini teslim edildi olarak işaretle
        if self.sale_order_id:
            self.sale_order_id.write(
                {
                    "state": "done",
                    "qcommerce_delivered_date": datetime.now(),
                }
            )

    def action_cancel(self):
        """Siparişi iptal et"""
        self.write({"status": "cancelled"})

        if self.sale_order_id:
            self.sale_order_id.write({"state": "cancel"})

    # ==================== Yardımcı Metodlar ====================

    def _request_courier(self):
        """Platformdan kurye talep et"""
        try:
            connector = self._get_connector()
            connector.request_courier(self)
        except Exception as e:
            _logger.error(f"Kurye talebi başarısız: {str(e)}")

    def _get_connector(self):
        """Platform connector'ını al"""
        if self.channel_id.platform_type == "getir":
            from .connectors.getir_connector import GetirConnector

            return GetirConnector(self.channel_id)
        elif self.channel_id.platform_type == "yemeksepeti":
            from .connectors.yemeksepeti_connector import YemeksepetiConnector

            return YemeksepetiConnector(self.channel_id)
        elif self.channel_id.platform_type == "vigo":
            from .connectors.vigo_connector import VigoConnector

            return VigoConnector(self.channel_id)
        else:
            raise ValueError(f"Bilinmeyen platform: {self.channel_id.platform_type}")

    def create_sale_order(self):
        """Qcommerce siparişinden satış siparişi oluştur"""
        if self.sale_order_id:
            return self.sale_order_id

        # Satış siparişi oluştur
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_id.id,
                "date_order": self.order_date,
                "qcommerce_order_id": self.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.quantity,
                            "price_unit": line.unit_price,
                        },
                    )
                    for line in self.line_ids
                ],
            }
        )

        self.sale_order_id = sale_order.id

        # Siparişi otomatik onayla
        sale_order.action_confirm()

        return sale_order


class QCommerceOrderLine(models.Model):
    """Q-Commerce Sipariş Hatları"""

    _name = "qcommerce.order.line"
    _description = "Q-Commerce Order Line"

    order_id = fields.Many2one(
        "qcommerce.order", "Sipariş", required=True, ondelete="cascade"
    )

    product_id = fields.Many2one("product.product", "Ürün")
    product_name = fields.Char("Ürün Adı", required=True)
    platform_product_id = fields.Char("Platform Ürün ID")

    quantity = fields.Integer("Miktar", required=True, default=1)
    unit_price = fields.Float("Birim Fiyat", required=True)
    subtotal = fields.Float("Toplam", compute="_compute_subtotal", store=True)

    notes = fields.Char("Not")

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        """Alt toplamı hesapla"""
        for line in self:
            line.subtotal = line.quantity * line.unit_price
