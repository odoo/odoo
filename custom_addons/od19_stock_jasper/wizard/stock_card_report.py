# -*- coding: utf-8 -*-
"""Stock Card (บัตรสินค้า) - port of the legacy ``dtr_stock_report`` report
``F-IV-001`` (``stock.card.report``).

The ``.jrxml`` (``jrxml/stock_card_report.jrxml``) is shipped unchanged except
for the ``queryString`` which now targets the Odoo 19 schema: the source table
is ``stock_move`` (aliased ``svl``) because ``stock.valuation.layer`` no longer
exists.
"""
from odoo import _, api, fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class StockCardReport(models.TransientModel):
    _name = "stock.card.report"
    _description = "Stock Card"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Stock Card")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
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
    p_EName = fields.Boolean(string="Show Employee Name", default=True)
    p_ESignature = fields.Boolean(string="Show Signature", default=True)

    wh = fields.Many2one("stock.location", string="Location Name")
    asdate = fields.Date(string="As of Date", default=fields.Date.today)
    p_Product = fields.Many2many(
        "product.product",
        "product_product_stock_card_report",
        string="Product (specific)",
    )
    start_date = fields.Date(
        string="Start Date", default=lambda self: self._default_start_date()
    )
    end_date = fields.Date(string="End Date", default=fields.Date.today)
    product_category_ids = fields.Many2many(
        "product.category", string="Product Category (specific)"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    date_option = fields.Selection(
        [("range", "Range"), ("asof", "As of Date")],
        string="Date Option",
        default="range",
        required=True,
    )

    @api.model
    def _default_start_date(self):
        return fields.Date.context_today(self).replace(day=1)

    def _date_text(self, value):
        """Legacy human readable date, shifted to พ.ศ. for the Thai document."""
        if not value:
            return ""
        year = value.year + 543 if self.p_language == "thai" else value.year
        return "{0:02d}-{1:02d}-{2:d}".format(value.day, value.month, year)

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Stock Card"
        if self.date_option == "range":
            p_where = (
                "WHERE svl.company_id={0} AND DATE(svl.date) >= '{1}' "
                "AND DATE(svl.date) <= '{2}'"
            ).format(self.company_id.id, self.start_date, self.end_date)
            start_date_text = self._date_text(self.start_date)
            end_date_text = self._date_text(self.end_date)
        else:
            p_where = (
                "WHERE svl.company_id={0} AND DATE(svl.date) <= '{1}'"
            ).format(self.company_id.id, self.asdate)
            start_date_text = self._date_text(self.asdate)
            end_date_text = ""
        if self.p_Product:
            p_where += " AND svl.product_id in ({0})".format(
                ", ".join(str(i.id) for i in self.p_Product)
            )
        if self.product_category_ids:
            p_where += " AND pt.categ_id in ({0})".format(
                ", ".join(str(i.id) for i in self.product_category_ids)
            )

        return {
            "p_Path": self._legacy_filestore_path(),
            "p_ISO": self.iso_no or "",
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_DateFormat": str(self.date_format),
            "p_language": str(self.p_language),
            "p_locale": self._legacy_locale(),
            "p_start_date_text": start_date_text,
            "p_end_date_text": end_date_text,
            "p_Where": p_where,
        }
