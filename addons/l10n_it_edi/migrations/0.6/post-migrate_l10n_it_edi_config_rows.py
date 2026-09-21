from odoo import SUPERUSER_ID, api
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
    present = [column for column in COLUMNS if column_exists(cr, "res_company", column)]
    if not present:
        return
    # the rows through the ORM, so every default and required value is
    # applied; the values by SQL, straight from the company's columns
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].with_context(active_test=False).search([])
    env["l10n_it_edi.config"]._for_each(companies)
    env.flush_all()
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE l10n_it_edi_config x SET {assignments} FROM res_company c WHERE c.id = x.company_id"
    )
    env.invalidate_all()
