"""
Q-Commerce Senkronizasyon Logları

API çağrılarını ve senkronizasyon işlemlerini loglar.
"""

from datetime import datetime
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class QCommerceSyncLog(models.Model):
    """Q-Commerce Senkronizasyon Logu"""

    _name = "qcommerce.sync.log"
    _description = "Q-Commerce Sync Log"
    _order = "create_date desc"

    # ==================== Temel Alanlar ====================

    name = fields.Char("Log", required=True)
    operation_type = fields.Selection(
        [
            ("sync_orders", "Siparişleri Senkronize Et"),
            ("sync_couriers", "Kuryeleri Senkronize Et"),
            ("request_courier", "Kurye Talep Et"),
            ("update_status", "Durumu Güncelle"),
            ("test_connection", "Bağlantı Testi"),
        ],
        "İşlem Tipi",
        required=True,
    )

    status = fields.Selection(
        [
            ("pending", "Beklemede"),
            ("success", "Başarılı"),
            ("error", "Hata"),
        ],
        "Durum",
        default="pending",
    )

    # ==================== Detaylar ====================

    channel_id = fields.Many2one("qcommerce.channel", "Kanal", required=True)

    records_processed = fields.Integer("İşlenen Kayıt")
    records_created = fields.Integer("Oluşturulan Kayıt")
    records_updated = fields.Integer("Güncellenen Kayıt")
    records_failed = fields.Integer("Başarısız Kayıt")

    duration_seconds = fields.Float("Süre (Saniye)")

    error_message = fields.Text("Hata Mesajı")
    error_details = fields.Text("Hata Detayları")

    # ==================== Tarih ====================

    start_date = fields.Datetime("Başlama Tarihi", default=fields.Datetime.now)
    end_date = fields.Datetime("Bitiş Tarihi")

    @api.model
    def create_sync_log(self, channel, operation_type):
        """Yeni sync logu oluştur"""
        return self.create(
            {
                "name": f"{channel.name} - {operation_type}",
                "channel_id": channel.id,
                "operation_type": operation_type,
                "start_date": datetime.now(),
            }
        )

    def log_success(
        self,
        records_processed=0,
        records_created=0,
        records_updated=0,
        records_failed=0,
    ):
        """Başarılı işlemi logla"""
        from datetime import datetime

        end_time = datetime.now()
        duration = (end_time - self.start_date).total_seconds()

        self.write(
            {
                "status": "success",
                "records_processed": records_processed,
                "records_created": records_created,
                "records_updated": records_updated,
                "records_failed": records_failed,
                "duration_seconds": duration,
                "end_date": end_time,
            }
        )

    def log_error(self, error_message, error_details=""):
        """Hata işlemi logla"""
        from datetime import datetime

        end_time = datetime.now()
        duration = (end_time - self.start_date).total_seconds()

        self.write(
            {
                "status": "error",
                "error_message": error_message,
                "error_details": error_details,
                "duration_seconds": duration,
                "end_date": end_time,
            }
        )
