from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "resource_asset_identifier", ["company_id"])
    schema.drop_columns(cr, "resource_asset_meter", ["company_id"])
    schema.drop_columns(cr, "resource_asset_meter_reading", ["asset_id", "company_id"])
