# -*- coding: utf-8 -*-

from odoo import api, fields, models


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

    # Çoklu şirket izolasyonu için backend şirketi
    company_id = fields.Many2one(
        related="backend_id.company_id",
        store=True,
        index=True,
        string="Şirket",
        readonly=True,
    )
    _check_company_auto = True


class BizimHesapPartnerBinding(models.Model):
    """
    BizimHesap - Odoo Partner Eşleştirmesi
    """

    _name = "bizimhesap.partner.binding"
    _description = "BizimHesap Partner Binding"
    _inherit = "bizimhesap.binding"
    _rec_name = "odoo_id"
    _sql_constraints = [
        (
            "uniq_backend_external_id",
            "unique(backend_id, external_id)",
            "Her backend için external_id benzersiz olmalı!",
        )
    ]

    odoo_id = fields.Many2one(
        "res.partner",
        string="Odoo Partner",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # BizimHesap'tan gelen ek bilgiler
    external_balance = fields.Float(string="BizimHesap Bakiye")
    contact_type = fields.Selection(
        [
            ("1", "Müşteri"),
            ("2", "Tedarikçi"),
            ("3", "Her İkisi"),
        ],
        string="Cari Tipi",
    )
    external_data = fields.Text(string="BizimHesap Verileri", readonly=True)


class BizimHesapProductBinding(models.Model):
    """
    BizimHesap - Odoo Product Eşleştirmesi
    """

    _name = "bizimhesap.product.binding"
    _description = "BizimHesap Product Binding"
    _inherit = "bizimhesap.binding"
    _rec_name = "odoo_id"
    _sql_constraints = [
        (
            "uniq_backend_external_id",
            "unique(backend_id, external_id)",
            "Her backend için external_id benzersiz olmalı!",
        )
    ]

    odoo_id = fields.Many2one(
        "product.product",
        string="Odoo Ürün",
        required=True,
        ondelete="cascade",
        index=True,
    )

    external_stock = fields.Float(string="BizimHesap Stok")
    external_data = fields.Text(string="BizimHesap Verileri", readonly=True)


class BizimHesapInvoiceBinding(models.Model):
    """
    BizimHesap - Odoo Invoice Eşleştirmesi
    """

    _name = "bizimhesap.invoice.binding"
    _description = "BizimHesap Invoice Binding"
    _inherit = "bizimhesap.binding"
    _rec_name = "odoo_id"
    _sql_constraints = [
        (
            "uniq_backend_external_id",
            "unique(backend_id, external_id)",
            "Her backend için external_id benzersiz olmalı!",
        )
    ]

    odoo_id = fields.Many2one(
        "account.move",
        string="Odoo Fatura",
        required=True,
        ondelete="cascade",
        index=True,
    )

    external_number = fields.Char(string="BizimHesap Fatura No")
    invoice_type = fields.Selection(
        [
            ("1", "Satış Faturası"),
            ("2", "Alış Faturası"),
        ],
        string="Fatura Tipi",
    )

    external_data = fields.Text(string="BizimHesap Verileri", readonly=True)
