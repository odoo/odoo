# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()
        self._fill_dashboard_data_count(dashboard_data, 'account.payment', 'num_checks_to_print', [
            ('payment_method_id.code', '=', 'check_printing'),
            ('state', '=', 'in_process'),
            ('is_sent', '=', False),
        ])
        return dashboard_data

    def action_checks_to_print(self):
        payment_method = self.env['account.payment.method'].search([
            ('code', '=', 'check_printing'),
            ('company_id', '=', self.env.company.id),
        ])
        return {
            'name': _('Checks to Print'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form,graph',
            'res_model': 'account.payment',
            'context': dict(
                self.env.context,
                search_default_checks_to_send=1,
                journal_id=self.id,
                default_journal_id=self.id,
                default_payment_type='outbound',
                default_payment_method_id=payment_method.id,
            ),
        }
