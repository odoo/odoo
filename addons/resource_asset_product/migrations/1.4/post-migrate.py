from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "resource_asset", ["product_tmpl_id"])
    schema.drop_columns(cr, "resource_asset_log", ["product_category_id"])
    schema.drop_columns(cr, "resource_asset_part", ["company_id"])
    schema.drop_columns(cr, "resource_asset_part_flag", ["asset_id", "company_id"])
