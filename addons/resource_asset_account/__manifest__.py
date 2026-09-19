{
    "name": "Assets - Accounting",
    "version": "1.2",
    "category": "Hidden",
    "summary": "Book journal items and analytic lines against an asset, and log the cost on it",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "account",
        "resource_asset_product",
    ],
    "data": [
        "views/account_account_views.xml",
        "views/account_move_views.xml",
        "views/account_analytic_line_views.xml",
        "views/resource_asset_views.xml",
    ],
    "auto_install": True,
}
