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
    journal_ids = fields.Many2many('account.journal', 'account_partner_ledger_journal_rel', 'account_id', 'journal_id', string='Journals', required=True)

    @api.onchange('filter', 'fiscalyear_id')
    def onchange_filter(self):
        res = super(account_partner_ledger, self).onchange_filter()
        if self.filter in ['filter_no', 'unreconciled']:
            if self.filter == 'unreconciled':
                self.fiscalyear_id = False
            self.initial_balance = False

    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'filter', 'page_split', 'amount_currency'])[0])
        if data['form'].get('page_split') is True: 
            return self.env['report'].get_action(self.env['account.partner.ledger'], 'account.report_partnerledgerother', data=data)
        return self.env['report'].get_action(self.env['account.partner.ledger'], 'account.report_partnerledger', data=data)
