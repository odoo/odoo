import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MarketplaceChannel(models.Model):
    """Pazaryeri Kanalı (N11, Trendyol, Hepsiburada, vb.)"""

    _name = "marketplace.channel"
    _description = "Pazaryeri Kanalı"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char("Kanal Adı", required=True, track_visibility="onchange")
    channel_type = fields.Selection(
        [
            ("n11", "N11"),
            ("trendyol", "Trendyol"),
            ("hepsiburada", "Hepsiburada"),
            ("cicek_sepeti", "Çiçek Sepeti"),
            ("amazon", "Amazon"),
            ("getir", "Getir"),
            ("yemeksepeti", "Yemeksepeti"),
            ("trendyol_go", "Trendyol Go"),
            ("other", "Diğer"),
        ],
        string="Kanal Tipi",
        required=True,
        track_visibility="onchange",
    )

    # API Credentials
    api_key = fields.Char("API Key", required=True)
    api_secret = fields.Char("API Secret", required=False)
    merchant_id = fields.Char("Satıcı ID", required=False)
    shop_id = fields.Char("Mağaza ID", required=False)

    # Configuration
    active = fields.Boolean("Aktif", default=True, track_visibility="onchange")
    sync_interval = fields.Integer(
        "Senkronizasyon Aralığı (dakika)",
        default=30,
        help="Pazaryerden veri çekme aralığı",
    )

    # Features
    supports_inventory = fields.Boolean("Stok Senkronizasyonu", default=True)
    supports_orders = fields.Boolean("Sipariş Senkronizasyonu", default=True)
    supports_pricing = fields.Boolean("Fiyat Senkronizasyonu", default=True)
    supports_returns = fields.Boolean("İade Yönetimi", default=False)

    # Sync Configuration
    auto_confirm_orders = fields.Boolean("Siparişleri Otomatik Onayla", default=False)
    auto_create_picking = fields.Boolean("İrsaliyeleri Otomatik Oluştur", default=False)
    auto_create_invoice = fields.Boolean("Faturaları Otomatik Oluştur", default=False)

    # Categories Mapping
    category_mapping = fields.Text(
        "Kategori Eşleştirmesi",
        help="JSON formatında pazaryeri kategorileri ile Odoo kategorileri eşleşmesi",
    )

    # Last Sync
    last_sync = fields.Datetime("Son Senkronizasyon", readonly=True)
    last_sync_status = fields.Selection(
        [
            ("pending", "Beklemede"),
            ("syncing", "Senkronize Ediliyor"),
            ("success", "Başarılı"),
            ("error", "Hata"),
        ],
        string="Son Senkronizasyon Durumu",
        default="pending",
    )
    last_error = fields.Text("Son Hata Mesajı", readonly=True)

    # Statistics
    total_products = fields.Integer(
        "Toplam Ürün", compute="_compute_statistics", readonly=True
    )
    total_orders = fields.Integer(
        "Toplam Sipariş", compute="_compute_statistics", readonly=True
    )
    pending_orders = fields.Integer(
        "Beklemede Sipariş", compute="_compute_statistics", readonly=True
    )

    # Relations
    company_id = fields.Many2one(
        "res.company", "Şirket", required=True, default=lambda self: self.env.company
    )
    warehouse_id = fields.Many2one("stock.warehouse", "Depo")
    product_ids = fields.One2many("marketplace.product", "channel_id", "Ürünler")
    order_ids = fields.One2many("marketplace.order", "channel_id", "Siparişler")
    sync_log_ids = fields.One2many(
        "marketplace.sync.log", "channel_id", "Senkronizasyon Logları"
    )

    _sql_constraints = [
        (
            "name_unique_per_company",
            "UNIQUE(name, company_id)",
            "Kanal adı şirket içinde benzersiz olmalıdır!",
        )
    ]

    @api.constrains("api_key", "api_secret")
    def _check_credentials(self):
        """API credential'larını doğrula"""
        for record in self:
            if not record.api_key:
                raise ValidationError("API Key gereklidir!")

    @api.depends("product_ids", "order_ids")
    def _compute_statistics(self):
        """İstatistikleri hesapla"""
        for record in self:
            record.total_products = len(record.product_ids)
            record.total_orders = len(record.order_ids)
            record.pending_orders = len(
                record.order_ids.filtered(lambda x: x.status == "pending")
            )

    def action_sync_now(self):
        """Hemen senkronizasyon yap"""
        for record in self:
            try:
                record.last_sync_status = "syncing"
                connector = record._get_connector()

                if record.supports_orders:
                    connector.sync_orders()
                if record.supports_inventory:
                    connector.sync_inventory()
                if record.supports_pricing:
                    connector.sync_prices()

                record.last_sync = fields.Datetime.now()
                record.last_sync_status = "success"
                record.last_error = False

                _logger.info(f"Kanal {record.name} başarıyla senkronize edildi")
            except Exception as e:
                record.last_sync_status = "error"
                record.last_error = str(e)
                _logger.error(f"Kanal {record.name} senkronizasyon hatası: {str(e)}")
                raise UserError(f"Senkronizasyon hatası: {str(e)}")

    def action_test_connection(self):
        """API bağlantısını test et"""
        for record in self:
            try:
                connector = record._get_connector()
                result = connector.test_connection()

                if result:
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": "Başarılı",
                            "message": f"{record.name} bağlantısı başarılı!",
                            "sticky": False,
                        },
                    }
            except Exception as e:
                raise UserError(f"Bağlantı hatası: {str(e)}")

    def _get_connector(self):
        """Uygun connector sınıfını döndür"""
        self.ensure_one()

        connector_mapping = {
            "trendyol": "joker_marketplace_trendyol.connectors.base_connector.TrendyolConnector",
            "hepsiburada": "joker_marketplace_hepsiburada.connectors.base_connector.HepsiburadaConnector",
            "n11": "joker_marketplace_n11.connectors.base_connector.N11Connector",
            "cicek_sepeti": "joker_marketplace_cicek_sepeti.connectors.base_connector.CicekSepetiConnector",
            "getir": "joker_qcommerce_getir.connectors.base_connector.GetirConnector",
            "yemeksepeti": "joker_qcommerce_yemeksepeti.connectors.base_connector.YemeksepetiConnector",
        }

        connector_path = connector_mapping.get(self.channel_type)
        if not connector_path:
            raise UserError(f"{self.channel_type} için connector bulunamadı!")

        # Import connector dynamically
        module_path, class_name = connector_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        connector_class = getattr(module, class_name)

        return connector_class(self)

    def get_category_mapping(self):
        """Kategori eşleştirmesini döndür"""
        if not self.category_mapping:
            return {}
        try:
            return json.loads(self.category_mapping)
        except:
            return {}

    def set_category_mapping(self, mapping_dict):
        """Kategori eşleştirmesini kaydet"""
        self.category_mapping = json.dumps(mapping_dict)
