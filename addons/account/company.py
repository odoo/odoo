# -*- coding: utf-8 -*-

from openerp import fields, models, api, _
from datetime import timedelta


class ResCompany(models.Model):
    _inherit = "res.company"

    #TODO check all the options/fields are in the views (settings + company form view)
    #TODO: add a cash_register_code_char for allowing cash journals' accounts having a different numbering than bank journals' accounts.
    fiscalyear_last_day = fields.Integer(default=31, required=True)
    fiscalyear_last_month = fields.Selection([(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], default=12, required=True)
    period_lock_date = fields.Date(help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this date")
    fiscalyear_lock_date = fields.Date(string="Fiscal Year lock date", help="No users, including Advisers, can edit accounts prior to and inclusive of this date")
    transfer_account_id = fields.Many2one('account.account',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id), ('deprecated', '=', False)], string="Transfer Account", help="Intermediary account used when moving money from a liquidity account to another")
    expects_chart_of_accounts = fields.Boolean(string='Expects a Chart of Accounts', default=True)
    chart_template_id = fields.Many2one('account.chart.template', help='The chart template for the company (if any)')
    bank_account_code_char = fields.Char(string='Code of the main bank account')
    accounts_code_digits = fields.Integer(string='Number of digits in an account code')
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
        ], default='round_per_line', string='Tax Calculation Rounding Method',
        help="If you select 'Round per Line' : for each tax, the tax amount will first be computed and rounded for each PO/SO/invoice line and then these rounded amounts will be summed, leading to the total amount for that tax. If you select 'Round Globally': for each tax, the tax amount will be computed for each PO/SO/invoice line, then these amounts will be summed and eventually this total tax amount will be rounded. If you sell with tax included, you should choose 'Round per line' because you certainly want the sum of your tax-included line subtotals to be equal to the total amount with taxes.")
    paypal_account = fields.Char(string='Paypal Account', size=128, help="Paypal username (usually email) for receiving online payments.")
    currency_exchange_journal_id = fields.Many2one('account.journal', string="Currency Adjustments Journal", domain=[('type', '=', 'general')])
    income_currency_exchange_account_id = fields.Many2one('account.account', related='currency_exchange_journal_id.default_credit_account_id',
        string="Gain Exchange Rate Account", domain="[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', id)]")
    expense_currency_exchange_account_id = fields.Many2one('account.account', related='currency_exchange_journal_id.default_debit_account_id',
        string="Loss Exchange Rate Account", domain="[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', id)]")
    anglo_saxon_accounting = fields.Boolean(string="Use anglo-saxon accounting")
    property_stock_account_input_categ_id = fields.Many2one('account.account', oldname="property_stock_account_input_categ")
    property_stock_account_output_categ_id = fields.Many2one('account.account', oldname="property_stock_account_output_categ")
    property_stock_valuation_account_id = fields.Many2one('account.account')

    @api.multi
    def compute_fiscalyear_dates(self, date):
        """ Computes the start and end dates of the fiscalyear where the given 'date' belongs to
            @param date: a datetime object
            @returns: a dictionary with date_from and date_to
        """
        self = self[0]
        last_month = self.fiscalyear_last_month
        last_day = self.fiscalyear_last_day
        if (date.month < last_month or (date.month == last_month and date.date <= last_day)):
            date = date.replace(month=last_month, day=last_day)
        else:
            date = date.replace(month=last_month, day=last_day, year=date.year + 1)
        date_to = date
        date_from = date + timedelta(days=1)
        date_from = date_from.replace(year=date_from.year - 1)
        return {'date_from': date_from, 'date_to': date_to}

    def get_new_account_code(self, code, old_prefix, new_prefix, digits):
        new_prefix_length = len(new_prefix)
        number = str(int(code[len(old_prefix):]))
        code = new_prefix + str('0' * (digits - new_prefix_length - len(number))) + number
        return code

    @api.multi
    def write(self, values):
        # Repercute the change on accounts
        if values.get('bank_account_code_char', False) or values.get('accounts_code_digits', False):
            bank_code = values.get('bank_account_code_char', False) or self.bank_account_code_char
            digits = values.get('accounts_code_digits', False) or self.accounts_code_digits

            accounts = self.env['account.account'].search([('code', 'like', self.bank_account_code_char), ('internal_type', '=', 'liquidity'), 
                ('company_id', '=', self.id)], order='code asc')
            for account in accounts:
                if account.code.startswith(self.bank_account_code_char):
                    account.write({'code': self.get_new_account_code(account.code, self.bank_account_code_char, bank_code, digits)})
        return super(ResCompany, self).write(values)
