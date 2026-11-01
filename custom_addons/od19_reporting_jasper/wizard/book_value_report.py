# -*- coding: utf-8 -*-
"""มูลค่าตามบัญชี — Odoo 19 port of the legacy ``book_value_report``.

Legacy source: ``dtr_fixed_assets_report/report/book_value_report.py``
(model ``book.value.report``).  Lists every non-draft asset with its gross
value and the depreciation accumulated up to a chosen "at date".

Odoo 19 adaptations applied to ``jrxml/book_value_report.jrxml``:

* ``account_asset_asset`` -> ``account_asset``.
* ``account_asset_category`` -> ``account_asset_profile`` (through
  ``asset.profile_id``).
* ``received_date`` -> ``date_start``; ``value`` -> ``purchase_value``.
* ``company_address_header_report.company_name_thai`` / ``_en`` ->
  ``res_company.name``.
* ``account_asset_depreciation_line.depreciation_date`` ->
  ``account_asset_line.line_date``.

The legacy ``category_ids`` Many2many to ``account.asset.category`` is replaced
by the plain ``p_category_codes`` Char filter, so the module does not need
``account_asset_management``.
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


class BookValueReport(models.TransientModel):
    _name = "book.value.report"
    _description = "Book Value Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Book Value Report")
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
    end_date = fields.Date(
        string="At Date",
        required=True,
        default=fields.Date.context_today,
    )
    p_category_codes = fields.Char(
        string="Asset Category",
        help="ชื่อหมวดหมู่ทรัพย์สิน (คั่นหลายรายการด้วยเครื่องหมายจุลภาค)",
    )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        english = self.p_language == "english"
        months = dict(MONTH_LIST_EN) if english else dict(MONTH_LIST)
        rpt_month = months.get(self.end_date.strftime("%m"))
        day = self.end_date.day
        year = self.end_date.year
        if english:
            header = "Book Value Report At {0} {1} {2}".format(day, rpt_month, year)
        else:
            header = "รายงานมูลค่าสินทรพย์ปัจจุบัน ณ วันที่ {0} {1} {2}".format(
                day, rpt_month, year + 543
            )
        where = "WHERE asset.state != 'draft' and asset.company_id = {0}".format(
            self.company_id.id
        )
        asset_category = "All" if english else "ทั้งหมด"
        if self.p_category_codes:
            names = [
                name.strip() for name in self.p_category_codes.split(",") if name.strip()
            ]
            where += " and cat.name in (%s)" % ", ".join(
                "'%s'" % name.replace("'", "''") for name in names
            )
            asset_category = ", ".join(names)
        self.name = "Book Value Report"
        return {
            "p_Print_By": self._legacy_print_by(),
            "p_Where": where,
            "p_DateFormat": str(self.date_format),
            "p_language": self.p_language,
            "p_locale": "th" if self.date_type == "BE" else "en",
            "p_HeaderName": header,
            "p_Asset_Category": asset_category,
            "p_AtDate": str(self.end_date),
        }
