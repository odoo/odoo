from odoo.db.schema import column_exists

COLUMNS = (
    "external_report_layout_id",
    "font",
    "primary_color",
    "secondary_color",
    "layout_background",
    "layout_background_image",
    "report_theme_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
