import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MarketplaceProduct(models.Model):
    """Pazaryeri Ürün İlanı"""

    _name = "marketplace.product"
    _description = "Pazaryeri Ürün İlanı"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    # Main Relations
    channel_id = fields.Many2one(
        "marketplace.channel", "Pazaryeri", required=True, ondelete="cascade"
    )
    product_id = fields.Many2one("product.product", "Odoo Ürünü", required=True)

    # Channel-specific IDs
    channel_product_id = fields.Char("Pazaryeri Ürün ID", required=True)
    channel_sku = fields.Char("Pazaryeri SKU")

    # Listing Info
    title = fields.Char("Başlık")
    description = fields.Text("Açıklama")

    # Pricing
    list_price = fields.Float("İlan Fiyatı")
    sale_price = fields.Float("Satış Fiyatı")
    cost_price = fields.Float("Maliyet Fiyatı")
    margin = fields.Float("Marj %", compute="_compute_margin")

    # Stock
    qty_available = fields.Float("Mevcut Stok")
    qty_reserved = fields.Float("Rezerve Stok")
    qty_sellable = fields.Float("Satılabilir Stok", compute="_compute_qty_sellable")

    # Categories
    category_ids = fields.Many2many("product.category", string="Kategoriler")
    channel_category = fields.Char("Pazaryeri Kategorisi")

    # Status
    active = fields.Boolean("Aktif", default=True)
    status = fields.Selection(
        [
            ("draft", "Taslak"),
            ("active", "Aktif"),
            ("inactive", "İnaktif"),
            ("suspended", "Askıya Alındı"),
            ("delisted", "Kaldırılmış"),
        ],
        string="Durum",
        default="draft",
    )

    # Sync Info
    sync_status = fields.Selection(
        [
            ("pending", "Beklemede"),
            ("synced", "Senkronize Edildi"),
            ("error", "Hata"),
        ],
        string="Senkronizasyon Durumu",
        default="pending",
    )
    last_sync = fields.Datetime("Son Senkronizasyon")
    sync_error = fields.Text("Senkronizasyon Hatası")

    # Extra Fields
    extra_data = fields.Text("Ek Veriler (JSON)")

    _sql_constraints = [
        (
            "channel_product_id_unique",
            "UNIQUE(channel_id, channel_product_id)",
            "Bu ürün ID pazaryeri içinde benzersiz olmalıdır!",
        )
    ]

    @api.depends("sale_price", "cost_price")
    def _compute_margin(self):
        """Margin yüzdesini hesapla"""
        for record in self:
            if record.sale_price and record.cost_price:
                record.margin = (
                    (record.sale_price - record.cost_price) / record.sale_price
                ) * 100
            else:
                record.margin = 0

    @api.depends("qty_available", "qty_reserved")
    def _compute_qty_sellable(self):
        """Satılabilir stoku hesapla"""
        for record in self:
            record.qty_sellable = record.qty_available - record.qty_reserved

    def action_sync_now(self):
        """Ürünü hemen senkronize et"""
        for record in self:
            record.channel_id.action_sync_now()

    def action_deactivate(self):
        """Ürünü pazaryerinde deaktif et"""
        for record in self:
            record.write({"status": "inactive", "active": False})
            record.channel_id.action_sync_now()

    def action_activate(self):
        """Ürünü pazaryerinde aktif et"""
        for record in self:
            record.write({"status": "active", "active": True})
            record.channel_id.action_sync_now()

    def get_extra_data(self):
        """Ek verileri JSON olarak döndür"""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except:
            return {}

    def set_extra_data(self, data_dict):
        """Ek verileri kaydet"""
        self.extra_data = json.dumps(data_dict)
