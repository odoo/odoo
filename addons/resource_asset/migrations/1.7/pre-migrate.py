from odoo.db.schema import column_exists, rename_column, table_exists

# The kinds whose assets become records of their own model, and the identifier
# column each takes off the root. The root's column is set aside under another
# name so that the schema pass gives the subtype a column of its own, which an
# inherited column of the same name would otherwise stand in for.
SUBTYPE_COLUMNS = {"cadastral_id": "property", "imei": ("telecom", "device")}


def migrate(cr, version):
    if not table_exists(cr, "resource_asset"):
        return
    for column in SUBTYPE_COLUMNS:
        if column_exists(cr, "resource_asset", column):
            rename_column(cr, "resource_asset", column, f"legacy_{column}")
