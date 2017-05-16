# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class ResCompany(models.Model):
    _inherit = "res.company"

    #TODO check all the options/fields are in the views (settings + company form view)
    fiscalyear_last_day = fields.Integer(default=31, required=True)
    fiscalyear_last_month = fields.Selection([(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], default=12, required=True)
    period_lock_date = fields.Date(string="Lock Date for Non-Advisers", help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this date. Use it for period locking inside an open fiscal year, for example.")
    fiscalyear_lock_date = fields.Date(string="Lock Date", help="No users, including Advisers, can edit accounts prior to and inclusive of this date. Use it for fiscal year locking for example.")
    transfer_account_id = fields.Many2one('account.account',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id), ('deprecated', '=', False)], string="Inter-Banks Transfer Account", help="Intermediary account used when moving money from a liquidity account to another")
    expects_chart_of_accounts = fields.Boolean(string='Expects a Chart of Accounts', default=True)
    chart_template_id = fields.Many2one('account.chart.template', help='The chart template for the company (if any)')
    bank_account_code_prefix = fields.Char(string='Prefix of the bank accounts', oldname="bank_account_code_char")
    cash_account_code_prefix = fields.Char(string='Prefix of the cash accounts')
    accounts_code_digits = fields.Integer(string='Number of digits in an account code')
    tax_cash_basis_journal_id = fields.Many2one('account.journal', string="Cash Basis Journal")
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
        ], default='round_per_line', string='Tax Calculation Rounding Method')
    currency_exchange_journal_id = fields.Many2one('account.journal', string="Exchange Gain or Loss Journal", domain=[('type', '=', 'general')])
    income_currency_exchange_account_id = fields.Many2one('account.account', related='currency_exchange_journal_id.default_credit_account_id',
        string="Gain Exchange Rate Account", domain="[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', id)]")
    expense_currency_exchange_account_id = fields.Many2one('account.account', related='currency_exchange_journal_id.default_debit_account_id',
        string="Loss Exchange Rate Account", domain="[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', id)]")
    anglo_saxon_accounting = fields.Boolean(string="Use anglo-saxon accounting")
    property_stock_account_input_categ_id = fields.Many2one('account.account', string="Input Account for Stock Valuation", oldname="property_stock_account_input_categ")
    property_stock_account_output_categ_id = fields.Many2one('account.account', string="Output Account for Stock Valuation", oldname="property_stock_account_output_categ")
    property_stock_valuation_account_id = fields.Many2one('account.account', string="Account Template for Stock Valuation")
    bank_journal_ids = fields.One2many('account.journal', 'company_id', domain=[('type', '=', 'bank')], string='Bank Journals')
    overdue_msg = fields.Text(string='Overdue Payments Message', translate=True,
        default='''Dear Sir/Madam,

Our records indicate that some payments on your account are still due. Please find details below.
If the amount has already been paid, please disregard this notice. Otherwise, please forward us the total amount stated below.
If you have any queries regarding your account, Please contact us.

Thank you in advance for your cooperation.
Best Regards,''')

    @api.multi
    def compute_fiscalyear_dates(self, date):
        """ Computes the start and end dates of the fiscalyear where the given 'date' belongs to
            @param date: a datetime object
            @returns: a dictionary with date_from and date_to
        """
        self = self[0]
        last_month = self.fiscalyear_last_month
        last_day = self.fiscalyear_last_day
        if (date.month < last_month or (date.month == last_month and date.day <= last_day)):
            date = date.replace(month=last_month, day=last_day)
        else:
            date = date.replace(month=last_month, day=last_day, year=date.year + 1)
        date_to = date
        date_from = date + timedelta(days=1)
        date_from = date_from.replace(year=date_from.year - 1)
        return {'date_from': date_from, 'date_to': date_to}

    def get_new_account_code(self, current_code, old_prefix, new_prefix, digits):
        return new_prefix + current_code.replace(old_prefix, '', 1).lstrip('0').rjust(digits-len(new_prefix), '0')

    def reflect_code_prefix_change(self, old_code, new_code, digits):
        accounts = self.env['account.account'].search([('code', 'like', old_code), ('internal_type', '=', 'liquidity'),
            ('company_id', '=', self.id)], order='code asc')
        for account in accounts:
            if account.code.startswith(old_code):
                account.write({'code': self.get_new_account_code(account.code, old_code, new_code, digits)})

    def reflect_code_digits_change(self, digits):
        accounts = self.env['account.account'].search([('company_id', '=', self.id)], order='code asc')
        for account in accounts:
            account.write({'code': account.code.rstrip('0').ljust(digits, '0')})

    @api.multi
    def _validate_fiscalyear_lock(self, values):
        if values.get('fiscalyear_lock_date'):
            nb_draft_entries = self.env['account.move'].search([
                ('company_id', 'in', [c.id for c in self]),
                ('state', '=', 'draft'),
                ('date', '<=', values['fiscalyear_lock_date'])])
            if nb_draft_entries:
                raise ValidationError(_('There are still unposted entries in the period you want to lock. You should either post or delete them.'))

    @api.multi
    def write(self, values):
        #restrict the closing of FY if there are still unposted entries
        self._validate_fiscalyear_lock(values)

        # Reflect the change on accounts
        for company in self:
            digits = values.get('accounts_code_digits') or company.accounts_code_digits
            if values.get('bank_account_code_prefix') or values.get('accounts_code_digits'):
                new_bank_code = values.get('bank_account_code_prefix') or company.bank_account_code_prefix
                company.reflect_code_prefix_change(company.bank_account_code_prefix, new_bank_code, digits)
            if values.get('cash_account_code_prefix') or values.get('accounts_code_digits'):
                new_cash_code = values.get('cash_account_code_prefix') or company.cash_account_code_prefix
                company.reflect_code_prefix_change(company.cash_account_code_prefix, new_cash_code, digits)
            if values.get('accounts_code_digits'):
                company.reflect_code_digits_change(digits)
        return super(ResCompany, self).write(values)
