from odoo.tools.module_data import rename_module

RENAMES = (
    ("delivery_tracking_product_asset_remote_gps", "asset_delivery_remote"),
    ("document_product_asset_compliance_hr", "asset_ledger_document_compliance_hr"),
    ("document_product_asset_compliance", "asset_ledger_document_compliance"),
    ("product_asset_maintenance_remote", "asset_ledger_maintenance_remote"),
    ("product_asset_maintenance_mrp", "asset_ledger_maintenance_mrp"),
    ("product_asset_remote_geoengine", "asset_remote_geoengine"),
    ("delivery_tracking_product_asset", "asset_delivery"),
    ("website_sale_product_asset", "asset_ledger_website_sale"),
    ("product_asset_maintenance", "asset_ledger_maintenance"),
    ("product_asset_remote_hr", "asset_remote_hr"),
    ("document_product_asset", "asset_ledger_document"),
    ("account_product_asset", "asset_ledger_account"),
    ("product_asset_device", "asset_device"),
    ("product_asset_wallet", "asset_wallet"),
    ("product_asset_remote", "asset_remote"),
    ("product_asset_mrp", "asset_ledger_mrp"),
    ("product_asset_hr", "asset_ledger_hr"),
    ("product_asset", "asset_ledger"),
)


def migrate(cr, version):
    """agromarin's product_asset family is named for what it serves."""
    if not version:
        return
    for old, new in RENAMES:
        rename_module(cr, old, new)
