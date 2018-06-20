# -*- coding: utf-8 -*-

from datetime import timedelta, datetime
import calendar
import time
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_round, float_is_zero


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
        default=lambda s: _('''Dear Sir/Madam,

Our records indicate that some payments on your account are still due. Please find details below.
If the amount has already been paid, please disregard this notice. Otherwise, please forward us the total amount stated below.
If you have any queries regarding your account, Please contact us.

Thank you in advance for your cooperation.
Best Regards,'''))
    tax_exigibility = fields.Boolean(string='Use Cash Basis')

    #Fields of the setup step for opening move
    account_opening_move_id = fields.Many2one(string='Opening Journal Entry', comodel_name='account.move', help="The journal entry containing the initial balance of all this company's accounts.")
    account_opening_journal_id = fields.Many2one(string='Opening Journal', comodel_name='account.journal', related='account_opening_move_id.journal_id', help="Journal where the opening entry of this company's accounting has been posted.")
    account_opening_date = fields.Date(string='Opening Date', related='account_opening_move_id.date', help="Date at which the opening entry of this company's accounting has been posted.")

    #Fields marking the completion of a setup step
    account_setup_company_data_done = fields.Boolean(string='Company Setup Marked As Done', help="Technical field holding the status of the company setup step.")
    account_setup_bank_data_done = fields.Boolean('Bank Setup Marked As Done', help="Technical field holding the status of the bank setup step.")
    account_setup_fy_data_done = fields.Boolean('Financial Year Setup Marked As Done', help="Technical field holding the status of the financial year setup step.")
    account_setup_coa_done = fields.Boolean(string='Chart of Account Checked', help="Technical field holding the status of the chart of account setup step.")
    account_setup_bar_closed = fields.Boolean(string='Setup Bar Closed', help="Technical field set to True when setup bar has been closed by the user.")

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

    @api.model
    def _verify_fiscalyear_last_day(self, company_id, last_day, last_month):
        company = self.browse(company_id)
        last_day = last_day or (company and company.fiscalyear_last_day) or 31
        last_month = last_month or (company and company.fiscalyear_last_month) or 12
        current_year = datetime.now().year
        last_day_of_month = calendar.monthrange(current_year, last_month)[1]
        return last_day > last_day_of_month and last_day_of_month or last_day

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

    @api.model
    def setting_init_company_action(self):
        """ Called by the 'Company Data' button of the setup bar."""
        company = self.env.user.company_id
        view_id = self.env.ref('account.setup_view_company_form').id
        return {'type': 'ir.actions.act_window',
                'name': _('Company Data'),
                'res_model': 'res.company',
                'target': 'new',
                'view_mode': 'form',
                'res_id': company.id,
                'views': [[view_id, 'form']],
        }

    @api.model
    def setting_init_bank_account_action(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        company = self.env.user.company_id
        view_id = self.env.ref('account.setup_bank_journal_form').id

        res = {
            'type': 'ir.actions.act_window',
            'name': _('Bank Account'),
            'view_mode': 'form',
            'res_model': 'account.journal',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

        # If some bank journal already exists, we open it in the form, so the user can edit it.
        # Otherwise, we just open the form in creation mode.
        bank_journal = self.env['account.journal'].search([('company_id','=', company.id), ('type','=','bank')], limit=1)
        if bank_journal:
            res['res_id'] = bank_journal.id
        else:
            res['context'] = {'default_type': 'bank'}
        return res

    @api.model
    def setting_init_fiscal_year_action(self):
        """ Called by the 'Fiscal Year Opening' button of the setup bar."""
        company = self.env.user.company_id
        new_wizard = self.env['account.financial.year.op'].create({'company_id': company.id})
        view_id = self.env.ref('account.setup_financial_year_opening_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Fiscal Year'),
            'view_mode': 'form',
            'res_model': 'account.financial.year.op',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }

    @api.model
    def setting_chart_of_accounts_action(self):
        """ Called by the 'Chart of Accounts' button of the setup bar."""
        company = self.env.user.company_id
        company.account_setup_coa_done = True

        # If an opening move has already been posted, we open the tree view showing all the accounts
        if company.opening_move_posted():
            return 'account.action_account_form'

        # Otherwise, we create the opening move
        company.create_op_move_if_non_existant()

        # Then, we open will open a custom tree view allowing to edit opening balances of the account
        view_id = self.env.ref('account.init_accounts_tree').id
        # Hide the current year earnings account as it is automatically computed
        domain = [('user_type_id', '!=', self.env.ref('account.data_unaffected_earnings').id), ('company_id','=', company.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Chart of Accounts'),
            'res_model': 'account.account',
            'view_mode': 'tree',
            'search_view_id': self.env.ref('account.view_account_search').id,
            'views': [[view_id, 'list']],
            'domain': domain,
        }

    @api.model
    def setting_opening_move_action(self):
        """ Called by the 'Initial Balances' button of the setup bar."""
        company = self.env.user.company_id

        # If the opening move has already been posted, we open its form view
        if company.opening_move_posted():
            form_view_id = self.env.ref('account.setup_posted_move_form').id
            return {
                'type': 'ir.actions.act_window',
                'name': _('Initial Balances'),
                'view_mode': 'form',
                'res_model': 'account.move',
                'target': 'new',
                'res_id': company.account_opening_move_id.id,
                'views': [[form_view_id, 'form']],
            }

        # Otherwise, we open a custom wizard to post it.
        company.create_op_move_if_non_existant()
        new_wizard = self.env['account.opening'].create({'company_id': company.id})
        view_id = self.env.ref('account.setup_opening_move_wizard_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Initial Balances'),
            'view_mode': 'form',
            'res_model': 'account.opening',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
            'context': {'check_move_validity': False},
        }

    @api.model
    def setting_hide_setup_bar(self):
        """ Called by the cross button of the setup bar, to close it."""
        self.env.user.company_id.account_setup_bar_closed = True

    @api.model
    def create_op_move_if_non_existant(self):
        """ Creates an empty opening move in 'draft' state for the current company
        if there wasn't already one defined. For this, the function needs at least
        one journal of type 'general' to exist (required by account.move).
        """
        self.ensure_one()
        if not self.account_opening_move_id:
            default_journal = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', self.id)], limit=1)

            if not default_journal:
                raise UserError(_("Please install a chart of accounts or create a miscellaneous journal before proceeding."))

            self.account_opening_move_id = self.env['account.move'].create({
                'name': _('Opening Journal Entry'),
                'company_id': self.id,
                'journal_id': default_journal.id,
            })

    def mark_company_setup_as_done_action(self):
        """ Marks the 'company' setup step as completed."""
        self.account_setup_company_data_done = True

    def unmark_company_setup_as_done_action(self):
        """ Marks the 'company' setup step as uncompleted."""
        self.account_setup_company_data_done = False

    def opening_move_posted(self):
        """ Returns true if this company has an opening account move and this move is posted."""
        return bool(self.account_opening_move_id) and self.account_opening_move_id.state == 'posted'

    def get_unaffected_earnings_account(self):
        """ Returns the unaffected earnings account for this company, creating one
        if none has yet been defined.
        """
        unaffected_earnings_type = self.env.ref("account.data_unaffected_earnings")
        account = self.env['account.account'].search([('company_id', '=', self.id),
                                                      ('user_type_id', '=', unaffected_earnings_type.id)])
        if account:
            return account[0]
        return self.env['account.account'].create({
                'code': '999999',
                'name': _('Undistributed Profits/Losses'),
                'user_type_id': unaffected_earnings_type.id,
                'company_id': self.id,
            })

    def get_opening_move_differences(self, opening_move_lines):
        currency = self.currency_id
        balancing_move_line = opening_move_lines.filtered(lambda x: x.account_id == self.get_unaffected_earnings_account())

        debits_sum = credits_sum = 0.0
        for line in opening_move_lines:
            if line != balancing_move_line:
                #skip the autobalancing move line
                debits_sum += line.debit
                credits_sum += line.credit

        difference = abs(debits_sum - credits_sum)
        debit_diff = (debits_sum > credits_sum) and float_round(difference, precision_rounding=currency.rounding) or 0.0
        credit_diff = (debits_sum < credits_sum) and float_round(difference, precision_rounding=currency.rounding) or 0.0
        return debit_diff, credit_diff

    def _auto_balance_opening_move(self):
        """ Checks the opening_move of this company. If it has not been posted yet
        and is unbalanced, balances it with a automatic account.move.line in the
        current year earnings account.
        """
        if self.account_opening_move_id and self.account_opening_move_id.state == 'draft':
            debit_diff, credit_diff = self.get_opening_move_differences(self.account_opening_move_id.line_ids)

            currency = self.currency_id
            balancing_move_line = self.account_opening_move_id.line_ids.filtered(lambda x: x.account_id == self.get_unaffected_earnings_account())

            if float_is_zero(debit_diff + credit_diff, precision_rounding=currency.rounding):
                if balancing_move_line:
                    # zero difference and existing line : delete the line
                    balancing_move_line.unlink()
            else:
                if balancing_move_line:
                    # Non-zero difference and existing line : edit the line
                    balancing_move_line.write({'debit': credit_diff, 'credit': debit_diff})
                else:
                    # Non-zero difference and no existing line : create a new line
                    balancing_account = self.get_unaffected_earnings_account()
                    self.env['account.move.line'].create({
                        'name': _('Automatic Balancing Line'),
                        'move_id': self.account_opening_move_id.id,
                        'account_id': balancing_account.id,
                        'debit': credit_diff,
                        'credit': debit_diff,
                    })
