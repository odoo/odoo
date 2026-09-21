from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists

COLUMNS = (
    "account_peppol_contact_email",
    "account_peppol_phone_number",
    "account_peppol_proxy_state",
    "peppol_purchase_journal_id",
    "peppol_external_provider",
    "peppol_metadata",
    "peppol_metadata_updated_at",
    "peppol_activate_self_billing_sending",
    "peppol_self_billing_reception_journal_id",
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
    env["account_peppol.config"]._for_each(companies)
    env.flush_all()
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE account_peppol_config x SET {assignments} FROM res_company c WHERE c.id = x.company_id"
    )
    env.invalidate_all()
