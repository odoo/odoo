from odoo import _, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def button_fetch_in_einvoices(self):
        """
        Extend to also fetch regulatory messages (exchanged with the PPF).
        This also includes outgoing messages sent by the user (i.e. to update the status in case of a sending error).
        """
        super().button_fetch_in_einvoices()
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'receiver'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'pdp'),
        ])
        edi_users._pdp_get_regulatory_documents()

    def _get_onboarding_action_data(self):
        if self.country_code != 'FR' and self.company_id.peppol_eas != '0225':
            return super()._get_onboarding_action_data()
        pdp_setup_wizard = self.env['pdp.registration'].create({'company_id': self.company_id.id})
        pdp_action = pdp_setup_wizard._get_records_action(target='new', name=_("Activate Electronic Invoicing"))
        return {
            'title': _("Activate Electronic Invoicing"),
            'action': pdp_action,
        }
