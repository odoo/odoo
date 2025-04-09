{
    "name": "Marketplace",
    "author": "AIT Solutions",
    "license": "LGPL-3",
    "version": "0.0.0",
    'installable': True,
    'application': True,
    "depends": [
        "mail",
        ],
    "data" : [
        "views/seller_views.xml",
        "views/product_views.xml",
        "security/ir.model.access.csv",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "marketplace/static/src/css/style.css",
        ],
    },
}