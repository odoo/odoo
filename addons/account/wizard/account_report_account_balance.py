from openerp import models, api


class account_balance_report(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = 'account.balance.report'
    _description = 'Trial Balance Report'

    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)

    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        return self.env['report'].get_action([], 'account.report_trialbalance', data=data)

