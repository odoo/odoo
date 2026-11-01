# -*- coding: utf-8 -*-
"""Advance Request Condition (เงื่อนไขใบขอเบิกทดรอง).

Odoo 19 port of the legacy ``dtr_advance`` report ``r_adv_001``
(``dtr.adv.request.condition.report``).  The legacy report template allow-guard
(``self.env.ref('dtr_advance.r_adv_001')``) is dropped because the module is
not installed on Odoo 19; fixed date defaults are used instead.

Odoo 19 has a single advance model (``account_advance``); the clearing
document/fund tables used by the legacy query are gone, so the report lists
each advance with its used amount (``used_amount``) and outstanding balance
(``remaining_amount``).
"""
from datetime import date

from odoo import fields, models

from .invoice_form import DATE_FORMATS


class DtrAdvRequestConditionReport(models.TransientModel):
    _name = "dtr.adv.request.condition.report"
    _description = "Advance Request Condition Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Advance Request Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_Start_Date = fields.Date(
        string="Start Date", required=True, default=lambda self: self.default_start_date()
    )
    p_End_Date = fields.Date(string="End Date", required=True, default=fields.Date.today)
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
    p_request_id = fields.Many2one("res.partner", string="Requester")

    def default_start_date(self):
        today = fields.Date.from_string(fields.Date.today())
        return date(today.year, today.month, 1)

    def get_parameters(self):
        where = (
            "WHERE (req.state = 'posted' OR req.state = 'reconciled')"
            " AND req.date >= '%s' AND req.date <= '%s'"
            % (self.p_Start_Date, self.p_End_Date)
        )
        if self.p_request_id:
            where += " AND req.partner_id = %s" % self.p_request_id.id

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_language": str(self.p_language),
                "p_Where": where,
                "p_Start_Date": self.p_Start_Date.strftime("%Y-%m-%d"),
                "p_End_Date": self.p_End_Date.strftime("%Y-%m-%d"),
                "p_request_name": self.p_request_id.name if self.p_request_id else "",
            }
        )
        return parameters
