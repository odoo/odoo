# -*- coding: utf-8 -*-
"""ค่าเสื่อมราคา (รายบรรทัด) — Odoo 19 port of ``asset_depreciation_line_report``.

Legacy source: ``dtr_fixed_assets_report/report/asset_depreciation_line_report.jrxml``.
Prints the year-by-year depreciation schedule of a single fixed asset.

Odoo 19 adaptations applied to ``jrxml/asset_depreciation_line_report.jrxml``:

* ``account_asset_asset`` -> ``account_asset`` and
  ``account_asset_depreciation_line`` -> ``account_asset_line``.
* ``asset.value`` -> ``asset.purchase_value``;
  ``asset.initial_depreciation`` -> literal ``0``.
* ``line.depreciation_date`` -> ``line.line_date``.

The asset is identified by its database id passed as the plain
``p_account_asset_asset_id`` Char parameter (the template injects it with
``$P!{...}``), so the wizard does not need a Many2one to ``account.asset`` and
therefore does not depend on ``account_asset_management``.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class AssetDepreciationLineReport(models.TransientModel):
    _name = "asset.depreciation.line.report"
    _description = "Asset Depreciation Line Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Asset Depreciation Line Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_account_asset_asset_id = fields.Char(
        string="Asset ID",
        help="รหัสฐานข้อมูลของทรัพย์สิน (จะใช้ทรัพย์สินที่เลือกไว้ "
        "หากเปิดรายงานจากหน้าจอทรัพย์สิน)",
    )
    date_type = fields.Selection(
        [("AD", "AD"), ("BE", "BE")],
        string="Date Type",
        default="AD",
        required=True,
        help="AD = คริสตศักราช\nBE = พุทธศักราช",
    )
    date_format = fields.Selection(
        [(value, value) for value in DATE_FORMATS],
        string="Date Format",
        default="dd-MM-yyyy",
        required=True,
    )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        asset_id = self.p_account_asset_asset_id
        if not asset_id:
            ids = self.env.context.get("active_ids") or []
            asset_id = str(ids[0]) if ids else ""
        self.name = "Asset Depreciation Line Report"
        return {
            "p_account_asset_asset_id": str(asset_id or ""),
            "p_DateFormat": str(self.date_format),
            "p_locale": "th" if self.date_type == "BE" else "en",
        }
