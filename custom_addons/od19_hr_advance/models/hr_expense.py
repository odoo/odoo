# -*- coding: utf-8 -*-
from odoo import fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    od19_hr_advance_id = fields.Many2one(
        "od19.hr.advance",
        string="Employee Advance / ใบเบิกเงินทดรอง",
        copy=False,
        index="btree_not_null",
        help="ใบเบิกเงินทดรองจ่ายพนักงานที่ค่าใช้จ่ายนี้ถูกนำไปเคลียร์",
    )
