# -*- coding: utf-8 -*-
{
    "name": "OD19 Project Timesheet Billing",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": (
        "เรียกเก็บค่าบริการจาก Timesheet (Timesheet → Invoice) สำหรับงานบริการ/โครงการ: "
        "เปิดใช้ sale_timesheet, ติดตาม Timesheet ที่ยังไม่เรียกเก็บ, "
        "และสร้างใบแจ้งหนี้ตามช่วงวันที่"
    ),
    "depends": [
        "sale_timesheet",
        "project",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/project_project_views.xml",
        "views/sale_order_views.xml",
        "wizards/od19_timesheet_invoice_wizard_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "icon": "/od19_project_timesheet_billing/static/description/icon.svg",
}
