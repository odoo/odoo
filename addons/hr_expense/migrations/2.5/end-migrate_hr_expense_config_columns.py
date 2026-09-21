from odoo.db.schema import column_exists

COLUMNS = ("expense_journal_id",)


def migrate(cr, version):
    if not version:
        return
    # the company's side of the many2many, whose rows post-migrate copied
    cr.execute("DROP TABLE IF EXISTS account_payment_channel_res_company_rel")
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
