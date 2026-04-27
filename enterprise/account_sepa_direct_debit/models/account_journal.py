# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    debit_sepa_pain_version = fields.Selection(
        [
            ('pain.008.001.02', 'Default (Pain 008.001.02)'),
            ('pain.008.001.08', 'Updated 2023 (Pain 008.001.08)'),
        ],
        required=True,
        string='SEPA Direct Debit Pain Version',
        default='pain.008.001.02',
    )

    def _default_inbound_payment_methods(self):
        res = super()._default_inbound_payment_methods()
        if self._is_payment_method_available('sdd'):
            res |= self.env.ref('account_sepa_direct_debit.payment_method_sdd')
        return res

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()
        self._fill_dashboard_data_count(dashboard_data, 'account.payment', 'sdd_payments_to_send_number', [
            ('payment_method_code', 'in', self.env['account.payment.method']._get_sdd_payment_method_code()),
            ('state', '=', 'in_process'),
            ('is_sent', '=', False),
            ('is_matched', '=', False),
        ])
        return dashboard_data

    def open_sdd_payments(self):
        # return action 'Direct debit payments to collect' with context forged
        ctx = self._context.copy()
        ctx.update({'default_journal_id': self.id, 'search_default_journal_id': self.id})
        action = self.env['ir.actions.act_window']._for_xml_id('account_sepa_direct_debit.action_sdd_payments_to_collect')
        action.update({'context': ctx})
        return action
