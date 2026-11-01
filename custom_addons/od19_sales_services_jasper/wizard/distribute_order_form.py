# -*- coding: utf-8 -*-
"""Distribute Order Form (ใบส่งของ) - Jasper port of the legacy distribute form.

Odoo 19 port of the legacy ``dtr_sales_services_form`` print form (report
``f_iv_013``).  The legacy source read the ``dtr.distribute.order`` document;
Odoo 19 stores the same information on :class:`od19.transport.order`
(alias ``dto``), which is read flat here (one document = one product, no child
table).

Unlike the other forms this report kept the raw parameter name ``ids`` (not
``p_Where``) and the lowercase ``where`` keyword, which is preserved verbatim
so the ported ``queryString`` keeps working.
"""
from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class DistributeOrderForm(models.TransientModel):
    _name = "distribute.order.form"
    _description = "Distribute Order Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Distribute Order")
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

    def get_parameters(self):
        ids = self.env.context.get("active_ids") or []
        self.name = self.get_file_name(ids, "od19.transport.order", "Distribute Order Report")
        return dict(
            self.get_common_parameters(),
            **{"ids": "where dto.id in (%s)" % ", ".join(str(i) for i in ids)},
        )

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        orders = self.env["od19.transport.order"].browse(
            self.env.context.get("active_ids", [])
        )
        for order in orders:
            if order.state not in ("confirmed", "in_transit", "delivered"):
                raise ValidationError(_("Distributes Order(s) is not ready to Print."))
        return super().show_report()
