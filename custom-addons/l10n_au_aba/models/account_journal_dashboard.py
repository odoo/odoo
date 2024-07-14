# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class AccountJournalDashboard(models.Model):
    _inherit = "account.journal"

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()
        self._fill_dashboard_data_count(dashboard_data, 'account.payment', 'num_aba_ct_to_send', [
            ('payment_method_id.code', '=', 'aba_ct'),
            ('is_move_sent', '=', False),
            ('is_matched', '=', False),
            ('state', '=', 'posted'),
        ])
        return dashboard_data

    def action_aba_ct_to_send(self):
        payment_method_line = self.outbound_payment_method_line_ids.filtered(lambda l: l.code == 'aba_ct')
        return {
            'name': _('ABA Credit Transfers to Send'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form,graph',
            'res_model': 'account.payment',
            'context': dict(
                self.env.context,
                search_default_aba_to_send=1,
                journal_id=self.id,
                default_journal_id=self.id,
                search_default_journal_id=self.id,
                default_payment_type='outbound',
                default_payment_method_line_id=payment_method_line.id,
            ),
        }
