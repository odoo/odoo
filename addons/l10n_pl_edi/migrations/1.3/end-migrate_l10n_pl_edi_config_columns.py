from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_pl_edi_certificate",
    "l10n_pl_edi_session_id",
    "l10n_pl_edi_session_key",
    "l10n_pl_edi_session_iv",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
