# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Delivery Label (Goods Pending Shipment)",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    "category": "Inventory/Delivery",
    "summary": "Print ใบปะหน้าสินค้ารอส่ง (FM-PU-12) for delivery orders",
    "description": """
OD19 Delivery Label (ใบปะหน้าสินค้ารอส่ง)
===========================================

Adds a printable delivery cover sheet (FM-PU-12) to stock.picking
(delivery orders). The label shows CODE, Customer, Project, and DEPT
as used in the warehouse shipment process.

Fields added to stock.picking:

* od19_department_code - Department code (DEPT) shown on the label
  and used in the picking reference (WH/{DEPT}/OUT/00001). Required.
* project_id (standard, from project_stock) - Project copied from the
  linked sale order for the delivery label.

Fields added to hr.department:

* code - Short department code (e.g. IA, BA, TA, DES, FA).
""",
    "depends": [
        "stock",
        "sale_stock",
        "project_stock",
        "hr",
        "od19_sales_project_context",
        "od19_inventory_execution_control",
        "od19_iso_document_control",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_views.xml",
        "report/delivery_label_report.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_delivery_label/static/description/icon.svg",
}
