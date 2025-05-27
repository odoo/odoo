from odoo import _, api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    zatca_format = env.ref('l10n_sa_edi.edi_sa_zatca')
    journals = env["account.journal"].search([
        ("edi_format_ids", "in", zatca_format.id),
        ("l10n_sa_compliance_checks_passed", "=", True),
        ("l10n_sa_production_csid_json", "!=", False)])
    journals.activity_schedule(
        act_type_xmlid='mail.mail_activity_data_warning',
        user_id=env.ref("base.user_admin").id,
        note=_('Please Re-Onboard the Journal for a new serial number'))
