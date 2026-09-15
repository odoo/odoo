{
    "name": "Assets - Inventory",
    "version": "1.0",
    "category": "Hidden",
    "summary": "A serial of an asset product is an asset; scrapping it disposes of the asset",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "resource_asset_product",
        "stock",
    ],
    "data": [
        "views/stock_lot_views.xml",
        "views/resource_asset_views.xml",
        "views/stock_location_views.xml",
    ],
    "auto_install": True,
}
