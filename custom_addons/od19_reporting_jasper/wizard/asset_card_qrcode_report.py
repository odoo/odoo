# -*- coding: utf-8 -*-
"""ทะเบียนทรัพย์สิน (QR) — Odoo 19 port of ``asset_card_qrcode_report``.

Legacy source: ``dtr_fixed_assets_report/report/asset_card_qrcode_report.py``
(model ``asset.card.qrcode.report``).  Prints one QR-code label per selected
fixed asset, repeated ``p_Print`` times.

Odoo 19 adaptations applied to ``jrxml/asset_card_qrcode_report.jrxml``:
``account_asset_asset`` -> ``account_asset``.  ``p_Company_Name`` falls back to
``res_company.name`` because ``res_company.name_en`` was removed.

The asset scope comes from the caller context (``active_ids``) or from the
plain ``p_asset_codes`` Char filter; no Many2one to ``account.asset`` is
declared, so the module stays independent from ``account_asset_management``.
"""
from odoo import fields, models


class AssetCardQrcodeReport(models.TransientModel):
    _name = "asset.card.qrcode.report"
    _description = "Asset Card QRcode Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Fixed Asset QRcode Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_Print = fields.Integer(string="Number to print", required=True, default=1)
    p_asset_codes = fields.Char(
        string="Asset Reference",
        help="รหัสทรัพย์สิน (คั่นหลายรายการด้วยเครื่องหมายจุลภาค) "
        "ใช้เมื่อเปิดรายงานจากเมนูโดยไม่มีทรัพย์สินที่เลือกไว้",
    )

    def get_locale(self):
        """Faithful to the legacy ``asset_card_qrcode_report.get_locale()``."""
        return "en_EN"

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self.env.context.get("active_ids") or []
        if ids:
            where = " where pt.id in (%s) " % ", ".join(str(i) for i in ids)
        elif self.p_asset_codes:
            codes = [code.strip() for code in self.p_asset_codes.split(",") if code.strip()]
            where = " where pt.code in (%s) " % ", ".join(
                "'%s'" % code.replace("'", "''") for code in codes
            )
        else:
            where = ""
        self.name = "Fixed Asset QRcode Report"
        return {
            "p_Where": where,
            "p_Print": str(self.p_Print),
            "p_Company_Name": self.env.company.name or "",
        }
