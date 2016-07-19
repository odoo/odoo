# -*- coding: utf-8 -*-

from openerp import models, api, _

class account_journal(models.Model):
    _inherit = "account.journal"

    @api.multi
    def get_journal_dashboard_datas(self):
        domain_checks_to_print = [
            ('journal_id', '=', self.id),
            ('payment_method_id.code', '=', 'check_printing'),
            ('state','=','posted')
        ]
        return dict(
            super(account_journal, self).get_journal_dashboard_datas(),
            num_checks_to_print=len(self.env['account.payment'].search(domain_checks_to_print))
        )

    @api.multi
    def action_checks_to_print(self):
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
                default_payment_method_id=self.env.ref('account_check_printing.account_payment_method_check').id,
            ),
        }
