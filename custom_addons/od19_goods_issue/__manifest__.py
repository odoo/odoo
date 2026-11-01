# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Goods Issue (ใบเบิกสินค้า)",
    "version": "19.0.1.0.0",
    "category": "Warehouse",
    "summary": "Thai goods issue (ใบเบิกสินค้า) document layer on OCA Stock Request",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": [
        "stock_request",
        "hr",
        "project",
        "od19_iso_document_control",
        "od19_security_roles",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/od19_department_rule.xml",
        "security/od19_goods_issue_security.xml",
        "data/od19_goods_issue_data.xml",
        "views/goods_issue_type_views.xml",
        "views/stock_request_order_views.xml",
        "views/stock_picking_views.xml",
        "views/goods_issue_menus.xml",
        "report/goods_issue_report.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_goods_issue/static/description/icon.svg",
}
