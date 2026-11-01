# -*- coding: utf-8 -*-
"""Product Return Form (ใบรับคืนสินค้า) - Jasper port of the legacy return form.

Odoo 19 port of the legacy ``dtr_sales_services_form`` print form (report
``f_ss_003``).  The legacy source read the ``dtr.product.return`` document;
Odoo 19 stores the same information on :class:`od19.product.return`
(alias ``pr``), which is read flat here (one document = one product, no child
table).
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class ProductReturnForm(models.TransientModel):
    _name = "product.return.form"
    _description = "Product Return Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Product Return Form")
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
        returns = self.env["od19.product.return"].browse(
            self.env.context.get("active_ids", [])
        )
        return returns.mapped("partner_id")

    def get_parameters(self):
        ids = self._legacy_active_ids()
        self.name = self.get_file_name(ids, "od19.product.return", "Product Return Report")
        return dict(
            self.get_common_parameters(),
            p_Where="WHERE pr.id in (%s)" % ", ".join(str(i) for i in ids),
        )

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        returns = self.env["od19.product.return"].browse(
            self.env.context.get("active_ids", [])
        )
        email_subject = "Product Return Form"
        email_document_number = ""
        if len(returns) == 1:
            email_subject = "Product Return Form: %s" % returns.name
            email_document_number = returns.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
