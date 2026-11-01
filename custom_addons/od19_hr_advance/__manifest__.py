# -*- coding: utf-8 -*-
{
    "name": "OD19 HR - Employee Advance (เงินทดรองจ่ายพนักงาน)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Expenses",
    "summary": "ใบเบิกเงินทดรองจ่ายพนักงาน: อนุมัติ 2 ชั้น, จ่ายเงินจริง, เคลียร์และคืนเงินส่วนที่เหลือ",
    "depends": [
        "hr_expense",
        "account",
        "mail",
        "base_tier_validation",
        "od19_accounting_features",
        "od19_hr_expense_enhanced",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/tier_definition_data.xml",
        "wizards/clear_advance_views.xml",
        "views/hr_advance_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_hr_advance/static/description/icon.svg",
}
