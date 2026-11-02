# -*- coding: utf-8 -*-
"""Advance Request Form (ใบขอเบิกเงินทดรองจ่าย).

Odoo 19 port of the legacy ``dtr_advance`` report ``f_adv_001``
(``dtr.adv.request.form``).  The legacy report template allow-guard
(``self.env.ref('dtr_advance.f_adv_001')``) is dropped because the module is
not installed on Odoo 19; fixed date defaults are used instead.

The template queries the employee advance model of the new stack
(``od19.hr.advance``, table ``od19_hr_advance``) instead of the legacy
``account_advance`` table, which does not exist on Odoo 19.  The form is bound
to ``od19.hr.advance`` so the Print menu on an advance passes ``active_ids``.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from .invoice_form import DATE_FORMATS


class DtrAdvRequestForm(models.TransientModel):
    _name = "dtr.adv.request.form"
    _description = "Advance Request Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Advance Request Report")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
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

    def get_parameters(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Print_By": self._legacy_print_by(),
                "p_language": str(self.p_language),
                "p_Where": "WHERE req.id in (%s)" % ", ".join(str(i) for i in ids),
            }
        )
        return parameters
