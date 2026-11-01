# -*- coding: utf-8 -*-
"""Goods Receipt Form (ใบรับสินค้า) - port of the legacy ``dtr_stock_form``
report ``F-IV-001`` (``receive.report``).

Reached from ``Stock > Receipts > Print > Receive Order Form`` and requires the
operation type to be ``incoming``.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class ReceiveReport(models.TransientModel):
    _name = "receive.report"
    _description = "Receive Order Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Receive Order Form")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )
    p_Header_Name = fields.Char(string="Dynamic Header Name", default="")
    show_serial = fields.Boolean(string="Show Serial Number")
    p_Show_Satisfation = fields.Boolean(string="Show Satisfation")
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
        pickings = self.env["stock.picking"].browse(
            self.env.context.get("active_ids", [])
        )
        return pickings.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        pickings = self.env["stock.picking"].browse(ids)
        if pickings.filtered(lambda x: x.picking_type_id.code != "incoming"):
            raise ValidationError(
                _("Cannot print operation type is not incoming")
            )
        self.name = self.get_file_name(
            ids, "stock.picking", "Receive Order Form"
        )
        return {
            "p_Header_Name": str(self.p_Header_Name),
            "p_Show_Satisfation": str(self.p_Show_Satisfation),
            "p_Receive_No": "WHERE sp.id in ({0})".format(
                ", ".join(str(i) for i in ids)
            ),
            "p_Path": self._legacy_filestore_path(),
            "p_Show_Serial": str(self.show_serial).lower(),
            "p_ISO": self.iso_no or "",
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_language": self.p_language,
            "p_DateFormat": str(self.date_format),
            "p_locale": "th" if self.date_type == "BE" else "en",
        }

    def show_report(
        self, report_name=False, email_subject=False, email_document_number=False
    ):
        ids = self.env.context.get("active_ids") or []
        pickings = self.env["stock.picking"].browse(ids)

        email_subject = "Goods Receipt Form"
        email_document_number = ""
        if len(ids) == 1:
            email_subject = "Goods Receipt Form: %s" % pickings.name
            email_document_number = pickings.name
            self.can_send_email = True

        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
