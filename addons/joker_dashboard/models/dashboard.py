from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class DashboardMetrics(models.TransientModel):
    """Pazaryeri ve Q-Commerce için birleştirilmiş metrik dashboard modeli"""

    _name = "dashboard.metrics"
    _description = "Dashboard Metrics"

    # ==================== PAZARYERI METRİKLERİ ====================
    pazaryeri_total_orders = fields.Integer(
        string="Pazaryeri: Toplam Sipariş",
        compute="_compute_pazaryeri_metrics",
        help="Trendyol, Hepsiburada, N11, Çiçek Sepeti toplam sipariş sayısı",
    )
    pazaryeri_pending_orders = fields.Integer(
        string="Pazaryeri: Beklemede",
        compute="_compute_pazaryeri_metrics",
    )
    pazaryeri_confirmed_orders = fields.Integer(
        string="Pazaryeri: Onaylanan",
        compute="_compute_pazaryeri_metrics",
    )
    pazaryeri_shipped_orders = fields.Integer(
        string="Pazaryeri: Gönderilen",
        compute="_compute_pazaryeri_metrics",
    )
    pazaryeri_success_rate = fields.Float(
        string="Pazaryeri: Başarı Oranı (%)",
        compute="_compute_pazaryeri_metrics",
        help="(Onaylanan + Gönderilen) / Toplam Sipariş %",
    )
    pazaryeri_total_amount = fields.Float(
        string="Pazaryeri: Toplam Tutar (₺)",
        compute="_compute_pazaryeri_metrics",
    )
    pazaryeri_top_platform = fields.Char(
        string="Pazaryeri: En İyi Platform",
        compute="_compute_pazaryeri_metrics",
        help="En fazla sipariş alan pazaryeri",
    )

    # ==================== Q-COMMERCE METRİKLERİ ====================
    qcommerce_total_orders = fields.Integer(
        string="Q-Commerce: Toplam Sipariş",
        compute="_compute_qcommerce_metrics",
        help="Getir, Yemeksepeti, Vigo toplam sipariş sayısı",
    )
    qcommerce_pending_orders = fields.Integer(
        string="Q-Commerce: Beklemede",
        compute="_compute_qcommerce_metrics",
    )
    qcommerce_preparing_orders = fields.Integer(
        string="Q-Commerce: Hazırlanıyor",
        compute="_compute_qcommerce_metrics",
    )
    qcommerce_on_way_orders = fields.Integer(
        string="Q-Commerce: Yolda",
        compute="_compute_qcommerce_metrics",
    )
    qcommerce_delivered_orders = fields.Integer(
        string="Q-Commerce: Teslim Edilen",
        compute="_compute_qcommerce_metrics",
    )
    qcommerce_success_rate = fields.Float(
        string="Q-Commerce: Başarı Oranı (%)",
        compute="_compute_qcommerce_metrics",
        help="Teslim Edilen / Toplam Sipariş %",
    )
    qcommerce_avg_delivery_time = fields.Float(
        string="Q-Commerce: Ort. Teslimat Süresi (dk)",
        compute="_compute_qcommerce_metrics",
    )
    qcommerce_total_amount = fields.Float(
        string="Q-Commerce: Toplam Tutar (₺)",
        compute="_compute_qcommerce_metrics",
    )
    qcommerce_top_platform = fields.Char(
        string="Q-Commerce: En İyi Platform",
        compute="_compute_qcommerce_metrics",
    )

    # ==================== GENEL METRİKLER ====================
    total_orders = fields.Integer(
        string="Toplam Sipariş (Tüm Platform)",
        compute="_compute_overall_metrics",
    )
    total_revenue = fields.Float(
        string="Toplam Gelir (₺)",
        compute="_compute_overall_metrics",
    )
    overall_success_rate = fields.Float(
        string="Genel Başarı Oranı (%)",
        compute="_compute_overall_metrics",
    )
    last_sync_time = fields.Datetime(
        string="Son Senkronizasyon",
        compute="_compute_last_sync",
    )
    pending_syncs = fields.Integer(
        string="Beklenen Senkronizasyonlar",
        compute="_compute_pending_syncs",
    )

    # ==================== CHANNEL İSTATİSTİKLERİ ====================
    channel_stats = fields.Html(
        string="Channel İstatistikleri",
        compute="_compute_channel_stats",
        help="Pazaryeri kanalları için detaylı istatistikler (HTML table)",
    )
    qcommerce_channel_stats = fields.Html(
        string="Q-Commerce Channel İstatistikleri",
        compute="_compute_qcommerce_channel_stats",
    )

    @api.depends()
    def _compute_pazaryeri_metrics(self):
        """Pazaryeri metriklerini hesapla"""
        for rec in self:
            # marketplace.order alanından hesapla
            orders = self.env["marketplace.order"].sudo().search([])

            rec.pazaryeri_total_orders = len(orders)
            rec.pazaryeri_pending_orders = len(
                orders.filtered(lambda o: o.status == "pending")
            )
            rec.pazaryeri_confirmed_orders = len(
                orders.filtered(lambda o: o.status == "confirmed")
            )
            rec.pazaryeri_shipped_orders = len(
                orders.filtered(lambda o: o.status in ["shipped", "delivered"])
            )

            if rec.pazaryeri_total_orders > 0:
                rec.pazaryeri_success_rate = (
                    (rec.pazaryeri_confirmed_orders + rec.pazaryeri_shipped_orders)
                    / rec.pazaryeri_total_orders
                    * 100
                )
                rec.pazaryeri_total_amount = sum(orders.mapped("total_amount"))
            else:
                rec.pazaryeri_success_rate = 0.0
                rec.pazaryeri_total_amount = 0.0

            # En iyi platform
            channel_orders = {}
            for order in orders:
                channel = order.channel_id.name
                channel_orders[channel] = channel_orders.get(channel, 0) + 1

            if channel_orders:
                rec.pazaryeri_top_platform = max(channel_orders, key=channel_orders.get)
            else:
                rec.pazaryeri_top_platform = "N/A"

    @api.depends()
    def _compute_qcommerce_metrics(self):
        """Q-Commerce metriklerini hesapla"""
        for rec in self:
            # qcommerce.order alanından hesapla
            orders = self.env["qcommerce.order"].sudo().search([])

            rec.qcommerce_total_orders = len(orders)
            rec.qcommerce_pending_orders = len(
                orders.filtered(lambda o: o.status == "pending")
            )
            rec.qcommerce_preparing_orders = len(
                orders.filtered(lambda o: o.status == "preparing")
            )
            rec.qcommerce_on_way_orders = len(
                orders.filtered(lambda o: o.status == "on_way")
            )
            rec.qcommerce_delivered_orders = len(
                orders.filtered(lambda o: o.status == "delivered")
            )

            if rec.qcommerce_total_orders > 0:
                rec.qcommerce_success_rate = (
                    rec.qcommerce_delivered_orders / rec.qcommerce_total_orders * 100
                )
                rec.qcommerce_total_amount = sum(orders.mapped("total_amount"))

                # Ortalama teslimat süresi (delivered siparişlerden)
                delivered = orders.filtered(lambda o: o.status == "delivered")
                if delivered:
                    total_minutes = 0
                    for order in delivered:
                        if order.delivery_id and order.delivery_id.actual_delivery_time:
                            # delivery.actual_delivery_time ve order.create_date farkı
                            delta = (
                                order.delivery_id.actual_delivery_time
                                - order.create_date
                            )
                            total_minutes += delta.total_seconds() / 60
                    rec.qcommerce_avg_delivery_time = total_minutes / len(delivered)
                else:
                    rec.qcommerce_avg_delivery_time = 0.0
            else:
                rec.qcommerce_success_rate = 0.0
                rec.qcommerce_total_amount = 0.0
                rec.qcommerce_avg_delivery_time = 0.0

            # En iyi platform
            channel_orders = {}
            for order in orders:
                channel = order.channel_id.name
                channel_orders[channel] = channel_orders.get(channel, 0) + 1

            if channel_orders:
                rec.qcommerce_top_platform = max(channel_orders, key=channel_orders.get)
            else:
                rec.qcommerce_top_platform = "N/A"

    @api.depends()
    def _compute_overall_metrics(self):
        """Genel metrikler"""
        for rec in self:
            rec.total_orders = rec.pazaryeri_total_orders + rec.qcommerce_total_orders
            rec.total_revenue = rec.pazaryeri_total_amount + rec.qcommerce_total_amount

            if rec.total_orders > 0:
                total_success = (
                    rec.pazaryeri_confirmed_orders
                    + rec.pazaryeri_shipped_orders
                    + rec.qcommerce_delivered_orders
                )
                rec.overall_success_rate = (total_success / rec.total_orders) * 100
            else:
                rec.overall_success_rate = 0.0

    @api.depends()
    def _compute_last_sync(self):
        """Son senkronizasyon zamanı"""
        for rec in self:
            # En son pazaryeri sync
            paz_sync = (
                self.env["marketplace.sync.log"]
                .sudo()
                .search([], order="create_date desc", limit=1)
            )
            # En son Q-Commerce sync
            qcom_sync = (
                self.env["qcommerce.sync.log"]
                .sudo()
                .search([], order="create_date desc", limit=1)
            )

            syncs = []
            if paz_sync:
                syncs.append(paz_sync.create_date)
            if qcom_sync:
                syncs.append(qcom_sync.create_date)

            rec.last_sync_time = max(syncs) if syncs else None

    @api.depends()
    def _compute_pending_syncs(self):
        """Beklenen senkronizasyonlar (error status olanlar)"""
        for rec in self:
            paz_pending = len(
                self.env["marketplace.sync.log"]
                .sudo()
                .search([("status", "=", "error")])
            )
            qcom_pending = len(
                self.env["qcommerce.sync.log"].sudo().search([("status", "=", "error")])
            )
            rec.pending_syncs = paz_pending + qcom_pending

    @api.depends()
    def _compute_channel_stats(self):
        """Pazaryeri channel istatistikleri HTML tablosu"""
        for rec in self:
            channels = self.env["marketplace.channel"].sudo().search([])

            rows = []
            rows.append('<table class="table table-sm">')
            rows.append("<thead><tr>")
            rows.append(
                "<th>Channel</th><th>Toplam</th><th>Beklemede</th><th>Başarılı</th><th>Başarı %</th>"
            )
            rows.append("</tr></thead><tbody>")

            for channel in channels:
                orders = (
                    self.env["marketplace.order"]
                    .sudo()
                    .search([("channel_id", "=", channel.id)])
                )
                total = len(orders)
                pending = len(orders.filtered(lambda o: o.status == "pending"))
                success = len(
                    orders.filtered(
                        lambda o: o.status in ["confirmed", "shipped", "delivered"]
                    )
                )
                success_rate = (success / total * 100) if total > 0 else 0

                rows.append("<tr>")
                rows.append(f"<td><strong>{channel.name}</strong></td>")
                rows.append(f"<td>{total}</td>")
                rows.append(f"<td>{pending}</td>")
                rows.append(f"<td>{success}</td>")
                rows.append(f"<td>{success_rate:.1f}%</td>")
                rows.append("</tr>")

            rows.append("</tbody></table>")
            rec.channel_stats = (
                "\n".join(rows) if channels else "<p>Kanal bulunamadı</p>"
            )

    @api.depends()
    def _compute_qcommerce_channel_stats(self):
        """Q-Commerce channel istatistikleri HTML tablosu"""
        for rec in self:
            channels = self.env["qcommerce.channel"].sudo().search([])

            rows = []
            rows.append('<table class="table table-sm">')
            rows.append("<thead><tr>")
            rows.append(
                "<th>Platform</th><th>Toplam</th><th>Beklemede</th><th>Hazırlanıyor</th><th>Teslim Edilen</th><th>Başarı %</th>"
            )
            rows.append("</tr></thead><tbody>")

            for channel in channels:
                orders = (
                    self.env["qcommerce.order"]
                    .sudo()
                    .search([("channel_id", "=", channel.id)])
                )
                total = len(orders)
                pending = len(orders.filtered(lambda o: o.status == "pending"))
                preparing = len(orders.filtered(lambda o: o.status == "preparing"))
                delivered = len(orders.filtered(lambda o: o.status == "delivered"))
                success_rate = (delivered / total * 100) if total > 0 else 0

                rows.append("<tr>")
                rows.append(f"<td><strong>{channel.name}</strong></td>")
                rows.append(f"<td>{total}</td>")
                rows.append(f"<td>{pending}</td>")
                rows.append(f"<td>{preparing}</td>")
                rows.append(f"<td>{delivered}</td>")
                rows.append(f"<td>{success_rate:.1f}%</td>")
                rows.append("</tr>")

            rows.append("</tbody></table>")
            rec.channel_stats = (
                "\n".join(rows) if channels else "<p>Kanal bulunamadı</p>"
            )


class DashboardSync(models.Model):
    """Senkronizasyon durumu tracker'ı"""

    _name = "dashboard.sync"
    _description = "Dashboard Sync Status"
    _rec_name = "channel_type"

    channel_id = fields.Many2one("marketplace.channel", string="Pazaryeri Kanalı")
    qcommerce_channel_id = fields.Many2one(
        "qcommerce.channel", string="Q-Commerce Kanalı"
    )
    channel_type = fields.Selection(
        [
            ("pazaryeri", "Pazaryeri"),
            ("qcommerce", "Q-Commerce"),
        ],
        string="Kanal Tipi",
        required=True,
    )
    last_sync = fields.Datetime(
        string="Son Senkronizasyon",
        readonly=True,
    )
    next_sync = fields.Datetime(
        string="Sonraki Senkronizasyon",
        compute="_compute_next_sync",
    )
    status = fields.Selection(
        [
            ("idle", "Boş"),
            ("syncing", "Senkronizasyon Yapıyor"),
            ("error", "Hata"),
            ("success", "Başarılı"),
        ],
        string="Durum",
        default="idle",
    )
    error_message = fields.Text(
        string="Hata Mesajı",
        readonly=True,
    )
    records_synced = fields.Integer(
        string="Senkronize Edilen Kayıt",
        readonly=True,
    )

    @api.depends("last_sync", "channel_id", "qcommerce_channel_id")
    def _compute_next_sync(self):
        """Sonraki senkronizasyon zamanını hesapla"""
        for rec in self:
            if rec.last_sync:
                if rec.channel_type == "pazaryeri":
                    # Pazaryeri: Her 1 saat
                    rec.next_sync = rec.last_sync + timedelta(hours=1)
                else:
                    # Q-Commerce: Her 15 dakika
                    rec.next_sync = rec.last_sync + timedelta(minutes=15)
            else:
                # Henüz sync olmadıysa, şimdi olması gerekir
                rec.next_sync = fields.Datetime.now()

    def action_sync_now(self):
        """Şimdi senkronizasyon başlat"""
        for rec in self:
            try:
                rec.status = "syncing"

                if rec.channel_type == "pazaryeri" and rec.channel_id:
                    # Pazaryeri sync
                    connector_class = rec.channel_id._get_connector_class()
                    connector = connector_class(rec.channel_id)
                    result = connector.sync_orders()
                    rec.records_synced = result.get("orders_created", 0) + result.get(
                        "orders_updated", 0
                    )

                elif rec.channel_type == "qcommerce" and rec.qcommerce_channel_id:
                    # Q-Commerce sync
                    connector_class = rec.qcommerce_channel_id._get_connector_class()
                    connector = connector_class(rec.qcommerce_channel_id)
                    result = connector.sync_orders(datetime.now() - timedelta(hours=1))
                    rec.records_synced = result.get("orders_created", 0) + result.get(
                        "orders_updated", 0
                    )

                rec.last_sync = fields.Datetime.now()
                rec.status = "success"
                rec.error_message = ""

            except Exception as e:
                rec.status = "error"
                rec.error_message = str(e)
