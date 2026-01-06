# -*- coding: utf-8 -*-

from odoo import fields, models


class BizimHesapBinding(models.Model):
    """BizimHesap Binding Taban Modeli"""

    _name = "bizimhesap.binding"
    _description = "BizimHesap Binding Base"
    _abstract = True

    # İlişkiler
    backend_id = fields.Many2one(
        "bizimhesap.backend",
        string="BizimHesap Bağlantısı",
        required=True,
        ondelete="cascade",
    )

    # Eşleştirme bilgileri
    external_id = fields.Char(
        string="Harici ID",
        required=True,
        index=True,
        help="BizimHesap'taki kayıt ID'si (GUID)",
    )

    external_code = fields.Char(
        string="Harici Kod",
        help="BizimHesap'taki kod/referans",
    )

    # Senkronizasyon bilgileri
    sync_date = fields.Datetime(
        string="Son Senkronizasyon",
        readonly=True,
        help="Son senkronizasyon tarihi",
    )

    sync_state = fields.Selection(
        [
            ("draft", "Taslak"),
            ("synced", "Senkronize"),
            ("to_update", "Güncelleme Bekliyor"),
            ("error", "Hata"),
        ],
        string="Senkronizasyon Durumu",
        default="draft",
        help="Eşleştirmenin senkronizasyon durumu",
    )

    def _compute_name(self):
        """Ad bilgisini otomatik oluştur"""
        for record in self:
            record.name = f"[{record.backend_id.name}] {record.external_code or record.external_id}"
