# -*- coding: utf-8 -*-
"""Quotation Form (ใบเสนอราคา) - Jasper port of the legacy quotation print form.

Shares the ``sale.order`` print flow with :class:`sale.order.form`; the only
extra legacy parameter is ``p_Company_No`` used by the template header.
Unlike the approved Sales Order form, a quotation is normally printed while the
order is still in ``draft`` / ``sent`` state, so no state restriction is applied.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class SaleQuotationForm(models.TransientModel):
    _name = "sale.quotation.form"
    _description = "Quotation Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Quotation Form")
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
        ids = self._legacy_active_ids()
        orders = self.env["sale.order"].browse(ids)
        self.name = self.get_file_name(ids, "sale.order", "Quotation Report")
        return dict(
            self.get_common_parameters(),
            p_Where="WHERE so.id in (%s)" % ", ".join(str(i) for i in ids),
            p_Company_No=str(orders[:1].company_id.id or self.env.company.id),
            p_ISO=self.iso_no or "",
            p_Path=self._legacy_filestore_path(),
            p_EName=str(self.p_EName),
            p_ESignature=str(self.p_ESignature),
        )
