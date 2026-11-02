# -*- coding: utf-8 -*-
"""Sales Services Form (ใบรับงานบริการ) - Jasper port of the legacy service card form.

Odoo 19 port of the legacy ``dtr_sales_services_form`` print form (report
``f_ss_001``).  In Odoo 15 the template joined the ``dtr.sales.services``
document with its child lines; Odoo 19 stores a service card flat (one document
= one product), so the child tables are dropped and the query reads
:class:`od19.service.card` directly (alias ``ss``).
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class SalesServicesForm(models.TransientModel):
    _name = "sales.services.form"
    _description = "Sales Services Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Sales Services Form")
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

    def _legacy_active_ids(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        return ids

    def get_partner_ids_for_send_by_email(self):
        cards = self.env["od19.service.card"].browse(
            self.env.context.get("active_ids", [])
        )
        return cards.mapped("partner_id")

    def get_parameters(self):
        ids = self._legacy_active_ids()
        self.name = self.get_file_name(ids, "od19.service.card", "Sales Services Report")
        return dict(
            self.get_common_parameters(),
            p_Where="WHERE ss.id in (%s)" % ", ".join(str(i) for i in ids),
        )

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        cards = self.env["od19.service.card"].browse(
            self.env.context.get("active_ids", [])
        )
        email_subject = "Sales Services Form"
        email_document_number = ""
        if len(cards) == 1:
            email_subject = "Sales Services Form: %s" % cards.name
            email_document_number = cards.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
