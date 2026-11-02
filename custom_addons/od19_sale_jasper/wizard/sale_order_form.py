# -*- coding: utf-8 -*-
"""Sale Order Form (ใบสั่งขาย) - the pilot Jasper port for the Sales domain.

Odoo 19 port of the legacy ``dtr_sales_form`` print form (report ``F-S-002``).
This is the reference form for the ``od19_sale_jasper`` module; the remaining
printed documents of the domain (quotation, proforma, warranty card) follow the
same pattern: inherit :class:`od19.jasper.report`, declare the parameters, and
inherit the shared wizard view.

The legacy "running line sequence" step - which wrote ``report_sequence`` on the
order lines to control the print order - is not needed any more: Odoo 19 already
stores the print order in ``sale.order.line.sequence``, which the ported
``sale_order_form.jrxml`` reads directly.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class SaleOrderForm(models.TransientModel):
    _name = "sale.order.form"
    _description = "Sale Order Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Sale Order Form")
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
        orders = self.env["sale.order"].browse(self.env.context.get("active_ids", []))
        return orders.mapped("partner_id")

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        self.name = self.get_file_name(ids, "sale.order", "Sale Order Report")
        return {
            "p_Where": "WHERE so.id in ({0})".format(", ".join(str(i) for i in ids)),
            "p_ISO": self.iso_no or "",
            "p_language": self.p_language,
            "p_DateFormat": str(self.date_format),
            "p_Path": self._legacy_filestore_path(),
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_locale": "th" if self.date_type == "BE" else "en",
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        orders = self.env["sale.order"].browse(self.env.context.get("active_ids", []))
        if orders.filtered(lambda order: order.state not in ("sale", "done")):
            raise ValidationError(_("Only Approved Sales Order is allow."))

        email_subject = "Sales Orders"
        if len(orders) == 1:
            email_subject = "Sales Orders: %s" % orders.name
            email_document_number = orders.name
            self.can_send_email = True
        return super().show_report(
            email_subject=email_subject,
            email_document_number=email_document_number,
        )
