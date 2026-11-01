# -*- coding: utf-8 -*-
"""Advance Request At Date (ใบขอเบิกทดรอง ตามวันที่).

Odoo 19 port of the legacy ``dtr_advance`` report ``r_adv_002``
(``dtr.adv.request.at.date.report``).  The legacy report template allow-guard
(``self.env.ref('dtr_advance.r_adv_002')``) is dropped because the module is
not installed on Odoo 19; fixed date defaults are used instead.

See the condition report for how the legacy clearing/fund tables are reduced
to the single ``account_advance`` model on Odoo 19.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class DtrAdvRequestAtDateReport(models.TransientModel):
    _name = "dtr.adv.request.at.date.report"
    _description = "Advance Request At Date Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Advance Request Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    p_At_Date = fields.Date(string="At Date", required=True, default=fields.Date.today)
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

    def get_parameters(self):
        where = (
            "WHERE (req.state = 'posted' OR req.state = 'reconciled')"
            " AND req.date <= '%s'" % self.p_At_Date
        )
        if self.p_request_id:
            where += " AND req.partner_id = %s" % self.p_request_id.id

        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_language": str(self.p_language),
                "p_Where": where,
                "p_At_Date": self.p_At_Date.strftime("%Y-%m-%d"),
                "p_request_name": self.p_request_id.name if self.p_request_id else "",
            }
        )
        return parameters
