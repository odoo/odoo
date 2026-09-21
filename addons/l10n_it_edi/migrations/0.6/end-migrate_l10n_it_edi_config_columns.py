from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_it_tax_system",
    "l10n_it_edi_register",
    "l10n_it_edi_purchase_journal_id",
    "l10n_it_has_eco_index",
    "l10n_it_eco_index_office",
    "l10n_it_eco_index_number",
    "l10n_it_eco_index_share_capital",
    "l10n_it_eco_index_sole_shareholder",
    "l10n_it_eco_index_liquidation_state",
    "l10n_it_has_tax_representative",
    "l10n_it_tax_representative_partner_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
