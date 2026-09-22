"""The columns the registry now holds. Harmless to lose, which is the only
kind of work an end-migration is for."""

from odoo.db.schema import column_exists, table_exists

MOVED = (
    ("iot_box", "name"),
    ("iot_box", "identifier"),
    ("iot_box", "company_id"),
    ("iot_box", "ip"),
    ("iot_device", "name"),
    ("iot_device", "identifier"),
    ("iot_device", "connected_status"),
)


def migrate(cr, version):
    if not version:
        return
    for table, column in MOVED:
        if table_exists(cr, table) and column_exists(cr, table, column):
            cr.execute(f"ALTER TABLE {table} DROP COLUMN {column} CASCADE")
