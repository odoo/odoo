# -*- coding: utf-8 -*-
"""Advance Clear Form (ใบเคลียร์เงินทดรอง).

Odoo 19 port of the legacy ``dtr_advance`` report ``f_adv_002``
(``dtr.adv.clear.form``).  The legacy report template allow-guard
(``self.env.ref('dtr_advance.f_adv_002')``) is dropped because the module is
not installed on Odoo 19; fixed date defaults are used instead.

On Odoo 19 there is no separate clearing document: an ``od19.hr.advance``
(table ``od19_hr_advance``) carries both the request and the cleared amount
(``cleared_amount``), so the form prints that record.  The legacy
``account_advance`` table and its ``used_amount`` column do not exist on
Odoo 19 and are replaced accordingly.  The form is bound to
``od19.hr.advance`` so the Print menu on an advance passes ``active_ids``.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from .invoice_form import DATE_FORMATS


class DtrAdvClearForm(models.TransientModel):
    _name = "dtr.adv.clear.form"
    _description = "Advance Clear Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Advance Clear Report")
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
                "p_Where": "WHERE clear.id in (%s)" % ", ".join(str(i) for i in ids),
            }
        )
        return parameters
