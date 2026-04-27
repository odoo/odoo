# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_in_gstr_activate_einvoice_fetch = fields.Selection(related="company_id.l10n_in_gstr_activate_einvoice_fetch")

    def l10n_in_action_fetch_irn_data_for_account_journal(self):
        """ Fetch the GST return period for the current company and return the corresponding form view. """
        process_return_period = self.env['l10n_in.gst.return.period']._get_gst_return_period(self.company_id, create_if_not_found=True)
        return process_return_period.open_gst_return_period_form_view()
