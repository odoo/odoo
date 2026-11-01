# -*- coding: utf-8 -*-
"""ค่าเสื่อมราคา — Odoo 19 port of the legacy ``asset_depreciation_report``.

Legacy source: ``dtr_fixed_assets_report/report/asset_depreciation_report.py``
(model ``asset.depreciation.report``).  Lists the monthly depreciation lines of
every non-draft asset for a chosen month/year, grouped by cost centre and asset
category.

Odoo 19 adaptations applied to ``jrxml/asset_depreciation_report.jrxml``:

* ``account_asset_asset`` -> ``account_asset``.
* ``account_asset_category`` -> ``account_asset_profile`` (through
  ``asset.profile_id``).
* The ``account_analytic_account`` (cost centre) join was dropped: the legacy
  ``asset.analytic_account_id`` field no longer exists, so the cost-centre
  columns print as literals.
* ``account_asset_depreciation_line.depreciation_date`` ->
  ``account_asset_line.line_date``.

The legacy ``analytic_account_ids`` / ``category_ids`` Many2many fields
(``account.analytic.account`` / ``account.asset.category``) are intentionally
replaced by the plain ``p_category_codes`` Char filter so the module does not
need ``account_asset_management``.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS

MONTH_LIST = [
    ("1", "มกราคม"),
    ("2", "กุมภาพันธ์"),
    ("3", "มีนาคม"),
    ("4", "เมษายน"),
    ("5", "พฤษภาคม"),
    ("6", "มิถุนายน"),
    ("7", "กรกฎาคม"),
    ("8", "สิงหาคม"),
    ("9", "กันยายน"),
    ("10", "ตุลาคม"),
    ("11", "พฤศจิกายน"),
    ("12", "ธันวาคม"),
]

MONTH_LIST_EN = [
    ("1", "January"),
    ("2", "Febuary"),
    ("3", "March"),
    ("4", "April"),
    ("5", "May"),
    ("6", "June"),
    ("7", "July"),
    ("8", "August"),
    ("9", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]


class AssetDepreciationReport(models.TransientModel):
    _name = "asset.depreciation.report"
    _description = "Asset Depreciation Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Asset Depreciation Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Language",
        default="thai",
        required=True,
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
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    rpt_month = fields.Selection(
        MONTH_LIST,
        string="Month",
        required=True,
        default=lambda self: "%d" % fields.Date.context_today(self).month,
    )
    rpt_year = fields.Selection(
        selection="_selection_year",
        string="Year",
        required=True,
        default=lambda self: "%d" % fields.Date.context_today(self).year,
    )
    p_category_codes = fields.Char(
        string="Asset Category",
        help="ชื่อหมวดหมู่ทรัพย์สิน (คั่นหลายรายการด้วยเครื่องหมายจุลภาค)",
    )

    def _selection_year(self):
        current_year = fields.Date.context_today(self).year
        return [
            ("%s" % year, "%s" % (year + 543))
            for year in range(current_year, current_year - 5, -1)
        ]

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        english = self.p_language == "english"
        months = dict(MONTH_LIST_EN) if english else dict(MONTH_LIST)
        rpt_month = months.get(self.rpt_month)
        rpt_year = int(self.rpt_year)
        if english:
            header = "Asset Depreciation Report At {0} {1}".format(rpt_month, rpt_year)
        else:
            header = "รายงานค่าเสื่อมประจำเดือน {0} {1}".format(
                rpt_month, rpt_year + 543
            )
        where = (
            "WHERE asset.state != 'draft' and line.move_check = True "
            "and asset.company_id = {0} "
            "and EXTRACT(YEAR FROM line.line_date) = {1} "
            "and EXTRACT(MONTH FROM line.line_date) = {2}"
        ).format(self.company_id.id, rpt_year, int(self.rpt_month))
        cost_center = "All" if english else "ทั้งหมด"
        asset_category = cost_center
        if self.p_category_codes:
            names = [
                name.strip() for name in self.p_category_codes.split(",") if name.strip()
            ]
            where += " and cat.name in (%s)" % ", ".join(
                "'%s'" % name.replace("'", "''") for name in names
            )
            asset_category = ", ".join(names)
        self.name = "Asset Depreciation Report"
        return {
            "p_Print_By": self._legacy_print_by(),
            "p_Where": where,
            "p_DateFormat": str(self.date_format),
            "p_language": self.p_language,
            "p_locale": "th" if self.date_type == "BE" else "en",
            "p_HeaderName": header,
            "p_CostCenter": cost_center,
            "p_Asset_Category": asset_category,
        }
