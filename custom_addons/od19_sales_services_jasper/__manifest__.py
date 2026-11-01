{
    "name": "OD19 Sales Services - Jasper Print Forms",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Jasper print forms for the Sales Services domain (service card, warranty claim, product return, transport order) ported from Odoo 15",
    "depends": [
        "sales_team",
        "od19_reporting_jasper",
        "od19_service_card",
        "od19_service_warranty",
        "od19_product_return",
        "od19_transportation",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sales_services_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
