# -*- coding: utf-8 -*-
"""Proforma Invoice Form (ใบแจ้งหนี้ชั่วคราว) - Jasper port.

Ported from the legacy proforma print form.  It reuses the same Odoo 19
``sale.order`` schema as :class:`sale.quotation.form`, so the parameter
contract is identical (``p_Where`` / ``p_Company_No`` plus the shared
language / date / signature toggles).
"""
from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class SaleOrderProformaForm(models.TransientModel):
    _name = "sale.order.proforma.form"
    _description = "Proforma Invoice Form"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Proforma Invoice Form")
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
        self.name = self.get_file_name(ids, "sale.order", "Proforma Invoice Report")
        return dict(
            self.get_common_parameters(),
            p_Where="WHERE so.id in (%s)" % ", ".join(str(i) for i in ids),
            p_Company_No=str(orders[:1].company_id.id or self.env.company.id),
            p_ISO=self.iso_no or "",
            p_Path=self._legacy_filestore_path(),
            p_EName=str(self.p_EName),
            p_ESignature=str(self.p_ESignature),
        )
