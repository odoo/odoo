from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def peppol_get_new_documents(self):
        """
        Extend to also fetch regulatory messages (exchanged with the PPF).
        This also includes outgoing messages sent by the user (i.e. to update the status in case of a sending error).
        """
        super().peppol_get_new_documents()
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'receiver'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'pdp'),
        ])
        edi_users._pdp_get_regulatory_documents()
