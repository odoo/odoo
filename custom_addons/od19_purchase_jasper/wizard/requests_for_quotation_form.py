# -*- coding: utf-8 -*-
"""Requests for Quotation (ใบขอราคา) - port of ``dtr_purchase_form`` F-P-002.

The legacy form rewrote ``purchase.order.line.report_sequence`` before printing
to control the row order, then committed the transaction.  Odoo 19 keeps that
order in ``purchase.order.line.sequence``, which the ported
``requests_for_quotation_report.jrxml`` reads directly, so the extra write and
the ``cr.commit()`` are gone.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class RequestsForQuotationForm(models.TransientModel):
    _name = "requests.for.quotation.form"
    _description = "Requests for Quotation Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Requests for Quotation Form")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(
            __file__, base_name="requests_for_quotation_report"
        )
    )
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
    p_EName = fields.Boolean(
        string="Show Employee Name",
        default=True,
        help="พิมพ์ชื่อผู้จัดทำ / ผู้ตรวจสอบ / ผู้อนุมัติ ในช่องลงนาม",
    )
    p_ESignature = fields.Boolean(
        string="Show Signature",
        default=True,
        help="พิมพ์รูปลายเซ็นพนักงานในช่องลงนาม",
    )

    def _legacy_active_ids(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        return ids

    def get_partner_ids_for_send_by_email(self):
        orders = self.env["purchase.order"].browse(
            self.env.context.get("active_ids", [])
        )
        return orders.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        self.name = self.get_file_name(
            ids, "purchase.order", "Requests for Quotation Report"
        )
        return {
            "p_Where": "where po.id in ({0})".format(
                ", ".join(str(i) for i in ids)
            ),
            "p_ISO": self.iso_no or "",
            "p_language": self.p_language,
            "p_DateFormat": str(self.date_format),
            "p_Path": self._legacy_filestore_path(),
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_locale": "th" if self.date_type == "BE" else "en",
        }

    def show_report(
        self, report_name=False, email_subject=False, email_document_number=False
    ):
        orders = self.env["purchase.order"].browse(
            self.env.context.get("active_ids", [])
        )
        email_subject = "Request for Quotation"
        if len(orders) == 1:
            email_subject = "Request for Quotation: %s" % orders.name
            email_document_number = orders.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
