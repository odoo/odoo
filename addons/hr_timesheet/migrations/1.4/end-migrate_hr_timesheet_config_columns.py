from odoo.db.schema import column_exists

COLUMNS = (
    "project_time_mode_id",
    "timesheet_encode_uom_id",
    "internal_project_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
