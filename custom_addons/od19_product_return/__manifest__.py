{
    "name": "Product Return / RMA",
    "version": "19.0.1.0.0",
    "summary": "Manage customer product returns, RMA, and refunds",
    "category": "Sales",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "sale",
        "account",
        "od19_service_warranty",
        "od19_delivery_label",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/product_return_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
    "icon": "/od19_product_return/static/description/icon.svg",
}
