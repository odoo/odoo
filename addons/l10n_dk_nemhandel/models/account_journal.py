from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_dk_nemhandel_proxy_state = fields.Selection(related='company_id.l10n_dk_nemhandel_proxy_state')
    is_nemhandel_journal = fields.Boolean(string='Journal used for Nemhandel')

    def nemhandel_get_new_documents(self):
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'nemhandel'),
        ])
        edi_users._nemhandel_get_new_documents()

    def nemhandel_get_message_status(self):
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'nemhandel'),
        ])
        edi_users._nemhandel_get_message_status()
