from odoo.db.schema import column_exists, drop_constraint


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'res_company'::regclass AND conname = 'res_company_name_uniq'
        """
    )
    if cr.fetchone():
        drop_constraint(cr, "res_company", "res_company_name_uniq")
    if column_exists(cr, "res_company", "name"):
        cr.execute("ALTER TABLE res_company DROP COLUMN name")
