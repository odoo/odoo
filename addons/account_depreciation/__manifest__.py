{
    "name": "Assets Management",
    "version": "1.4",
    "category": "Accounting/Accounting",
    "sequence": 32,
    "description": """
Assets management
=================
Manage assets owned by a company or a person.
Keeps track of depreciations, and creates corresponding journal entries.

    """,
    "author": "Odoo S.A.",
    "license": "OEEL-1",
    "depends": [
        "account",
        "resource_asset",
    ],
    "data": [
        "security/account_asset_security.xml",
        "security/ir.model.access.csv",
        "data/resource_asset_kind_data.xml",
        "wizards/asset_modify_views.xml",
        "views/account_account_views.xml",
        "views/account_asset_views.xml",
        "views/account_asset_group_views.xml",
        "views/account_depreciation_profile_views.xml",
        "views/account_move_views.xml",
        "data/asset_export_template.xml",
        "data/assets_report.xml",
        "data/account_report_actions.xml",
        "data/account_return_check_template.xml",
        "data/menuitems.xml",
    ],
    "demo": [
        "demo/account_asset_demo.xml",
    ],
    "assets": {
        "account.assets_financial_report": [
            "account_depreciation/static/src/scss/account_asset.scss",
        ],
        "web.assets_backend": [
            "account_depreciation/static/src/scss/account_asset.scss",
            "account_depreciation/static/src/components/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
}
