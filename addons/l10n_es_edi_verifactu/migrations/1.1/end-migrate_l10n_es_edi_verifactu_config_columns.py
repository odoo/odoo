from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_es_edi_verifactu_required",
    "l10n_es_edi_verifactu_test_environment",
    "l10n_es_edi_verifactu_chain_sequence_id",
    "l10n_es_edi_verifactu_next_batch_time",
    "l10n_es_edi_verifactu_special_vat_regime",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
