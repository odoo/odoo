from odoo import SUPERUSER_ID, api
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
    present = [column for column in COLUMNS if column_exists(cr, "res_company", column)]
    if not present:
        return
    # the rows through the ORM, so every default and required value is
    # applied; the values by SQL, straight from the company's columns
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].with_context(active_test=False).search([])
    env["l10n_es_edi_verifactu.config"]._for_each(companies)
    env.flush_all()
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE l10n_es_edi_verifactu_config x SET {assignments} FROM res_company c WHERE c.id = x.company_id"
    )
    env.invalidate_all()
