# -*- coding: utf-8 -*-
import time

from odoo import api, _, models, Command


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = {
            'account.journal': {},
            **super()._get_demo_data(company),
        }
        demo_data['account.journal'].update({
            'auto_transfer_journal': {
                'name': _("IFRS Automatic Transfers"),
                'code': "IFRSA",
                'type': 'general',
                'show_on_dashboard': False,
                'sequence': 1000,
            },
        })
        demo_data['account.transfer.model'] = {
            'monthly_model': {
                'name': _("IFRS rent expense transfer"),
                'date_start': time.strftime('%Y-01-01'),
                'frequency': 'month',
                'journal_id': 'auto_transfer_journal',
                'account_ids': [self._get_demo_account('expense_rent', 'expense', company).id],
                'line_ids': [
                    Command.create({
                        'account_id': self._get_demo_account('expense_rd', 'expense', company).id,
                        'percent': 35.0,
                    }),
                    Command.create({
                        'account_id': self._get_demo_account('expense_sales', 'expense_direct_cost', company).id,
                        'percent': 65.0,
                    }),
                ],
            },
            'yearly_model': {
                'name': _("Yearly liabilites auto transfers"),
                'date_start': time.strftime('%Y-01-01'),
                'frequency': 'year',
                'journal_id': 'auto_transfer_journal',
                'account_ids': [Command.set([
                    self._get_demo_account('current_liabilities', 'liability_current', company).id,
                    self._get_demo_account('payable', 'liability_payable', company).id
                ])],
                'line_ids': [
                    Command.create({
                        'account_id': self._get_demo_account('payable', 'liability_payable', company).id,
                        'percent': 77.5,
                    }),
                    Command.create({
                        'account_id': self._get_demo_account('non_current_liabilities', 'liability_non_current', company).id,
                        'percent': 22.5,
                    }),
                ],
            },
        }
        return demo_data
