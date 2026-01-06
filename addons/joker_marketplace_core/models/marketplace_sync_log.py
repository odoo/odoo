import json

from odoo import api, fields, models


class MarketplaceSyncLog(models.Model):
    """Pazaryeri Senkronizasyon Logları"""

    _name = "marketplace.sync.log"
    _description = "Senkronizasyon Logları"
    _order = "create_date desc"

    channel_id = fields.Many2one(
        "marketplace.channel", "Pazaryeri", required=True, ondelete="cascade"
    )

    operation = fields.Selection(
        [
            ("sync_orders", "Siparişleri Senkronize Et"),
            ("sync_inventory", "Stok Senkronizasyonu"),
            ("sync_prices", "Fiyat Senkronizasyonu"),
            ("sync_products", "Ürün Senkronizasyonu"),
            ("update_order_status", "Sipariş Durumu Güncelleme"),
            ("test_connection", "Bağlantı Testi"),
        ],
        string="İşlem",
        required=True,
    )

    status = fields.Selection(
        [
            ("pending", "Beklemede"),
            ("processing", "İşlem Yapılıyor"),
            ("success", "Başarılı"),
            ("error", "Hata"),
            ("partial", "Kısmi"),
        ],
        string="Durum",
        default="pending",
    )

    start_time = fields.Datetime("Başlangıç Zamanı", default=fields.Datetime.now)
    end_time = fields.Datetime("Bitiş Zamanı")
    duration = fields.Float("Süre (saniye)", compute="_compute_duration")

    records_processed = fields.Integer("İşlenen Kayıt Sayısı", default=0)
    records_created = fields.Integer("Oluşturulan Kayıt Sayısı", default=0)
    records_updated = fields.Integer("Güncellenen Kayıt Sayısı", default=0)
    records_failed = fields.Integer("Başarısız Kayıt Sayısı", default=0)

    error_message = fields.Text("Hata Mesajı")
    error_details = fields.Text("Hata Detayları (JSON)")

    notes = fields.Text("Notlar")

    # Log details
    api_call_count = fields.Integer("API Çağrı Sayısı", default=0)
    response_time = fields.Float("Ortalama Yanıt Süresi (ms)", default=0)

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        """Senkronizasyon süresini hesapla"""
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds()
            else:
                record.duration = 0

    def get_error_details(self):
        """Hata detaylarını JSON olarak döndür"""
        if not self.error_details:
            return {}
        try:
            return json.loads(self.error_details)
        except:
            return {}

    def set_error_details(self, error_dict):
        """Hata detaylarını kaydet"""
        self.error_details = json.dumps(error_dict)

    def action_retry(self):
        """Senkronizasyonu yeniden dene"""
        self.channel_id.action_sync_now()
