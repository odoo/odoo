from odoo import _, api, SUPERUSER_ID
from odoo.exceptions import UserError


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    zatca_format = env.ref('l10n_sa_edi.edi_sa_zatca')
    journals = env["account.journal"].search([
        ("edi_format_ids", "in", zatca_format.id),
        ("l10n_sa_compliance_checks_passed", "=", True),
        ("l10n_sa_production_csid_json", "!=", False)])

    journals_to_schedule = journals_to_reonboard = env["account.journal"]
    for journal in journals:
        try:
            journal._l10n_sa_api_onboard_sanity_checks()
            journals_to_reonboard += journal
        except UserError:
            journals_to_schedule += journal

    journals_to_schedule.activity_schedule(
        act_type_xmlid='mail.mail_activity_data_warning',
        user_id=env.ref("base.user_admin").id,
        note=_('Failed to Re-Onboard Journal: Kindly post all invoices to ZATCA and re-onboard the journal'))

    journals_to_reonboard._l10n_sa_reset_certificates()
