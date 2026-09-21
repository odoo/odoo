from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_jo_edi_sequence_income_source",
    "l10n_jo_edi_client_identifier",
    "l10n_jo_edi_taxpayer_type",
    "l10n_jo_edi_demo_mode",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
