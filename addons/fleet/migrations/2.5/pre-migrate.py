from odoo.db.schema import column_exists, rename_column, table_exists

# The identifier columns leave the root for the vehicle. Each is set aside
# under another name so that the schema pass gives the vehicle a column of its
# own, which the inherited column of the same name would otherwise stand in for.
COLUMNS = ("license_plate", "vin_sn", "engine_sn")


def migrate(cr, version):
    if not table_exists(cr, "resource_asset"):
        return
    for column in COLUMNS:
        if column_exists(cr, "resource_asset", column):
            rename_column(cr, "resource_asset", column, f"legacy_{column}")
