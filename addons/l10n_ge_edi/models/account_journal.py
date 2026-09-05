from odoo import api, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.depends("type", "company_id.l10n_ge_edi_user_id")
    def _compute_show_refresh_out_einvoices_status_button(self):
        # EXTENDS 'account'
        super()._compute_show_refresh_out_einvoices_status_button()
        self.filtered(
            lambda j: j.type == "sale" and j.company_id.sudo().l10n_ge_edi_user_id,
        ).show_refresh_out_einvoices_status_button = True

    def button_refresh_out_einvoices_status(self):
        # EXTENDS 'account'
        super().button_refresh_out_einvoices_status()
        self.env["account.move"]._l10n_ge_edi_refresh_all_statuses()
