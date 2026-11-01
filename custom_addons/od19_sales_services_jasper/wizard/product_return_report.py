# -*- coding: utf-8 -*-
"""Product Return Report (รายงานรับคืนสินค้าตามช่วงเวลา).

Odoo 19 port of the legacy ``dtr_sales_services_report`` report
(``r_ss_003``).  It is a period report: the user picks a date range and an
optional customer filter, and the template aggregates the selected returns.
The query is built flat against :class:`od19.product.return` (alias ``pr``).
"""
from odoo import fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class ProductReturnReport(models.TransientModel):
    _name = "product.return.report"
    _description = "Product Return Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Product Return Report")
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
    p_Start_Date = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: self.default_start_date(),
    )
    p_End_Date = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.context_today,
    )
    p_Customer = fields.Many2many(
        "res.partner",
        string="Customer (Specific)",
        domain="[('customer', '=', True)]",
    )

    def default_start_date(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    def get_parameters(self):
        self.name = "Product Return Report"
        p_Where = (
            "WHERE pr.state not in ('draft') AND date(pr.return_date) >= '"
            + str(self.p_Start_Date)
            + "' AND date(pr.return_date) <= '"
            + str(self.p_End_Date)
            + "' AND pr.company_id = "
            + str(self.env.company.id)
        )
        if self.p_Customer:
            p_Where += " AND pr.partner_id in ({0})".format(
                ", ".join([str(i.id) for i in self.p_Customer])
            )
        return dict(
            self.get_common_parameters(),
            p_Print_By=self.env.user.name,
            p_Where=p_Where,
            p_Start_Date=str(self.p_Start_Date.strftime("%Y-%m-%d")),
            p_End_Date=str(self.p_End_Date.strftime("%Y-%m-%d")),
            p_Customer=", ".join(self.p_Customer.mapped("display_name"))
            if self.p_Customer
            else ("ทั้งหมด" if self.p_language == "thai" else "All"),
        )
