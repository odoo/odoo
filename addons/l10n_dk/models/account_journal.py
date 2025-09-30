from odoo import Command, api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_dk_nemhandel_proxy_state = fields.Selection(related='company_id.l10n_dk_nemhandel_proxy_state')
    is_nemhandel_journal = fields.Boolean(string='Journal used for Nemhandel')

    @api.depends('l10n_dk_nemhandel_proxy_state')
    def _compute_show_refresh_out_einvoices_status_button(self):
        # EXTENDS 'account'
        super()._compute_show_refresh_out_einvoices_status_button()
        self.filtered(lambda j: j.l10n_dk_nemhandel_proxy_state == 'receiver' and j.type == 'sale').show_refresh_out_einvoices_status_button = True

    @api.depends('is_nemhandel_journal', 'l10n_dk_nemhandel_proxy_state')
    def _compute_show_fetch_in_einvoices_button(self):
        # EXTENDS 'account'
        super()._compute_show_fetch_in_einvoices_button()

        self.filtered(lambda j: j.is_nemhandel_journal and j.l10n_dk_nemhandel_proxy_state == 'receiver' and j.type == 'purchase').show_fetch_in_einvoices_button = True

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        # OVERRIDE
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)

        if company.account_fiscal_country_id.code == 'DK':
            # Ensure the newly liquidity accounts have the right account tag in order to be part
            # of the Danish financial reports.
            account_vals.setdefault('tag_ids', [])
            if vals.get('type') == 'bank':
                account_vals['tag_ids'].append(Command.link(self.env.ref('l10n_dk.account_tag_6481').id))
            elif vals.get('type') == 'cash':
                account_vals['tag_ids'].append(Command.link(self.env.ref('l10n_dk.account_tag_6471').id))

        return account_vals

    def button_fetch_in_einvoices(self):
        # EXTENDS 'account'
        super().button_fetch_in_einvoices()
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'nemhandel'),
        ])
        edi_users._nemhandel_get_new_documents()

    def button_refresh_out_einvoices_status(self):
        # EXTENDS 'account'
        super().button_refresh_out_einvoices_status()
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'nemhandel'),
        ])
        edi_users._nemhandel_get_message_status()
