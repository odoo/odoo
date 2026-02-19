from odoo import _, api, models
from odoo.exceptions import RedirectWarning


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.depends('is_nilvera_journal', 'l10n_tr_nilvera_api_key', 'type')
    def _compute_show_fetch_in_einvoices_button(self):
        # EXTENDS 'account'
        super()._compute_show_fetch_in_einvoices_button()
        self.filtered(
            lambda j: j.is_nilvera_journal and
                      j.type == 'purchase'
        ).show_fetch_in_einvoices_button = True

    @api.depends('l10n_tr_nilvera_api_key', 'type')
    def _compute_show_refresh_out_einvoices_status_button(self):
        # EXTENDS 'account'
        super()._compute_show_refresh_out_einvoices_status_button()
        self.filtered(
            lambda j: j.type == 'sale'
        ).show_refresh_out_einvoices_status_button = True

    def button_fetch_in_einvoices(self):
        # EXTENDS 'account'
        """ Fetches bills from Nilvera."""
        self._check_api_key()
        super().button_fetch_in_einvoices()
        self.env['account.move']._cron_nilvera_get_new_einvoice_purchase_documents()

    def button_refresh_out_einvoices_status(self):
        # EXTENDS 'account'
        self._check_api_key()
        super().button_refresh_out_einvoices_status()
        self.env['account.move']._cron_nilvera_get_invoice_status()

    def _check_api_key(self):
        if self.sudo().filtered(lambda j: not j.l10n_tr_nilvera_api_key):
            raise RedirectWarning(
                _("Please configure your Nilvera API key"),
                self.env.ref('account.action_account_config').id,
                _("Go to the Accounting Settings")
            )
