from odoo.tools.module_data import adopt_xmlids, rename_module


def migrate(cr, version):
    if not version:
        return
    if rename_module(cr, "account_asset", "account_depreciation"):
        adopt_xmlids(
            cr,
            "accountant",
            "account_depreciation",
            ["account_assets_liabilities_menu"],
        )
