# -*- coding: utf-8 -*-

from datetime import timedelta, datetime
import calendar
import time
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


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
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
        ], default='round_per_line', string='Tax Calculation Rounding Method',
        help="If you select 'Round per Line' : for each tax, the tax amount will first be computed and rounded for each PO/SO/invoice line and then these rounded amounts will be summed, leading to the total amount for that tax. If you select 'Round Globally': for each tax, the tax amount will be computed for each PO/SO/invoice line, then these amounts will be summed and eventually this total tax amount will be rounded. If you sell with tax included, you should choose 'Round per line' because you certainly want the sum of your tax-included line subtotals to be equal to the total amount with taxes.")
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
    def _check_lock_dates(self, vals):
        '''Check the lock dates for the current companies. This can't be done in a api.constrains because we need
        to perform some comparison between new/old values. This method forces the lock dates to be irreversible.

        * You cannot define stricter conditions on advisors than on users. Then, the lock date on advisor must be set
        after the lock date for users.
        * You cannot lock a period that is not finished yet. Then, the lock date for advisors must be set after the
        last day of the previous month.
        * The new lock date for advisors must be set after the previous lock date.

        :param vals: The values passed to the write method.
        '''
        period_lock_date = vals.get('period_lock_date') and\
            time.strptime(vals['period_lock_date'], DEFAULT_SERVER_DATE_FORMAT)
        fiscalyear_lock_date = vals.get('fiscalyear_lock_date') and\
            time.strptime(vals['fiscalyear_lock_date'], DEFAULT_SERVER_DATE_FORMAT)

        previous_month = datetime.strptime(fields.Date.today(), DEFAULT_SERVER_DATE_FORMAT) + relativedelta(months=-1)
        days_previous_month = calendar.monthrange(previous_month.year, previous_month.month)
        previous_month = previous_month.replace(day=days_previous_month[1]).timetuple()
        for company in self:
            old_fiscalyear_lock_date = company.fiscalyear_lock_date and\
                time.strptime(company.fiscalyear_lock_date, DEFAULT_SERVER_DATE_FORMAT)

            # The user attempts to remove the lock date for advisors
            if old_fiscalyear_lock_date and not fiscalyear_lock_date and 'fiscalyear_lock_date' in vals:
                raise ValidationError(_('The lock date for advisors is irreversible and can\'t be removed.'))

            # The user attempts to set a lock date for advisors prior to the previous one
            if old_fiscalyear_lock_date and fiscalyear_lock_date and fiscalyear_lock_date < old_fiscalyear_lock_date:
                raise ValidationError(_('The new lock date for advisors must be set after the previous lock date.'))

            # In case of no new fiscal year in vals, fallback to the oldest
            if not fiscalyear_lock_date:
                if old_fiscalyear_lock_date:
                    fiscalyear_lock_date = old_fiscalyear_lock_date
                else:
                    continue

            # The user attempts to set a lock date for advisors prior to the last day of previous month
            if fiscalyear_lock_date > previous_month:
                raise ValidationError(_('You cannot lock a period that is not finished yet. Please make sure that the lock date for advisors is not set after the last day of the previous month.'))

            # In case of no new period lock date in vals, fallback to the one defined in the company
            if not period_lock_date:
                if company.period_lock_date:
                    period_lock_date = time.strptime(company.period_lock_date, DEFAULT_SERVER_DATE_FORMAT)
                else:
                    continue

            # The user attempts to set a lock date for advisors prior to the lock date for users
            if period_lock_date < fiscalyear_lock_date:
                raise ValidationError(_('You cannot define stricter conditions on advisors than on users. Please make sure that the lock date on advisor is set before the lock date for users.'))

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
            # FORWARD-PORT UP TO v11
            if last_month == 2 and last_day == 29 and date.year % 4 != 0:
                date = date.replace(month=last_month, day=28)
            else:
                date = date.replace(month=last_month, day=last_day)
        else:
            if last_month == 2 and last_day == 29 and (date.year + 1) % 4 != 0:
                date = date.replace(month=last_month, day=28, year=date.year + 1)
            else:
                date = date.replace(month=last_month, day=last_day, year=date.year + 1)
        date_to = date
        date_from = date + timedelta(days=1)
        if date_from.month == 2 and date_from.day == 29:
            date_from = date_from.replace(day=28, year=date_from.year - 1)
        else:
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

            #forbid the change of currency_id if there are already some accounting entries existing
            if 'currency_id' in values and values['currency_id'] != company.currency_id.id:
                if self.env['account.move.line'].search([('company_id', '=', company.id)]):
                    raise UserError(_('You cannot change the currency of the company since some journal items already exist'))

        return super(ResCompany, self).write(values)
