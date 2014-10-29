from openerp import models, fields, api


class account_partner_ledger(models.TransientModel):
    """
    This wizard will provide the partner Ledger report by periods, between any two dates.
    """
    _name = 'account.partner.ledger'
    _inherit = 'account.common.partner.report'
    _description = 'Account Partner Ledger'

    initial_balance = fields.Boolean(string='Include Initial Balances',
        help='''If you selected to filter by date or period, this field allow you to add a row 
        to display the amount of debit/credit/balance that precedes the filter you\'ve set.''')
    filter = fields.Selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods'), ('unreconciled', 'Unreconciled Entries')],
        string='Filter by', required=True)
    page_split = fields.Boolean(string='One Partner Per Page', help='Display Ledger Report with One partner per page')
    amount_currency = fields.Boolean(string='With Currency',
        help="It adds the currency column on report if the currency differs from the company currency.")
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)

    @api.multi
    def onchange_filter(self, filter='filter_no', fiscalyear_id=False):
        res = super(account_partner_ledger, self).onchange_filter(filter=filter, fiscalyear_id=fiscalyear_id)
        if filter in ['filter_no', 'unreconciled']:
            if filter == 'unreconciled':
                res['value'].update({'fiscalyear_id': False})
            res['value'].update({'initial_balance': False, 'period_from': False, 'period_to': False, 'date_from': False ,'date_to': False})
        return res

    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'filter', 'page_split', 'amount_currency'])[0])
        if data['form'].get('page_split') is True: 
            return self.env['report'].get_action([], 'account.report_partnerledgerother', data=data)
        return self.env['report'].get_action([], 'account.report_partnerledger', data=data)
