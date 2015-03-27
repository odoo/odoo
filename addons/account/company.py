# -*- coding: utf-8 -*-

from openerp import fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    fiscalyear_last_day = fields.Integer(default=31)
    fiscalyear_last_month = fields.Selection([(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], default=12)
    period_lock_date = fields.Date(help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this date")
    fiscalyear_lock_date = fields.Date(string="Fiscal Year lock date", help="No users, including Advisers, can edit accounts prior to and inclusive of this date")
    transfer_account_id = fields.Many2one('account.account',
        domain=lambda self: [('reconcile', '=', True), ('user_type.id', '=', self.env.ref('account.data_account_type_current_assets').id), ('deprecated', '=', False)],
        help="Intermediary account used when moving money from a liquidity account to another")
    expects_chart_of_accounts = fields.Boolean(string='Expects a Chart of Accounts', default=True)
    bank_account_code_char = fields.Char(string='Code of the main bank account')
    accounts_code_digits = fields.Integer(string='Number of digits in an account code')
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
        ], default='round_per_line', string='Tax Calculation Rounding Method',
        help="If you select 'Round per Line' : for each tax, the tax amount will first be computed and rounded for each PO/SO/invoice line and then these rounded amounts will be summed, leading to the total amount for that tax. If you select 'Round Globally': for each tax, the tax amount will be computed for each PO/SO/invoice line, then these amounts will be summed and eventually this total tax amount will be rounded. If you sell with tax included, you should choose 'Round per line' because you certainly want the sum of your tax-included line subtotals to be equal to the total amount with taxes.")
    paypal_account = fields.Char(string='Paypal Account', size=128, help="Paypal username (usually email) for receiving online payments.")
    days_between_two_followups = fields.Integer(string='Number of days between two follow-ups', default=14)
    overdue_msg = fields.Text(string='Overdue Payments Message', translate=True,
        default='''Dear Sir/Madam,

Our records indicate that some payments on your account are still due. Please find details below.
If the amount has already been paid, please disregard this notice. Otherwise, please forward us the total amount stated below.
If you have any queries regarding your account, Please contact us.

Thank you in advance for your cooperation.
Best Regards,''')

    def _create_bank_account_and_journal(self, account_number, currency_id=None):
        """ Create a journal and its account """
        MultiChartsAccounts = self.env['wizard.multi.charts.accounts']

        if currency_id is None:
            currency_id = self.currency_id

        vals_account = {'currency_id': currency_id, 'acc_name': account_number, 'account_type': 'bank', 'currency_id': currency_id}
        vals_account = MultiChartsAccounts._prepare_bank_account(self, vals_account)
        account_id = self.env['account.account'].create(vals_account).id

        vals_journal = {'currency_id': currency_id, 'acc_name': _('Bank') + ' ' + account_number, 'account_type': 'bank'}
        vals_journal = MultiChartsAccounts._prepare_bank_journal(self, vals_journal, account_id)
        return self.env['account.journal'].create(vals_journal).id
