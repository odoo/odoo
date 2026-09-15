from odoo.db.schema import table_exists
from odoo.tools.module_data import adopt_xmlids, rename_model


def migrate(cr, version):
    if not table_exists(cr, "product_asset_log") or table_exists(
        cr, "resource_asset_log"
    ):
        return
    rename_model(cr, "product.asset.log", "resource.asset.log")
    adopt_xmlids(
        cr,
        "product_asset",
        "resource_asset_product",
        ["model_resource_asset_log"],
        renamed={
            "product_asset_log_comp_rule": "resource_asset_log_rule_multi_company"
        },
    )
