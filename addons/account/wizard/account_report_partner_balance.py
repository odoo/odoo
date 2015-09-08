# -*- coding: utf-8 -*-

from openerp import fields, models


class AccountPartnerBalance(models.TransientModel):
    """
        This wizard will provide the partner balance report between any two dates.
    """
    _inherit = 'account.common.partner.report'
    _name = 'account.partner.balance'
    _description = 'Print Account Partner Balance'

    display_partner = fields.Selection([('non-zero_balance', 'With balance is not equal to 0'), ('all', 'All Partners')]
                                    , string='Display Partners', default='non-zero_balance')
    journal_ids = fields.Many2many('account.journal', sting='Journals', required=True)

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['display_partner'])[0])
        return self.env['report'].get_action(self, 'account.report_partnerbalance', data=data)
