# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()
        sale_journals = self.filtered(lambda journal: journal.company_id.l10n_in_edi_feature and journal.type == 'sale')
        sale_journals._fill_dashboard_data_count(dashboard_data, 'account.move', 'l10n_in_edi_to_send_count', [('l10n_in_edi_status', '=', 'to_send')])
        return dashboard_data

    def action_l10n_in_einvoice_open_pending(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Invoices to send for E-Invoicing"),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('journal_id', '=', self.id),
                ('l10n_in_edi_status', '=', 'to_send'),
            ],
            'context': {'create': False},
        }
