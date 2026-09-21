from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists

COLUMNS = (
    "l10n_in_upi_id",
    "l10n_in_hsn_code_digit",
    "l10n_in_edi_production_env",
    "l10n_in_tds_feature",
    "l10n_in_tcs_feature",
    "l10n_in_withholding_account_id",
    "l10n_in_withholding_journal_id",
    "l10n_in_is_gst_registered",
    "l10n_in_gstin_status_feature",
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
    env["l10n_in.config"]._for_each(companies)
    env.flush_all()
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE l10n_in_config x SET {assignments} FROM res_company c WHERE c.id = x.company_id"
    )
    env.invalidate_all()
