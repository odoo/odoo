{
    "name": "Assets - Product",
    "version": "1.4",
    "category": "Hidden",
    "summary": "A product whose units are assets: the kind on the template, the asset on the unit",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "resource_asset",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/resource_asset_product_security.xml",
        "views/product_template_views.xml",
        "views/resource_asset_views.xml",
        "views/resource_asset_log_views.xml",
        "views/resource_asset_part_views.xml",
        "views/resource_asset_product_menus.xml",
    ],
    "auto_install": True,
}
