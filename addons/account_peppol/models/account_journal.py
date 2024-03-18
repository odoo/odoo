from odoo import _, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state')
    is_peppol_journal = fields.Boolean(string="Account used for Peppol", default=False)

    def peppol_get_new_documents(self):
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'receiver'),
            ('company_id', 'in', self.company_id.ids),
        ])
        edi_users._peppol_get_new_documents()

    def peppol_get_message_status(self):
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', 'in', can_send),
            ('company_id', 'in', self.company_id.ids),
        ])
        edi_users._peppol_get_message_status()

    def action_peppol_ready_moves(self):
        return {
            'name': _("Peppol Ready invoices"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'context': {
                'search_default_peppol_ready': 1,
            }
        }
