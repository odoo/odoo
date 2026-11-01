# -*- coding: utf-8 -*-
"""Sale Order Values Report (รายงานมูลค่าใบสั่งขายตามช่วงเวลา).

Ported from the legacy values report.  It is a period report: the user picks a
date range and a grouping key (product / category / customer / order) and the
template aggregates the order lines.  The legacy ``dtr_product_brand`` grouping
has no Odoo 19 counterpart, so it is no longer offered.
"""
from odoo import _, fields, models

from odoo.addons.od19_reporting_jasper.wizard.invoice_form import DATE_FORMATS


class SaleOrderValuesReport(models.TransientModel):
    _name = "sale.order.values.report"
    _description = "Sale Order Values Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Sale Order Values Report")
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
    date_start = fields.Date(
        string="From Date",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1),
    )
    date_end = fields.Date(
        string="To Date",
        required=True,
        default=fields.Date.context_today,
    )
    p_Group = fields.Selection(
        [
            ("1", "Product"),
            ("2", "Product Category"),
            ("4", "Customer"),
            ("5", "Order"),
        ],
        string="Group By",
        default="1",
        required=True,
    )
    p_Group_Name = fields.Char(string="Group Label")
    p_Period_Start = fields.Char(string="Period Start")
    p_Period_End = fields.Char(string="Period End")
    p_EName = fields.Boolean(string="Show Employee Name", default=True)
    p_ESignature = fields.Boolean(string="Show Signature", default=True)

    def get_parameters(self):
        self.name = self.get_file_name([], "sale.order", "Sale Order Values Report")
        return dict(
            self.get_common_parameters(),
            p_Path=self._legacy_filestore_path(),
            p_User_ID=str(self.env.user.id),
            p_ISO=self.iso_no or "",
            p_EName=str(self.p_EName),
            p_ESignature=str(self.p_ESignature),
            p_Start_Date=self.date_start.strftime("%Y-%m-%d"),
            p_To_Date=self.date_end.strftime("%Y-%m-%d"),
            p_Group=str(self.p_Group),
            p_Group_Name=self.p_Group_Name or "",
            p_Period_Start=self.p_Period_Start or "",
            p_Period_End=self.p_Period_End or "",
        )
