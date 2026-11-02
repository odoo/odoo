{
    "name": "OD19 Sales OCA Workflow Bridge",
    "author": "OD19",
    "version": "19.0.1.2.0",
    "depends": [
        "sale_delivery_state",
        "base_revision",
        "sale_order_revision",
        "base_exception",
        "sale_exception",
        "sale_blanket_order",
        "base_tier_validation",
    ],
    "data": [
        "security/sale_director_security.xml",
        "data/od19_sale_tier_definition.xml",
        "views/sale_order_bridge_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_sales_oca_bridge_workflow/static/description/icon.svg",
}
