# -*- coding: utf-8 -*-
"""ทะเบียนทรัพย์สิน (ฟอร์ม) — Odoo 19 port of the legacy ``asset_card_form``.

Legacy source: ``dtr_fixed_assets_report/report/asset_card_form.py``
(model ``asset.card.form``).  The report prints the full registration card of
one (or many) fixed assets selected on the asset list.

Odoo 19 adaptations applied to ``jrxml/asset_card_form.jrxml``:

* ``account_asset_asset`` -> ``account_asset``.
* ``account_asset_category`` -> ``account_asset_profile`` (through
  ``asset.profile_id``).
* ``dtr_asset_class`` / ``dtr_asset_brand`` / ``dtr_asset_brand_series`` /
  ``dtr_asset_insurance`` and the ``company_address_header_report`` columns no
  longer exist, so they print as literals.
* ``account_account.code`` -> ``code_store ->> company_id::text``.
* ``received_date`` -> ``date_start``; ``total`` -> ``purchase_value``;
  ``asset_value`` -> ``depreciation_base``; ``accumulated_depreciation_bf`` ->
  ``value_depreciated``.
* ``account_asset_depreciation_line.depreciation_date`` ->
  ``account_asset_line.line_date``.

The wizard deliberately avoids any dependency on ``account_asset_management``:
the asset scope comes from the caller context (``active_ids``) or from the
plain ``p_asset_codes`` Char filter, never from a Many2one to ``account.asset``.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class AssetCardForm(models.TransientModel):
    _name = "asset.card.form"
    _description = "Asset Card Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Asset Card Form")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Language",
        default="thai",
        required=True,
    )
    date_format = fields.Selection(
        [(value, value) for value in DATE_FORMATS],
        string="Date Format",
        default="dd-MM-yyyy",
        required=True,
    )
    p_asset_codes = fields.Char(
        string="Asset Reference",
        help="รหัสทรัพย์สิน (คั่นหลายรายการด้วยเครื่องหมายจุลภาค) "
        "ใช้เมื่อเปิดรายงานจากเมนูโดยไม่มีทรัพย์สินที่เลือกไว้",
    )

    def get_locale(self):
        """Faithful to the legacy ``asset_card_form.get_locale()``."""
        return "en_EN"

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self.env.context.get("active_ids") or []
        if ids:
            where = "where a.id in (%s)" % ", ".join(str(i) for i in ids)
        elif self.p_asset_codes:
            codes = [code.strip() for code in self.p_asset_codes.split(",") if code.strip()]
            where = "where a.code in (%s)" % ", ".join(
                "'%s'" % code.replace("'", "''") for code in codes
            )
        else:
            where = "where 1 = 1"
        self.name = "Asset Card Form"
        return {
            "p_Print_By": self._legacy_print_by(),
            "p_Where": where,
            "p_DateFormat": str(self.date_format),
            "p_language": self.p_language,
            "p_Path": self._legacy_filestore_path(),
        }
