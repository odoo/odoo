# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ResPartner(models.Model):
    """
    Partner model extension for BizimHesap
    """

    _inherit = "res.partner"

    bizimhesap_binding_ids = fields.One2many(
        "bizimhesap.partner.binding",
        "odoo_id",
        string="BizimHesap Eşleşmeleri",
    )

    bizimhesap_synced = fields.Boolean(
        compute="_compute_bizimhesap_synced",
        string="BizimHesap Senkronize",
        store=True,
    )

    # BizimHesap'tan gelen bakiye bilgileri
    bizimhesap_balance = fields.Float(
        string="BizimHesap Bakiye",
        digits=(16, 2),
        readonly=True,
        help="BizimHesap sistemindeki cari bakiye",
    )

    bizimhesap_cheque_bond = fields.Float(
        string="Çek/Senet Bakiyesi",
        digits=(16, 2),
        readonly=True,
        help="BizimHesap sistemindeki çek ve senet bakiyesi",
    )

    bizimhesap_currency = fields.Char(
        string="BizimHesap Para Birimi",
        readonly=True,
    )

    bizimhesap_last_balance_update = fields.Datetime(
        string="Son Bakiye Güncelleme",
        readonly=True,
    )

    @api.depends("bizimhesap_binding_ids")
    def _compute_bizimhesap_synced(self):
        for record in self:
            record.bizimhesap_synced = bool(record.bizimhesap_binding_ids)

    def action_sync_to_bizimhesap(self):
        """Manuel olarak BizimHesap'a gönder"""
        self.ensure_one()

        backend = self.env["bizimhesap.backend"].search(
            [
                ("state", "=", "connected"),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not backend:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Hata"),
                    "message": _("Aktif BizimHesap bağlantısı bulunamadı!"),
                    "type": "danger",
                    "sticky": False,
                },
            }

        try:
            backend.export_partner(self)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Başarılı"),
                    "message": _("Cari BizimHesap'a gönderildi!"),
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Hata"),
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_view_customer_abstract(self):
        """
        BizimHesap'tan cari hesap ekstresini görüntüle
        """
        self.ensure_one()

        # BizimHesap binding kontrolü
        if not self.bizimhesap_binding_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Uyarı"),
                    "message": _("Bu cari BizimHesap ile senkronize değil!"),
                    "type": "warning",
                    "sticky": False,
                },
            }

        binding = self.bizimhesap_binding_ids[0]
        backend = binding.backend_id

        if not backend or backend.state != "connected":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Hata"),
                    "message": _("BizimHesap bağlantısı aktif değil!"),
                    "type": "danger",
                    "sticky": False,
                },
            }

        try:
            # API'den ekstre çek
            result = backend.get_customer_abstract(binding.external_id)

            if not result or "error" in result:
                error_msg = (
                    result.get("error", "Bilinmeyen hata")
                    if result
                    else "API yanıt vermedi"
                )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Hata"),
                        "message": f"Ekstre alınamadı: {error_msg}",
                        "type": "danger",
                        "sticky": True,
                    },
                }

            # Partner üzerinde bakiye alanlarını güncelle
            partner_updates = {
                "bizimhesap_balance": result.get("balance", 0.0),
                "bizimhesap_cheque_bond": result.get("cheque_bond", 0.0),
                "bizimhesap_currency": result.get("currency", "TRY"),
                "bizimhesap_last_balance_update": fields.Datetime.now(),
            }
            self.write(partner_updates)

            # Wizard oluştur ve ekstre datalarını göster
            wizard = self.env["bizimhesap.customer.abstract.wizard"].create(
                {
                    "partner_id": self.id,
                    "backend_id": backend.id,
                    "external_id": binding.external_id,
                    "abstract_data": str(result),
                    "balance": result.get("balance", 0.0),
                    "currency": result.get("currency", "TRY"),
                }
            )

            return {
                "type": "ir.actions.act_window",
                "name": _("Cari Hesap Ekstresi - %s") % self.name,
                "res_model": "bizimhesap.customer.abstract.wizard",
                "res_id": wizard.id,
                "view_mode": "form",
                "target": "new",
            }

        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Hata"),
                    "message": f"Ekstre alınırken hata: {str(e)}",
                    "type": "danger",
                    "sticky": True,
                },
            }
