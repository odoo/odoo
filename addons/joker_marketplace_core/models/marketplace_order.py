import json

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class MarketplaceOrder(models.Model):
    """Pazaryeri Siparişi"""

    _name = "marketplace.order"
    _description = "Pazaryeri Siparişi"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "order_date desc"

    # Marketplace Info
    channel_id = fields.Many2one(
        "marketplace.channel", "Pazaryeri", required=True, ondelete="cascade"
    )
    channel_order_id = fields.Char("Pazaryeri Sipariş ID", required=True)

    # Order Info
    order_date = fields.Datetime("Sipariş Tarihi", required=True)
    status = fields.Selection(
        [
            ("pending", "Beklemede"),
            ("confirmed", "Onaylandı"),
            ("packed", "Paketlendi"),
            ("shipped", "Gönderildi"),
            ("delivered", "Teslim Edildi"),
            ("cancelled", "İptal Edildi"),
            ("returned", "İade Edildi"),
            ("error", "Hata"),
        ],
        string="Durum",
        default="pending",
        track_visibility="onchange",
    )

    # Customer Info
    partner_id = fields.Many2one("res.partner", "Müşteri")
    partner_name = fields.Char("Müşteri Adı")
    partner_email = fields.Char("E-posta")
    partner_phone = fields.Char("Telefon")

    # Address
    shipping_address = fields.Text("Teslimat Adresi")
    billing_address = fields.Text("Fatura Adresi")

    # Order Details
    amount_total = fields.Float("Toplam Tutar")
    shipping_cost = fields.Float("Kargo Ücreti")
    commission = fields.Float("Pazaryeri Komisyonu")

    # Order Lines
    line_ids = fields.One2many(
        "marketplace.order.line", "order_id", "Sipariş Satırları"
    )

    # Odoo Integration
    sale_order_id = fields.Many2one("sale.order", "Satış Siparişi")
    picking_ids = fields.One2many(
        "stock.picking", "marketplace_order_id", "İrsaliyeler"
    )
    invoice_ids = fields.One2many("account.move", "marketplace_order_id", "Faturalar")

    # Shipping
    shipping_method = fields.Char("Kargo Yöntemi")
    tracking_number = fields.Char("Takip Numarası")
    courier_id = fields.Many2one("res.partner", "Kurye Şirketi")
    shipping_status = fields.Selection(
        [
            ("pending", "Hazırlanıyor"),
            ("picked_up", "Toplandı"),
            ("in_transit", "Yolda"),
            ("delivered", "Teslim Edildi"),
            ("failed", "Başarısız"),
        ],
        string="Kargo Durumu",
    )

    # Notes & Comments
    customer_notes = fields.Text("Müşteri Notları")
    internal_notes = fields.Text("İç Notlar")

    # Sync Info
    synced_to_odoo = fields.Boolean("Odoo'ya Senkronize Edildi", default=False)
    sync_error = fields.Text("Senkronizasyon Hatası")

    # Extra Data
    extra_data = fields.Text("Ek Veriler (JSON)")

    _sql_constraints = [
        (
            "channel_order_id_unique",
            "UNIQUE(channel_id, channel_order_id)",
            "Bu sipariş ID pazaryeri içinde benzersiz olmalıdır!",
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Sipariş oluştur ve otomatik olarak Odoo'ya senkronize et"""
        records = super().create(vals_list)
        for record in records:
            if record.channel_id.auto_confirm_orders:
                record.action_confirm()
        return records

    def action_confirm(self):
        """Siparişi onayla ve Odoo'ya aktar"""
        for record in self:
            if record.synced_to_odoo:
                raise UserError("Bu sipariş zaten Odoo'ya aktarılmış!")

            try:
                # Create customer if not exists
                partner = record._get_or_create_partner()

                # Create Sales Order
                sale_order_vals = {
                    "partner_id": partner.id,
                    "partner_shipping_id": partner.id,
                    "partner_invoice_id": partner.id,
                    "marketplace_order_id": record.id,
                    "date_order": record.order_date,
                }

                sale_order = self.env["sale.order"].create(sale_order_vals)

                # Create Order Lines
                for line in record.line_ids:
                    sale_order.write(
                        {
                            "order_line": [
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": line.product_id.id,
                                        "product_uom_qty": line.qty,
                                        "price_unit": line.price,
                                    },
                                )
                            ]
                        }
                    )

                record.write(
                    {
                        "sale_order_id": sale_order.id,
                        "status": "confirmed",
                        "synced_to_odoo": True,
                    }
                )

                # Auto create invoice if needed
                if record.channel_id.auto_create_invoice:
                    sale_order.action_invoice_create()

            except Exception as e:
                record.write(
                    {
                        "status": "error",
                        "sync_error": str(e),
                    }
                )
                raise UserError(f"Sipariş onaylama hatası: {str(e)}")

    def action_mark_shipped(self, tracking_number=False):
        """Siparişi gönderildi olarak işaretle"""
        for record in self:
            record.write(
                {
                    "status": "shipped",
                    "shipping_status": "in_transit",
                    "tracking_number": tracking_number or record.tracking_number,
                }
            )
            # Notify marketplace
            record._notify_marketplace_shipment()

    def action_mark_delivered(self):
        """Siparişi teslim edildi olarak işaretle"""
        for record in self:
            record.write(
                {
                    "status": "delivered",
                    "shipping_status": "delivered",
                }
            )
            # Notify marketplace
            record._notify_marketplace_delivery()

    def action_cancel(self):
        """Siparişi iptal et"""
        for record in self:
            if record.status == "delivered":
                raise UserError("Teslim edilen sipariş iptal edilemez!")

            record.write({"status": "cancelled"})

            if record.sale_order_id:
                record.sale_order_id.action_cancel()

    def _get_or_create_partner(self):
        """Müşteri bilgisinden partner oluştur veya var olanı döndür"""
        self.ensure_one()

        partner = self.env["res.partner"].search(
            [
                ("email", "=", self.partner_email),
            ],
            limit=1,
        )

        if partner:
            return partner

        # Parse address
        address_data = self._parse_address(self.shipping_address)

        return self.env["res.partner"].create(
            {
                "name": self.partner_name,
                "email": self.partner_email,
                "phone": self.partner_phone,
                "street": address_data.get("street"),
                "city": address_data.get("city"),
                "state_id": address_data.get("state_id"),
                "zip": address_data.get("zip"),
                "country_id": address_data.get("country_id"),
            }
        )

    def _parse_address(self, address_string):
        """Adres stringini parse et"""
        # This is a placeholder. Real implementation depends on marketplace format
        return {
            "street": address_string,
            "city": "",
            "state_id": False,
            "zip": "",
            "country_id": (
                self.env.ref("base.tr").id if self.env.ref("base.tr") else False
            ),
        }

    def _notify_marketplace_shipment(self):
        """Pazaryerini kargo gönderiminden haberdar et"""
        pass

    def _notify_marketplace_delivery(self):
        """Pazaryerini teslimat tamamlanması hakkında haberdar et"""
        pass

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


class MarketplaceOrderLine(models.Model):
    """Pazaryeri Sipariş Satırı"""

    _name = "marketplace.order.line"
    _description = "Pazaryeri Sipariş Satırı"
    _order = "sequence"

    order_id = fields.Many2one(
        "marketplace.order", "Sipariş", required=True, ondelete="cascade"
    )
    sequence = fields.Integer("Sıra", default=10)

    product_id = fields.Many2one("product.product", "Ürün", required=True)
    marketplace_product_id = fields.Many2one("marketplace.product", "Pazaryeri Ürünü")

    qty = fields.Float("Miktar", required=True, default=1)
    price = fields.Float("Birim Fiyatı", required=True)
    discount = fields.Float("İndirim %")
    subtotal = fields.Float("Ara Toplam", compute="_compute_subtotal")

    _sql_constraints = [
        ("qty_positive", "CHECK(qty > 0)", "Miktar sıfırdan büyük olmalıdır!")
    ]

    @api.depends("qty", "price", "discount")
    def _compute_subtotal(self):
        """Satır toplamını hesapla"""
        for record in self:
            total = record.qty * record.price
            discount_amount = total * (record.discount / 100)
            record.subtotal = total - discount_amount
