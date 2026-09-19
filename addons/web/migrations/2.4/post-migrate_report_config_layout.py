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
    if not version or not column_exists(cr, "res_company", "font"):
        return
    present = [column for column in COLUMNS if column_exists(cr, "res_company", column)]
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE report_config rc SET {assignments} FROM res_company c WHERE c.id = rc.company_id"
    )
