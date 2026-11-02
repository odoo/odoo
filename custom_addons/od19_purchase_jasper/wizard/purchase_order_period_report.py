# -*- coding: utf-8 -*-
"""Purchase Order By Period (ใบสั่งซื้อตามช่วงเวลา) - port of
``dtr_purchase_report`` r_p_001.

Unlike the two forms above this report is not bound to a document: the legacy
wizard was opened from the ``Purchase > Purchases Report`` menu and selects its
own scope (period + vendors).
"""
from odoo import fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class PurchaseOrderPeriodReport(models.TransientModel):
    _name = "purchase.order.period.report"
    _description = "Purchase Order By Period Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Purchase Order By Period")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(
            __file__, base_name="purchase_order_period_report"
        )
    )
    startdate = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: self._default_start_date(),
    )
    todate = fields.Date(
        string="To Date",
        required=True,
        default=fields.Date.context_today,
    )
    partner = fields.Many2many(
        "res.partner",
        relation="od19_purchase_order_period_report_partner_rel",
        string="Vendor",
        domain=[("supplier_rank", ">", 0)],
        default=lambda self: self._default_partners(),
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

    def _default_start_date(self):
        """First day of the current month, as in the legacy wizard."""
        return fields.Date.context_today(self).replace(day=1)

    def _default_partners(self):
        return self.env["res.partner"].search([("supplier_rank", ">", 0)])

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Purchase Order By Period"
        partner_list = " "
        if self.partner:
            partner_list = " and p.partner_id in ({0}) ".format(
                ", ".join(str(i) for i in self.partner.ids)
            )
        return {
            "p_StartDate": str(self.startdate),
            "p_ToDate": str(self.todate),
            "p_ISO": self.iso_no or "",
            "p_User_ID": str(self.env.user.id),
            "p_Path": self._legacy_filestore_path(),
            "p_Partner": partner_list,
            "p_EName": str(self.p_EName),
            "p_ESignature": str(self.p_ESignature),
            "p_DateFormat": str(self.date_format),
            "p_language": self.p_language,
            "p_Period_Start": str(self.startdate),
            "p_Period_End": str(self.todate),
            "p_locale": "th" if self.date_type == "BE" else "en",
        }

    def action_clear_partner(self):
        """Legacy "Clear" button: drop the vendor filter and reopen the dialog."""
        self.ensure_one()
        self.partner = [(5, 0, 0)]
        return self._action_reopen_wizard()
