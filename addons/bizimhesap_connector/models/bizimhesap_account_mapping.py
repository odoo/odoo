# -*- coding: utf-8 -*-
"""
BizimHesap - Odoo Muhasebe Hesabı Eşleştirmesi
Ön muhasebe (BizimHesap) kodlarını Odoo hesap planına bağla
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BizimHesapAccountMapping(models.Model):
    """
    BizimHesap muhasebe codes → Odoo account.account mapping

    BizimHesap'taki 100-199 (Satış), 200-299 (Gider) vb kodları
    Odoo'daki genel muhasebe hesaplarına otomatik eşle.
    """

    _name = "bizimhesap.account.mapping"
    _description = "BizimHesap Account Mapping"
    _rec_name = "bizimhesap_code"

    backend_id = fields.Many2one(
        "bizimhesap.backend",
        string="BizimHesap Bağlantısı",
        required=True,
        ondelete="cascade",
        help="Bu eşleştirmenin hangi BizimHesap bağlantısı için olduğu",
    )

    # BizimHesap tarafı
    bizimhesap_code = fields.Char(
        string="BizimHesap Hesap Kodu",
        required=True,
        size=20,
        help="BizimHesap'ta kullanılan muhasebe hesap kodu (ör: 600, 701, 800)",
    )

    bizimhesap_account_name = fields.Char(
        string="BizimHesap Hesap Adı",
        help="BizimHesap'ta tanımlı hesap adı (bilgi amaçlı)",
    )

    # Odoo tarafı
    odoo_account_id = fields.Many2one(
        "account.account",
        string="Odoo Hesabı",
        required=True,
        ondelete="cascade",
        help="Bu BizimHesap koduna karşılık gelen Odoo genel muhasebe hesabı",
    )

    # Meta bilgiler
    account_type = fields.Selection(
        [
            ("revenue", "Gelir"),
            ("expense", "Gider"),
            ("asset", "Varlık"),
            ("liability", "Yükümlülük"),
            ("equity", "Öz Sermaye"),
        ],
        string="Hesap Tipi",
        help="Ön muhasebede bu hesabın tipi",
    )

    is_active = fields.Boolean(
        string="Aktif",
        default=True,
        help="Bu eşleştirme senkronizasyonda kullanılsın mı?",
    )

    notes = fields.Text(
        string="Notlar",
        help="Bu eşleştirme hakkında açıklamalar",
    )

    # Constraint: Aynı backend'de aynı BizimHesap kodu iki kez tanımlanmasın
    _sql_constraints = [
        (
            "uniq_backend_bizimhesap_code",
            "unique(backend_id, bizimhesap_code)",
            "Aynı backend için BizimHesap kodu benzersiz olmalı!",
        )
    ]

    def get_odoo_account(self, bizimhesap_code):
        """
        BizimHesap kodundan Odoo hesabını getir

        :param bizimhesap_code: BizimHesap kodu
        :return: account.account kaydı veya False
        """
        mapping = self.search(
            [
                ("backend_id", "=", self.backend_id.id),
                ("bizimhesap_code", "=", str(bizimhesap_code)),
                ("is_active", "=", True),
            ],
            limit=1,
        )

        return mapping.odoo_account_id if mapping else False


class BizimHesapInvoiceAccountLine(models.Model):
    """
    Fatura kalemi → Muhasebe hesabı otomatik bağlanması

    Fatura senkronize edilirken, her kaleme otomatik olarak
    doğru muhasebe hesabı atanır.
    """

    _name = "account.move.line"
    _inherit = "account.move.line"

    bizimhesap_account_code = fields.Char(
        string="BizimHesap Hesap Kodu",
        help="BizimHesap'tan gelen orijinal hesap kodu",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Satış sırasında BizimHesap eşleştirmesi yap"""
        for vals in vals_list:
            # Eğer BizimHesap kodu varsa ve hesap atanmamışsa
            if vals.get("bizimhesap_account_code") and not vals.get("account_id"):
                bizimhesap_code = vals["bizimhesap_account_code"]

                # Move'dan backend'i bul
                move_id = vals.get("move_id")
                if move_id:
                    move = self.env["account.move"].browse(move_id)
                    # Invoice binding'den backend'i bulma
                    binding = self.env["bizimhesap.invoice.binding"].search(
                        [("odoo_id", "=", move_id)], limit=1
                    )

                    if binding:
                        mapping = self.env["bizimhesap.account.mapping"].search(
                            [
                                ("backend_id", "=", binding.backend_id.id),
                                ("bizimhesap_code", "=", bizimhesap_code),
                                ("is_active", "=", True),
                            ],
                            limit=1,
                        )

                        if mapping:
                            vals["account_id"] = mapping.odoo_account_id.id

        return super().create(vals_list)
