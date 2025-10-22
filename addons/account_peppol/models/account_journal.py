from odoo import _, fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state')
    is_peppol_journal = fields.Boolean(string="Account used for Peppol", default=False)

    @api.depends('account_peppol_proxy_state')
    def _compute_show_refresh_out_einvoices_status_button(self):
        # EXTENDS 'account'
        super()._compute_show_refresh_out_einvoices_status_button()
        sender_states = self.env['account_edi_proxy_client.user']._get_can_send_domain()

        self.filtered(lambda j: (
            j.account_peppol_proxy_state in sender_states
            and (
                j.type == 'sale'
                or (
                    j.type == 'purchase'
                    and j.is_self_billing
                    and j.company_id.peppol_activate_self_billing_sending
                )
            )
        )).show_refresh_out_einvoices_status_button = True

    @api.depends('is_peppol_journal', 'account_peppol_proxy_state')
    def _compute_show_fetch_in_einvoices_button(self):
        # EXTENDS 'account'
        super()._compute_show_fetch_in_einvoices_button()

        self.filtered(lambda j: (
            j.is_peppol_journal
            and j.account_peppol_proxy_state == 'receiver'
            and j.type == 'purchase'
            and not j.is_self_billing
        )).show_fetch_in_einvoices_button = True

    def button_fetch_in_einvoices(self):
        # EXTENDS 'account'
        super().button_fetch_in_einvoices()
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'receiver'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'peppol')
        ])
        edi_users._peppol_get_new_documents()

    def button_refresh_out_einvoices_status(self):
        # EXTENDS 'account'
        super().button_refresh_out_einvoices_status()
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', 'in', can_send),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'peppol')
        ])
        edi_users._peppol_get_message_status()
