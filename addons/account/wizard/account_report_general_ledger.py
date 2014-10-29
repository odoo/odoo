from openerp import models, api


class account_report_general_ledger(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    landscape = fields.Boolean(string='Landscape Mode', default=True)
    initial_balance = fields.Boolean(string='Include Initial Balances', default=False,
        help='''If you selected to filter by date or period, this field allow you to add a 
        row to display the amount of debit/credit/balance that precedes the filter you\'ve set.''')
    amount_currency = fields.Boolean(string='With Currency', default=True,
        help="It adds the currency column on report if the currency differs from the company currency.")
    sortby = fields.Selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string='Sort by', required=True, default='sort_date')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)

    @api.multi
    def onchange_fiscalyear(self, fiscalyear=False):
        res = {}
        if not fiscalyear:
            res['value'] = {'initial_balance': False}
        return res

    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(self.ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby'])[0])
        if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
            data['form'].update({'initial_balance': False})

        if data['form']['landscape'] is False:
            data['form'].pop('landscape')

        return self.env['report'].get_action([], 'account.report_generalledger', data=data)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
