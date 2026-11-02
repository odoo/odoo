{
    "name": "OD19 Sales - Jasper Print Forms",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Jasper print forms for the Sales domain (Sale Order Form, and later quotation/proforma)",
    "depends": [
        "sale",
        "sales_team",
        "od19_reporting_jasper",
        "od19_service_warranty",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sale_order_form_views.xml",
        "wizard/sale_reports_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_sale_jasper/static/description/icon.svg",
}
