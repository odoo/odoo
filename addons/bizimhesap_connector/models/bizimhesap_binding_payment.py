# -*- coding: utf-8 -*-

from odoo import api, fields, models


class BizimHesapPaymentBinding(models.Model):
    """BizimHesap Ödeme Eşleştirmesi"""

    _name = "bizimhesap.payment.binding"
    _description = "BizimHesap Payment Binding"
    _inherit = ["bizimhesap.binding"]
    _rec_name = "external_code"
    _sql_constraints = [
        (
            "uniq_backend_external_id",
            "unique(backend_id, external_id)",
            "Her backend için external_id benzersiz olmalı!",
        )
    ]

    # Odoo ilişkisi
    odoo_id = fields.Many2one(
        "account.payment",
        string="Odoo Ödeme Kaydı",
        ondelete="set null",
        help="Odoo'daki ilişkili ödeme kaydı",
        index=True,
    )

    # BizimHesap verileri
    external_code = fields.Char(string="BizimHesap Referans", index=True)

    contact_type = fields.Selection(
        [("customer", "Müşteri"), ("supplier", "Tedarikçi")],
        string="Cari Türü",
    )

    external_amount = fields.Float(
        string="BizimHesap Tutarı",
        help="BizimHesap'taki ödeme tutarı",
    )

    external_description = fields.Text(
        string="BizimHesap Açıklaması",
        help="BizimHesap'ta kayıtlı açıklama",
    )

    external_date = fields.Date(
        string="BizimHesap Ödeme Tarihi",
        help="BizimHesap'ta kayıtlı ödeme tarihi",
    )

    reconciliation_status = fields.Selection(
        [
            ("pending", "Mutabakat Bekleniyor"),
            ("reconciled", "Mutabakat Yapıldı"),
            ("failed", "Mutabakat Başarısız"),
        ],
        string="Mutabakat Durumu",
        default="pending",
        help="Ödemenin ilgili faturalarla mutabakat durumu",
    )

    reconciliation_note = fields.Text(
        string="Mutabakat Notu",
        help="Mutabakat işlemi hakkında notlar",
    )

    external_data = fields.Text(string="BizimHesap Verileri", readonly=True)
