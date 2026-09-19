from odoo.db.schema import column_exists


def migrate(cr, version):
    if not version:
        return
    for column in (
        "report_header",
        "report_footer",
        "company_details",
        "paperformat_id",
    ):
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
