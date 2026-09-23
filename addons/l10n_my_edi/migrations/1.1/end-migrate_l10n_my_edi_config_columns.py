from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_my_edi_mode",
    "l10n_my_edi_default_import_journal_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
