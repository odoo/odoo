{
    "name": "Repairs - Assets",
    "version": "1.0",
    "category": "Hidden",
    "summary": "A repair of a serial that is one of our assets records the parts it installs on the asset",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "repair",
        "resource_asset_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/repair_views.xml",
    ],
    "auto_install": True,
}
