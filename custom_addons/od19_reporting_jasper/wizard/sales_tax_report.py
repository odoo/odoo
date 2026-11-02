# -*- coding: utf-8 -*-
"""Sales Tax Report (รายงานภาษีขาย).

Odoo 19 port of the legacy ``dtr_taxation`` wizard ``sales_tax_report``.

The legacy ``dtr.vat`` register table (filled by the Odoo 15 "confirm VAT"
step) does not exist in Odoo 19.  The Thai localisation keeps the tax-invoice
register in ``account.move.tax.invoice`` (OCA ``l10n_th_account_tax``), so the
ported ``jrxml/sales_tax_report.jrxml`` reads that table instead:

    v.vat_date    -> tinv.tax_invoice_date
    v.vat_no      -> tinv.tax_invoice_number
    v.name        -> mv.name
    v.tax_name    -> COALESCE(part.tax_name, part.name)
    v.tax_code    -> at.description
    v.branch_code -> part.branch_code
    v.amount      -> tinv.tax_base_amount
    v.amount_vat  -> tinv.balance
    v.remark      -> mv.narration
    v.state       -> tinv.move_state  ('confirm' -> 'posted')
    v.vat_type    -> account_tax.type_tax_use
    v.send_date   -> tinv.report_date
    v.company_id  -> tinv.company_id
    parent.reference -> parent.ref

The legacy report-allow guard (``dtr_taxation.f_ac_012``) has no Odoo 19
equivalent and is dropped; the report date format falls back to the fixed
legacy default ``dd-MM-yyyy``.
"""
from calendar import monthrange
from datetime import date

from odoo import fields, models

from .pl_bs import MONTH_LIST, MONTH_LIST_EN


class SalesTaxReport(models.TransientModel):
    _name = "sales.tax.report"
    _description = "Sales Tax Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Sales Tax Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Language",
        default="thai",
        required=True,
    )
    year = fields.Char(
        string="Year", required=True, default=lambda self: self._get_current_year()
    )
    month = fields.Selection(
        MONTH_LIST,
        string="Month",
        required=True,
        default=lambda self: self._get_current_month(),
    )
    vat_types = fields.Many2many(
        "account.tax",
        relation="od19_sales_tax_report_vat_rel",
        string="VAT Type",
        required=True,
        domain=[("type_tax_use", "=", "sale")],
    )
    vat_name = fields.Char(compute="_compute_vat_name")
    vat_rate = fields.Float(compute="_compute_vat_name")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    def _compute_vat_name(self):
        for rec in self:
            for vat_type in rec.vat_types:
                rec.vat_name = "%d%%" % int(vat_type.amount)
                rec.vat_rate = int(vat_type.amount)

    def _get_current_year(self):
        return str(date.today().year + 543)

    def _get_current_month(self):
        return str(date.today().month)

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Sales Tax Report"
        year, month = int(self.year) - 543, int(self.month)
        days = monthrange(year, month)[1]
        from_date = fields.Date.to_string(date(year, month, 1))
        to_date = fields.Date.to_string(date(year, month, days))

        p_Where = (
            "WHERE tinv.move_state = 'posted' AND at.type_tax_use = 'sale'"
            " AND tinv.report_date BETWEEN '" + str(from_date) + "' AND '"
            + str(to_date) + "' AND tinv.company_id = " + str(self.company_id.id)
        )
        if self.vat_types:
            p_Where += " AND at.id in ({0})".format(
                ", ".join(str(vat.id) for vat in self.vat_types)
            )

        months = dict(MONTH_LIST_EN if self.p_language == "english" else MONTH_LIST)
        rpt_month = months.get(self.month)
        rpt_year = self.year if self.p_language == "thai" else (int(self.year) - 543)
        period_format = "เดือน {0} ปี {1}" if self.p_language == "thai" else "{0}, {1}"

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_Where": p_Where,
                "p_DateFormat": self.LEGACY_DEFAULT_DATE_FORMAT,
                "p_language": str(self.p_language),
                "p_MonthYear": period_format.format(rpt_month, rpt_year),
            }
        )
        return parameters

    def get_locale(self):
        return "en_EN"
