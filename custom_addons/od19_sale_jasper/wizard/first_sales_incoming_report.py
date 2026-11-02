# -*- coding: utf-8 -*-
"""First Sales Incoming Report (รายงานลูกค้ารายใหม่ / ยอดขายเดือนแรก).

Ported from the legacy monthly report.  The template selects the customers whose
very first order fell inside the chosen month; the wizard therefore only asks for
the target year and month.
"""
from odoo import _, fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class FirstSalesIncomingReport(models.TransientModel):
    _name = "first.sales.incoming.report"
    _description = "First Sales Incoming Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="First Sales Incoming Report")
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
    p_Year = fields.Integer(
        string="Year",
        required=True,
        default=lambda self: fields.Date.context_today(self).year,
    )
    p_Month = fields.Integer(
        string="Month",
        required=True,
        default=lambda self: fields.Date.context_today(self).month,
    )
    p_EName = fields.Boolean(string="Show Employee Name", default=True)
    p_ESignature = fields.Boolean(string="Show Signature", default=True)

    def get_parameters(self):
        self.name = self.get_file_name([], "sale.order", "First Sales Incoming Report")
        return dict(
            self.get_common_parameters(),
            p_Year=str(self.p_Year),
            p_Month=str(self.p_Month),
            p_Path=self._legacy_filestore_path(),
            p_User_ID=str(self.env.user.id),
            p_ISO=self.iso_no or "",
            p_EName=str(self.p_EName),
            p_ESignature=str(self.p_ESignature),
        )
