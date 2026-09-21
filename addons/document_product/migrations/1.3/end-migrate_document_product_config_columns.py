from odoo.db.schema import column_exists

COLUMNS = (
    "documents_product_settings",
    "product_folder_id",
)


def migrate(cr, version):
    if not version:
        return
    # the company's side of the many2many, whose rows post-migrate copied
    cr.execute("DROP TABLE IF EXISTS product_tags_table")
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
