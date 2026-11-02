# -*- coding: utf-8 -*-
{
    "name": "Sales Confirm Stamp (OD19)",
    "version": "19.0.1.0.0",
    "summary": "Red CONFIRMED stamp box on printed quotations, driven by stamp_date",
    "description": """
Adds a Stamp Date field and supporting fields to sale orders.
When a quotation is confirmed and Stamp Date is filled, the printed
quotation displays a red CONFIRMED stamp box containing:

- SIGN  : handwritten signature image of the user who confirmed the order
  (falls back to the user's name if no signature is uploaded)
- DATE  : Stamp Date
- DELIVERY ON : commitment date
- JOB   : linked project job number
- CODE  : stamp code (free text)

Also renames the legacy x_stamp_date signal to stamp_date.
    """,
    "author": "OD19 Custom",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "hr",
        "od19_sales_project_context",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/hr_employee_views.xml",
        "report/report_saleorder_stamp.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_sales_confirm_stamp/static/description/icon.svg",
}
