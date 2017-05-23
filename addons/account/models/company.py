# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    def _default_opening_date(self):
        today = datetime.now()
        return today + relativedelta(day=1, hour=0, minute=0, second=0, microsecond=0)

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
    use_cash_basis = fields.Boolean(string='Use Cash Basis')
    account_opening_move_id = fields.Many2one(string='Opening journal entry', comodel_name='account.move', help="The journal entry containing all the opening journal items of this company's accounting.")
    account_opening_journal_id = fields.Many2one(string='Opening journal', comodel_name='account.journal', related='account_opening_move_id.journal_id', help="Journal when the opening moves of this company's accounting has been posted.")
    account_opening_date = fields.Date(string='Accounting opening date',default=_default_opening_date, related='account_opening_move_id.date', help="Date of the opening entries of this company's accounting.")

    #Fields marking the completion of a setup step
    account_setup_company_data_marked_done = fields.Boolean(string='Company setup marked as done', default=False, help="True iff the user has forced the completion of the company setup step.")
    account_setup_bank_data_marked_done = fields.Boolean('Bank setup marked as done', default=False, help="True iff the user has forced the completion of the bank setup step.")
    account_setup_financial_year_data_marked_done = fields.Boolean('Financial year setup marked as done', default=False, help="True iff the user has forced the completion of the financial year setup step.")
    account_setup_chart_of_accounts_marked_done = fields.Boolean(string='Chart of account checked', default=False, help="True iff the wizard has displayed the chart of account once.")
    account_setup_bar_closed = fields.Boolean(string='Setup bar closed', default=False, help="True iff the setup bar has been closed by the user.")


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
        return super(ResCompany, self).write(values)

    @api.model
    def setting_init_company_action(self):
        """ Called by the 'Company Data' button of the setup bar.
        """
        current_company = self.env['res.company']._company_default_get()
        view_id = self.env.ref('account.setup_view_company_form').id

        return {'type': 'ir.actions.act_window',
                'name': _('Company Data'),
                'res_model': 'res.company',
                'target': 'new',
                'view_mode': 'form',
                'res_id': current_company.id,
                'views': [[view_id, 'form']],
        }

    @api.model
    def setting_init_bank_account_action(self):
        """ Called by the 'Bank Account' button of the setup bar.
        """
        current_company = self.env['res.company']._company_default_get()
        view_id = self.env.ref('account.setup_bank_journal_form').id

        rslt_act_dict = {
            'type': 'ir.actions.act_window',
            'name': _('Bank Account'),
            'view_mode': 'form',
            'res_model': 'account.journal',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

        # If some bank journal already exists, we open it in the form, so the user can edit it.
        # Otherwise, we just open the form in creation mode.
        bank_journal = self.env['account.journal'].search([('company_id','=',current_company.id), ('type','=','bank')], limit=1)
        if bank_journal:
            rslt_act_dict['res_id'] = bank_journal.id
        else:
            rslt_act_dict['context'] = {'default_type': 'bank'}

        return rslt_act_dict

    @api.model
    def setting_init_fiscal_year_action(self):
        """ Called by the 'Fiscal Year Opening' button of the setup bar.
        """
        current_company = self.env['res.company']._company_default_get()
        current_company.create_op_move_if_non_existant()

        new_wizard = self.env['account.financial.year.op'].create({'company_id': current_company.id})
        view_id = self.env.ref('account.setup_financial_year_opening_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Fiscal Year',
            'view_mode': 'form',
            'res_model': 'account.financial.year.op',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }

    @api.model
    def setting_chart_of_accounts_action(self):
        """ Called by the 'Chart of Accounts' button of the setup bar.
        """
        current_company = self._company_default_get()

        # If an opening move has already been posted, we open the tree view showing all the accounts
        if current_company.opening_move_posted():
            return 'account.action_account_form'

        # Otherwise, we open a custom tree view allowing to edit opening balances of the account, to prepare the opening move
        current_company.account_setup_chart_of_accounts_marked_done = True
        self.create_op_move_if_non_existant()

        # We return the name of the action to execute (to display the list of all the accounts,
        # now we have created an opening move allowing to post initial balances through this view.
        return 'account.action_accounts_setup_tree'

    @api.model
    def setting_opening_move_action(self):
        """ Called by the 'Initial Balances' button of the setup bar.
        """
        current_company = self.env['res.company']._company_default_get()

        # If the opening move has already been posted, we open its form view
        if current_company.opening_move_posted():
            form_view_id = self.env.ref('account.setup_posted_move_form').id

            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'target': 'new',
                'res_id': current_company.account_opening_move_id.id,
                'views': [[form_view_id, 'form']],
            }

        # Otherwise, we open a custom wizard to post it.
        self.create_op_move_if_non_existant()
        new_wizard = self.env['account.opening'].create({'company_id': current_company.id})
        view_id = self.env.ref('account.setup_opening_move_wizard_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Initial Balances',
            'view_mode': 'form',
            'res_model': 'account.opening',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }

    @api.model
    def setting_hide_setup_bar(self):
        """ Called by the cross button of the setup bar, to close it.
        """
        current_company = self._company_default_get()
        current_company.account_setup_bar_closed = True
        return 'account.setup_wizard_refresh_view'

    @api.model
    def create_op_move_if_non_existant(self):
        """ Creates an empty opening move in 'draft' state for the current company
        if there wasn't already one defined. For this, the function needs at least
        one journal of type 'bank' to exist (required by account.move).
        """
        current_company = self._company_default_get()
        if not current_company.account_opening_move_id:
            default_journal = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', current_company.id)], limit=1)

            if not default_journal:
                raise UserError("No miscellanous journal could be found. Please create one before proceeding.")

            current_company.account_opening_move_id = self.env['account.move'].create({
                'name': _('Opening move'),
                'company_id': current_company.id,
                'journal_id': default_journal.id,
            })

    def mark_company_setup_as_done_action(self):
        """ Forces the completion of the 'company' setup step and returns an action
        refreshing the view.
        """
        self.account_setup_company_data_marked_done = True
        return self.env.ref('account.setup_wizard_refresh_view').read([])[0]

    def unmark_company_setup_as_done_action(self):
        """ Returns the 'company' setup step to its 'not done' state.
        """
        self.account_setup_company_data_marked_done = False
        return self.env.ref('account.setup_wizard_refresh_view').read([])[0]

    def opening_move_posted(self):
        """ Returns true if and only if this company has an opening account move,
        and this move has been posted.
        """
        return bool(self.account_opening_move_id) and self.account_opening_move_id.state == 'posted'
