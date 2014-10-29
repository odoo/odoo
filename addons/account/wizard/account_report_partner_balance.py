from openerp import models, api


class account_partner_balance(models.TransientModel):
    """
        This wizard will provide the partner balance report by periods, between any two dates.
    """
    _inherit = 'account.common.partner.report'
    _name = 'account.partner.balance'
    _description = 'Print Account Partner Balance'

    display_partner = fields.Selection([('non-zero_balance', 'Display partners with balance is not equal to 0'), ('all', 'Display all partners')],
        default='non-zero_balance' ,string='Display Partners')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)

    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(self.ids, ['display_partner'])[0])
        return self.pool['report'].get_action([], 'account.report_partnerbalance', data=data)
