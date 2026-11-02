# -*- coding: utf-8 -*-
"""Sale Order Outstanding Report (รายงานใบสั่งขายค้างส่ง/ค้างส่งของ).

Ported from the legacy outstanding report.  The template composes its own
``WHERE`` through the raw-SQL parameter ``p_Condition``; this wizard builds it
either from the selected orders (``active_ids``) or, when the report is launched
from the menu, from the current company and the open/confirmed states.
"""
from odoo import _, fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class SaleOrderOutstandingReport(models.TransientModel):
    _name = "sale.order.outstanding.report"
    _description = "Sale Order Outstanding Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Sale Order Outstanding Report")
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
    p_EName = fields.Boolean(string="Show Employee Name", default=True)
    p_ESignature = fields.Boolean(string="Show Signature", default=True)
    p_Show_Picture = fields.Boolean(string="Show Product Picture", default=True)

    def _legacy_condition(self):
        ids = self.env.context.get("active_ids") or []
        if ids:
            return " where a.id in (%s)" % ", ".join(str(i) for i in ids)
        company_id = self.env.company.id
        return (
            " where a.company_id = %s and a.state in ('sale','done')" % company_id
        )

    def get_parameters(self):
        self.name = self.get_file_name(
            [], "sale.order", "Sale Order Outstanding Report"
        )
        return dict(
            self.get_common_parameters(),
            p_Condition=self._legacy_condition(),
            p_Show_Picture=str(self.p_Show_Picture),
            p_Path=self._legacy_filestore_path(),
            p_User_ID=str(self.env.user.id),
            p_ISO=self.iso_no or "",
            p_EName=str(self.p_EName),
            p_ESignature=str(self.p_ESignature),
        )
