# -*- coding: utf-8 -*-
"""Purchase Order referencing a Purchase Request - port of ``dtr_purchase_form``
F-P-001 (ใบสั่งซื้ออ้างอิงใบขอซื้อ).

The form is bound to a ``purchase.request`` document and only prints once the
request has been approved (``approved`` / ``done``), mirroring the legacy
guard.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS

# States in which the legacy form allowed printing (OCA ``purchase_request``).
PRINTABLE_STATES = ("approved", "done")


class PoPurchaseRequestForm(models.TransientModel):
    _name = "po.purchase.request.form"
    _description = "Purchase Request Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Purchase Request Form")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(
            __file__, base_name="po_purchase_request_report"
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

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        self.name = self.get_file_name(
            ids, "purchase.request", "Purchase Request Report"
        )
        return {
            "p_PRNo": "WHERE p.id in ({0})".format(
                ", ".join(str(i) for i in ids)
            ),
            "p_ISO": self.iso_no or "",
            "p_Path": self._legacy_filestore_path(),
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_DateFormat": str(self.date_format),
            "p_language": self.p_language,
            "p_locale": "th" if self.date_type == "BE" else "en",
        }

    def show_report(
        self, report_name=False, email_subject=False, email_document_number=False
    ):
        requests = self.env["purchase.request"].browse(
            self.env.context.get("active_ids", [])
        )
        if requests.filtered(lambda request: request.state not in PRINTABLE_STATES):
            raise ValidationError(_("Only Approved Purchase Request is allow."))

        email_subject = "Purchase Request"
        if len(requests) == 1:
            email_subject = "Purchase Request: %s" % requests.name
            email_document_number = requests.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
