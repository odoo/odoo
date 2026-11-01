{
    "name": "OD19 Sales Project Context",
    "author": "OD19",
    "version": "19.0.1.1.0",
    "depends": [
        "sale_management",
        "mail",
        "od19_contacts_partner_roles",
        "od19_project_analytic",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/project_context_views.xml",
        "views/sale_order_views.xml",
        "views/sale_order_pnl_analysis_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_sales_project_context/static/description/icon.svg",
}
