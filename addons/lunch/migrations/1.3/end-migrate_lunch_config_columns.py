from odoo.db.schema import column_exists

COLUMNS = (
    "lunch_minimum_threshold",
    "lunch_notify_message",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
