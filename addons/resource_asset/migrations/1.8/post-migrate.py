from odoo.db import schema

from odoo.addons.resource_asset.table_inheritance import move_rows_into_subtype_table


def migrate(cr, version):
    if not version:
        return
    for code in ("machinery", "equipment", "it", "furniture"):
        move_rows_into_subtype_table(cr, code, f"resource_asset_{code}")
    schema.drop_columns(cr, "resource_asset_identifier", ["company_id"])
    schema.drop_columns(cr, "resource_asset_meter", ["company_id"])
    schema.drop_columns(cr, "resource_asset_meter_reading", ["asset_id", "company_id"])
