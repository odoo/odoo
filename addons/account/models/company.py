# -*- coding: utf-8 -*-

from datetime import timedelta, datetime
import calendar
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.tools import date_utils
from odoo.tests.common import Form


MONTH_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    #TODO check all the options/fields are in the views (settings + company form view)
    fiscalyear_last_day = fields.Integer(default=31, required=True)
    fiscalyear_last_month = fields.Selection(MONTH_SELECTION, default='12', required=True)
    period_lock_date = fields.Date(string="Lock Date for Non-Advisers", help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this date. Use it for period locking inside an open fiscal year, for example.")
    fiscalyear_lock_date = fields.Date(string="Lock Date", help="No users, including Advisers, can edit accounts prior to and inclusive of this date. Use it for fiscal year locking for example.")
    tax_lock_date = fields.Date("Tax Lock Date", help="No users can edit journal entries related to a tax prior and inclusive of this date.")
    transfer_account_id = fields.Many2one('account.account',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id), ('deprecated', '=', False)], string="Inter-Banks Transfer Account", help="Intermediary account used when moving money from a liquidity account to another")
    expects_chart_of_accounts = fields.Boolean(string='Expects a Chart of Accounts', default=True)
    chart_template_id = fields.Many2one('account.chart.template', help='The chart template for the company (if any)')
    bank_account_code_prefix = fields.Char(string='Prefix of the bank accounts', oldname="bank_account_code_char")
    cash_account_code_prefix = fields.Char(string='Prefix of the cash accounts')
    transfer_account_code_prefix = fields.Char(string='Prefix of the transfer accounts')
    account_sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax")
    account_purchase_tax_id = fields.Many2one('account.tax', string="Default Purchase Tax")
    tax_cash_basis_journal_id = fields.Many2one('account.journal', string="Cash Basis Journal")
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
        ], default='round_per_line', string='Tax Calculation Rounding Method')
    currency_exchange_journal_id = fields.Many2one('account.journal', string="Exchange Gain or Loss Journal", domain=[('type', '=', 'general')])
    income_currency_exchange_account_id = fields.Many2one('account.account', related='currency_exchange_journal_id.default_credit_account_id', readonly=False,
        string="Gain Exchange Rate Account", domain="[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', id)]")
    expense_currency_exchange_account_id = fields.Many2one('account.account', related='currency_exchange_journal_id.default_debit_account_id', readonly=False,
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
    account_bank_reconciliation_start = fields.Date(string="Bank Reconciliation Threshold", help="""The bank reconciliation widget won't ask to reconcile payments older than this date.
                                                                                                       This is useful if you install accounting after having used invoicing for some time and
                                                                                                       don't want to reconcile all the past payments with bank statements.""")

    incoterm_id = fields.Many2one('account.incoterms', string='Default incoterm',
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')

    qr_code = fields.Boolean(string='Display SEPA QR code')

    invoice_is_email = fields.Boolean('Email by default', default=True)
    invoice_is_print = fields.Boolean('Print by default', default=True)

    #Fields of the setup step for opening move
    account_opening_move_id = fields.Many2one(string='Opening Journal Entry', comodel_name='account.move', help="The journal entry containing the initial balance of all this company's accounts.")
    account_opening_journal_id = fields.Many2one(string='Opening Journal', comodel_name='account.journal', related='account_opening_move_id.journal_id', help="Journal where the opening entry of this company's accounting has been posted.", readonly=False)
    account_opening_date = fields.Date(string='Opening Date', related='account_opening_move_id.date', help="Date at which the opening entry of this company's accounting has been posted.", readonly=False)

    # Fields marking the completion of a setup step
    # YTI FIXME : The selection should be factorize as a static list in base, like ONBOARDING_STEP_STATES
    account_setup_bank_data_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding bank data step", default='not_done')
    account_setup_fy_data_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding fiscal year step", default='not_done')
    account_setup_coa_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding charts of account step", default='not_done')
    account_onboarding_invoice_layout_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding invoice layout step", default='not_done')
    account_onboarding_sample_invoice_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding sample invoice step", default='not_done')
    account_onboarding_sale_tax_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding sale tax step", default='not_done')

    # account dashboard onboarding
    account_invoice_onboarding_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done"), ('closed', "Closed")], string="State of the account invoice onboarding panel", default='not_done')
    account_dashboard_onboarding_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done"), ('closed', "Closed")], string="State of the account dashboard onboarding panel", default='not_done')
    invoice_terms = fields.Text(string='Default Terms and Conditions', translate=True)

    @api.constrains('account_opening_move_id', 'fiscalyear_last_day', 'fiscalyear_last_month')
    def _check_fiscalyear_last_day(self):
        # if the user explicitly chooses the 29th of February we allow it:
        # there is no "fiscalyear_last_year" so we do not know his intentions.
        if self.fiscalyear_last_day == 29 and self.fiscalyear_last_month == '2':
            return

        if self.account_opening_date:
            year = self.account_opening_date.year
        else:
            year = datetime.now().year

        max_day = calendar.monthrange(year, int(self.fiscalyear_last_month))[1]
        if self.fiscalyear_last_day > max_day:
            raise ValidationError(_("Invalid fiscal year last day"))

    def get_and_update_account_invoice_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        return self.get_and_update_onbarding_state(
            'account_invoice_onboarding_state',
            self.get_account_invoice_onboarding_steps_states_names()
        )

    # YTI FIXME: Define only one method that returns {'account': [], 'sale': [], ...}
    def get_account_invoice_onboarding_steps_states_names(self):
        """ Necessary to add/edit steps from other modules (payment acquirer in this case). """
        return [
            'base_onboarding_company_state',
            'account_onboarding_invoice_layout_state',
            'account_onboarding_sample_invoice_state',
        ]

    def get_and_update_account_dashboard_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        return self.get_and_update_onbarding_state('account_dashboard_onboarding_state', [
            'base_onboarding_company_state',
            'account_setup_bank_data_state',
            'account_setup_fy_data_state',
            'account_setup_coa_state',
        ])

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
            fields.Date.from_string(vals['period_lock_date'])
        fiscalyear_lock_date = vals.get('fiscalyear_lock_date') and\
            fields.Date.from_string(vals['fiscalyear_lock_date'])

        previous_month = fields.Date.today() + relativedelta(months=-1)
        days_previous_month = calendar.monthrange(previous_month.year, previous_month.month)
        previous_month = previous_month.replace(day=days_previous_month[1])
        for company in self:
            old_fiscalyear_lock_date = company.fiscalyear_lock_date

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
                    period_lock_date = company.period_lock_date
                else:
                    continue

            # The user attempts to set a lock date for advisors prior to the lock date for users
            if period_lock_date < fiscalyear_lock_date:
                raise ValidationError(_('You cannot define stricter conditions on advisors than on users. Please make sure that the lock date on advisor is set before the lock date for users.'))

    def compute_fiscalyear_dates(self, current_date):
        '''Computes the start and end dates of the fiscal year where the given 'date' belongs to.

        :param current_date: A datetime.date/datetime.datetime object.
        :return: A dictionary containing:
            * date_from
            * date_to
            * [Optionally] record: The fiscal year record.
        '''
        self.ensure_one()
        date_str = current_date.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # Search a fiscal year record containing the date.
        # If a record is found, then no need further computation, we get the dates range directly.
        fiscalyear = self.env['account.fiscal.year'].search([
            ('company_id', '=', self.id),
            ('date_from', '<=', date_str),
            ('date_to', '>=', date_str),
        ], limit=1)
        if fiscalyear:
            return {
                'date_from': fiscalyear.date_from,
                'date_to': fiscalyear.date_to,
                'record': fiscalyear,
            }

        date_from, date_to = date_utils.get_fiscal_year(
            current_date, day=self.fiscalyear_last_day, month=int(self.fiscalyear_last_month))

        date_from_str = date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_to_str = date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # Search for fiscal year records reducing the delta between the date_from/date_to.
        # This case could happen if there is a gap between two fiscal year records.
        # E.g. two fiscal year records: 2017-01-01 -> 2017-02-01 and 2017-03-01 -> 2017-12-31.
        # => The period 2017-02-02 - 2017-02-30 is not covered by a fiscal year record.

        fiscalyear_from = self.env['account.fiscal.year'].search([
            ('company_id', '=', self.id),
            ('date_from', '<=', date_from_str),
            ('date_to', '>=', date_from_str),
        ], limit=1)
        if fiscalyear_from:
            date_from = fiscalyear_from.date_to + timedelta(days=1)

        fiscalyear_to = self.env['account.fiscal.year'].search([
            ('company_id', '=', self.id),
            ('date_from', '<=', date_to_str),
            ('date_to', '>=', date_to_str),
        ], limit=1)
        if fiscalyear_to:
            date_to = fiscalyear_to.date_from - timedelta(days=1)

        return {'date_from': date_from, 'date_to': date_to}

    def get_new_account_code(self, current_code, old_prefix, new_prefix):
        digits = len(current_code)
        return new_prefix + current_code.replace(old_prefix, '', 1).lstrip('0').rjust(digits-len(new_prefix), '0')

    def reflect_code_prefix_change(self, old_code, new_code):
        accounts = self.env['account.account'].search([('code', 'like', old_code), ('internal_type', '=', 'liquidity'),
            ('company_id', '=', self.id)], order='code asc')
        for account in accounts:
            if account.code.startswith(old_code):
                account.write({'code': self.get_new_account_code(account.code, old_code, new_code)})

    def _validate_fiscalyear_lock(self, values):
        if values.get('fiscalyear_lock_date'):
            nb_draft_entries = self.env['account.move'].search([
                ('company_id', 'in', [c.id for c in self]),
                ('state', '=', 'draft'),
                ('date', '<=', values['fiscalyear_lock_date'])])
            if nb_draft_entries:
                raise ValidationError(_('There are still unposted entries in the period you want to lock. You should either post or delete them.'))

    def write(self, values):
        #restrict the closing of FY if there are still unposted entries
        self._validate_fiscalyear_lock(values)

        # Reflect the change on accounts
        for company in self:
            if values.get('bank_account_code_prefix'):
                new_bank_code = values.get('bank_account_code_prefix') or company.bank_account_code_prefix
                company.reflect_code_prefix_change(company.bank_account_code_prefix, new_bank_code)
            if values.get('cash_account_code_prefix'):
                new_cash_code = values.get('cash_account_code_prefix') or company.cash_account_code_prefix
                company.reflect_code_prefix_change(company.cash_account_code_prefix, new_cash_code)

            #forbid the change of currency_id if there are already some accounting entries existing
            if 'currency_id' in values and values['currency_id'] != company.currency_id.id:
                if self.env['account.move.line'].search([('company_id', '=', company.id)]):
                    raise UserError(_('You cannot change the currency of the company since some journal items already exist'))

        return super(ResCompany, self).write(values)

    @api.model
    def setting_init_bank_account_action(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('account.setup_bank_account_wizard').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Bank Account'),
                'res_model': 'account.setup.bank.manual.config',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
        }

    @api.model
    def setting_init_fiscal_year_action(self):
        """ Called by the 'Fiscal Year Opening' button of the setup bar."""
        company = self.env.company
        company.create_op_move_if_non_existant()
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
        company = self.env.company
        company.set_onboarding_step_done('account_setup_coa_state')

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
            'limit': 99999999,
            'search_view_id': self.env.ref('account.view_account_search').id,
            'views': [[view_id, 'list']],
            'domain': domain,
        }

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

            today = datetime.today().date()
            opening_date = today.replace(month=int(self.fiscalyear_last_month), day=self.fiscalyear_last_day) + timedelta(days=1)
            if opening_date > today:
                opening_date = opening_date + relativedelta(years=-1)

            self.account_opening_move_id = self.env['account.move'].create({
                'name': _('Opening Journal Entry'),
                'company_id': self.id,
                'journal_id': default_journal.id,
                'date': opening_date,
            })

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
        # Do not assume '999999' doesn't exist since the user might have created such an account
        # manually.
        code = 999999
        while self.env['account.account'].search([('code', '=', str(code)), ('company_id', '=', self.id)]):
            code -= 1
        return self.env['account.account'].create({
                'code': str(code),
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

    @api.model
    def action_close_account_invoice_onboarding(self):
        """ Mark the invoice onboarding panel as closed. """
        self.env.company.account_invoice_onboarding_state = 'closed'

    @api.model
    def action_close_account_dashboard_onboarding(self):
        """ Mark the dashboard onboarding panel as closed. """
        self.env.company.account_dashboard_onboarding_state = 'closed'

    @api.model
    def action_open_account_onboarding_invoice_layout(self):
        """ Onboarding step for the invoice layout. """
        action = self.env.ref('account.action_open_account_onboarding_invoice_layout').read()[0]
        action['res_id'] = self.env.company.id
        return action

    @api.model
    def action_open_account_onboarding_sale_tax(self):
        """ Onboarding step for the invoice layout. """
        action = self.env.ref('account.action_open_account_onboarding_sale_tax').read()[0]
        action['res_id'] = self.env.company.id
        return action

    @api.model
    def _get_sample_invoice(self):
        """ Get a sample invoice or create one if it does not exist. """
        # use current user as partner
        partner = self.env.user.partner_id

        company_id = self.env.company.id
        # try to find an existing sample invoice
        sample_invoice = self.env['account.move'].search(
            [('company_id', '=', company_id),
             ('partner_id', '=', partner.id)], limit=1)

        if len(sample_invoice) == 0:
            # If there are no existing accounts or no journal, fail
            account = self.env.company.get_chart_of_accounts_or_fail()

            journal = self.env['account.journal'].search([('company_id', '=', company_id)], limit=1)
            if len(journal) == 0:
                action = self.env.ref('account.action_account_journal_form')
                msg = _("We cannot find any journal for this company. You should create one."
                        "\nPlease go to Configuration > Journals.")
                raise RedirectWarning(msg, action.id, _("Go to the journal configuration"))

            sample_invoice = self.env['account.move'].with_context(default_type='out_invoice', default_journal_id=journal.id).create({
                'invoice_payment_ref': _('Sample invoice'),
                'partner_id': partner.id,
                'invoice_line_ids': [
                    (0, 0, {
                        'name': _('Sample invoice line name'),
                        'account_id': account.id,
                        'quantity': 2,
                        'price_unit': 199.99,
                    }),
                    (0, 0, {
                        'name': _('Sample invoice line name 2'),
                        'account_id': account.id,
                        'quantity': 1,
                        'price_unit': 25.0,
                    }),
                ],
            })
        return sample_invoice

    @api.model
    def action_open_account_onboarding_sample_invoice(self):
        """ Onboarding step for sending a sample invoice. Open a window to compose an email,
            with the edi_invoice_template message loaded by default. """
        sample_invoice = self._get_sample_invoice()
        template = self.env.ref('account.email_template_edi_invoice', False)
        action = self.env.ref('account.action_open_account_onboarding_sample_invoice').read()[0]
        action['context'] = {
            'default_res_id': sample_invoice.id,
            'default_use_template': bool(template),
            'default_template_id': template and template.id or False,
            'default_model': 'account.move',
            'default_composition_mode': 'comment',
            'mark_invoice_as_sent': True,
            'custom_layout': 'mail.mail_notification_borders',
            'force_email': True,
            'mail_notify_author': True,
        }
        return action

    def action_save_onboarding_invoice_layout(self):
        """ Set the onboarding step as done """
        if bool(self.logo) and self.logo != self._get_logo():
            self.set_onboarding_step_done('account_onboarding_invoice_layout_state')

    def action_save_onboarding_sale_tax(self):
        """ Set the onboarding step as done """
        self.set_onboarding_step_done('account_onboarding_sale_tax_state')

    def get_chart_of_accounts_or_fail(self):
        account = self.env['account.account'].search([('company_id', '=', self.id)], limit=1)
        if len(account) == 0:
            action = self.env.ref('account.action_account_config')
            msg = _(
                "We cannot find a chart of accounts for this company, you should configure it. \n"
                "Please go to Account Configuration and select or install a fiscal localization.")
            raise RedirectWarning(msg, action.id, _("Go to the configuration panel"))
        return account
