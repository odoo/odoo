from odoo import api, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.depends('type', 'company_id')
    def _compute_show_fetch_in_einvoices_button(self):
        # EXTENDS 'account'
        super()._compute_show_fetch_in_einvoices_button()
        self.filtered(lambda j: j.type == 'purchase' and j.company_id.sudo().l10n_pl_edi_access_token).show_fetch_in_einvoices_button = True

    def button_fetch_in_einvoices(self):
        # EXTENDS 'account'
        super().button_fetch_in_einvoices()
        self.env['account.move'].with_company(self.company_id)._l10n_pl_edi_download_bills_from_ksef()
