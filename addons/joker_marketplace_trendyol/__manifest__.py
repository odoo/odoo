{
    "name": "JOKER Pazaryeri - Trendyol Entegrasyonu",
    "version": "19.0.1.0.0",
    "category": "Sales/Marketplace",
    "summary": "Trendyol REST API entegrasyonu",
    "author": "JOKER CEO",
    "website": "https://joker.ai",
    "depends": [
        "joker_marketplace_core",
        "sale",
        "stock",
    ],
    "data": [
        "views/menu.xml",
    ],
    "external_dependencies": {
        "python": ["requests", "python-dateutil"],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
