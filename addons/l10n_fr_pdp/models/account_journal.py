from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def button_fetch_in_einvoices(self):
        """
        Extend to also fetch regulatory messages (exchanged with the PPF).
        This also includes outgoing messages sent by the user (i.e. to update the status in case of a sending error).
        """
        # The generic Peppol fetch runs before the PPF fetch. Share the same
        # collector so a PPF status replaces the intermediate PA status.
        chatter_messages = {}
        journals = self.with_context(pdp_einvoicing_chatter_messages=chatter_messages)
        super(AccountJournal, journals).button_fetch_in_einvoices()
        edi_users = journals.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'receiver'),
            ('company_id', 'in', journals.company_id.ids),
            ('proxy_type', '=', 'pdp'),
        ])
        edi_users._pdp_get_regulatory_documents()

    def _get_onboarding_action_data(self):
        if not self.company_id._peppol_is_french_company():
            return super()._get_onboarding_action_data()
        if self.company_id.account_peppol_proxy_state == 'not_registered':
            return {
                'title': self.env._("Activate Electronic Invoicing"),
                'action': self.company_id._action_open_pdp_form(),
            }
        return {
            'title': self.env._("Electronic Invoicing Settings"),
            'action': self.env.ref('account.action_account_config')._get_action_dict(),
        }
