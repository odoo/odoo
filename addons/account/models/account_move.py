# -*- coding: utf-8 -*-

from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re, is_html_empty, sql
from odoo.tools.misc import format_amount, formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
from contextlib import contextmanager
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import ast
import json
import re
import warnings


#forbidden fields
INTEGRITY_HASH_MOVE_FIELDS = ('date', 'journal_id', 'company_id')
INTEGRITY_HASH_LINE_FIELDS = ('debit', 'credit', 'account_id', 'partner_id')


def calc_check_digits(number):
    """Calculate the extra digits that should be appended to the number to make it a valid number.
    Source: python-stdnum iso7064.mod_97_10.calc_check_digits
    """
    number_base10 = ''.join(str(int(x, 36)) for x in number)
    checksum = int(number_base10) % 97
    return '%02d' % ((98 - 100 * checksum) % 97)

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
]

class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _description = "Journal Entry"
    _order = 'date desc, name desc, id desc'
    _mail_post_access = 'read'
    _check_company_auto = True
    _sequence_index = "journal_id"

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS account_move_to_check_idx
            ON account_move(journal_id) WHERE to_check = true;
            CREATE INDEX IF NOT EXISTS account_move_payment_idx
            ON account_move(journal_id, state, payment_state, move_type, date);
        """)

    @property
    def _sequence_monthly_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_monthly_regex

    @property
    def _sequence_yearly_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_yearly_regex

    @property
    def _sequence_fixed_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_fixed_regex

    @api.model
    def _search_default_journal(self, journal_types):
        company_id = self._context.get('default_company_id', self.env.company.id)
        domain = [('company_id', '=', company_id), ('type', 'in', journal_types)]

        journal = None
        if self._context.get('default_currency_id'):
            currency_domain = domain + [('currency_id', '=', self._context['default_currency_id'])]
            journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            company = self.env['res.company'].browse(company_id)

            error_msg = _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company.display_name,
                journal_types=', '.join(journal_types),
            )
            raise UserError(error_msg)

        return journal

    @api.model
    def _get_default_journal(self):
        ''' Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        '''
        move_type = self._context.get('default_move_type', 'entry')
        if move_type in self.get_sale_types(include_receipts=True):
            journal_types = ['sale']
        elif move_type in self.get_purchase_types(include_receipts=True):
            journal_types = ['purchase']
        else:
            journal_types = self._context.get('default_move_journal_types', ['general'])

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self._context['default_journal_id'])

            if move_type != 'entry' and journal.type not in journal_types:
                raise UserError(_(
                    "Cannot create an invoice of type %(move_type)s with a journal having %(journal_type)s as type.",
                    move_type=move_type,
                    journal_type=journal.type,
                ))
        else:
            journal = self._search_default_journal(journal_types)

        return journal

    # TODO remove in master
    @api.model
    def _get_default_invoice_date(self):
        warnings.warn("Method '_get_default_invoice_date()' is deprecated and has been removed.", DeprecationWarning)
        return fields.Date.context_today(self) if self._context.get('default_move_type', 'entry') in self.get_purchase_types(include_receipts=True) else False

    @api.model
    def _get_default_currency(self):
        ''' Get the default currency from either the journal, either the default journal's company. '''
        journal = self._get_default_journal()
        return journal.currency_id or journal.company_id.currency_id

    @api.model
    def _get_default_invoice_incoterm(self):
        ''' Get the default incoterm for invoice. '''
        return self.env.company.incoterm_id

    # ==== Business fields ====
    name = fields.Char(string='Number', copy=False, compute='_compute_name', readonly=False, store=True, index='btree', tracking=True)
    highest_name = fields.Char(compute='_compute_highest_name')
    made_sequence_hole = fields.Boolean(compute='_compute_made_sequence_hole')
    show_name_warning = fields.Boolean(store=False)
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        tracking=True,
        default=fields.Date.context_today
    )
    ref = fields.Char(string='Reference', copy=False, tracking=True)
    narration = fields.Html(string='Terms and Conditions', compute='_compute_narration', store=True, readonly=False)

    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    posted_before = fields.Boolean(help="Technical field for knowing if the move has been posted before", copy=False)
    move_type = fields.Selection(selection=[
            ('entry', 'Journal Entry'),
            ('out_invoice', 'Customer Invoice'),
            ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'Vendor Bill'),
            ('in_refund', 'Vendor Credit Note'),
            ('out_receipt', 'Sales Receipt'),
            ('in_receipt', 'Purchase Receipt'),
        ], string='Type', required=True, store=True, index=True, readonly=True, tracking=True,
        default="entry", change_default=True)
    type_name = fields.Char('Type Name', compute='_compute_type_name')
    is_storno = fields.Boolean(compute='_compute_is_storno', store=True, copy=False, readonly=False,
                               help='Utility field to express whether the journal entry is subject to storno accounting. That is when the company uses storno and the journal entry is a refund or a reversal.')
    to_check = fields.Boolean(string='To Check', default=False, tracking=True,
        help='If this checkbox is ticked, it means that the user was not sure of all the related information at the time of the creation of the move and that the move needs to be checked again.')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        check_company=True, domain="[('id', 'in', suitable_journal_ids)]",
        default=_get_default_journal)
    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids')
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 store=True, readonly=True,
                                 compute='_compute_company_id')
    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,
        related='company_id.currency_id')
    currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=True,
        states={'draft': [('readonly', False)]},
        string='Currency',
        default=_get_default_currency)
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items', copy=True, readonly=True,
        states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', readonly=True, tracking=True,
        states={'draft': [('readonly', False)]},
        check_company=True,
        string='Partner', change_default=True, ondelete='restrict')
    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity', store=True, readonly=True,
        compute='_compute_commercial_partner_id', ondelete='restrict')
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', readonly=True)
    user_id = fields.Many2one(string='User', related='invoice_user_id',
        help='Technical field used to fit the generic behavior in mail templates.')
    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        readonly=False,
        store=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Delivery address for current invoice.",
        compute='_compute_partner_shipping_id',
    )
    is_move_sent = fields.Boolean(
        readonly=True,
        default=False,
        copy=False,
        tracking=True,
        help="It indicates that the invoice/payment has been sent.",
    )
    partner_bank_id = fields.Many2one('res.partner.bank', string='Recipient Bank',
        help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.',
        check_company=True)
    payment_reference = fields.Char(string='Payment Reference', index='trigram', copy=False,
        help="The payment reference to set on journal items.")
    payment_id = fields.Many2one(
        index='btree_not_null',
        comodel_name='account.payment',
        string="Payment", copy=False, check_company=True)
    statement_line_id = fields.Many2one(
        comodel_name='account.bank.statement.line',
        string="Statement Line", copy=False, check_company=True)
    statement_id = fields.Many2one(
        related='statement_line_id.statement_id',
        copy=False,
        readonly=True,
        help="Technical field used to open the linked bank statement from the edit button in a group by view,"
             " or via the smart button on journal entries.")

    # === Amount fields ===
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, tracking=True,
        compute='_compute_amount')
    amount_tax = fields.Monetary(string='Tax', store=True, readonly=True,
        compute='_compute_amount')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
        compute='_compute_amount',
        inverse='_inverse_amount_total')
    amount_residual = fields.Monetary(string='Amount Due', store=True,
        compute='_compute_amount')
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount Signed', store=True, readonly=True,
        compute='_compute_amount', currency_field='company_currency_id')
    amount_tax_signed = fields.Monetary(string='Tax Signed', store=True, readonly=True,
        compute='_compute_amount', currency_field='company_currency_id')
    amount_total_signed = fields.Monetary(string='Total Signed', store=True, readonly=True,
        compute='_compute_amount', currency_field='company_currency_id')
    amount_total_in_currency_signed = fields.Monetary(string='Total in Currency Signed', store=True, readonly=True,
        compute='_compute_amount', currency_field='currency_id')
    amount_residual_signed = fields.Monetary(string='Amount Due Signed', store=True,
        compute='_compute_amount', currency_field='company_currency_id')
    tax_totals_json = fields.Char(
        string="Invoice Totals JSON",
        compute='_compute_tax_totals_json',
        readonly=False,
        help='Edit Tax amounts if you encounter rounding issues.')
    payment_state = fields.Selection(PAYMENT_STATE_SELECTION, string="Payment Status", store=True,
        readonly=True, copy=False, tracking=True, compute='_compute_amount')

    # ==== Cash basis feature fields ====
    tax_cash_basis_rec_id = fields.Many2one(
        'account.partial.reconcile',
        string='Tax Cash Basis Entry of',
        help="Technical field used to keep track of the tax cash basis reconciliation. "
             "This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")
    tax_cash_basis_origin_move_id = fields.Many2one(
        comodel_name='account.move',
        index='btree_not_null',
        string="Cash Basis Origin",
        readonly=1,
        help="The journal entry from which this tax cash basis journal entry has been created.")
    tax_cash_basis_created_move_ids = fields.One2many(
        string="Cash Basis Entries",
        comodel_name='account.move',
        inverse_name='tax_cash_basis_origin_move_id',
        help="The cash basis entries created from the taxes on this entry, when reconciling its lines."
    )
    always_tax_exigible = fields.Boolean(
        compute='_compute_always_tax_exigible',
        store=True,
        help="Technical field used by cash basis taxes, telling the lines of the move are always exigible. "
             "This happens if the move contains no payable or receivable line.")

    # ==== Auto-post feature fields ====
    auto_post = fields.Boolean(string='Post Automatically', default=False, copy=False,
        help='If this checkbox is ticked, this entry will be automatically posted at its date.')

    # ==== Reverse feature fields ====
    reversed_entry_id = fields.Many2one('account.move', string="Reversal of", readonly=True, copy=False,
        check_company=True)
    reversal_move_id = fields.One2many('account.move', 'reversed_entry_id')

    # =========================================================
    # Invoice related fields
    # =========================================================

    # ==== Business fields ====
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Fiscal Position', readonly=True,
        states={'draft': [('readonly', False)]}, check_company=True,
        domain="[('company_id', '=', company_id)]", ondelete="restrict",
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices. "
             "The default value comes from the customer.")
    invoice_user_id = fields.Many2one('res.users', copy=False, tracking=True,
        string='Salesperson',
        default=lambda self: self.env.user)
    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)]})
    invoice_date_due = fields.Date(string='Due Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)]})
    invoice_origin = fields.Char(string='Origin', readonly=True, tracking=True,
        help="The document(s) that generated the invoice.")
    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',
        check_company=True,
        readonly=True, states={'draft': [('readonly', False)]})
    # /!\ invoice_line_ids is just a subset of line_ids.
    invoice_line_ids = fields.One2many('account.move.line', 'move_id', string='Invoice lines',
        copy=False, readonly=True,
        domain=[('exclude_from_invoice_tab', '=', False)],
        states={'draft': [('readonly', False)]})
    invoice_incoterm_id = fields.Many2one('account.incoterms', string='Incoterm',
        default=_get_default_invoice_incoterm,
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')
    display_qr_code = fields.Boolean(string="Display QR-code", related='company_id.qr_code')
    qr_code_method = fields.Selection(string="Payment QR-code", copy=False,
        selection=lambda self: self.env['res.partner.bank'].get_available_qr_methods_in_sequence(),
        help="Type of QR-code to be generated for the payment of this invoice, when printing it. If left blank, the first available and usable method will be used.")

    # ==== Payment widget fields ====
    invoice_outstanding_credits_debits_widget = fields.Text(groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_to_reconcile_info')
    invoice_has_outstanding = fields.Boolean(groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_to_reconcile_info')
    invoice_payments_widget = fields.Text(groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_reconciled_info')

    # ==== Vendor bill fields ====
    invoice_vendor_bill_id = fields.Many2one('account.move', store=False,
        check_company=True,
        string='Vendor Bill',
        help="Auto-complete from a past bill.")
    invoice_source_email = fields.Char(string='Source Email', tracking=True)
    invoice_partner_display_name = fields.Char(compute='_compute_invoice_partner_display_info', store=True)

    # ==== Cash rounding fields ====
    invoice_cash_rounding_id = fields.Many2one('account.cash.rounding', string='Cash Rounding Method',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Defines the smallest coinage of the currency that can be used to pay by cash.')

    # ==== Display purpose fields ====
    invoice_filter_type_domain = fields.Char(compute='_compute_invoice_filter_type_domain',
        help="Technical field used to have a dynamic domain on journal / taxes in the form view.")
    bank_partner_id = fields.Many2one('res.partner', help='Technical field to get the domain on the bank', compute='_compute_bank_partner_id')
    invoice_has_matching_suspense_amount = fields.Boolean(compute='_compute_has_matching_suspense_amount',
        groups='account.group_account_invoice,account.group_account_readonly',
        help="Technical field used to display an alert on invoices if there is at least a matching amount in any supsense account.")
    tax_lock_date_message = fields.Char(
        compute='_compute_tax_lock_date_message',
        help="Technical field used to display a message when the invoice's accounting date is prior of the tax lock date.")
    display_inactive_currency_warning = fields.Boolean(
        compute="_compute_display_inactive_currency_warning",
        help="Technical field used for tracking the status of the currency")
    tax_country_id = fields.Many2one(comodel_name='res.country', compute='_compute_tax_country_id', help="Technical field to filter the available taxes depending on the fiscal country and fiscal position.")
    tax_country_code = fields.Char(compute="_compute_tax_country_code")
    # Technical field to hide Reconciled Entries stat button
    has_reconciled_entries = fields.Boolean(compute="_compute_has_reconciled_entries")
    show_reset_to_draft_button = fields.Boolean(compute='_compute_show_reset_to_draft_button')
    # Credit Limit related field
    partner_credit_warning = fields.Text(
        compute='_compute_partner_credit_warning',
        groups="account.group_account_invoice,account.group_account_readonly")

    # ==== Hash Fields ====
    restrict_mode_hash_table = fields.Boolean(related='journal_id.restrict_mode_hash_table')
    secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True, copy=False)
    inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True)

    # We neeed the btree index for unicity constraint (on field) AND this one for human searches
    def _auto_init(self):
        super(AccountMove, self)._auto_init()
        if sql.install_pg_trgm(self._cr):
            sql.create_index(self._cr, 'account_move_name_trigram_index', self._table, ['"name" gin_trgm_ops'], 'gin')

    @api.model
    def _field_will_change(self, record, vals, field_name):
        if field_name not in vals:
            return False
        field = record._fields[field_name]
        if field.type == 'many2one':
            return record[field_name].id != vals[field_name]
        if field.type == 'many2many':
            current_ids = set(record[field_name].ids)
            after_write_ids = set(record.new({field_name: vals[field_name]})[field_name].ids)
            return current_ids != after_write_ids
        if field.type == 'one2many':
            return True
        if field.type == 'monetary' and record[field.get_currency_field(record)]:
            return not record[field.get_currency_field(record)].is_zero(record[field_name] - vals[field_name])
        if field.type == 'float':
            record_value = field.convert_to_cache(record[field_name], record)
            to_write_value = field.convert_to_cache(vals[field_name], record)
            return record_value != to_write_value
        return record[field_name] != vals[field_name]

    @api.model
    def _cleanup_write_orm_values(self, record, vals):
        cleaned_vals = dict(vals)
        for field_name, value in vals.items():
            if not self._field_will_change(record, vals, field_name):
                del cleaned_vals[field_name]
        return cleaned_vals

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    def _get_accounting_date(self, invoice_date, has_tax):
        """Get correct accounting date for previous periods, taking tax lock date into account.

        When registering an invoice in the past, we still want the sequence to be increasing.
        We then take the last day of the period, depending on the sequence format.
        If there is a tax lock date and there are taxes involved, we register the invoice at the
        last date of the first open period.

        :param invoice_date (datetime.date): The invoice date
        :param has_tax (bool): Iff any taxes are involved in the lines of the invoice
        :return (datetime.date):
        """
        lock_dates = self._get_violated_lock_dates(invoice_date, has_tax)
        today = fields.Date.today()
        highest_name = self.highest_name or self._get_last_sequence(relaxed=True, lock=False)
        number_reset = self._deduce_sequence_number_reset(highest_name)
        if lock_dates:
            invoice_date = lock_dates[-1][0] + timedelta(days=1)
        if self.is_sale_document(include_receipts=True):
            if lock_dates:
                if not highest_name or number_reset == 'month':
                    return min(today, date_utils.get_month(invoice_date)[1])
                elif number_reset == 'year':
                    return min(today, date_utils.end_of(invoice_date, 'year'))
        else:
            if not highest_name or number_reset == 'month':
                if (today.year, today.month) > (invoice_date.year, invoice_date.month):
                    return date_utils.get_month(invoice_date)[1]
                else:
                    return max(invoice_date, today)
            elif number_reset == 'year':
                if today.year > invoice_date.year:
                    return date(invoice_date.year, 12, 31)
                else:
                    return max(invoice_date, today)
        return invoice_date

    def _get_violated_lock_dates(self, invoice_date, has_tax):
        """Get all the lock dates affecting the current invoice_date.

        :param invoice_date: The invoice date
        :param has_tax: If any taxes are involved in the lines of the invoice
        :return: a list of tuples containing the lock dates affecting this move, ordered chronologically.
        """
        locks = []
        user_lock_date = self.company_id._get_user_fiscal_lock_date()
        if invoice_date and user_lock_date and invoice_date <= user_lock_date:
            locks.append((user_lock_date, _('user')))
        tax_lock_date = self.company_id.tax_lock_date
        if invoice_date and tax_lock_date and has_tax and invoice_date <= tax_lock_date:
            locks.append((tax_lock_date, _('tax')))
        locks.sort()
        return locks

    @api.onchange('invoice_date', 'highest_name', 'company_id')
    def _onchange_invoice_date(self):
        if self.invoice_date:
            if not self.invoice_payment_term_id and (not self.invoice_date_due or self.invoice_date_due < self.invoice_date):
                self.invoice_date_due = self.invoice_date

            accounting_date = self.invoice_date
            if not self.is_sale_document(include_receipts=True):
                accounting_date = self._get_accounting_date(self.invoice_date, self._affect_tax_report())
            if accounting_date != self.date:
                self.date = accounting_date
                self._onchange_currency()
            else:
                self._onchange_recompute_dynamic_lines()

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id and self.journal_id.currency_id:
            new_currency = self.journal_id.currency_id
            if new_currency != self.currency_id:
                self.currency_id = new_currency
                self._onchange_currency()
        if self.state == 'draft' and self._get_last_sequence(lock=False) and self.name and self.name != '/':
            self.name = '/'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self = self.with_company(self.journal_id.company_id)

        warning = {}
        if self.partner_id:
            rec_account = self.partner_id.property_account_receivable_id
            pay_account = self.partner_id.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            p = self.partner_id
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn and p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s", p.name),
                    'message': p.invoice_warn_msg
                }
                if p.invoice_warn == 'block':
                    self.partner_id = False
                    return {'warning': warning}

        if self.is_sale_document(include_receipts=True) and self.partner_id:
            self.invoice_payment_term_id = self.partner_id.property_payment_term_id or self.invoice_payment_term_id
            new_term_account = self.partner_id.commercial_partner_id.property_account_receivable_id
        elif self.is_purchase_document(include_receipts=True) and self.partner_id:
            self.invoice_payment_term_id = self.partner_id.property_supplier_payment_term_id or self.invoice_payment_term_id
            new_term_account = self.partner_id.commercial_partner_id.property_account_payable_id
        else:
            new_term_account = None

        for line in self.line_ids:
            line.partner_id = self.partner_id.commercial_partner_id

            if new_term_account and line.account_id.user_type_id.type in ('receivable', 'payable'):
                line.account_id = new_term_account

        self._compute_bank_partner_id()
        bank_ids = self.bank_partner_id.bank_ids.filtered(lambda bank: not bank.company_id or bank.company_id == self.company_id)
        self.partner_bank_id = bank_ids and bank_ids[0]

        # Find the new fiscal position.
        delivery_partner = self.partner_shipping_id
        self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(
            self.partner_id, delivery=delivery_partner)
        self._recompute_dynamic_lines()
        if warning:
            return {'warning': warning}

    @api.onchange('date', 'currency_id')
    def _onchange_currency(self):
        currency = self.currency_id or self.company_id.currency_id

        if self.is_invoice(include_receipts=True):
            for line in self._get_lines_onchange_currency():
                line.currency_id = currency
                line._onchange_currency()
        else:
            for line in self.line_ids:
                line._onchange_currency()

        self._recompute_dynamic_lines(recompute_tax_base_amount=True)

    @api.onchange('payment_reference')
    def _onchange_payment_reference(self):
        for line in self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
            line.name = self.payment_reference or ''

    @api.onchange('invoice_vendor_bill_id')
    def _onchange_invoice_vendor_bill(self):
        if self.invoice_vendor_bill_id:
            # Copy invoice lines.
            for line in self.invoice_vendor_bill_id.invoice_line_ids:
                copied_vals = line.copy_data()[0]
                copied_vals['move_id'] = self.id
                new_line = self.env['account.move.line'].new(copied_vals)
                new_line.recompute_tax_line = True

            # Copy payment terms.
            self.invoice_payment_term_id = self.invoice_vendor_bill_id.invoice_payment_term_id

            # Copy currency.
            if self.currency_id != self.invoice_vendor_bill_id.currency_id:
                self.currency_id = self.invoice_vendor_bill_id.currency_id

            # Reset
            self.invoice_vendor_bill_id = False
            self._recompute_dynamic_lines()


    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        current_invoice_lines = self.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)
        others_lines = self.line_ids - current_invoice_lines
        if others_lines and current_invoice_lines - self.invoice_line_ids:
            others_lines[0].recompute_tax_line = True
        self.line_ids = others_lines + self.invoice_line_ids
        self._onchange_recompute_dynamic_lines()

    @api.onchange('line_ids', 'invoice_payment_term_id', 'invoice_date_due', 'invoice_cash_rounding_id', 'invoice_vendor_bill_id')
    def _onchange_recompute_dynamic_lines(self):
        self._recompute_dynamic_lines()

    @api.onchange('tax_totals_json')
    def _onchange_tax_totals_json(self):
        """ This method is triggered by the tax group widget. It allows modifying the right
            move lines depending on the tax group whose amount got edited.
        """
        for move in self:
            if not move.is_invoice(include_receipts=True):
                continue

            invoice_totals = json.loads(move.tax_totals_json)
            for amount_by_group_list in invoice_totals['groups_by_subtotal'].values():
                for amount_by_group in amount_by_group_list:
                    tax_lines = move.line_ids.filtered(lambda line: line.tax_group_id.id == amount_by_group['tax_group_id'])

                    if tax_lines:
                        first_tax_line = tax_lines[0]
                        tax_group_old_amount = sum(tax_lines.mapped('amount_currency'))
                        sign = -1 if move.is_inbound() else 1
                        delta_amount = tax_group_old_amount * sign - amount_by_group['tax_group_amount']

                        if not move.currency_id.is_zero(delta_amount):
                            first_tax_line.amount_currency = first_tax_line.amount_currency - delta_amount * sign
                            # We have to trigger the on change manually because we don"t change the value of
                            # amount_currency in the view.
                            first_tax_line._onchange_amount_currency()

            move._recompute_dynamic_lines()

    @api.onchange('partner_shipping_id', 'company_id')
    def _onchange_partner_shipping_id(self):
        """
        Trigger the change of fiscal position when the shipping address is modified.
        """
        fiscal_position = self.env['account.fiscal.position']\
            .with_company(self.company_id)\
            ._get_fiscal_position(self.partner_id, delivery=self.partner_shipping_id)

        if fiscal_position:
            self.fiscal_position_id = fiscal_position

    def _get_tax_force_sign(self):
        """ The sign must be forced to a negative sign in case the balance is on credit
            to avoid negatif taxes amount.
            Example - Customer Invoice :
            Fixed Tax  |  unit price  |   discount   |  amount_tax  | amount_total |
            -------------------------------------------------------------------------
                0.67   |      115      |     100%     |    - 0.67    |      0
            -------------------------------------------------------------------------"""
        self.ensure_one()
        return -1 if self.move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: recompute only the tax_base_amount field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin
        sign = -1 if self.is_inbound(include_receipts=True) else 1

        def fill_accounting_tax_vals(update_vals):
            currency = self.env['res.currency'].browse(update_vals['currency_id'])
            tax_amount = update_vals.pop('tax_amount')

            if currency.is_zero(tax_amount):
                return True

            tax_rep = self.env['account.tax.repartition.line'].browse(update_vals['tax_repartition_line_id'])
            tax_id = update_vals.pop('tax_id')
            if tax_id == tax_rep.tax_id.id:
                group_tax = None
            else:
                group_tax = self.env['account.tax'].browse(tax_id)

            tax_base_amount = sign * currency._convert(
                update_vals['tax_base_amount'],
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )
            tax_base_amount = self._get_base_amount_to_display(tax_base_amount, tax_rep, group_tax)
            amount_currency = sign * tax_amount
            balance = currency._convert(
                amount_currency,
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )

            update_vals.update({
                'name': tax_rep.tax_id.name,
                'tax_base_amount': tax_base_amount,
                'amount_currency': amount_currency,
                'debit': self._get_debit_from_balance(balance, currency.id),
                'credit': self._get_credit_from_balance(balance, currency.id),
                'exclude_from_invoice_tab': True,
                'currency_id': currency.id,
                'group_tax_id': group_tax.id if group_tax else None,
            })

        line_ids_commands = []
        is_invoice = self.is_invoice(include_receipts=True)

        if is_invoice:
            base_lines = self.line_ids.filtered(lambda x: not x.display_type and not x.exclude_from_invoice_tab)
            force_sign = 1
        else:
            base_lines = self.line_ids.filtered(lambda x: not x.display_type and not x.tax_repartition_line_id)
            force_sign = self._get_tax_force_sign()
        tax_lines = self.line_ids.filtered(lambda x: not x.display_type and x.tax_repartition_line_id)

        tax_results = self.env['account.tax'].with_context(force_sign=force_sign)._compute_taxes(
            [x._convert_to_tax_base_line_dict() for x in base_lines],
            tax_lines=[x._convert_to_tax_line_dict() for x in tax_lines],
            handle_price_include=is_invoice,
            include_caba_tags=self.always_tax_exigible,
        )

        # ==== BASE LINES =====

        if not recompute_tax_base_amount:

            # Recompute 'tax_tag_ids'.
            for base_line_vals, to_update in tax_results['base_lines_to_update']:
                base_line = base_line_vals['record']
                line_ids_commands.append(Command.update(base_line.id, {
                    'tax_tag_ids': to_update['tax_tag_ids'],
                }))

        # ===== TAX LINES =====

        # Tax lines that are no longer needed.
        if not recompute_tax_base_amount:
            for tax_line_vals in tax_results['tax_lines_to_delete']:
                tax_line = tax_line_vals['record']
                line_ids_commands.append(Command.unlink(tax_line.id))

        # Newly created tax lines.
        if not recompute_tax_base_amount:
            for tax_line_vals in tax_results['tax_lines_to_add']:
                if not fill_accounting_tax_vals(tax_line_vals):
                    line_ids_commands.append(Command.create(tax_line_vals))

        # Update of existing tax lines.
        for tax_line_vals, to_update in tax_results['tax_lines_to_update']:
            tax_line = tax_line_vals['record']
            if fill_accounting_tax_vals(to_update):
                line_ids_commands.append(Command.unlink(tax_line.id))
            else:
                if recompute_tax_base_amount:
                    fields_to_update = ('tax_base_amount',)
                else:
                    fields_to_update = ('tax_base_amount', 'amount_currency', 'debit', 'credit')
                line_ids_commands.append(Command.update(tax_line.id, {k: v for k, v in to_update.items() if k in fields_to_update}))

        (self.update if in_draft_mode else self.write)({'line_ids': line_ids_commands})

        if in_draft_mode:
            for tax_line in tax_lines:
                tax_line.update(tax_line._get_fields_onchange_balance(force_computation=True))

    @api.model
    def _get_base_amount_to_display(self, base_amount, tax_rep_ln, parent_tax_group=None):
        """ The base amount returned for taxes by compute_all has is the balance
        of the base line. For inbound operations, positive sign is on credit, so
        we need to invert the sign of this amount before displaying it.
        """
        source_tax = parent_tax_group or tax_rep_ln.invoice_tax_id or tax_rep_ln.refund_tax_id
        if (tax_rep_ln.invoice_tax_id and source_tax.type_tax_use == 'sale') \
           or (tax_rep_ln.refund_tax_id and source_tax.type_tax_use == 'purchase'):
            return -base_amount
        return base_amount

    def _recompute_cash_rounding_lines(self):
        ''' Handle the cash rounding feature on invoices.

        In some countries, the smallest coins do not exist. For example, in Switzerland, there is no coin for 0.01 CHF.
        For this reason, if invoices are paid in cash, you have to round their total amount to the smallest coin that
        exists in the currency. For the CHF, the smallest coin is 0.05 CHF.

        There are two strategies for the rounding:

        1) Add a line on the invoice for the rounding: The cash rounding line is added as a new invoice line.
        2) Add the rounding in the biggest tax amount: The cash rounding line is added as a new tax line on the tax
        having the biggest balance.
        '''
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _compute_cash_rounding(self, total_amount_currency):
            ''' Compute the amount differences due to the cash rounding.
            :param self:                    The current account.move record.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        The amount differences both in company's currency & invoice's currency.
            '''
            difference = self.invoice_cash_rounding_id.compute_difference(self.currency_id, total_amount_currency)
            if self.currency_id == self.company_id.currency_id:
                diff_amount_currency = diff_balance = difference
            else:
                diff_amount_currency = difference
                diff_balance = self.currency_id._convert(diff_amount_currency, self.company_id.currency_id, self.company_id, self.date)
            return diff_balance, diff_amount_currency

        def _apply_cash_rounding(self, diff_balance, diff_amount_currency, cash_rounding_line):
            ''' Apply the cash rounding.
            :param self:                    The current account.move record.
            :param diff_balance:            The computed balance to set on the new rounding line.
            :param diff_amount_currency:    The computed amount in invoice's currency to set on the new rounding line.
            :param cash_rounding_line:      The existing cash rounding line.
            :return:                        The newly created rounding line.
            '''
            rounding_line_vals = {
                'debit': self._get_debit_from_balance(diff_balance, self.currency_id.id),
                'credit': self._get_credit_from_balance(diff_balance, self.currency_id.id),
                'quantity': 1.0,
                'amount_currency': diff_amount_currency,
                'partner_id': self.partner_id.id,
                'move_id': self.id,
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'company_currency_id': self.company_id.currency_id.id,
                'is_rounding_line': True,
                'sequence': 9999,
            }

            if self.invoice_cash_rounding_id.strategy == 'biggest_tax':
                biggest_tax_line = None
                for tax_line in self.line_ids.filtered('tax_repartition_line_id'):
                    if not biggest_tax_line or tax_line.price_subtotal > biggest_tax_line.price_subtotal:
                        biggest_tax_line = tax_line

                # No tax found.
                if not biggest_tax_line:
                    return

                rounding_line_vals.update({
                    'name': _('%s (rounding)', biggest_tax_line.name),
                    'account_id': biggest_tax_line.account_id.id,
                    'tax_repartition_line_id': biggest_tax_line.tax_repartition_line_id.id,
                    'tax_tag_ids': [(6, 0, biggest_tax_line.tax_tag_ids.ids)],
                    'exclude_from_invoice_tab': True,
                })

            elif self.invoice_cash_rounding_id.strategy == 'add_invoice_line':
                if diff_balance > 0.0 and self.invoice_cash_rounding_id.loss_account_id:
                    account_id = self.invoice_cash_rounding_id.loss_account_id.id
                else:
                    account_id = self.invoice_cash_rounding_id.profit_account_id.id
                rounding_line_vals.update({
                    'name': self.invoice_cash_rounding_id.name,
                    'account_id': account_id,
                })

            # Create or update the cash rounding line.
            if cash_rounding_line:
                cash_rounding_line.update({
                    'amount_currency': rounding_line_vals['amount_currency'],
                    'debit': rounding_line_vals['debit'],
                    'credit': rounding_line_vals['credit'],
                    'account_id': rounding_line_vals['account_id'],
                })
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                cash_rounding_line = create_method(rounding_line_vals)

            if in_draft_mode:
                cash_rounding_line.update(cash_rounding_line._get_fields_onchange_balance(force_computation=True))

        existing_cash_rounding_line = self.line_ids.filtered(lambda line: line.is_rounding_line)

        # The cash rounding has been removed.
        if not self.invoice_cash_rounding_id:
            self.line_ids -= existing_cash_rounding_line
            return

        # The cash rounding strategy has changed.
        if self.invoice_cash_rounding_id and existing_cash_rounding_line:
            strategy = self.invoice_cash_rounding_id.strategy
            old_strategy = 'biggest_tax' if existing_cash_rounding_line.tax_line_id else 'add_invoice_line'
            if strategy != old_strategy:
                self.line_ids -= existing_cash_rounding_line
                existing_cash_rounding_line = self.env['account.move.line']

        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        others_lines -= existing_cash_rounding_line
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        diff_balance, diff_amount_currency = _compute_cash_rounding(self, total_amount_currency)

        # The invoice is already rounded.
        if self.currency_id.is_zero(diff_balance) and self.currency_id.is_zero(diff_amount_currency):
            self.line_ids -= existing_cash_rounding_line
            return

        _apply_cash_rounding(self, diff_balance, diff_amount_currency, existing_cash_rounding_line)

    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        self = self.with_company(self.company_id)
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_company(self.journal_id.company_id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=', 'receivable' if self.move_type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                if self.currency_id == self.company_id.currency_id:
                    # Single-currency.
                    return [(b[0], b[1], b[1]) for b in to_compute]
                else:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                currency = self.journal_id.company_id.currency_id
                if currency and currency.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': self._get_debit_from_balance(-balance, currency.id),
                        'credit': self._get_credit_from_balance(-balance, currency.id),
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.payment_reference or '',
                        'debit': self._get_debit_from_balance(-balance, currency.id),
                        'credit': self._get_credit_from_balance(-balance, currency.id),
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate.update(candidate._get_fields_onchange_balance(force_computation=True))
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.payment_reference = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        ''' Recompute all lines that depend on others.

        For example, tax lines depends on base lines (lines having tax_ids set). This is also the case of cash rounding
        lines that depend on base lines or tax lines depending on the cash rounding strategy. When a payment term is set,
        this method will auto-balance the move with payment term lines.

        :param recompute_all_taxes: Force the computation of taxes. If set to False, the computation will be done
                                    or not depending on the field 'recompute_tax_line' in lines.
        '''
        for invoice in self:
            # Dispatch lines and pre-compute some aggregated values like taxes.
            expected_tax_rep_lines = set()
            current_tax_rep_lines = set()
            inv_recompute_all_taxes = recompute_all_taxes
            for line in invoice.line_ids:
                if line.recompute_tax_line:
                    inv_recompute_all_taxes = True
                    line.recompute_tax_line = False
                if line.tax_repartition_line_id:
                    current_tax_rep_lines.add(line.tax_repartition_line_id._origin)
                elif line.tax_ids:
                    if invoice.is_invoice(include_receipts=True):
                        is_refund = invoice.move_type in ('out_refund', 'in_refund')
                    else:
                        tax_type = line.tax_ids[0].type_tax_use
                        is_refund = (tax_type == 'sale' and line.debit) or (tax_type == 'purchase' and line.credit)
                    taxes = line.tax_ids.flatten_taxes_hierarchy()
                    if is_refund:
                        tax_rep_lines = taxes.refund_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    else:
                        tax_rep_lines = taxes.invoice_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    for tax_rep_line in tax_rep_lines:
                        expected_tax_rep_lines.add(tax_rep_line)
            delta_tax_rep_lines = expected_tax_rep_lines - current_tax_rep_lines

            # Compute taxes.
            if inv_recompute_all_taxes:
                invoice._recompute_tax_lines()
            elif recompute_tax_base_amount:
                invoice._recompute_tax_lines(recompute_tax_base_amount=True)
            elif delta_tax_rep_lines and not self._context.get('move_reverse_cancel'):
                invoice._recompute_tax_lines()

            if invoice.is_invoice(include_receipts=True):

                # Compute cash rounding.
                invoice._recompute_cash_rounding_lines()

                # Compute payment terms.
                invoice._recompute_payment_terms_lines()

                # Only synchronize one2many in onchange.
                if invoice != invoice._origin:
                    invoice.invoice_line_ids = invoice.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)

    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            move.company_id = move.journal_id.company_id or move.company_id or self.env.company

    def _get_lines_onchange_currency(self):
        # Override needed for COGS
        return self.line_ids

    def onchange(self, values, field_name, field_onchange):
        # OVERRIDE
        # As the dynamic lines in this model are quite complex, we need to ensure some computations are done exactly
        # at the beginning / at the end of the onchange mechanism. So, the onchange recursivity is disabled.
        return super(AccountMove, self.with_context(recursive_onchanges=False)).onchange(values, field_name, field_onchange)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type')
    def _compute_is_storno(self):
        for move in self:
            move.is_storno = move.is_storno or (move.move_type in ('out_refund', 'in_refund') and move.company_id.account_storno)

    @api.depends('partner_id')
    def _compute_partner_shipping_id(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                addr = move.partner_id.address_get(['delivery'])
                move.partner_shipping_id = addr and addr.get('delivery')
            else:
                move.partner_shipping_id = False

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        def journal_key(move):
            return (move.journal_id, move.journal_id.refund_sequence and move.move_type)

        def date_key(move):
            return (move.date.year, move.date.month)

        grouped = defaultdict(  # key: journal_id, move_type
            lambda: defaultdict(  # key: first adjacent (date.year, date.month)
                lambda: {
                    'records': self.env['account.move'],
                    'format': False,
                    'format_values': False,
                    'reset': False
                }
            )
        )
        self = self.sorted(lambda m: (m.date, m.ref or '', m.id))
        highest_name = self[0]._get_last_sequence(lock=False) if self else False

        # Group the moves by journal and month
        for move in self:
            if not highest_name and move == self[0] and not move.posted_before and move.date:
                # In the form view, we need to compute a default sequence so that the user can edit
                # it. We only check the first move as an approximation (enough for new in form view)
                pass
            elif (move.name and move.name != '/') or move.state != 'posted':
                try:
                    if not move.posted_before:
                        move._constrains_date_sequence()
                    # Has already a name or is not posted, we don't add to a batch
                    continue
                except ValidationError:
                    # Has never been posted and the name doesn't match the date: recompute it
                    pass
            group = grouped[journal_key(move)][date_key(move)]
            if not group['records']:
                # Compute all the values needed to sequence this whole group
                move._set_next_sequence()
                group['format'], group['format_values'] = move._get_sequence_format_param(move.name)
                group['reset'] = move._deduce_sequence_number_reset(move.name)
            group['records'] += move

        # Fusion the groups depending on the sequence reset and the format used because `seq` is
        # the same counter for multiple groups that might be spread in multiple months.
        final_batches = []
        for journal_group in grouped.values():
            journal_group_changed = True
            for date_group in journal_group.values():
                if (
                    journal_group_changed
                    or final_batches[-1]['format'] != date_group['format']
                    or dict(final_batches[-1]['format_values'], seq=0) != dict(date_group['format_values'], seq=0)
                ):
                    final_batches += [date_group]
                    journal_group_changed = False
                elif date_group['reset'] == 'never':
                    final_batches[-1]['records'] += date_group['records']
                elif (
                    date_group['reset'] == 'year'
                    and final_batches[-1]['records'][0].date.year == date_group['records'][0].date.year
                ):
                    final_batches[-1]['records'] += date_group['records']
                else:
                    final_batches += [date_group]

        # Give the name based on previously computed values
        for batch in final_batches:
            for move in batch['records']:
                move.name = batch['format'].format(**batch['format_values'])
                batch['format_values']['seq'] += 1
            batch['records']._compute_split_sequence()

        self.filtered(lambda m: not m.name).name = '/'

    @api.depends('journal_id', 'date')
    def _compute_highest_name(self):
        for record in self:
            record.highest_name = record._get_last_sequence(lock=False)

    @api.depends('name', 'journal_id')
    def _compute_made_sequence_hole(self):
        self.env.cr.execute("""
            SELECT this.id
              FROM account_move this
         LEFT JOIN account_move other ON this.journal_id = other.journal_id
                                     AND this.sequence_prefix = other.sequence_prefix
                                     AND this.sequence_number = other.sequence_number + 1
             WHERE other.id IS NULL
               AND this.sequence_number != 1
               AND this.name != '/'
               AND this.id = ANY(%(move_ids)s)
        """, {
            'move_ids': self.ids,
        })
        made_sequence_hole = set(r[0] for r in self.env.cr.fetchall())
        for move in self:
            move.made_sequence_hole = move.id in made_sequence_hole

    @api.onchange('name', 'highest_name')
    def _onchange_name_warning(self):
        if self.name and self.name != '/' and self.name <= (self.highest_name or ''):
            self.show_name_warning = True
        else:
            self.show_name_warning = False

        origin_name = self._origin.name
        if not origin_name or origin_name == '/':
            origin_name = self.highest_name
        if self.name and self.name != '/' and origin_name and origin_name != '/':
            new_format, new_format_values = self._get_sequence_format_param(self.name)
            origin_format, origin_format_values = self._get_sequence_format_param(origin_name)

            if (
                new_format != origin_format
                or dict(new_format_values, seq=0) != dict(origin_format_values, seq=0)
            ):
                changed = _(
                    "It was previously '%(previous)s' and it is now '%(current)s'.",
                    previous=origin_name,
                    current=self.name,
                )
                reset = self._deduce_sequence_number_reset(self.name)
                if reset == 'month':
                    detected = _(
                        "The sequence will restart at 1 at the start of every month.\n"
                        "The year detected here is '%(year)s' and the month is '%(month)s'.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                elif reset == 'year':
                    detected = _(
                        "The sequence will restart at 1 at the start of every year.\n"
                        "The year detected here is '%(year)s'.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                else:
                    detected = _(
                        "The sequence will never restart.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                new_format_values['formatted_seq'] = "{seq:0{seq_length}d}".format(**new_format_values)
                detected = detected % new_format_values
                return {'warning': {
                    'title': _("The sequence format has changed."),
                    'message': "%s\n\n%s" % (changed, detected)
                }}

    def _get_last_sequence_domain(self, relaxed=False):
        self.ensure_one()
        if not self.date or not self.journal_id:
            return "WHERE FALSE", {}
        where_string = "WHERE journal_id = %(journal_id)s AND name != '/'"
        param = {'journal_id': self.journal_id.id}

        if not relaxed:
            domain = [('journal_id', '=', self.journal_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]
            if self.journal_id.refund_sequence:
                refund_types = ('out_refund', 'in_refund')
                domain += [('move_type', 'in' if self.move_type in refund_types else 'not in', refund_types)]
            reference_move_name = self.search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
            if not reference_move_name:
                reference_move_name = self.search(domain, order='date asc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(reference_move_name)
            if sequence_number_reset == 'year':
                where_string += " AND date_trunc('year', date::timestamp without time zone) = date_trunc('year', %(date)s) "
                param['date'] = self.date
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
            elif sequence_number_reset == 'month':
                where_string += " AND date_trunc('month', date::timestamp without time zone) = date_trunc('month', %(date)s) "
                param['date'] = self.date
            else:
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

            if param.get('anti_regex') and not self.journal_id.sequence_override_regex:
                where_string += " AND sequence_prefix !~ %(anti_regex)s "

        if self.journal_id.refund_sequence:
            if self.move_type in ('out_refund', 'in_refund'):
                where_string += " AND move_type IN ('out_refund', 'in_refund') "
            else:
                where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "

        return where_string, param

    def _get_starting_sequence(self):
        self.ensure_one()
        if self.journal_id.type == 'sale':
            starting_sequence = "%s/%04d/00000" % (self.journal_id.code, self.date.year)
        else:
            starting_sequence = "%s/%04d/%02d/0000" % (self.journal_id.code, self.date.year, self.date.month)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        return starting_sequence

    @api.depends('move_type')
    def _compute_type_name(self):
        type_name_mapping = {k: v for k, v in
                             self._fields['move_type']._description_selection(self.env)}
        replacements = {'out_invoice': _('Invoice'), 'out_refund': _('Credit Note')}

        for record in self:
            name = type_name_mapping[record.move_type]
            record.type_name = replacements.get(record.move_type, name)

    @api.depends('move_type')
    def _compute_invoice_filter_type_domain(self):
        for move in self:
            if move.is_sale_document(include_receipts=True):
                move.invoice_filter_type_domain = 'sale'
            elif move.is_purchase_document(include_receipts=True):
                move.invoice_filter_type_domain = 'purchase'
            else:
                move.invoice_filter_type_domain = False

    @api.depends('partner_id')
    def _compute_commercial_partner_id(self):
        for move in self:
            move.commercial_partner_id = move.partner_id.commercial_partner_id

    @api.depends('commercial_partner_id')
    def _compute_bank_partner_id(self):
        for move in self:
            if move.is_inbound():
                move.bank_partner_id = move.company_id.partner_id
            else:
                move.bank_partner_id = move.commercial_partner_id

    @api.model
    def _get_invoice_in_payment_state(self):
        ''' Hook to give the state when the invoice becomes fully paid. This is necessary because the users working
        with only invoicing don't want to see the 'in_payment' state. Then, this method will be overridden in the
        accountant module to enable the 'in_payment' state. '''
        return 'paid'

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        stored_ids = tuple(self.ids)
        if stored_ids:
            self.env['account.partial.reconcile'].flush(self.env['account.partial.reconcile']._fields)
            self.env['account.payment'].flush(fnames=['is_matched'])

            queries = []
            for source_field, counterpart_field in (('debit', 'credit'), ('credit', 'debit')):
                queries.append(f'''
                    SELECT
                        source_line.id AS source_line_id,
                        source_line.move_id AS source_move_id,
                        account_type.type AS source_line_account_type,
                        ARRAY_AGG(counterpart_move.reversed_entry_id)
                            FILTER (WHERE counterpart_move.reversed_entry_id IS NOT NULL) AS counterpart_reversed_entry_ids,
                        ARRAY_AGG(counterpart_move.move_type)
                            FILTER (WHERE counterpart_move.reversed_entry_id IS NOT NULL) AS counterpart_move_types,
                        COALESCE(BOOL_AND(COALESCE(pay.is_matched, FALSE))
                            FILTER (WHERE counterpart_move.payment_id IS NOT NULL), TRUE) AS all_payments_matched
                    FROM account_partial_reconcile part
                    JOIN account_move_line source_line ON source_line.id = part.{source_field}_move_id
                    JOIN account_account account ON account.id = source_line.account_id
                    JOIN account_account_type account_type ON account_type.id = account.user_type_id
                    JOIN account_move_line counterpart_line ON counterpart_line.id = part.{counterpart_field}_move_id
                    JOIN account_move counterpart_move ON counterpart_move.id = counterpart_line.move_id
                    LEFT JOIN account_payment pay ON pay.id = counterpart_move.payment_id
                    WHERE source_line.move_id IN %s AND counterpart_line.move_id != source_line.move_id
                    GROUP BY source_line_id, source_move_id, source_line_account_type
                ''')

            self._cr.execute(' UNION ALL '.join(queries), [stored_ids, stored_ids])

            payment_data = defaultdict(lambda: [])
            for row in self._cr.dictfetchall():
                payment_data[row['source_move_id']].append(row)
        else:
            payment_data = {}

        for move in self:

            if move.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                move.payment_state = move.payment_state
                continue

            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_to_pay = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = move._get_lines_onchange_currency().currency_id

            for line in move.line_ids:
                if move._payment_state_matters():
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_to_pay += line.balance
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
            move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)

            currency = currencies if len(currencies) == 1 else move.company_id.currency_id

            # === Compute 'payment_state' ===
            reconciliation_vals = payment_data.get(move.id, [])
            payment_state_matters = move._payment_state_matters()

            # Restrict on 'receivable'/'payable' lines for invoices/expense entries.
            if payment_state_matters:
                reconciliation_vals = [x for x in reconciliation_vals if x['source_line_account_type'] in ('receivable', 'payable')]

            new_pmt_state = 'not_paid'
            if move.state == 'posted':

                # Posted invoice/expense entry.
                if payment_state_matters:

                    if currency.is_zero(move.amount_residual):
                        # Check if the invoice/expense entry is fully paid or 'in_payment'.
                        if all(x['all_payments_matched'] for x in reconciliation_vals):
                            new_pmt_state = 'paid'
                        else:
                            new_pmt_state = move._get_invoice_in_payment_state()
                    elif reconciliation_vals:
                        new_pmt_state = 'partial'

                # Check if the journal entry is 'reversed' (1 on 1 full reconciliation with entries being of the opposite types)
                if new_pmt_state == 'paid':
                    reverse_move_types = []
                    for x in reconciliation_vals:
                        for rec_move_type, rec_reversed_entry_id in zip(x['counterpart_move_types'] or [], x['counterpart_reversed_entry_ids'] or []):
                            if rec_reversed_entry_id == move.id:
                                reverse_move_types.append(rec_move_type)

                    if (move.move_type in ('in_invoice', 'in_receipt') and reverse_move_types == ['in_refund']) \
                      or (move.move_type in ('out_invoice', 'out_receipt') and reverse_move_types == ['out_refund']) \
                      or (move.move_type in ('entry', 'out_refund', 'in_refund') and reverse_move_types == ['entry']):
                        new_pmt_state = 'reversed'

            move.payment_state = new_pmt_state

    def _inverse_amount_total(self):
        for move in self:
            if len(move.line_ids) != 2 or move.is_invoice(include_receipts=True):
                continue

            to_write = []

            amount_currency = abs(move.amount_total)
            balance = move.currency_id._convert(amount_currency, move.company_currency_id, move.company_id, move.date)

            for line in move.line_ids:
                if not line.currency_id.is_zero(balance - abs(line.balance)):
                    to_write.append((1, line.id, {
                        'debit': line.balance > 0.0 and balance or 0.0,
                        'credit': line.balance < 0.0 and balance or 0.0,
                        'amount_currency': line.balance > 0.0 and amount_currency or -amount_currency,
                    }))

            move.write({'line_ids': to_write})

    def _get_domain_matching_suspense_moves(self):
        self.ensure_one()
        domain = self.env['account.move.line']._get_suspense_moves_domain()
        domain += ['|', ('partner_id', '=?', self.partner_id.id), ('partner_id', '=', False)]
        if self.is_inbound():
            domain.append(('balance', '=', -self.amount_residual))
        else:
            domain.append(('balance', '=', self.amount_residual))
        return domain

    def _compute_has_matching_suspense_amount(self):
        for r in self:
            res = False
            if r.state == 'posted' and r.is_invoice() and r.payment_state == 'not_paid':
                domain = r._get_domain_matching_suspense_moves()
                #there are more than one but less than 5 suspense moves matching the residual amount
                if (0 < self.env['account.move.line'].search_count(domain) < 5):
                    domain2 = [
                        ('payment_state', '=', 'not_paid'),
                        ('state', '=', 'posted'),
                        ('amount_residual', '=', r.amount_residual),
                        ('move_type', '=', r.move_type)]
                    #there are less than 5 other open invoices of the same type with the same residual
                    if self.env['account.move'].search_count(domain2) < 5:
                        res = True
            r.invoice_has_matching_suspense_amount = res

    @api.depends('partner_id', 'invoice_source_email', 'partner_id.name')
    def _compute_invoice_partner_display_info(self):
        for move in self:
            vendor_display_name = move.partner_id.display_name
            if not vendor_display_name:
                if move.invoice_source_email:
                    vendor_display_name = _('@From: %(email)s', email=move.invoice_source_email)
                else:
                    vendor_display_name = _('#Created by: %s', move.sudo().create_uid.name or self.env.user.name)
            move.invoice_partner_display_name = vendor_display_name

    @api.depends('currency_id')
    def _compute_display_inactive_currency_warning(self):
        for move in self.with_context(active_test=False):
            move.display_inactive_currency_warning = not move.currency_id.active

    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency': move.currency_id.symbol,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'position': move.currency_id.position,
                    'digits': [69, move.currency_id.decimal_places],
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                })

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = json.dumps(payments_widget_vals)
            move.invoice_has_outstanding = True

    def _get_reconciled_info_JSON_values(self):
        self.ensure_one()
        reconciled_vals = []
        reconciled_partials, exchange_diff_moves = self._get_reconciled_invoices_partials()
        for partial, amount, counterpart_line in reconciled_partials:
            if counterpart_line.move_id.ref:
                reconciliation_ref = '%s (%s)' % (counterpart_line.move_id.name, counterpart_line.move_id.ref)
            else:
                reconciliation_ref = counterpart_line.move_id.name

            currency = self.currency_id
            is_exchange = counterpart_line.move_id.id in exchange_diff_moves
            if is_exchange:
                amount = counterpart_line.move_id.amount_total_signed
                currency = self.company_id.currency_id

            reconciled_vals.append({
                'name': counterpart_line.name,
                'journal_name': counterpart_line.journal_id.name,
                'amount': amount,
                'currency': currency.symbol,
                'digits': [69, currency.decimal_places],
                'position': currency.position,
                'date': counterpart_line.date,
                'payment_id': counterpart_line.id,
                'partial_id': partial.id,
                'account_payment_id': counterpart_line.payment_id.id,
                'payment_method_name': counterpart_line.payment_id.payment_method_line_id.name,
                'move_id': counterpart_line.move_id.id,
                'ref': reconciliation_ref,
                # these are necessary for the views to change depending on the values
                'is_exchange': is_exchange,
                'amount_company_currency': formatLang(self.env, abs(counterpart_line.balance), currency_obj=counterpart_line.company_id.currency_id),
                'amount_foreign_currency': formatLang(self.env, abs(counterpart_line.amount_currency), currency_obj=counterpart_line.currency_id) if counterpart_line.currency_id != counterpart_line.company_id.currency_id else False
            })
        return reconciled_vals

    @api.depends('move_type', 'line_ids.amount_residual')
    def _compute_payments_widget_reconciled_info(self):
        for move in self:
            payments_widget_vals = {'title': _('Less Payment'), 'outstanding': False, 'content': []}

            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                payments_widget_vals['content'] = move._get_reconciled_info_JSON_values()

            if payments_widget_vals['content']:
                move.invoice_payments_widget = json.dumps(payments_widget_vals, default=date_utils.json_default)
            else:
                move.invoice_payments_widget = json.dumps(False)

    @api.depends('line_ids.amount_currency', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id', 'currency_id', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines = move.line_ids.filtered(lambda x: not x.display_type and not x.exclude_from_invoice_tab)
                tax_lines = move.line_ids.filtered(lambda x: not x.display_type and x.tax_repartition_line_id)

                tax_totals = self.env['account.tax']._prepare_tax_totals_json(
                    [x._convert_to_tax_base_line_dict() for x in base_lines],
                    move.currency_id,
                    tax_lines=[x._convert_to_tax_line_dict() for x in tax_lines],
                )
                tax_totals['allow_tax_edition'] = move.is_purchase_document(include_receipts=True)

                move.tax_totals_json = json.dumps(tax_totals)
            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals_json = None

    @api.depends('date', 'line_ids.debit', 'line_ids.credit', 'line_ids.tax_line_id', 'line_ids.tax_ids', 'line_ids.tax_tag_ids')
    def _compute_tax_lock_date_message(self):
        for move in self:
            invoice_date = move.invoice_date or fields.Date.context_today(move)
            accounting_date = move.date or fields.Date.context_today(move)
            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(accounting_date, affects_tax_report)
            if lock_dates:
                accounting_date = move._get_accounting_date(invoice_date, affects_tax_report)
                lock_date, lock_type = lock_dates[-1]
                tax_lock_date_message = _(
                    "The accounting date being set prior to the %(lock_type)s lock date %(lock_date)s,"
                    " it will be changed to %(accounting_date)s upon posting.",
                    lock_type=lock_type,
                    lock_date=format_date(move.env, lock_date),
                    accounting_date=format_date(move.env, accounting_date))
                for lock_date, lock_type in lock_dates[:-1]:
                    tax_lock_date_message += _(" The %(lock_type)s lock date is set on %(lock_date)s.",
                                               lock_type=lock_type,
                                               lock_date=format_date(move.env, lock_date))
                move.tax_lock_date_message = tax_lock_date_message
            else:
                move.tax_lock_date_message = False

    @api.depends('line_ids.account_id.internal_type')
    def _compute_always_tax_exigible(self):
        for record in self:
            # We need to check is_invoice as well because always_tax_exigible is used to
            # set the tags as well, during the encoding. So, if no receivable/payable
            # line has been created yet, the invoice would be detected as always exigible,
            # and set the tags on some lines ; which would be wrong.
            record.always_tax_exigible = not record.is_invoice(True) \
                                         and not record._collect_tax_cash_basis_values()

    @api.depends('restrict_mode_hash_table', 'state')
    def _compute_show_reset_to_draft_button(self):
        for move in self:
            move.show_reset_to_draft_button = not move.restrict_mode_hash_table and move.state in ('posted', 'cancel')

    @api.depends('company_id.account_fiscal_country_id', 'fiscal_position_id.country_id', 'fiscal_position_id.foreign_vat')
    def _compute_tax_country_id(self):
        for record in self:
            if record.fiscal_position_id.foreign_vat:
                record.tax_country_id = record.fiscal_position_id.country_id
            else:
                record.tax_country_id = record.company_id.account_fiscal_country_id

    @api.depends('tax_country_id.code')
    def _compute_tax_country_code(self):
        for record in self:
            record.tax_country_code = record.tax_country_id.code

    @api.depends('company_id', 'partner_id', 'amount_total_signed')
    def _compute_partner_credit_warning(self):
        for move in self:
            move.with_company(move.company_id)
            move.partner_credit_warning = ''
            show_warning = move.state == 'draft' and \
                           move.move_type == 'out_invoice' and \
                           move.company_id.account_use_credit_limit
            if show_warning:
                updated_credit = move.partner_id.credit + move.amount_total_signed
                move.partner_credit_warning = self._build_credit_warning_message(move, updated_credit)

    def _build_credit_warning_message(self, record, updated_credit):
        ''' Build the warning message that will be displayed in a yellow banner on top of the current record
            if the partner exceeds a credit limit (set on the company or the partner itself).

            :param record:                  The record where the warning will appear (Invoice, Sales Order...).
            :param updated_credit (float):  The partner's updated credit limit including the current record.
            :return (str):                  The warning message to be showed.
        '''
        credit_limit = record.partner_id.credit_limit
        if (not credit_limit) or updated_credit <= credit_limit:
            return ''
        msg = _('%s has reached its Credit Limit of : %s\nTotal amount due ',
                record.partner_id.name,
                formatLang(self.env, credit_limit, currency_obj=record.company_id.currency_id))
        if updated_credit > record.partner_id.credit:
            msg += _('(including this document) ')
        msg += ': %s' % formatLang(self.env, updated_credit, currency_obj=record.company_id.currency_id)
        return msg

    # -------------------------------------------------------------------------
    # BUSINESS MODELS SYNCHRONIZATION
    # -------------------------------------------------------------------------

    def _synchronize_business_models(self, changed_fields):
        ''' Ensure the consistency between:
        account.payment & account.move
        account.bank.statement.line & account.move

        The idea is to call the method performing the synchronization of the business
        models regarding their related journal entries. To avoid cycling, the
        'skip_account_move_synchronization' key is used through the context.

        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        self_sudo = self.sudo()
        self_sudo.payment_id._synchronize_from_moves(changed_fields)
        self_sudo.statement_line_id._synchronize_from_moves(changed_fields)

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        moves = self.filtered(lambda move: move.state == 'posted')
        if not moves:
            return

        self.flush(['name', 'journal_id', 'move_type', 'state'])

        # /!\ Computed stored fields are not yet inside the database.
        self._cr.execute('''
            SELECT move2.id, move2.name
            FROM account_move move
            INNER JOIN account_move move2 ON
                move2.name = move.name
                AND move2.journal_id = move.journal_id
                AND move2.move_type = move.move_type
                AND move2.id != move.id
            WHERE move.id IN %s AND move2.state = 'posted'
        ''', [tuple(moves.ids)])
        res = self._cr.fetchall()
        if res:
            raise ValidationError(_('Posted journal entry must have an unique sequence number per company.\n'
                                    'Problematic numbers: %s\n') % ', '.join(r[1] for r in res))

    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id', 'invoice_date', 'state')
    def _check_duplicate_supplier_reference(self):
        moves = self.filtered(lambda move: move.state == 'posted' and move.is_purchase_document() and move.ref)
        if not moves:
            return

        self.env["account.move"].flush([
            "ref", "move_type", "invoice_date", "journal_id",
            "company_id", "partner_id", "commercial_partner_id",
        ])
        self.env["account.journal"].flush(["company_id"])
        self.env["res.partner"].flush(["commercial_partner_id"])

        # /!\ Computed stored fields are not yet inside the database.
        self._cr.execute('''
            SELECT move2.id
            FROM account_move move
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_partner partner ON partner.id = move.partner_id
            INNER JOIN account_move move2 ON
                move2.ref = move.ref
                AND move2.company_id = journal.company_id
                AND move2.commercial_partner_id = partner.commercial_partner_id
                AND move2.move_type = move.move_type
                AND (move.invoice_date is NULL OR move2.invoice_date = move.invoice_date)
                AND move2.id != move.id
            WHERE move.id IN %s
        ''', [tuple(moves.ids)])
        duplicated_moves = self.browse([r[0] for r in self._cr.fetchall()])
        if duplicated_moves:
            raise ValidationError(_('Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note:\n%s') % "\n".join(
                duplicated_moves.mapped(lambda m: "%(partner)s - %(ref)s - %(date)s" % {
                    'ref': m.ref,
                    'partner': m.partner_id.display_name,
                    'date': format_date(self.env, m.invoice_date),
                })
            ))

    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(self.env['account.move.line']._fields)
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            WITH error_moves AS (
                SELECT line.move_id,
                       ROUND(SUM(line.debit - line.credit), currency.decimal_places) balance,
                       bool_or((not is_storno) AND (credit + debit < 0)) negative_normal,
                       bool_or((is_storno) AND (credit + debit > 0)) positive_storno
                  FROM account_move_line line
                  JOIN account_move move ON move.id = line.move_id
                  JOIN account_journal journal ON journal.id = move.journal_id
                  JOIN res_company company ON company.id = journal.company_id
                  JOIN res_currency currency ON currency.id = company.currency_id
                 WHERE line.move_id IN %s
              GROUP BY line.move_id, currency.decimal_places
            )
            SELECT *
              FROM error_moves
             WHERE balance !=0
                OR negative_normal
                OR positive_storno
        ''', [tuple(self.ids)])

        query_res = self._cr.fetchall()
        if query_res:
            error_msg = _("There was a problem with the following move(s):\n")
            for move in query_res:
                id_, balance, negative_normal, positive_storno = move
                error_msg += _("- Move with id %i\n", id_)
                if balance != 0.0:
                    error_msg += _("\tCannot create unbalanced journal entry. The balance is equal to %s\n",
                                   format_amount(self.env, balance, self.currency_id))
                if negative_normal:
                    error_msg += _("\tThe debit and credit should be positive and only one can be set\n")
                if positive_storno:
                    error_msg += _("\tThe debit and credit should be negative and only one can be set\n")
            raise UserError(error_msg)

    def _check_fiscalyear_lock_date(self):
        for move in self:
            lock_date = move.company_id._get_user_fiscal_lock_date()
            if move.date <= lock_date:
                if self.user_has_groups('account.group_account_manager'):
                    message = _("You cannot add/modify entries prior to and inclusive of the lock date %s.", format_date(self.env, lock_date))
                else:
                    message = _("You cannot add/modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role", format_date(self.env, lock_date))
                raise UserError(message)
        return True

    @api.constrains('move_type', 'journal_id')
    def _check_journal_type(self):
        for record in self:
            journal_type = record.journal_id.type

            if record.is_sale_document() and journal_type != 'sale' or record.is_purchase_document() and journal_type != 'purchase':
                raise ValidationError(_("The chosen journal has a type that is not compatible with your invoice type. Sales operations should go to 'sale' journals, and purchase operations to 'purchase' ones."))

    @api.constrains('line_ids', 'fiscal_position_id', 'company_id')
    def _validate_taxes_country(self):
        """ By playing with the fiscal position in the form view, it is possible to keep taxes on the invoices from
        a different country than the one allowed by the fiscal country or the fiscal position.
        This contrains ensure such account.move cannot be kept, as they could generate inconsistencies in the reports.
        """
        self._compute_tax_country_id() # We need to ensure this field has been computed, as we use it in our check
        for record in self:
            amls = record.line_ids
            impacted_countries = amls.tax_ids.country_id | amls.tax_line_id.country_id | amls.tax_tag_ids.country_id
            if impacted_countries and impacted_countries != record.tax_country_id:
                if record.fiscal_position_id and impacted_countries != record.fiscal_position_id.country_id:
                    raise ValidationError(_("This entry contains taxes that are not compatible with your fiscal position. Check the country set in fiscal position and in your tax configuration."))
                raise ValidationError(_("This entry contains one or more taxes that are incompatible with your fiscal country. Check company fiscal country in the settings and tax country in taxes configuration."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def _get_debit_from_balance(self, balance, currency_id):
        currency = self.env['res.currency'].browse(currency_id)
        compare_res = currency.compare_amounts(balance, 0.0)
        if self.is_storno:
            return balance if compare_res < 0.0 else 0.0
        return balance if compare_res > 0.0 else 0.0

    def _get_credit_from_balance(self, balance, currency_id):
        currency = self.env['res.currency'].browse(currency_id)
        compare_res = currency.compare_amounts(balance, 0.0)
        if self.is_storno:
            return -balance if compare_res > 0.0 else 0.0
        return -balance if compare_res < 0.0 else 0.0

    def _move_autocomplete_invoice_lines_values(self):
        ''' This method recomputes dynamic lines on the current journal entry that include taxes, cash rounding
        and payment terms lines.
        '''
        self.ensure_one()

        invoice_lines = self.line_ids.filtered(lambda x: not x.exclude_from_invoice_tab and not x.display_type and not x._origin)
        cached_vals_list = [dict(x._cache) for x in invoice_lines]

        for cached_vals, line in zip(cached_vals_list, invoice_lines):

            # Shortcut to load the demo data.
            # Doing line.account_id triggers a default_get(['account_id']) that could returns a result.
            # A section / note must not have an account_id set.
            if not line._cache.get('account_id') and not line._origin:
                line.account_id = line._get_computed_account() or self.journal_id.default_account_id
            if line.product_id and not line._cache.get('name'):
                line.name = line._get_computed_name()

            # Compute the account before the partner_id
            # In case account_followup is installed
            # Setting the partner will get the account_id in cache
            # If the account_id is not in cache, it will trigger the default value
            # Which is wrong in some case
            # It's better to set the account_id before the partner_id
            # Ensure related fields are well copied.
            if line.partner_id != self.partner_id.commercial_partner_id:
                line.partner_id = self.partner_id.commercial_partner_id

            line.date = self.date
            line.recompute_tax_line = True
            line.currency_id = self.currency_id

            for k, v in cached_vals.items():
                field = line._fields[k]
                if field.compute and not field.readonly:
                    line[k] = v

        self.line_ids._onchange_price_subtotal()
        self._recompute_dynamic_lines(recompute_all_taxes=True)

        values = self._convert_to_write(self._cache)
        values.pop('invoice_line_ids', None)
        return values

    @api.model
    def _move_autocomplete_invoice_lines_create(self, vals_list):
        ''' During the create of an account.move with only 'invoice_line_ids' set and not 'line_ids', this method is called
        to auto compute accounting lines of the invoice. In that case, accounts will be retrieved and taxes, cash rounding
        and payment terms will be computed. At the end, the values will contains all accounting lines in 'line_ids'
        and the moves should be balanced.

        :param vals_list:   The list of values passed to the 'create' method.
        :return:            Modified list of values.
        '''
        new_vals_list = []
        for vals in vals_list:
            vals = dict(vals)

            if vals.get('invoice_date') and not vals.get('date'):
                vals['date'] = vals['invoice_date']

            default_move_type = vals.get('move_type') or self._context.get('default_move_type')
            ctx_vals = {}
            if default_move_type:
                ctx_vals['default_move_type'] = default_move_type
            if vals.get('journal_id'):
                ctx_vals['default_journal_id'] = vals['journal_id']
                # reorder the companies in the context so that the company of the journal
                # (which will be the company of the move) is the main one, ensuring all
                # property fields are read with the correct company
                journal_company = self.env['account.journal'].browse(vals['journal_id']).company_id
                allowed_companies = self._context.get('allowed_company_ids', journal_company.ids)
                reordered_companies = sorted(allowed_companies, key=lambda cid: cid != journal_company.id)
                ctx_vals['allowed_company_ids'] = reordered_companies
            self_ctx = self.with_context(**ctx_vals)
            vals = self_ctx._add_missing_default_values(vals)

            is_invoice = vals.get('move_type') in self.get_invoice_types(include_receipts=True)

            if 'line_ids' in vals:
                vals.pop('invoice_line_ids', None)
                new_vals_list.append(vals)
                continue

            if is_invoice and 'invoice_line_ids' in vals:
                vals['line_ids'] = vals['invoice_line_ids']

            vals.pop('invoice_line_ids', None)

            move = self_ctx.new(vals)
            new_vals_list.append(move._move_autocomplete_invoice_lines_values())

        return new_vals_list

    def _move_autocomplete_invoice_lines_write(self, vals):
        ''' During the write of an account.move with only 'invoice_line_ids' set and not 'line_ids', this method is called
        to auto compute accounting lines of the invoice. In that case, accounts will be retrieved and taxes, cash rounding
        and payment terms will be computed. At the end, the values will contains all accounting lines in 'line_ids'
        and the moves should be balanced.

        :param vals_list:   A python dict representing the values to write.
        :return:            True if the auto-completion did something, False otherwise.
        '''
        enable_autocomplete = 'invoice_line_ids' in vals and 'line_ids' not in vals and True or False

        if not enable_autocomplete:
            return False

        vals['line_ids'] = vals.pop('invoice_line_ids')
        for invoice in self:
            invoice_new = invoice.with_context(
                default_move_type=invoice.move_type,
                default_journal_id=invoice.journal_id.id,
                default_partner_id=invoice.partner_id.id,
                default_currency_id=invoice.currency_id.id,
            ).new(origin=invoice)
            invoice_new.update(vals)
            values = invoice_new._move_autocomplete_invoice_lines_values()
            values.pop('invoice_line_ids', None)
            invoice.write(values)
        return True

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if (fields.Date.to_date(default.get('date')) or self.date) <= self.company_id._get_user_fiscal_lock_date():
            default['date'] = self.company_id._get_user_fiscal_lock_date() + timedelta(days=1)
        if self.move_type == 'entry':
            default['partner_id'] = False
        if not self.journal_id.active:
            default['journal_id'] = self.with_context(
                default_company_id=self.company_id.id,
                default_move_type=self.move_type,
            )._get_default_journal().id
        copied_am = super().copy(default)
        copied_am._message_log(body=_(
            'This entry has been duplicated from %s',
            self._get_html_link()
        ))

        if copied_am.is_invoice(include_receipts=True):
            # Make sure to recompute payment terms. This could be necessary if the date is different for example.
            # Also, this is necessary when creating a credit note because the current invoice is copied.
            copied_am._recompute_payment_terms_lines()

        return copied_am

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        if any('state' in vals and vals.get('state') == 'posted' for vals in vals_list):
            raise UserError(_('You cannot create a move already in the posted state. Please create a draft move and post it after.'))

        vals_list = self._move_autocomplete_invoice_lines_create(vals_list)
        return super(AccountMove, self).create(vals_list)

    def write(self, vals):
        for move in self:
            if (move.restrict_mode_hash_table and move.state == "posted" and set(vals).intersection(INTEGRITY_HASH_MOVE_FIELDS)):
                raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(INTEGRITY_HASH_MOVE_FIELDS))
            if (move.restrict_mode_hash_table and move.inalterable_hash and 'inalterable_hash' in vals) or (move.secure_sequence_number and 'secure_sequence_number' in vals):
                raise UserError(_('You cannot overwrite the values ensuring the inalterability of the accounting.'))
            if (move.posted_before and 'journal_id' in vals and move.journal_id.id != vals['journal_id']):
                raise UserError(_('You cannot edit the journal of an account move if it has been posted once.'))
            if (move.name and move.name != '/' and move.sequence_number not in (0, 1) and 'journal_id' in vals and move.journal_id.id != vals['journal_id']):
                raise UserError(_('You cannot edit the journal of an account move if it already has a sequence number assigned.'))

            # You can't change the date of a move being inside a locked period.
            if move.state == "posted" and 'date' in vals and move.date != vals['date']:
                move._check_fiscalyear_lock_date()
                move.line_ids._check_tax_lock_date()

            # You can't post subtract a move to a locked period.
            if 'state' in vals and move.state == 'posted' and vals['state'] != 'posted':
                move._check_fiscalyear_lock_date()
                move.line_ids._check_tax_lock_date()

            if move.journal_id.sequence_override_regex and vals.get('name') and vals['name'] != '/' and not re.match(move.journal_id.sequence_override_regex, vals['name']):
                if not self.env.user.has_group('account.group_account_manager'):
                    raise UserError(_('The Journal Entry sequence is not conform to the current format. Only the Advisor can change it.'))
                move.journal_id.sequence_override_regex = False

        if self._move_autocomplete_invoice_lines_write(vals):
            res = True
        else:
            vals.pop('invoice_line_ids', None)
            res = super(AccountMove, self.with_context(check_move_validity=False, skip_account_move_synchronization=True)).write(vals)

        # You can't change the date of a not-locked move to a locked period.
        # You can't post a new journal entry inside a locked period.
        if 'date' in vals or 'state' in vals:
            posted_move = self.filtered(lambda m: m.state == 'posted')
            posted_move._check_fiscalyear_lock_date()
            posted_move.line_ids._check_tax_lock_date()

        if ('state' in vals and vals.get('state') == 'posted'):
            for move in self.filtered(lambda m: m.restrict_mode_hash_table and not(m.secure_sequence_number or m.inalterable_hash)).sorted(lambda m: (m.date, m.ref or '', m.id)):
                new_number = move.journal_id.secure_sequence_id.next_by_id()
                vals_hashing = {'secure_sequence_number': new_number,
                                'inalterable_hash': move._get_new_hash(new_number)}
                res |= super(AccountMove, move).write(vals_hashing)

        # Ensure the move is still well balanced.
        if 'line_ids' in vals and self._context.get('check_move_validity', True):
            self._check_balanced()

        self._synchronize_business_models(set(vals.keys()))

        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_forbid_parts_of_chain(self):
        """ Moves with a sequence number can only be deleted if they are the last element of a chain of sequence.
        If they are not, deleting them would create a gap. If the user really wants to do this, he still can
        explicitly empty the 'name' field of the move; but we discourage that practice.
        """
        if not self._context.get('force_delete') and not self.filtered(lambda move: move.name != '/')._is_end_of_seq_chain():
            raise UserError(_(
                "You cannot delete this entry, as it has already consumed a sequence number and is not the last one in the chain. You should probably revert it instead."
            ))

    def unlink(self):
        self.line_ids.unlink()
        return super(AccountMove, self).unlink()

    @api.depends('name', 'state')
    def name_get(self):
        result = []
        for move in self:
            if self._context.get('name_groupby'):
                name = '**%s**, %s' % (format_date(self.env, move.date), move._get_move_display_name())
                if move.ref:
                    name += '     (%s)' % move.ref
                if move.partner_id.name:
                    name += ' - %s' % move.partner_id.name
            else:
                name = move._get_move_display_name(show_ref=True)
            result.append((move.id, name))
        return result

    # -------------------------------------------------------------------------
    # RECONCILIATION METHODS
    # -------------------------------------------------------------------------

    def _collect_tax_cash_basis_values(self):
        ''' Collect all information needed to create the tax cash basis journal entries:
        - Determine if a tax cash basis journal entry is needed.
        - Compute the lines to be processed and the amounts needed to compute a percentage.
        :return: A dictionary:
            * move:                     The current account.move record passed as parameter.
            * to_process_lines:         A tuple (caba_treatment, line) where:
                                            - caba_treatment is either 'tax' or 'base', depending on what should
                                              be considered on the line when generating the caba entry.
                                              For example, a line with tax_ids=caba and tax_line_id=non_caba
                                              will have a 'base' caba treatment, as we only want to treat its base
                                              part in the caba entry (the tax part is already exigible on the invoice)

                                            - line is an account.move.line record being not exigible on the tax report.
            * currency:                 The currency on which the percentage has been computed.
            * total_balance:            sum(payment_term_lines.mapped('balance').
            * total_residual:           sum(payment_term_lines.mapped('amount_residual').
            * total_amount_currency:    sum(payment_term_lines.mapped('amount_currency').
            * total_residual_currency:  sum(payment_term_lines.mapped('amount_residual_currency').
            * is_fully_paid:            A flag indicating the current move is now fully paid.
        '''
        self.ensure_one()

        values = {
            'move': self,
            'to_process_lines': [],
            'total_balance': 0.0,
            'total_residual': 0.0,
            'total_amount_currency': 0.0,
            'total_residual_currency': 0.0,
        }

        currencies = set()
        has_term_lines = False
        for line in self.line_ids:
            if line.account_internal_type in ('receivable', 'payable'):
                sign = 1 if line.balance > 0.0 else -1

                currencies.add(line.currency_id)
                has_term_lines = True
                values['total_balance'] += sign * line.balance
                values['total_residual'] += sign * line.amount_residual
                values['total_amount_currency'] += sign * line.amount_currency
                values['total_residual_currency'] += sign * line.amount_residual_currency

            elif line.tax_line_id.tax_exigibility == 'on_payment':
                values['to_process_lines'].append(('tax', line))
                currencies.add(line.currency_id)

            elif 'on_payment' in line.tax_ids.flatten_taxes_hierarchy().mapped('tax_exigibility'):
                values['to_process_lines'].append(('base', line))
                currencies.add(line.currency_id)

        if not values['to_process_lines'] or not has_term_lines:
            return None

        # Compute the currency on which made the percentage.
        if len(currencies) == 1:
            values['currency'] = list(currencies)[0]
        else:
            # Don't support the case where there is multiple involved currencies.
            return None

        # Determine whether the move is now fully paid.
        values['is_fully_paid'] = self.company_id.currency_id.is_zero(values['total_residual']) \
                                  or values['currency'].is_zero(values['total_residual_currency'])

        return values

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    @api.model
    def get_invoice_types(self, include_receipts=False):
        return ['out_invoice', 'out_refund', 'in_refund', 'in_invoice'] + (include_receipts and ['out_receipt', 'in_receipt'] or [])

    def _payment_state_matters(self):
        ''' Determines when new_pmt_state must be upated.
        Method created to allow overrides.
        :return: Boolean '''
        self.ensure_one()
        return self.is_invoice(include_receipts=True)

    def is_invoice(self, include_receipts=False):
        return self.move_type in self.get_invoice_types(include_receipts)

    @api.model
    def get_sale_types(self, include_receipts=False):
        return ['out_invoice', 'out_refund'] + (include_receipts and ['out_receipt'] or [])

    def is_sale_document(self, include_receipts=False):
        return self.move_type in self.get_sale_types(include_receipts)

    @api.model
    def get_purchase_types(self, include_receipts=False):
        return ['in_invoice', 'in_refund'] + (include_receipts and ['in_receipt'] or [])

    def is_purchase_document(self, include_receipts=False):
        return self.move_type in self.get_purchase_types(include_receipts)

    @api.model
    def get_inbound_types(self, include_receipts=True):
        return ['out_invoice', 'in_refund'] + (include_receipts and ['out_receipt'] or [])

    def is_inbound(self, include_receipts=True):
        return self.move_type in self.get_inbound_types(include_receipts)

    @api.model
    def get_outbound_types(self, include_receipts=True):
        return ['in_invoice', 'out_refund'] + (include_receipts and ['in_receipt'] or [])

    def is_outbound(self, include_receipts=True):
        return self.move_type in self.get_outbound_types(include_receipts)

    def _affect_tax_report(self):
        return any(line._affect_tax_report() for line in self.line_ids)

    def _get_invoice_reference_euro_invoice(self):
        """ This computes the reference based on the RF Creditor Reference.
            The data of the reference is the database id number of the invoice.
            For instance, if an invoice is issued with id 43, the check number
            is 07 so the reference will be 'RF07 43'.
        """
        self.ensure_one()
        base = self.id
        check_digits = calc_check_digits('{}RF'.format(base))
        reference = 'RF{} {}'.format(check_digits, " ".join(["".join(x) for x in zip_longest(*[iter(str(base))]*4, fillvalue="")]))
        return reference

    def _get_invoice_reference_euro_partner(self):
        """ This computes the reference based on the RF Creditor Reference.
            The data of the reference is the user defined reference of the
            partner or the database id number of the parter.
            For instance, if an invoice is issued for the partner with internal
            reference 'food buyer 654', the digits will be extracted and used as
            the data. This will lead to a check number equal to 00 and the
            reference will be 'RF00 654'.
            If no reference is set for the partner, its id in the database will
            be used.
        """
        self.ensure_one()
        partner_ref = self.partner_id.ref
        partner_ref_nr = re.sub('\D', '', partner_ref or '')[-21:] or str(self.partner_id.id)[-21:]
        partner_ref_nr = partner_ref_nr[-21:]
        check_digits = calc_check_digits('{}RF'.format(partner_ref_nr))
        reference = 'RF{} {}'.format(check_digits, " ".join(["".join(x) for x in zip_longest(*[iter(partner_ref_nr)]*4, fillvalue="")]))
        return reference

    def _get_invoice_reference_odoo_invoice(self):
        """ This computes the reference based on the Odoo format.
            We simply return the number of the invoice, defined on the journal
            sequence.
        """
        self.ensure_one()
        return self.name

    def _get_invoice_reference_odoo_partner(self):
        """ This computes the reference based on the Odoo format.
            The data used is the reference set on the partner or its database
            id otherwise. For instance if the reference of the customer is
            'dumb customer 97', the reference will be 'CUST/dumb customer 97'.
        """
        ref = self.partner_id.ref or str(self.partner_id.id)
        prefix = _('CUST')
        return '%s/%s' % (prefix, ref)

    def _get_invoice_computed_reference(self):
        self.ensure_one()
        if self.journal_id.invoice_reference_type == 'none':
            return ''
        else:
            ref_function = getattr(self, '_get_invoice_reference_{}_{}'.format(self.journal_id.invoice_reference_model, self.journal_id.invoice_reference_type))
            if ref_function:
                return ref_function()
            else:
                raise UserError(_('The combination of reference model and reference type on the journal is not implemented'))

    def _get_move_display_name(self, show_ref=False):
        ''' Helper to get the display name of an invoice depending of its type.
        :param show_ref:    A flag indicating of the display name must include or not the journal entry reference.
        :return:            A string representing the invoice.
        '''
        self.ensure_one()
        name = ''
        if self.state == 'draft':
            name += {
                'out_invoice': _('Draft Invoice'),
                'out_refund': _('Draft Credit Note'),
                'in_invoice': _('Draft Bill'),
                'in_refund': _('Draft Vendor Credit Note'),
                'out_receipt': _('Draft Sales Receipt'),
                'in_receipt': _('Draft Purchase Receipt'),
                'entry': _('Draft Entry'),
            }[self.move_type]
            name += ' '
        if not self.name or self.name == '/':
            name += '(* %s)' % str(self.id)
        else:
            name += self.name
        return name + (show_ref and self.ref and ' (%s%s)' % (self.ref[:50], '...' if len(self.ref) > 50 else '') or '')

    def _get_reconciled_payments(self):
        """Helper used to retrieve the reconciled payments on this journal entry"""
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        reconciled_amls = reconciled_lines.mapped('matched_debit_ids.debit_move_id') + \
                          reconciled_lines.mapped('matched_credit_ids.credit_move_id')
        return reconciled_amls.move_id.payment_id

    def _get_reconciled_statement_lines(self):
        """Helper used to retrieve the reconciled payments on this journal entry"""
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        reconciled_amls = reconciled_lines.mapped('matched_debit_ids.debit_move_id') + \
                          reconciled_lines.mapped('matched_credit_ids.credit_move_id')
        return reconciled_amls.move_id.statement_line_id

    def _get_reconciled_invoices(self):
        """Helper used to retrieve the reconciled payments on this journal entry"""
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        reconciled_amls = reconciled_lines.mapped('matched_debit_ids.debit_move_id') + \
                          reconciled_lines.mapped('matched_credit_ids.credit_move_id')
        return reconciled_amls.move_id.filtered(lambda move: move.is_invoice(include_receipts=True))

    def _get_reconciled_invoices_partials(self):
        ''' Helper to retrieve the details about reconciled invoices.
        :return A list of tuple (partial, amount, invoice_line).
        '''
        self.ensure_one()
        pay_term_lines = self.line_ids\
            .filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
        invoice_partials = []
        exchange_diff_moves = []

        for partial in pay_term_lines.matched_debit_ids:
            invoice_partials.append((partial, partial.credit_amount_currency, partial.debit_move_id))
            if partial.exchange_move_id:
                exchange_diff_moves.append(partial.exchange_move_id.id)
        for partial in pay_term_lines.matched_credit_ids:
            invoice_partials.append((partial, partial.debit_amount_currency, partial.credit_move_id))
            if partial.exchange_move_id:
                exchange_diff_moves.append(partial.exchange_move_id.id)
        return invoice_partials, exchange_diff_moves

    def _reverse_move_vals(self, default_values, cancel=True):
        ''' Reverse values passed as parameter being the copied values of the original journal entry.
        For example, debit / credit must be switched. The tax lines must be edited in case of refunds.

        :param default_values:  A copy_date of the original journal entry.
        :param cancel:          A flag indicating the reverse is made to cancel the original journal entry.
        :return:                The updated default_values.
        '''
        self.ensure_one()

        def compute_tax_repartition_lines_mapping(move_vals):
            ''' Computes and returns a mapping between the current repartition lines to the new expected one.
            :param move_vals:   The newly created invoice as a python dictionary to be passed to the 'create' method.
            :return:            A map invoice_repartition_line => refund_repartition_line.
            '''
            # invoice_repartition_line => refund_repartition_line
            mapping = {}

            for line_command in move_vals.get('line_ids', []):
                line_vals = line_command[2]  # (0, 0, {...})

                if line_vals.get('tax_line_id'):
                    # Tax line.
                    tax_ids = [line_vals['tax_line_id']]
                elif line_vals.get('tax_ids') and line_vals['tax_ids'][0][2]:
                    # Base line.
                    tax_ids = line_vals['tax_ids'][0][2]
                else:
                    continue

                for tax in self.env['account.tax'].browse(tax_ids).flatten_taxes_hierarchy():
                    for inv_rep_line, ref_rep_line in zip(tax.invoice_repartition_line_ids, tax.refund_repartition_line_ids):
                        mapping[inv_rep_line] = ref_rep_line
            return mapping

        move_vals = self.with_context(include_business_fields=True).copy_data(default=default_values)[0]

        is_storno_move = move_vals['move_type'] in ('entry', 'out_refund', 'in_refund') and self.company_id.account_storno
        if is_storno_move:
            move_vals['is_storno'] = True

        tax_repartition_lines_mapping = compute_tax_repartition_lines_mapping(move_vals)
        is_refund = False
        if move_vals['move_type'] in ('out_refund', 'in_refund'):
            is_refund = True
        elif move_vals['move_type'] == 'entry':
            base_lines = self.line_ids.filtered(lambda line: line.tax_ids)
            tax_type = set(base_lines.tax_ids.mapped('type_tax_use'))
            if tax_type == {'sale'} and sum(base_lines.mapped('debit')) == 0:
                is_refund = True
            elif tax_type == {'purchase'} and sum(base_lines.mapped('credit')) == 0:
                is_refund = True

        tax_repartition_lines_mapping = compute_tax_repartition_lines_mapping(move_vals) if is_refund else {}

        for line_command in move_vals.get('line_ids', []):
            line_vals = line_command[2]  # (0, 0, {...})

            # ==== Non-Storno: Inverse debit <-> credit and negate amount_currency ====
            amount_currency = -line_vals.get('amount_currency', 0.0)
            debit = line_vals['credit']
            credit = line_vals['debit']

            # ==== Storno: Negate debit / credit / amount_currency in same column====
            if is_storno_move:
                debit = -line_vals['debit']
                credit = -line_vals['credit']

            if 'tax_tag_invert' in line_vals and not self.tax_cash_basis_origin_move_id:
                # This is an editable computed field; we want to it recompute itself
                del line_vals['tax_tag_invert']

            line_vals.update({
                'amount_currency': amount_currency,
                'debit': debit,
                'credit': credit,
            })

            if not is_refund or self.tax_cash_basis_origin_move_id:
                # We don't map tax repartition for non-refund operations, nor for cash basis entries.
                # Indeed, cancelling a cash basis entry usually happens when unreconciling and invoice,
                # in which case we always want the reverse entry to totally cancel the original one, keeping the same accounts,
                # tags and repartition lines
                continue

            # ==== Map tax repartition lines ====
            if line_vals.get('tax_repartition_line_id'):
                # Tax line.
                invoice_repartition_line = self.env['account.tax.repartition.line'].browse(line_vals['tax_repartition_line_id'])
                # CABA taxes should not generate tax grids on reverse move.
                if invoice_repartition_line.invoice_tax_id.tax_exigibility == 'on_payment':
                    continue
                if invoice_repartition_line not in tax_repartition_lines_mapping:
                    raise UserError(_("It seems that the taxes have been modified since the creation of the journal entry. You should create the credit note manually instead."))
                refund_repartition_line = tax_repartition_lines_mapping[invoice_repartition_line]

                # Find the right account.
                account_id = self.env['account.move.line']._get_default_tax_account(refund_repartition_line).id
                if not account_id:
                    if not invoice_repartition_line.account_id:
                        # Keep the current account as the current one comes from the base line.
                        account_id = line_vals['account_id']
                    else:
                        tax = invoice_repartition_line.invoice_tax_id
                        base_line = self.line_ids.filtered(lambda line: tax in line.tax_ids.flatten_taxes_hierarchy())[0]
                        account_id = base_line.account_id.id

                tags = refund_repartition_line.tag_ids
                if line_vals.get('tax_ids'):
                    subsequent_taxes = self.env['account.tax'].browse(line_vals['tax_ids'][0][2])
                    tags += subsequent_taxes.refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'base').tag_ids

                line_vals.update({
                    'tax_repartition_line_id': refund_repartition_line.id,
                    'account_id': account_id,
                    'tax_tag_ids': [(6, 0, tags.ids)],
                })
            elif line_vals.get('tax_ids') and line_vals['tax_ids'][0][2]:
                # Base line.
                taxes = self.env['account.tax'].browse(line_vals['tax_ids'][0][2]).flatten_taxes_hierarchy()
                # CABA taxes should not generate tax grids on reverse move.
                taxes = taxes.filtered(lambda t: t.tax_exigibility != 'on_payment')
                if not taxes:
                    continue
                invoice_repartition_lines = taxes\
                    .mapped('invoice_repartition_line_ids')\
                    .filtered(lambda line: line.repartition_type == 'base')
                refund_repartition_lines = invoice_repartition_lines\
                    .mapped(lambda line: tax_repartition_lines_mapping[line])

                line_vals['tax_tag_ids'] = [(6, 0, refund_repartition_lines.mapped('tag_ids').ids)]
        return move_vals

    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.

        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''
        if not default_values_list:
            default_values_list = [{} for move in self]

        if cancel:
            lines = self.mapped('line_ids')
            # Avoid maximum recursion depth.
            if lines:
                lines.remove_move_reconcile()

        reverse_type_map = {
            'entry': 'entry',
            'out_invoice': 'out_refund',
            'out_refund': 'entry',
            'in_invoice': 'in_refund',
            'in_refund': 'entry',
            'out_receipt': 'entry',
            'in_receipt': 'entry',
        }

        move_vals_list = []
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'move_type': reverse_type_map[move.move_type],
                'reversed_entry_id': move.id,
            })
            move_vals_list.append(move.with_context(move_reverse_cancel=cancel)._reverse_move_vals(default_values, cancel=cancel))

        reverse_moves = self.env['account.move'].create(move_vals_list)
        for move, reverse_move in zip(self, reverse_moves.with_context(check_move_validity=False, move_reverse_cancel=cancel)):
            # Update amount_currency if the date has changed.
            if move.date != reverse_move.date:
                for line in reverse_move.line_ids:
                    if line.currency_id:
                        line._onchange_currency()
            reverse_move._recompute_dynamic_lines(recompute_all_taxes=False)
        reverse_moves._check_balanced()

        # Reconcile moves together to cancel the previous one.
        if cancel:
            reverse_moves.with_context(move_reverse_cancel=cancel)._post(soft=False)
            for move, reverse_move in zip(self, reverse_moves):
                group = defaultdict(list)
                for line in (move.line_ids + reverse_move.line_ids).filtered(lambda l: not l.reconciled):
                    group[(line.account_id, line.currency_id)].append(line.id)
                for (account, dummy), line_ids in group.items():
                    if account.reconcile or account.internal_type == 'liquidity':
                        self.env['account.move.line'].browse(line_ids).with_context(move_reverse_cancel=cancel).reconcile()

        return reverse_moves

    def _action_invoice_ready_to_be_sent(self):
        """ Hook allowing custom code when an invoice becomes ready to be sent by mail to the customer.
        For example, when an EDI document must be sent to the government and be signed by it.
        """

    def _is_ready_to_be_sent(self):
        """ Helper telling if a journal entry is ready to be sent by mail to the customer.

        :return: True if the invoice is ready, False otherwise.
        """
        self.ensure_one()
        return True

    @contextmanager
    def _send_only_when_ready(self):
        moves_not_ready = self.filtered(lambda x: not x._is_ready_to_be_sent())

        try:
            yield
        finally:
            moves_now_ready = moves_not_ready.filtered(lambda x: x._is_ready_to_be_sent())
            if moves_now_ready:
                moves_now_ready._action_invoice_ready_to_be_sent()

    def open_reconcile_view(self):
        return self.line_ids.open_reconcile_view()

    def open_bank_statement_view(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'view_mode': 'form',
            'res_id': self.statement_id.id,
            'views': [(False, 'form')],
        }

    def open_payment_view(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.payment_id.id,
            'views': [(False, 'form')],
        }

    def open_created_caba_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Cash Basis Entries"),
            'res_model': 'account.move',
            'view_mode': 'form',
            'domain': [('id', 'in', self.tax_cash_basis_created_move_ids.ids)],
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
        }

    def post(self):
        warnings.warn(
            "RedirectWarning method 'post()' is a deprecated alias to 'action_post()' or _post()",
            DeprecationWarning,
            stacklevel=2
        )
        return self.action_post()

    def _post(self, soft=True):
        """Post/Validate the documents.

        Posting the documents will give it a number, and check that the document is
        complete (some fields might not be required if not posted but are required
        otherwise).
        If the journal is locked with a hash table, it will be impossible to change
        some fields afterwards.

        :param soft (bool): if True, future documents are not immediately posted,
            but are set to be auto posted automatically at the set accounting date.
            Nothing will be performed on those documents before the accounting date.
        :return Model<account.move>: the documents that have been posted
        """
        if soft:
            future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
            future_moves.auto_post = True
            for move in future_moves:
                msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
                move.message_post(body=msg)
            to_post = self - future_moves
        else:
            to_post = self

        # `user_has_group` won't be bypassed by `sudo()` since it doesn't change the user anymore.
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))
        for move in to_post:
            if move.partner_bank_id and not move.partner_bank_id.active:
                raise UserError(_("The recipient bank account link to this invoice is archived.\nSo you cannot confirm the invoice."))
            if move.state == 'posted':
                raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
            if not move.line_ids.filtered(lambda line: not line.display_type):
                raise UserError(_('You need to add a line before posting.'))
            if move.auto_post and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                raise UserError(_("This move is configured to be auto-posted on %s", date_msg))
            if not move.journal_id.active:
                raise UserError(_(
                    "You cannot post an entry in an archived journal (%(journal)s)",
                    journal=move.journal_id.display_name,
                ))

            if not move.partner_id:
                if move.is_sale_document():
                    raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
                elif move.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

            if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
                raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))

            if move.display_inactive_currency_warning:
                raise UserError(_("You cannot validate an invoice with an inactive currency: %s",
                                  move.currency_id.name))

            # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
            # lines are recomputed accordingly.
            # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
            # environment.
            if not move.invoice_date:
                if move.is_sale_document(include_receipts=True):
                    move.invoice_date = fields.Date.context_today(self)
                    move.with_context(check_move_validity=False)._onchange_invoice_date()
                elif move.is_purchase_document(include_receipts=True):
                    raise UserError(_("The Bill/Refund date is required to validate this document."))

            # When the accounting date is prior to a lock date, change it automatically upon posting.
            # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
            # environment.
            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report)
                if move.move_type and move.move_type != 'entry':
                    move.with_context(check_move_validity=False)._onchange_currency()

        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        to_post.mapped('line_ids').create_analytic_lines()

        for move in to_post:
            # Fix inconsistencies that may occure if the OCR has been editing the invoice at the same time of a user. We force the
            # partner on the lines to be the same as the one on the move, because that's the only one the user can see/edit.
            wrong_lines = move.is_invoice() and move.line_ids.filtered(lambda aml: aml.partner_id != move.commercial_partner_id and not aml.display_type)
            if wrong_lines:
                wrong_lines.write({'partner_id': move.commercial_partner_id.id})

        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        for move in to_post:
            move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])

            # Compute 'ref' for 'out_invoice'.
            if move._auto_compute_invoice_reference():
                to_write = {
                    'payment_reference': move._get_invoice_computed_reference(),
                    'line_ids': []
                }
                for line in move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
                    to_write['line_ids'].append((1, line.id, {'name': to_write['payment_reference']}))
                move.write(to_write)

        for move in to_post:
            if move.is_sale_document() \
                    and move.journal_id.sale_activity_type_id \
                    and (move.journal_id.sale_activity_user_id or move.invoice_user_id).id not in (self.env.ref('base.user_root').id, False):
                move.activity_schedule(
                    date_deadline=min((date for date in move.line_ids.mapped('date_maturity') if date), default=move.date),
                    activity_type_id=move.journal_id.sale_activity_type_id.id,
                    summary=move.journal_id.sale_activity_note,
                    user_id=move.journal_id.sale_activity_user_id.id or move.invoice_user_id.id,
                )

        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for move in to_post:
            if move.is_sale_document():
                customer_count[move.partner_id] += 1
            elif move.is_purchase_document():
                supplier_count[move.partner_id] += 1
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

        # Trigger action for paid invoices in amount is zero
        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        ).action_invoice_paid()

        # Force balance check since nothing prevents another module to create an incorrect entry.
        # This is performed at the very end to avoid flushing fields before the whole processing.
        to_post._check_balanced()
        return to_post

    def _auto_compute_invoice_reference(self):
        ''' Hook to be overridden to set custom conditions for auto-computed invoice references.
            :return True if the move should get a auto-computed reference else False
            :rtype bool
        '''
        self.ensure_one()
        return self.move_type == 'out_invoice' and not self.payment_reference

    def action_reverse(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_view_account_move_reversal")

        if self.is_invoice():
            action['name'] = _('Credit Note')

        return action

    def action_post(self):
        moves_with_payments = self.filtered('payment_id')
        other_moves = self - moves_with_payments
        if moves_with_payments:
            moves_with_payments.payment_id.action_post()
        if other_moves:
            other_moves._post(soft=False)
        return False

    def js_assign_outstanding_line(self, line_id):
        ''' Called by the 'payment' widget to reconcile a suggested journal item to the present
        invoice.

        :param line_id: The id of the line to reconcile with the current invoice.
        '''
        self.ensure_one()
        lines = self.env['account.move.line'].browse(line_id)
        lines += self.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
        return lines.reconcile()

    def js_remove_outstanding_partial(self, partial_id):
        ''' Called by the 'payment' widget to remove a reconciled entry to the present invoice.

        :param partial_id: The id of an existing partial reconciled with the current invoice.
        '''
        self.ensure_one()
        partial = self.env['account.partial.reconcile'].browse(partial_id)
        return partial.unlink()

    def button_set_checked(self):
        for move in self:
            move.to_check = False

    def button_draft(self):
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                # If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
                # but we still don't want to allow setting the caba entry to draft
                # (it'll have been reversed automatically, so no manual intervention is required),
                # so we also check tax_cash_basis_origin_move_id, which stays unchanged
                # (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft', 'is_move_sent': False})

    def button_cancel(self):
        self.write({'auto_post': False, 'state': 'cancel'})

    def _get_mail_template(self):
        """
        :return: the correct mail template based on the current move type
        """
        return (
            'account.email_template_edi_credit_note'
            if all(move.move_type == 'out_refund' for move in self)
            else 'account.email_template_edi_invoice'
        )

    def action_send_and_print(self):
        return {
            'name': _('Send Invoice'),
            'res_model': 'account.invoice.send',
            'view_mode': 'form',
            'context': {
                'default_email_layout_xmlid': 'mail.mail_notification_paynow',
                'default_template_id': self.env.ref(self._get_mail_template()).id,
                'mark_invoice_as_sent': True,
                'active_model': 'account.move',
                # Setting both active_id and active_ids is required, mimicking how direct call to
                # ir.actions.act_window works
                'active_id': self.ids[0],
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref(self._get_mail_template(), raise_if_not_found=False)
        lang = False
        if template:
            lang = template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            # For the sake of consistency we need a default_res_model if
            # default_res_id is set. Not renaming default_model as it can
            # create many side-effects.
            default_res_model='account.move',
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            default_email_layout_xmlid="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True,
        )
        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on journal entries when they get posted"""
        self.ensure_one()
        #get the only one exact previous move in the securisation sequence
        prev_move = self.search([('state', '=', 'posted'),
                                 ('company_id', '=', self.company_id.id),
                                 ('journal_id', '=', self.journal_id.id),
                                 ('secure_sequence_number', '!=', 0),
                                 ('secure_sequence_number', '=', int(secure_seq_number) - 1)])
        if prev_move and len(prev_move) != 1:
            raise UserError(
               _('An error occurred when computing the inalterability. Impossible to get the unique previous posted journal entry.'))

        #build and return the hash
        return self._compute_hash(prev_move.inalterable_hash if prev_move else u'')

    def _compute_hash(self, previous_hash):
        """ Computes the hash of the browse_record given as self, based on the hash
        of the previous record in the company's securisation sequence given as parameter"""
        self.ensure_one()
        hash_string = sha256((previous_hash + self.string_to_hash).encode('utf-8'))
        return hash_string.hexdigest()

    def _compute_string_to_hash(self):
        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            return str(field_value)

        for move in self:
            values = {}
            for field in INTEGRITY_HASH_MOVE_FIELDS:
                values[field] = _getattrstring(move, field)

            for line in move.line_ids:
                for field in INTEGRITY_HASH_LINE_FIELDS:
                    k = 'line_%d_%s' % (line.id, field)
                    values[k] = _getattrstring(line, field)
            #make the json serialization canonical
            #  (https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
            move.string_to_hash = dumps(values, sort_keys=True,
                                                ensure_ascii=True, indent=None,
                                                separators=(',',':'))

    def action_invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        if any(not move.is_invoice(include_receipts=True) for move in self):
            raise UserError(_("Only invoices could be printed."))

        self.filtered(lambda inv: not inv.is_move_sent).write({'is_move_sent': True})
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref('account.account_invoices').report_action(self)
        else:
            return self.env.ref('account.account_invoices_without_payment').report_action(self)

    def action_invoice_paid(self):
        ''' Hook to be overrided called when the invoice moves to the paid state. '''
        pass

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_switch_invoice_into_refund_credit_note(self):
        if any(move.move_type not in ('in_invoice', 'out_invoice') for move in self):
            raise ValidationError(_("This action isn't available for this document."))

        for move in self:
            reversed_move = move._reverse_move_vals({}, False)
            new_invoice_line_ids = []
            for cmd, virtualid, line_vals in reversed_move['line_ids']:
                if not line_vals['exclude_from_invoice_tab']:
                    new_invoice_line_ids.append((0, 0,line_vals))
            if move.amount_total < 0:
                # Inverse all invoice_line_ids
                for cmd, virtualid, line_vals in new_invoice_line_ids:
                    line_vals.update({
                        'quantity': -line_vals['quantity'],
                        'amount_currency': -line_vals['amount_currency'],
                    })
            move.write({
                'move_type': move.move_type.replace('invoice', 'refund'),
                'invoice_line_ids' : [(5, 0, 0)],
                'partner_bank_id': False,
            })
            move.write({'invoice_line_ids' : new_invoice_line_ids})

    def _get_report_base_filename(self):
        return self._get_move_display_name()

    def _get_name_invoice_report(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'account.report_invoice_document'

    def preview_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def _compute_access_url(self):
        super(AccountMove, self)._compute_access_url()
        for move in self.filtered(lambda move: move.is_invoice()):
            move.access_url = '/my/invoices/%s' % (move.id)

    @api.depends('line_ids')
    def _compute_has_reconciled_entries(self):
        for move in self:
            move.has_reconciled_entries = len(move.line_ids._reconciled_lines()) > 1

    @api.model
    def _autopost_draft_entries(self):
        ''' This method is called from a cron job.
        It is used to post entries such as those created by the module
        account_asset.
        '''
        records = self.search([
            ('state', '=', 'draft'),
            ('date', '<=', fields.Date.context_today(self)),
            ('auto_post', '=', True),
        ])
        for ids in self._cr.split_for_in_conditions(records.ids, size=1000):
            self.browse(ids)._post()
            if not self.env.registry.in_test_mode():
                self._cr.commit()

    # offer the possibility to duplicate thanks to a button instead of a hidden menu, which is more visible
    def action_duplicate(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['context'] = dict(self.env.context)
        action['context']['form_view_initial_mode'] = 'edit'
        action['context']['view_no_maturity'] = False
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.copy().id
        return action

    def action_activate_currency(self):
        self.currency_id.filtered(lambda currency: not currency.active).write({'active': True})

    @api.model
    def _move_dict_to_preview_vals(self, move_vals, currency_id=None):
        preview_vals = {
            'group_name': "%s, %s" % (format_date(self.env, move_vals['date']) or _('[Not set]'), move_vals['ref']),
            'items_vals': move_vals['line_ids'],
        }
        for line in preview_vals['items_vals']:
            if 'partner_id' in line[2]:
                # sudo is needed to compute display_name in a multi companies environment
                line[2]['partner_id'] = self.env['res.partner'].browse(line[2]['partner_id']).sudo().display_name
            line[2]['account_id'] = self.env['account.account'].browse(line[2]['account_id']).display_name or _('Destination Account')
            line[2]['debit'] = currency_id and formatLang(self.env, line[2]['debit'], currency_obj=currency_id) or line[2]['debit']
            line[2]['credit'] = currency_id and formatLang(self.env, line[2]['credit'], currency_obj=currency_id) or line[2]['debit']
        return preview_vals

    def generate_qr_code(self):
        """ Generates and returns a QR-code generation URL for this invoice,
        raising an error message if something is misconfigured.

        The chosen QR generation method is the one set in qr_method field if there is one,
        or the first eligible one found. If this search had to be performed and
        and eligible method was found, qr_method field is set to this method before
        returning the URL. If no eligible QR method could be found, we return None.
        """
        self.ensure_one()

        if not self.is_invoice():
            raise UserError(_("QR-codes can only be generated for invoice entries."))

        qr_code_method = self.qr_code_method
        if qr_code_method:
            # If the user set a qr code generator manually, we check that we can use it
            if not self.partner_bank_id._eligible_for_qr_code(self.qr_code_method, self.partner_id, self.currency_id):
                raise UserError(_("The chosen QR-code type is not eligible for this invoice."))
        else:
            # Else we find one that's eligible and assign it to the invoice
            for candidate_method, candidate_name in self.env['res.partner.bank'].get_available_qr_methods_in_sequence():
                if self.partner_bank_id._eligible_for_qr_code(candidate_method, self.partner_id, self.currency_id):
                    qr_code_method = candidate_method
                    break

        if not qr_code_method:
            # No eligible method could be found; we can't generate the QR-code
            return None

        unstruct_ref = self.ref if self.ref else self.name
        rslt = self.partner_bank_id.build_qr_code_base64(self.amount_residual, unstruct_ref, self.payment_reference, self.currency_id, self.partner_id, qr_code_method, silent_errors=False)

        # We only set qr_code_method after generating the url; otherwise, it
        # could be set even in case of a failure in the QR code generation
        # (which would change the field, but not refresh UI, making the displayed data inconsistent with db)
        self.qr_code_method = qr_code_method

        return rslt

    def _get_create_invoice_from_attachment_decoders(self):
        """ Returns a list of method that are able to create an invoice from an attachment and a priority.

        :returns:   A list of tuples (priority, method) where method takes an attachment as parameter.
        """
        return []

    def _get_update_invoice_from_attachment_decoders(self, invoice):
        """ Returns a list of method that are able to create an invoice from an attachment and a priority.

        :param invoice: The invoice on which to update the data.
        :returns:       A list of tuples (priority, method) where method takes an attachment as parameter.
        """
        return []

    @api.depends('move_type', 'partner_id', 'company_id')
    def _compute_narration(self):
        use_invoice_terms = self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms')
        for move in self:
            if not move.is_sale_document(include_receipts=True):
                continue
            if not use_invoice_terms:
                move.narration = False
            else:
                lang = move.partner_id.lang or self.env.user.lang
                if not move.company_id.terms_type == 'html':
                    narration = move.company_id.with_context(lang=lang).invoice_terms if not is_html_empty(move.company_id.invoice_terms) else ''
                else:
                    baseurl = self.env.company.get_base_url() + '/terms'
                    context = {'lang': lang}
                    narration = _('Terms & Conditions: %s', baseurl)
                    del context
                move.narration = narration or False

    # ------------------------------------------------------------
    # MAIL.THREAD
    # ------------------------------------------------------------

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # OVERRIDE
        # Add custom behavior when receiving a new invoice through the mail's gateway.
        if (custom_values or {}).get('move_type', 'entry') not in ('out_invoice', 'in_invoice'):
            return super().message_new(msg_dict, custom_values=custom_values)

        def is_internal_partner(partner):
            # Helper to know if the partner is an internal one.
            return partner.user_ids and all(user.has_group('base.group_user') for user in partner.user_ids)

        extra_domain = False
        if custom_values.get('company_id'):
            extra_domain = ['|', ('company_id', '=', custom_values['company_id']), ('company_id', '=', False)]

        # Search for partners in copy.
        cc_mail_addresses = email_split(msg_dict.get('cc', ''))
        followers = [partner for partner in self._mail_find_partner_from_emails(cc_mail_addresses, extra_domain) if partner]

        # Search for partner that sent the mail.
        from_mail_addresses = email_split(msg_dict.get('from', ''))
        senders = partners = [partner for partner in self._mail_find_partner_from_emails(from_mail_addresses, extra_domain) if partner]

        # Search for partners using the user.
        if not senders:
            senders = partners = list(self._mail_search_on_user(from_mail_addresses))

        if partners:
            # Check we are not in the case when an internal user forwarded the mail manually.
            if is_internal_partner(partners[0]):
                # Search for partners in the mail's body.
                body_mail_addresses = set(email_re.findall(msg_dict.get('body')))
                company_id = custom_values.get('company_id', self.env.company.id)
                partners = [
                    partner
                    for partner in self._mail_find_partner_from_emails(body_mail_addresses, extra_domain)
                    if not is_internal_partner(partner) and partner.company_id.id in (False, company_id)
                ]

        # Little hack: Inject the mail's subject in the body.
        if msg_dict.get('subject') and msg_dict.get('body'):
            msg_dict['body'] = '<div><div><h3>%s</h3></div>%s</div>' % (msg_dict['subject'], msg_dict['body'])

        # Create the invoice.
        values = {
            'name': '/',  # we have to give the name otherwise it will be set to the mail's subject
            'invoice_source_email': from_mail_addresses[0],
            'partner_id': partners and partners[0].id or False,
        }
        move_ctx = self.with_context(default_move_type=custom_values['move_type'], default_journal_id=custom_values['journal_id'])
        move = super(AccountMove, move_ctx).message_new(msg_dict, custom_values=values)
        move._compute_name()  # because the name is given, we need to recompute in case it is the first invoice of the journal

        # Assign followers.
        all_followers_ids = set(partner.id for partner in followers + senders + partners if is_internal_partner(partner))
        move.message_subscribe(list(all_followers_ids))
        return move

    def _message_post_after_hook(self, new_message, message_values):
        # OVERRIDE
        # When posting a message, check the attachment to see if it's an invoice and update with the imported data.
        res = super()._message_post_after_hook(new_message, message_values)

        attachments = new_message.attachment_ids
        if len(self) != 1 or not attachments or self.env.context.get('no_new_invoice') or not self.is_invoice(include_receipts=True):
            return res

        odoobot = self.env.ref('base.partner_root')
        if attachments and self.state != 'draft':
            self.message_post(body=_('The invoice is not a draft, it was not updated from the attachment.'),
                              message_type='comment',
                              subtype_xmlid='mail.mt_note',
                              author_id=odoobot.id)
            return res
        if attachments and self.line_ids:
            self.message_post(body=_('The invoice already contains lines, it was not updated from the attachment.'),
                              message_type='comment',
                              subtype_xmlid='mail.mt_note',
                              author_id=odoobot.id)
            return res

        decoders = self.env['account.move']._get_update_invoice_from_attachment_decoders(self)
        for decoder in sorted(decoders, key=lambda d: d[0]):
            # start with message_main_attachment_id, that way if OCR is installed, only that one will be parsed.
            # this is based on the fact that the ocr will be the last decoder.
            for attachment in attachments.sorted(lambda x: x != self.message_main_attachment_id):
                invoice = decoder[1](attachment, self)
                if invoice:
                    return res

        return res

    def _creation_subtype(self):
        # OVERRIDE
        if self.move_type in ('out_invoice', 'out_receipt'):
            return self.env.ref('account.mt_invoice_created')
        else:
            return super(AccountMove, self)._creation_subtype()

    def _track_subtype(self, init_values):
        # OVERRIDE to add custom subtype depending of the state.
        self.ensure_one()

        if not self.is_invoice(include_receipts=True):
            if self.payment_id and 'state' in init_values:
                self.payment_id._message_track(['state'], {self.payment_id.id: init_values})
            return super(AccountMove, self)._track_subtype(init_values)

        if 'payment_state' in init_values and self.payment_state == 'paid':
            return self.env.ref('account.mt_invoice_paid')
        elif 'state' in init_values and self.state == 'posted' and self.is_sale_document(include_receipts=True):
            return self.env.ref('account.mt_invoice_validated')
        return super(AccountMove, self)._track_subtype(init_values)

    def _creation_message(self):
        # OVERRIDE
        if not self.is_invoice(include_receipts=True):
            return super()._creation_message()
        return {
            'out_invoice': _('Invoice Created'),
            'out_refund': _('Credit Note Created'),
            'in_invoice': _('Vendor Bill Created'),
            'in_refund': _('Refund Created'),
            'out_receipt': _('Sales Receipt Created'),
            'in_receipt': _('Purchase Receipt Created'),
        }[self.move_type]

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        if self.invoice_date_due:
            render_context['subtitle'] = _('%(amount)s due\N{NO-BREAK SPACE}%(date)s',
                           amount=format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang')),
                           date=format_date(self.env, self.invoice_date_due, date_format='short', lang_code=render_context.get('lang'))
                          )
        else:
            render_context['subtitle'] = format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang'))
        return render_context


    def _is_downpayment(self):
        ''' Return true if the invoice is a downpayment.
        Down-payments can be created from a sale order. This method is overridden in the sale order module.
        '''
        return False


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _description = "Journal Item"
    _order = "date desc, move_name desc, id"
    _check_company_auto = True
    _rec_names_search = ['name', 'move_id', 'product_id']

    # ==== Business fields ====
    move_id = fields.Many2one('account.move', string='Journal Entry',
        index=True, required=True, readonly=True, auto_join=True, ondelete="cascade",
        check_company=True,
        help="The move of this entry line.")
    move_name = fields.Char(string='Number', related='move_id.name', store=True, index='trigram')
    date = fields.Date(related='move_id.date', store=True, readonly=True, index=True, copy=False, group_operator='min')
    ref = fields.Char(related='move_id.ref', store=True, copy=False, index='trigram', readonly=True)
    parent_state = fields.Selection(related='move_id.state', store=True, readonly=True)
    journal_id = fields.Many2one(related='move_id.journal_id', store=True, index=True, copy=False)
    company_id = fields.Many2one(related='move_id.company_id', store=True, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')
    is_storno = fields.Boolean(
        related='move_id.is_storno',
        string='Company Storno Accounting',
        help='Utility field to express whether the journal item is subject to storno accounting')
    account_id = fields.Many2one('account.account', string='Account',
        index=True, ondelete="cascade",
        domain="[('deprecated', '=', False), ('company_id', '=', 'company_id'),('is_off_balance', '=', False)]",
        check_company=True,
        tracking=True)
    account_internal_type = fields.Selection(related='account_id.user_type_id.type', string="Internal Type", readonly=True)
    account_internal_group = fields.Selection(related='account_id.user_type_id.internal_group', string="Internal Group", readonly=True)
    account_root_id = fields.Many2one(related='account_id.root_id', string="Account Root", store=True, readonly=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Label', tracking=True)
    quantity = fields.Float(string='Quantity',
        default=1.0, digits='Product Unit of Measure',
        help="The optional quantity expressed by this line, eg: number of product sold. "
             "The quantity is not a legal requirement but is very useful for some reports.")
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    debit = fields.Monetary(string='Debit', default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', default=0.0, currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', store=True,
        currency_field='company_currency_id',
        compute='_compute_balance',
        help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
    cumulated_balance = fields.Monetary(string='Cumulated Balance', store=False,
        currency_field='company_currency_id',
        compute='_compute_cumulated_balance',
        help="Cumulated balance depending on the domain and the order chosen in the view.")
    amount_currency = fields.Monetary(string='Amount in Currency', store=True, copy=True,
        help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=True,
        currency_field='currency_id')
    price_total = fields.Monetary(string='Total', store=True, readonly=True,
        currency_field='currency_id')
    reconciled = fields.Boolean(compute='_compute_amount_residual', store=True)
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")
    date_maturity = fields.Date(string='Due Date', index=True, tracking=True,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]", ondelete="restrict")
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id')

    # ==== Origin fields ====
    reconcile_model_id = fields.Many2one('account.reconcile.model', string="Reconciliation Model", copy=False, readonly=True, check_company=True)
    payment_id = fields.Many2one('account.payment', index='btree_not_null', store=True,
        string="Originator Payment",
        related='move_id.payment_id',
        help="The payment that created this entry")
    statement_line_id = fields.Many2one('account.bank.statement.line', index='btree_not_null', store=True,
        string="Originator Statement Line",
        related='move_id.statement_line_id',
        help="The statement line that created this entry")
    statement_id = fields.Many2one(related='statement_line_id.statement_id', store=True, index='btree_not_null', copy=False,
        help="The bank statement used for bank reconciliation")

    # ==== Tax fields ====
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        context={'active_test': False},
        check_company=True,
        help="Taxes that apply on the base amount")
    group_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Originator Group of Taxes",
        index='btree_not_null',
        help="The group of taxes that generated this tax line",
    )
    tax_line_id = fields.Many2one('account.tax', string='Originator Tax', ondelete='restrict', store=True,
        compute='_compute_tax_line_id', help="Indicates that this journal item is a tax line")
    tax_group_id = fields.Many2one(related='tax_line_id.tax_group_id', string='Originator tax group',
        readonly=True, store=True,
        help='technical field for widget tax-group-custom-field')
    tax_base_amount = fields.Monetary(string="Base Amount", store=True, readonly=True,
        currency_field='company_currency_id')
    tax_repartition_line_id = fields.Many2one(comodel_name='account.tax.repartition.line',
        string="Originator Tax Distribution Line", ondelete='restrict', readonly=True,
        check_company=True,
        help="Tax distribution line that caused the creation of this move line, if any")
    tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.", tracking=True)
    tax_audit = fields.Char(string="Tax Audit String", compute="_compute_tax_audit", store=True,
        help="Computed field, listing the tax grids impacted by this line, and the amount it applies to each of them.")
    tax_tag_invert = fields.Boolean(string="Invert Tags", compute='_compute_tax_tag_invert', store=True, readonly=False,
        help="Technical field. True if the balance of this move line needs to be "
             "inverted when computing its total for each tag (for sales invoices, for example).")

    # ==== Reconciliation fields ====
    amount_residual = fields.Monetary(string='Residual Amount', store=True,
        currency_field='company_currency_id',
        compute='_compute_amount_residual',
        help="The residual amount on a journal item expressed in the company currency.")
    amount_residual_currency = fields.Monetary(string='Residual Amount in Currency', store=True,
        compute='_compute_amount_residual',
        help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Matching", copy=False, index='btree_not_null', readonly=True)
    matched_debit_ids = fields.One2many('account.partial.reconcile', 'credit_move_id', string='Matched Debits',
        help='Debit journal items that are matched with this journal item.', readonly=True)
    matched_credit_ids = fields.One2many('account.partial.reconcile', 'debit_move_id', string='Matched Credits',
        help='Credit journal items that are matched with this journal item.', readonly=True)
    matching_number = fields.Char(string="Matching #", compute='_compute_matching_number', store=True, help="Matching number for this line, 'P' if it is only partially reconcile, or the name of the full reconcile if it exists.")

    # ==== Analytic fields ====
    analytic_line_ids = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
        index='btree_not_null', compute="_compute_analytic_account_id", store=True, readonly=False, check_company=True, copy=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags',
        compute="_compute_analytic_tag_ids", store=True, readonly=False, check_company=True, copy=True)

    # ==== Onchange / display purpose fields ====
    recompute_tax_line = fields.Boolean(store=False, readonly=True,
        help="Technical field used to know on which lines the taxes must be recomputed.")
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")
    is_rounding_line = fields.Boolean(help="Technical field used to retrieve the cash rounding line.")
    exclude_from_invoice_tab = fields.Boolean(help="Technical field used to exclude some lines from the invoice_line_ids tab in the form view.")

    _sql_constraints = [
        (
            'check_credit_debit',
            'CHECK(credit * debit=0)',
            'Wrong credit or debit value in accounting entry !'
        ),
        (
            'check_accountable_required_fields',
             "CHECK(COALESCE(display_type IN ('line_section', 'line_note'), 'f') OR account_id IS NOT NULL)",
             "Missing required account on accountable invoice line."
        ),
        (
            'check_non_accountable_fields_null',
             "CHECK(display_type NOT IN ('line_section', 'line_note') OR (amount_currency = 0 AND debit = 0 AND credit = 0 AND account_id IS NULL))",
             "Forbidden unit price, account and quantity on non-accountable invoice line"
        ),
        (
            'check_amount_currency_balance_sign',
            '''CHECK(
                (
                    (currency_id != company_currency_id)
                    AND
                    (
                        (debit - credit <= 0 AND amount_currency <= 0)
                        OR
                        (debit - credit >= 0 AND amount_currency >= 0)
                    )
                )
                OR
                (
                    currency_id = company_currency_id
                    AND
                    ROUND(debit - credit - amount_currency, 2) = 0
                )
            )''',
            "The amount expressed in the secondary currency must be positive when account is debited and negative when "
            "account is credited. If the currency is the same as the one from the company, this amount must strictly "
            "be equal to the balance."
        ),
    ]

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_default_line_name(self, document, amount, currency, date, partner=None):
        ''' Helper to construct a default label to set on journal items.

        E.g. Vendor Reimbursement $ 1,555.00 - Azure Interior - 05/14/2020.

        :param document:    A string representing the type of the document.
        :param amount:      The document's amount.
        :param currency:    The document's currency.
        :param date:        The document's date.
        :param partner:     The optional partner.
        :return:            A string.
        '''
        values = ['%s %s' % (document, formatLang(self.env, amount, currency_obj=currency))]
        if partner:
            values.append(partner.display_name)
        values.append(format_date(self.env, fields.Date.to_string(date)))
        return ' - '.join(values)

    @api.model
    def _get_default_tax_account(self, repartition_line):
        tax = repartition_line.invoice_tax_id or repartition_line.refund_tax_id
        if tax.tax_exigibility == 'on_payment':
            account = tax.cash_basis_transition_account_id
        else:
            account = repartition_line.account_id
        return account

    def _get_computed_name(self):
        self.ensure_one()

        if not self.product_id:
            return ''

        if self.partner_id.lang:
            product = self.product_id.with_context(lang=self.partner_id.lang)
        else:
            product = self.product_id

        values = []
        if product.partner_ref:
            values.append(product.partner_ref)
        if self.journal_id.type == 'sale':
            if product.description_sale:
                values.append(product.description_sale)
        elif self.journal_id.type == 'purchase':
            if product.description_purchase:
                values.append(product.description_purchase)
        return '\n'.join(values)

    def _get_computed_price_unit(self):
        ''' Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        '''
        self.ensure_one()

        if not self.product_id:
            return 0.0
        if self.move_id.is_sale_document(include_receipts=True):
            document_type = 'sale'
        elif self.move_id.is_purchase_document(include_receipts=True):
            document_type = 'purchase'
        else:
            document_type = 'other'

        return self.product_id._get_tax_included_unit_price(
            self.move_id.company_id,
            self.move_id.currency_id,
            self.move_id.date,
            document_type,
            fiscal_position=self.move_id.fiscal_position_id,
            product_uom=self.product_uom_id
        )

    def _get_computed_account(self):
        self.ensure_one()
        self = self.with_company(self.move_id.journal_id.company_id)

        if not self.product_id:
            return

        fiscal_position = self.move_id.fiscal_position_id
        accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            return accounts['income'] or self.account_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            return accounts['expense'] or self.account_id

    def _get_computed_taxes(self):
        self.ensure_one()

        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids and not self.exclude_from_invoice_tab:
                tax_ids = self.move_id.company_id.account_sale_tax_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids and not self.exclude_from_invoice_tab:
                tax_ids = self.move_id.company_id.account_purchase_tax_id
        else:
            # Miscellaneous operation.
            tax_ids = self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == self.company_id)

        return tax_ids

    def _get_computed_uom(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id.uom_id
        return False

    def _set_price_and_tax_after_fpos(self):
        self.ensure_one()
        # Manage the fiscal position after that and adapt the price_unit.
        # E.g. mapping a price-included-tax to a price-excluded-tax must
        # remove the tax amount from the price_unit.
        # However, mapping a price-included tax to another price-included tax must preserve the balance but
        # adapt the price_unit to the new tax.
        # E.g. mapping a 10% price-included tax to a 20% price-included tax for a price_unit of 110 should preserve
        # 100 as balance but set 120 as price_unit.
        if self.tax_ids and self.move_id.fiscal_position_id and self.move_id.fiscal_position_id.tax_ids:
            price_subtotal = self._get_price_total_and_subtotal()['price_subtotal']
            self.tax_ids = self.move_id.fiscal_position_id.map_tax(self.tax_ids._origin)
            accounting_vals = self._get_fields_onchange_subtotal(
                price_subtotal=price_subtotal,
                currency=self.move_id.company_currency_id)
            amount_currency = accounting_vals['amount_currency']
            business_vals = self._get_fields_onchange_balance(amount_currency=amount_currency)
            if 'price_unit' in business_vals:
                self.price_unit = business_vals['price_unit']

    @api.depends('product_id', 'account_id', 'partner_id', 'date')
    def _compute_analytic_account_id(self):
        for record in self:
            if not record.exclude_from_invoice_tab or not record.move_id.is_invoice(include_receipts=True):
                rec = self.env['account.analytic.default'].account_get(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date,
                    company_id=record.move_id.company_id.id
                )
                if rec:
                    record.analytic_account_id = rec.analytic_id

    @api.depends('product_id', 'account_id', 'partner_id', 'date')
    def _compute_analytic_tag_ids(self):
        for record in self:
            if not record.exclude_from_invoice_tab or not record.move_id.is_invoice(include_receipts=True):
                rec = self.env['account.analytic.default'].account_get(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date,
                    company_id=record.move_id.company_id.id
                )
                if rec:
                    record.analytic_tag_ids = rec.analytic_tag_ids

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=self.price_unit if price_unit is None else price_unit,
            quantity=self.quantity if quantity is None else quantity,
            discount=self.discount if discount is None else discount,
            currency=self.currency_id if currency is None else currency,
            product=self.product_id if product is None else product,
            partner=self.partner_id if partner is None else partner,
            taxes=self.tax_ids if taxes is None else taxes,
            move_type=self.move_id.move_type if move_type is None else move_type,
        )

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    def _get_fields_onchange_subtotal(self, price_subtotal=None, move_type=None, currency=None, company=None, date=None):
        self.ensure_one()
        return self._get_fields_onchange_subtotal_model(
            price_subtotal=self.price_subtotal if price_subtotal is None else price_subtotal,
            move_type=self.move_id.move_type if move_type is None else move_type,
            currency=self.currency_id if currency is None else currency,
            company=self.move_id.company_id if company is None else company,
            date=self.move_id.date if date is None else date,
        )

    @api.model
    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
        ''' This method is used to recompute the values of 'amount_currency', 'debit', 'credit' due to a change made
        in some business fields (affecting the 'price_subtotal' field).

        :param price_subtotal:  The untaxed amount.
        :param move_type:       The type of the move.
        :param currency:        The line's currency.
        :param company:         The move's company.
        :param date:            The move's date.
        :return:                A dictionary containing 'debit', 'credit', 'amount_currency'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1

        amount_currency = price_subtotal * sign
        balance = currency._convert(amount_currency, company.currency_id, company, date or fields.Date.context_today(self))
        return {
            'amount_currency': amount_currency,
            'currency_id': currency.id,
            'debit': self.move_id._get_debit_from_balance(balance, company.currency_id.id),
            'credit': self.move_id._get_credit_from_balance(balance, company.currency_id.id),
        }

    def _get_fields_onchange_balance(self, quantity=None, discount=None, amount_currency=None, move_type=None, currency=None, taxes=None, price_subtotal=None, force_computation=False):
        self.ensure_one()
        return self._get_fields_onchange_balance_model(
            quantity=self.quantity if quantity is None else quantity,
            discount=self.discount if discount is None else discount,
            amount_currency=self.amount_currency if amount_currency is None else amount_currency,
            move_type=self.move_id.move_type if move_type is None else move_type,
            currency=(self.currency_id or self.move_id.currency_id) if currency is None else currency,
            taxes=self.tax_ids if taxes is None else taxes,
            price_subtotal=self.price_subtotal if price_subtotal is None else price_subtotal,
            force_computation=force_computation,
        )

    @api.model
    def _get_fields_onchange_balance_model(self, quantity, discount, amount_currency, move_type, currency, taxes, price_subtotal, force_computation=False):
        ''' This method is used to recompute the values of 'quantity', 'discount', 'price_unit' due to a change made
        in some accounting fields such as 'balance'.

        This method is a bit complex as we need to handle some special cases.
        For example, setting a positive balance with a 100% discount.

        :param quantity:        The current quantity.
        :param discount:        The current discount.
        :param amount_currency: The new balance in line's currency.
        :param move_type:       The type of the move.
        :param currency:        The currency.
        :param taxes:           The applied taxes.
        :param price_subtotal:  The price_subtotal.
        :return:                A dictionary containing 'quantity', 'discount', 'price_unit'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1
        amount_currency *= sign

        # Avoid rounding issue when dealing with price included taxes. For example, when the price_unit is 2300.0 and
        # a 5.5% price included tax is applied on it, a balance of 2300.0 / 1.055 = 2180.094 ~ 2180.09 is computed.
        # However, when triggering the inverse, 2180.09 + (2180.09 * 0.055) = 2180.09 + 119.90 = 2299.99 is computed.
        # To avoid that, set the price_subtotal at the balance if the difference between them looks like a rounding
        # issue.
        if not force_computation and currency.is_zero(amount_currency - price_subtotal):
            return {}

        taxes = taxes.flatten_taxes_hierarchy()
        if taxes and any(tax.price_include for tax in taxes):
            # Inverse taxes. E.g:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 110           | 10% incl, 5%  |                   | 100               | 115
            # 10            |               | 10% incl          | 10                | 10
            # 5             |               | 5%                | 5                 | 5
            #
            # When setting the balance to -200, the expected result is:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 220           | 10% incl, 5%  |                   | 200               | 230
            # 20            |               | 10% incl          | 20                | 20
            # 10            |               | 5%                | 10                | 10
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(amount_currency, currency=currency, handle_price_include=False)
            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                if tax.price_include:
                    amount_currency += tax_res['amount']

        discount_factor = 1 - (discount / 100.0)
        if amount_currency and discount_factor:
            # discount != 100%
            vals = {
                'quantity': quantity or 1.0,
                'price_unit': amount_currency / discount_factor / (quantity or 1.0),
            }
        elif amount_currency and not discount_factor:
            # discount == 100%
            vals = {
                'quantity': quantity or 1.0,
                'discount': 0.0,
                'price_unit': amount_currency / (quantity or 1.0),
            }
        elif not discount_factor:
            # balance of line is 0, but discount  == 100% so we display the normal unit_price
            vals = {}
        else:
            # balance is 0, so unit price is 0 as well
            vals = {'price_unit': 0.0}
        return vals

    @api.model
    def _get_tax_exigible_domain(self):
        """ Returns a domain to be used to identify the move lines that are allowed
        to be taken into account in the tax report.
        """
        return [
            # Lines on moves without any payable or receivable line are always exigible
            '|', ('move_id.always_tax_exigible', '=', True),

            # Lines with only tags are always exigible
            '|', '&', ('tax_line_id', '=', False), ('tax_ids', '=', False),

            # Lines from CABA entries are always exigible
            '|', ('move_id.tax_cash_basis_rec_id', '!=', False),

            # Lines from non-CABA taxes are always exigible
            '|', ('tax_line_id.tax_exigibility', '!=', 'on_payment'),
            ('tax_ids.tax_exigibility', '!=', 'on_payment'), # So: exigible if at least one tax from tax_ids isn't on_payment
        ]

    def belongs_to_refund(self):
        """ Tells whether or not this move line corresponds to a refund operation.
        """
        self.ensure_one()

        if self.tax_repartition_line_id:
            return self.tax_repartition_line_id.refund_tax_id

        elif self.move_id.move_type == 'entry':
            tax_type = self.tax_ids[0].type_tax_use if self.tax_ids else None
            return (tax_type == 'sale' and self.debit) or (tax_type == 'purchase' and self.credit)

        return self.move_id.move_type in ('in_refund', 'out_refund')

    def _get_invoiced_qty_per_product(self):
        qties = defaultdict(float)
        for aml in self:
            qty = aml.product_uom_id._compute_quantity(aml.quantity, aml.product_id.uom_id)
            if aml.move_id.move_type == 'out_invoice':
                qties[aml.product_id] += qty
            elif aml.move_id.move_type == 'out_refund':
                qties[aml.product_id] -= qty
        return qties

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('amount_currency', 'currency_id', 'debit', 'credit', 'tax_ids', 'account_id', 'price_unit', 'quantity')
    def _onchange_mark_recompute_taxes(self):
        ''' Recompute the dynamic onchange based on taxes.
        If the edited line is a tax line, don't recompute anything as the user must be able to
        set a custom value.
        '''
        for line in self:
            if not line.tax_repartition_line_id:
                line.recompute_tax_line = True

    @api.onchange('analytic_account_id', 'analytic_tag_ids')
    def _onchange_mark_recompute_taxes_analytic(self):
        ''' Trigger tax recomputation only when some taxes with analytics
        '''
        for line in self:
            if not line.tax_repartition_line_id and any(tax.analytic for tax in line.tax_ids):
                line.recompute_tax_line = True

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes)
            line.tax_ids = taxes
            line.product_uom_id = line._get_computed_uom()
            line.price_unit = line._get_computed_price_unit()

    @api.onchange('product_uom_id')
    def _onchange_uom_id(self):
        ''' Recompute the 'price_unit' depending of the unit of measure. '''
        if self.display_type in ('line_section', 'line_note'):
            return
        taxes = self._get_computed_taxes()
        if taxes and self.move_id.fiscal_position_id:
            taxes = self.move_id.fiscal_position_id.map_tax(taxes)
        self.tax_ids = taxes
        self.price_unit = self._get_computed_price_unit()

    @api.onchange('account_id')
    def _onchange_account_id(self):
        ''' Recompute 'tax_ids' based on 'account_id'.
        /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
        '''
        for line in self:
            if not line.display_type and (line.account_id.tax_ids or not line.tax_ids):
                taxes = line._get_computed_taxes()

                if taxes and line.move_id.fiscal_position_id:
                    taxes = line.move_id.fiscal_position_id.map_tax(taxes)

                line.tax_ids = taxes

    def _onchange_balance(self):
        for line in self:
            if line.currency_id == line.move_id.company_id.currency_id:
                line.amount_currency = line.balance
            else:
                continue
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            line.update(line._get_fields_onchange_balance())

    @api.onchange('debit')
    def _onchange_debit(self):
        if self.debit:
            self.credit = 0.0
        self._onchange_balance()

    @api.onchange('credit')
    def _onchange_credit(self):
        if self.credit:
            self.debit = 0.0
        self._onchange_balance()

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        for line in self:
            company = line.move_id.company_id
            balance = line.currency_id._convert(line.amount_currency, company.currency_id, company, line.move_id.date or fields.Date.context_today(line))
            line.debit = line.move_id._get_debit_from_balance(balance, company.currency_id.id)
            line.credit = line.move_id._get_credit_from_balance(balance, company.currency_id.id)

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())

    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids')
    def _onchange_price_subtotal(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_price_total_and_subtotal())
            line.update(line._get_fields_onchange_subtotal())

    @api.onchange('currency_id')
    def _onchange_currency(self):
        for line in self:
            company = line.move_id.company_id

            if line.move_id.is_invoice(include_receipts=True):
                line._onchange_price_subtotal()
            elif not line.move_id.reversed_entry_id:
                balance = line.currency_id._convert(line.amount_currency, company.currency_id, company, line.move_id.date or fields.Date.context_today(line))
                line.debit = balance if balance > 0.0 else 0.0
                line.credit = -balance if balance < 0.0 else 0.0

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('full_reconcile_id.name', 'matched_debit_ids', 'matched_credit_ids')
    def _compute_matching_number(self):
        for record in self:
            if record.full_reconcile_id:
                record.matching_number = record.full_reconcile_id.name
            elif record.matched_debit_ids or record.matched_credit_ids:
                record.matching_number = 'P'
            else:
                record.matching_number = None

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        def to_tuple(t):
            return tuple(map(to_tuple, t)) if isinstance(t, (list, tuple)) else t
        # Make an explicit order because we will need to reverse it
        order = (order or self._order) + ', id'
        # Add the domain and order by in order to compute the cumulated balance in _compute_cumulated_balance
        return super(AccountMoveLine, self.with_context(domain_cumulated_balance=to_tuple(domain or []), order_cumulated_balance=order)).search_read(domain, fields, offset, limit, order)

    @api.depends_context('order_cumulated_balance', 'domain_cumulated_balance')
    def _compute_cumulated_balance(self):
        if not self.env.context.get('order_cumulated_balance'):
            # We do not come from search_read, so we are not in a list view, so it doesn't make any sense to compute the cumulated balance
            self.cumulated_balance = 0
            return

        # get the where clause
        query = self._where_calc(list(self.env.context.get('domain_cumulated_balance') or []))
        order_string = ", ".join(self._generate_order_by_inner(self._table, self.env.context.get('order_cumulated_balance'), query, reverse_direction=True))
        from_clause, where_clause, where_clause_params = query.get_sql()
        sql = """
            SELECT account_move_line.id, SUM(account_move_line.balance) OVER (
                ORDER BY %(order_by)s
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
            FROM %(from)s
            WHERE %(where)s
        """ % {'from': from_clause, 'where': where_clause or 'TRUE', 'order_by': order_string}
        self.env.cr.execute(sql, where_clause_params)
        result = {r[0]: r[1] for r in self.env.cr.fetchall()}
        for record in self:
            record.cumulated_balance = result[record.id]

    @api.depends('debit', 'credit', 'amount_currency', 'account_id', 'currency_id', 'move_id.state', 'company_id',
                 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        need_residual_lines = self.filtered(lambda x: x.account_id.reconcile or x.account_id.internal_type == 'liquidity')
        stored_lines = need_residual_lines.filtered('id')

        if stored_lines:
            self.env['account.partial.reconcile'].flush(self.env['account.partial.reconcile']._fields)
            self.env['res.currency'].flush(['decimal_places'])

            aml_ids = tuple(stored_lines.ids)
            self._cr.execute('''
                SELECT
                    part.debit_move_id AS line_id,
                    'debit' AS flag,
                    COALESCE(SUM(part.amount), 0.0) AS amount,
                    ROUND(SUM(part.debit_amount_currency), curr.decimal_places) AS amount_currency
                FROM account_partial_reconcile part
                JOIN res_currency curr ON curr.id = part.debit_currency_id
                WHERE part.debit_move_id IN %s
                GROUP BY part.debit_move_id, curr.decimal_places

                UNION ALL

                SELECT
                    part.credit_move_id AS line_id,
                    'credit' AS flag,
                    COALESCE(SUM(part.amount), 0.0) AS amount,
                    ROUND(SUM(part.credit_amount_currency), curr.decimal_places) AS amount_currency
                FROM account_partial_reconcile part
                JOIN res_currency curr ON curr.id = part.credit_currency_id
                WHERE part.credit_move_id IN %s
                GROUP BY part.credit_move_id, curr.decimal_places
            ''', [aml_ids, aml_ids])
            a = self._cr.fetchall()
            amounts_map = dict(((r[0], r[1]), (r[2], r[3])) for r in a)
        else:
            amounts_map = {}

        # Lines that can't be reconciled with anything since the account doesn't allow that.
        for line in self - need_residual_lines:
            line.amount_residual = 0.0
            line.amount_residual_currency = 0.0
            line.reconciled = False

        for line in need_residual_lines:
            # Since this part could be call on 'new' records, 'company_currency_id'/'currency_id' could be not set.
            comp_curr = line.company_currency_id or self.env.company.currency_id
            foreign_curr = line.currency_id or comp_curr

            # Retrieve the amounts in both foreign/company currencies. If the record is 'new', the amounts_map is empty.
            debit_amount, debit_amount_currency = amounts_map.get((line.id, 'debit'), (0.0, 0.0))
            credit_amount, credit_amount_currency = amounts_map.get((line.id, 'credit'), (0.0, 0.0))

            # Subtract the values from the account.partial.reconcile to compute the residual amounts.
            line.amount_residual = comp_curr.round(line.balance - debit_amount + credit_amount)
            line.amount_residual_currency = foreign_curr.round(line.amount_currency - debit_amount_currency + credit_amount_currency)
            line.reconciled = (
                comp_curr.is_zero(line.amount_residual)
                and foreign_curr.is_zero(line.amount_residual_currency)
                and line.move_id.state not in ('draft', 'cancel')
            )

    @api.depends('tax_repartition_line_id.invoice_tax_id', 'tax_repartition_line_id.refund_tax_id')
    def _compute_tax_line_id(self):
        """ tax_line_id is computed as the tax linked to the repartition line creating
        the move.
        """
        for record in self:
            rep_line = record.tax_repartition_line_id
            # A constraint on account.tax.repartition.line ensures both those fields are mutually exclusive
            record.tax_line_id = rep_line.invoice_tax_id or rep_line.refund_tax_id

    @api.depends('move_id.move_type', 'tax_ids', 'tax_repartition_line_id', 'debit', 'credit', 'tax_tag_ids')
    def _compute_tax_tag_invert(self):
        for record in self:
            if not record.tax_repartition_line_id and not record.tax_ids :
                # Invoices imported from other softwares might only have kept the tags, not the taxes.
                record.tax_tag_invert = record.tax_tag_ids and record.move_id.is_inbound()

            elif record.move_id.move_type == 'entry':
                # For misc operations, cash basis entries and write-offs from the bank reconciliation widget
                rep_line = record.tax_repartition_line_id
                if rep_line:
                    tax_type = (rep_line.refund_tax_id or rep_line.invoice_tax_id).type_tax_use
                    is_refund = bool(rep_line.refund_tax_id)
                elif record.tax_ids:
                    tax_type = record.tax_ids[0].type_tax_use
                    is_refund = (tax_type == 'sale' and record.debit) or (tax_type == 'purchase' and record.credit)

                record.tax_tag_invert = (tax_type == 'purchase' and is_refund) or (tax_type == 'sale' and not is_refund)

            else:
                # For invoices with taxes
                record.tax_tag_invert = record.move_id.is_inbound()

    @api.depends('tax_tag_ids', 'debit', 'credit', 'journal_id', 'tax_tag_invert')
    def _compute_tax_audit(self):
        separator = '        '

        for record in self:
            currency = record.company_id.currency_id
            audit_str = ''
            for tag in record.tax_tag_ids:
                tag_amount = (record.tax_tag_invert and -1 or 1) * (tag.tax_negate and -1 or 1) * record.balance

                if tag.tax_report_line_ids:
                    #Then, the tag comes from a report line, and hence has a + or - sign (also in its name)
                    for report_line in tag.tax_report_line_ids:
                        audit_str += separator if audit_str else ''
                        audit_str += report_line.tag_name + ': ' + formatLang(self.env, tag_amount, currency_obj=currency)
                else:
                    # Then, it's a financial tag (sign is always +, and never shown in tag name)
                    audit_str += separator if audit_str else ''
                    audit_str += tag.name + ': ' + formatLang(self.env, tag_amount, currency_obj=currency)

            record.tax_audit = audit_str

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('account_id', 'journal_id')
    def _check_constrains_account_id_journal_id(self):
        for line in self.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
            account = line.account_id
            journal = line.move_id.journal_id

            if account.deprecated:
                raise UserError(_('The account %s (%s) is deprecated.') % (account.name, account.code))

            account_currency = account.currency_id
            if account_currency and account_currency != line.company_currency_id and account_currency != line.currency_id:
                raise UserError(_('The account selected on your journal entry forces to provide a secondary currency. You should remove the secondary currency on the account.'))

            if account.allowed_journal_ids and journal not in account.allowed_journal_ids:
                raise UserError(_('You cannot use this account (%s) in this journal, check the field \'Allowed Journals\' on the related account.', account.display_name))

            if account in (journal.default_account_id, journal.suspense_account_id):
                continue

            is_account_control_ok = not journal.account_control_ids or account in journal.account_control_ids
            is_type_control_ok = not journal.type_control_ids or account.user_type_id in journal.type_control_ids

            if not is_account_control_ok or not is_type_control_ok:
                raise UserError(_("You cannot use this account (%s) in this journal, check the section 'Control-Access' under "
                                  "tab 'Advanced Settings' on the related journal.", account.display_name))

    @api.constrains('account_id', 'tax_ids', 'tax_line_id', 'reconciled')
    def _check_off_balance(self):
        for line in self:
            if line.account_id.internal_group == 'off_balance':
                if any(a.internal_group != line.account_id.internal_group for a in line.move_id.line_ids.account_id):
                    raise UserError(_('If you want to use "Off-Balance Sheet" accounts, all the accounts of the journal entry must be of this type'))
                if line.tax_ids or line.tax_line_id:
                    raise UserError(_('You cannot use taxes on lines with an Off-Balance account'))
                if line.reconciled:
                    raise UserError(_('Lines from "Off-Balance Sheet" accounts cannot be reconciled'))

    def _affect_tax_report(self):
        self.ensure_one()
        return self.tax_ids or self.tax_line_id or self.tax_tag_ids.filtered(lambda x: x.applicability == "taxes")

    def _check_tax_lock_date(self):
        for line in self.filtered(lambda l: l.move_id.state == 'posted'):
            move = line.move_id
            if move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date and line._affect_tax_report():
                raise UserError(_("The operation is refused as it would impact an already issued tax statement. "
                                  "Please change the journal entry date or the tax lock date set in the settings (%s) to proceed.")
                                % format_date(self.env, move.company_id.tax_lock_date))

    def _check_reconciliation(self):
        for line in self:
            if line.matched_debit_ids or line.matched_credit_ids:
                raise UserError(_("You cannot do this modification on a reconciled journal entry. "
                                  "You can just change some non legal fields or you must unreconcile first.\n"
                                  "Journal Entry (id): %s (%s)") % (line.move_id.name, line.move_id.id))

    @api.constrains('tax_ids', 'tax_repartition_line_id')
    def _check_caba_non_caba_shared_tags(self):
        """ When mixing cash basis and non cash basis taxes, it is important
        that those taxes don't share tags on the repartition creating
        a single account.move.line.

        Shared tags in this context cannot work, as the tags would need to
        be present on both the invoice and cash basis move, leading to the same
        base amount to be taken into account twice; which is wrong.This is
        why we don't support that. A workaround may be provided by the use of
        a group of taxes, whose children are type_tax_use=None, and only one
        of them uses the common tag.

        Note that taxes of the same exigibility are allowed to share tags.
        """
        def get_base_repartition(base_aml, taxes):
            if not taxes:
                return self.env['account.tax.repartition.line']

            is_refund = base_aml.belongs_to_refund()
            repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
            return taxes.mapped(repartition_field)

        for aml in self:
            caba_taxes = aml.tax_ids.filtered(lambda x: x.tax_exigibility == 'on_payment')
            non_caba_taxes = aml.tax_ids - caba_taxes

            caba_base_tags = get_base_repartition(aml, caba_taxes).filtered(lambda x: x.repartition_type == 'base').tag_ids
            non_caba_base_tags = get_base_repartition(aml, non_caba_taxes).filtered(lambda x: x.repartition_type == 'base').tag_ids

            common_tags = caba_base_tags & non_caba_base_tags

            if not common_tags:
                # When a tax is affecting another one with different tax exigibility, tags cannot be shared either.
                tax_tags = aml.tax_repartition_line_id.tag_ids
                comparison_tags = non_caba_base_tags if aml.tax_repartition_line_id.tax_id.tax_exigibility == 'on_payment' else caba_base_tags
                common_tags = tax_tags & comparison_tags

            if common_tags:
                raise ValidationError(_("Taxes exigible on payment and on invoice cannot be mixed on the same journal item if they share some tag."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def init(self):
        """ change index on partner_id to a multi-column index on (partner_id, ref), the new index will behave in the
            same way when we search on partner_id, with the addition of being optimal when having a query that will
            search on partner_id and ref at the same time (which is the case when we open the bank reconciliation widget)
        """
        cr = self._cr
        cr.execute('DROP INDEX IF EXISTS account_move_line_partner_id_index')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_move_line_partner_id_ref_idx',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_partner_id_ref_idx ON account_move_line (partner_id, ref)')

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')

        for vals in vals_list:
            move = self.env['account.move'].browse(vals['move_id'])
            vals.setdefault('company_currency_id', move.company_id.currency_id.id) # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message

            # Ensure balance == amount_currency in case of missing currency or same currency as the one from the
            # company.
            currency_id = vals.get('currency_id') or move.company_id.currency_id.id
            if currency_id == move.company_id.currency_id.id:
                balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
                vals.update({
                    'currency_id': currency_id,
                    'amount_currency': balance,
                })
            else:
                vals['amount_currency'] = vals.get('amount_currency', 0.0)

            if move.is_invoice(include_receipts=True):
                currency = move.currency_id
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                taxes = self.new({'tax_ids': vals.get('tax_ids', [])}).tax_ids
                tax_ids = set(taxes.ids)
                taxes = self.env['account.tax'].browse(tax_ids)

                # Ensure consistency between accounting & business fields.
                # As we can't express such synchronization as computed fields without cycling, we need to do it both
                # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
                # business [resp. accounting] fields are recomputed.
                if any(vals.get(field) for field in ACCOUNTING_FIELDS):
                    price_subtotal = self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ).get('price_subtotal', 0.0)
                    vals.update(self._get_fields_onchange_balance_model(
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        vals['amount_currency'],
                        move.move_type,
                        currency,
                        taxes,
                        price_subtotal
                    ))
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ))
                elif any(vals.get(field) for field in BUSINESS_FIELDS):
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ))
                    vals.update(self._get_fields_onchange_subtotal_model(
                        vals['price_subtotal'],
                        move.move_type,
                        currency,
                        move.company_id,
                        move.date,
                    ))

        lines = super(AccountMoveLine, self).create(vals_list)

        moves = lines.mapped('move_id')
        if self._context.get('check_move_validity', True):
            moves._check_balanced()
        moves.filtered(lambda m: m.state == 'posted')._check_fiscalyear_lock_date()
        lines.filtered(lambda l: l.parent_state == 'posted')._check_tax_lock_date()
        moves._synchronize_business_models({'line_ids'})

        return lines

    def write(self, vals):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        PROTECTED_FIELDS_TAX_LOCK_DATE = ['debit', 'credit', 'tax_line_id', 'tax_ids', 'tax_tag_ids']
        PROTECTED_FIELDS_LOCK_DATE = PROTECTED_FIELDS_TAX_LOCK_DATE + ['account_id', 'journal_id', 'amount_currency', 'currency_id', 'partner_id']
        PROTECTED_FIELDS_RECONCILIATION = ('account_id', 'date', 'debit', 'credit', 'amount_currency', 'currency_id')

        account_to_write = self.env['account.account'].browse(vals['account_id']) if 'account_id' in vals else None

        # Check writing a deprecated account.
        if account_to_write and account_to_write.deprecated:
            raise UserError(_('You cannot use a deprecated account.'))

        for line in self:
            if line.parent_state == 'posted':
                if line.move_id.restrict_mode_hash_table and set(vals).intersection(INTEGRITY_HASH_LINE_FIELDS):
                    raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(INTEGRITY_HASH_LINE_FIELDS))
                if any(key in vals for key in ('tax_ids', 'tax_line_id')):
                    raise UserError(_('You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so.'))

            # Check the lock date.
            if line.parent_state == 'posted' and any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_LOCK_DATE):
                line.move_id._check_fiscalyear_lock_date()

            # Check the tax lock date.
            if line.parent_state == 'posted' and any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_TAX_LOCK_DATE):
                line._check_tax_lock_date()

            # Check the reconciliation.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_RECONCILIATION):
                line._check_reconciliation()

            # Check switching receivable / payable accounts.
            if account_to_write:
                account_type = line.account_id.user_type_id.type
                if line.move_id.is_sale_document(include_receipts=True):
                    if (account_type == 'receivable' and account_to_write.user_type_id.type != account_type) \
                            or (account_type != 'receivable' and account_to_write.user_type_id.type == 'receivable'):
                        raise UserError(_("You can only set an account having the receivable type on payment terms lines for customer invoice."))
                if line.move_id.is_purchase_document(include_receipts=True):
                    if (account_type == 'payable' and account_to_write.user_type_id.type != account_type) \
                            or (account_type != 'payable' and account_to_write.user_type_id.type == 'payable'):
                        raise UserError(_("You can only set an account having the payable type on payment terms lines for vendor bill."))

        # Tracking stuff can be skipped for perfs using tracking_disable context key
        if not self.env.context.get('tracking_disable', False):
            # Get all tracked fields (without related fields because these fields must be manage on their own model)
            tracking_fields = []
            for value in vals:
                field = self._fields[value]
                if hasattr(field, 'related') and field.related:
                    continue # We don't want to track related field.
                if hasattr(field, 'tracking') and field.tracking:
                    tracking_fields.append(value)
            ref_fields = self.env['account.move.line'].fields_get(tracking_fields)

            # Get initial values for each line
            move_initial_values = {}
            for line in self.filtered(lambda l: l.move_id.posted_before): # Only lines with posted once move.
                for field in tracking_fields:
                    # Group initial values by move_id
                    if line.move_id.id not in move_initial_values:
                        move_initial_values[line.move_id.id] = {}
                    move_initial_values[line.move_id.id].update({field: line[field]})

        result = True
        for line in self:
            cleaned_vals = line.move_id._cleanup_write_orm_values(line, vals)
            if not cleaned_vals:
                continue

            # Auto-fill amount_currency if working in single-currency.
            if 'currency_id' not in cleaned_vals \
                and line.currency_id == line.company_currency_id \
                and any(field_name in cleaned_vals for field_name in ('debit', 'credit')):
                cleaned_vals.update({
                    'amount_currency': vals.get('debit', 0.0) - vals.get('credit', 0.0),
                })

            result |= super(AccountMoveLine, line).write(cleaned_vals)

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            # Ensure consistency between accounting & business fields.
            # As we can't express such synchronization as computed fields without cycling, we need to do it both
            # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
            # business [resp. accounting] fields are recomputed.
            if any(field in cleaned_vals for field in ACCOUNTING_FIELDS):
                price_subtotal = line._get_price_total_and_subtotal().get('price_subtotal', 0.0)
                to_write = line._get_fields_onchange_balance(price_subtotal=price_subtotal)
                to_write.update(line._get_price_total_and_subtotal(
                    price_unit=to_write.get('price_unit', line.price_unit),
                    quantity=to_write.get('quantity', line.quantity),
                    discount=to_write.get('discount', line.discount),
                ))
                result |= super(AccountMoveLine, line).write(to_write)
            elif any(field in cleaned_vals for field in BUSINESS_FIELDS):
                to_write = line._get_price_total_and_subtotal()
                to_write.update(line._get_fields_onchange_subtotal(
                    price_subtotal=to_write['price_subtotal'],
                ))
                result |= super(AccountMoveLine, line).write(to_write)

        # Check total_debit == total_credit in the related moves.
        if self._context.get('check_move_validity', True):
            self.mapped('move_id')._check_balanced()

        self.mapped('move_id')._synchronize_business_models({'line_ids'})

        if not self.env.context.get('tracking_disable', False):
            # Log changes to move lines on each move
            for move_id, modified_lines in move_initial_values.items():
                for line in self.filtered(lambda l: l.move_id.id == move_id):
                    tracking_value_ids = line._mail_track(ref_fields, modified_lines)[1]
                    if tracking_value_ids:
                        msg = _(
                            "Journal Item %s updated",
                            line._get_html_link(title=f"#{line.id}")
                        )
                        line.move_id._message_log(
                            body=msg,
                            tracking_value_ids=tracking_value_ids
                        )

        return result

    def _valid_field_parameter(self, field, name):
        # I can't even
        return name == 'tracking' or super()._valid_field_parameter(field, name)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted(self):
        # Prevent deleting lines on posted entries
        if not self._context.get('force_delete') and any(m.state == 'posted' for m in self.move_id):
            raise UserError(_('You cannot delete an item linked to a posted entry.'))

    def unlink(self):
        moves = self.mapped('move_id')

        # Check the lines are not reconciled (partially or not).
        self._check_reconciliation()

        # Check the lock date.
        moves._check_fiscalyear_lock_date()

        # Check the tax lock date.
        self._check_tax_lock_date()

        res = super(AccountMoveLine, self).unlink()

        # Check total_debit == total_credit in the related moves.
        if self._context.get('check_move_validity', True):
            moves._check_balanced()

        return res

    @api.model
    def default_get(self, default_fields):
        # OVERRIDE
        values = super(AccountMoveLine, self).default_get(default_fields)

        if 'account_id' in default_fields and not values.get('account_id') \
            and (self._context.get('journal_id') or self._context.get('default_journal_id')) \
            and self._context.get('default_move_type') in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt'):
            # Fill missing 'account_id'.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            values['account_id'] = journal.default_account_id.id
        elif self._context.get('line_ids') and any(field_name in default_fields for field_name in ('debit', 'credit', 'account_id', 'partner_id')):
            move = self.env['account.move'].new({'line_ids': self._context['line_ids']})

            # Suggest default value for debit / credit to balance the journal entry.
            balance = sum(line['debit'] - line['credit'] for line in move.line_ids)
            # if we are here, line_ids is in context, so journal_id should also be.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            currency = journal.exists() and journal.company_id.currency_id
            if currency:
                balance = currency.round(balance)
            if balance < 0.0:
                values.update({'debit': -balance})
            if balance > 0.0:
                values.update({'credit': balance})

            # Suggest default value for 'partner_id'.
            if 'partner_id' in default_fields and not values.get('partner_id'):
                if len(move.line_ids[-2:]) == 2 and  move.line_ids[-1].partner_id == move.line_ids[-2].partner_id != False:
                    values['partner_id'] = move.line_ids[-2:].mapped('partner_id').id

            # Suggest default value for 'account_id'.
            if 'account_id' in default_fields and not values.get('account_id'):
                if len(move.line_ids[-2:]) == 2 and  move.line_ids[-1].account_id == move.line_ids[-2].account_id != False:
                    values['account_id'] = move.line_ids[-2:].mapped('account_id').id
        if values.get('display_type') or self.display_type:
            values.pop('account_id', None)
        return values

    @api.depends('ref', 'move_id')
    def name_get(self):
        result = []
        for line in self:
            name = line.move_id.name or ''
            if line.ref:
                name += " (%s)" % line.ref
            name += (line.name or line.product_id.display_name) and (' ' + (line.name or line.product_id.display_name)) or ''
            result.append((line.id, name))
        return result

    @api.model
    def invalidate_cache(self, fnames=None, ids=None):
        # Invalidate cache of related moves
        if fnames is None or 'move_id' in fnames:
            field = self._fields['move_id']
            lines = self.env.cache.get_records(self, field) if ids is None else self.browse(ids)
            move_ids = {id_ for id_ in self.env.cache.get_values(lines, field) if id_}
            if move_ids:
                self.env['account.move'].invalidate_cache(ids=move_ids)
        return super().invalidate_cache(fnames=fnames, ids=ids)

    # -------------------------------------------------------------------------
    # TRACKING METHODS
    # -------------------------------------------------------------------------

    def _mail_track(self, tracked_fields, initial):
        changes, tracking_value_ids = super()._mail_track(tracked_fields, initial)
        if len(changes) > len(tracking_value_ids):
            for i, changed_field in enumerate(changes):
                if tracked_fields[changed_field]['type'] in ['one2many', 'many2many']:
                    field = self.env['ir.model.fields']._get(self._name, changed_field)
                    vals = {
                        'field': field.id,
                        'field_desc': field.field_description,
                        'field_type': field.ttype,
                        'tracking_sequence': field.tracking,
                        'old_value_char': ', '.join(initial[changed_field].mapped('name')),
                        'new_value_char': ', '.join(self[changed_field].mapped('name')),
                    }
                    tracking_value_ids.insert(i, Command.create(vals))
        return changes, tracking_value_ids

    # -------------------------------------------------------------------------
    # RECONCILIATION
    # -------------------------------------------------------------------------

    def _prepare_reconciliation_partials(self):
        ''' Prepare the partials on the current journal items to perform the reconciliation.
        /!\ The order of records in self is important because the journal items will be reconciled using this order.

        :return: a tuple of 1) list of vals for partial reconcilation creation, 2) the list of vals for the exchange difference entries to be created
        '''
        def get_odoo_rate(line):
            return recon_currency._get_conversion_rate(company_currency, recon_currency, line.company_id, line.date)

        def get_accounting_rate(line):
            if company_currency.is_zero(line.balance) or line.currency_id.is_zero(line.amount_currency):
                return None
            else:
                return abs(line.amount_currency) / abs(line.balance)

        debit_lines = iter(self.filtered(lambda line: line.balance > 0.0 or line.amount_currency > 0.0))
        credit_lines = iter(self.filtered(lambda line: line.balance < 0.0 or line.amount_currency < 0.0))
        debit_line = None
        credit_line = None

        remaining_debit_amount_curr = 0.0
        remaining_credit_amount_curr = 0.0
        remaining_debit_amount = 0.0
        remaining_credit_amount = 0.0

        partials_vals_list = []
        exchange_data = {}

        while True:

            # ==== Find the next available lines ====
            # For performance reasons, the partials are created all at once meaning the residual amounts can't be
            # trusted from one iteration to another. That's the reason why all residual amounts are kept as variables
            # and reduced "manually" every time we append a dictionary to 'partials_vals_list'.

            # Move to the next available debit line.
            if not debit_line:
                debit_line = next(debit_lines, None)
                if not debit_line:
                    break
                remaining_debit_amount_curr = debit_line.amount_residual_currency
                remaining_debit_amount = debit_line.amount_residual

            # Move to the next available credit line.
            if not credit_line:
                credit_line = next(credit_lines, None)
                if not credit_line:
                    break
                remaining_credit_amount_curr = credit_line.amount_residual_currency
                remaining_credit_amount = credit_line.amount_residual

            # ==== Determine the currency in which the reconciliation will be done ====
            # In this part, we retrieve the residual amounts, check if they are zero or not and determine in which
            # currency and at which rate the reconciliation will be done.

            company_currency = debit_line.company_currency_id
            has_debit_zero_residual = debit_line.company_currency_id.is_zero(remaining_debit_amount)
            has_credit_zero_residual = credit_line.company_currency_id.is_zero(remaining_credit_amount)
            has_debit_zero_residual_currency = debit_line.currency_id.is_zero(remaining_debit_amount_curr)
            has_credit_zero_residual_currency = credit_line.currency_id.is_zero(remaining_credit_amount_curr)

            if debit_line.currency_id == credit_line.currency_id == company_currency \
                    and not has_debit_zero_residual \
                    and not has_credit_zero_residual:
                # Everything is expressed in company's currency and there is something left to reconcile.
                recon_currency = company_currency
                debit_rate = credit_rate = 1.0
                recon_debit_amount = remaining_debit_amount
                recon_credit_amount = -remaining_credit_amount
            elif debit_line.currency_id == company_currency \
                    and not has_debit_zero_residual \
                    and credit_line.currency_id != company_currency \
                    and not has_credit_zero_residual_currency:
                # The credit line is using a foreign currency but not the opposite line.
                # In that case, convert the amount in company currency to the foreign currency one.
                recon_currency = credit_line.currency_id
                debit_rate = get_odoo_rate(debit_line)
                credit_rate = get_accounting_rate(credit_line)
                recon_debit_amount = recon_currency.round(remaining_debit_amount * debit_rate)
                recon_credit_amount = -remaining_credit_amount_curr
            elif debit_line.currency_id != company_currency \
                    and not has_debit_zero_residual_currency \
                    and credit_line.currency_id == company_currency \
                    and not has_credit_zero_residual:
                # The debit line is using a foreign currency but not the opposite line.
                # In that case, convert the amount in company currency to the foreign currency one.
                recon_currency = debit_line.currency_id
                debit_rate = get_accounting_rate(debit_line)
                credit_rate = get_odoo_rate(credit_line)
                recon_debit_amount = remaining_debit_amount_curr
                recon_credit_amount = recon_currency.round(-remaining_credit_amount * credit_rate)
            elif debit_line.currency_id == credit_line.currency_id \
                    and debit_line.currency_id != company_currency \
                    and not has_debit_zero_residual_currency \
                    and not has_credit_zero_residual_currency:
                # Both lines are sharing the same foreign currency.
                recon_currency = debit_line.currency_id
                debit_rate = get_accounting_rate(debit_line)
                credit_rate = get_accounting_rate(credit_line)
                recon_debit_amount = remaining_debit_amount_curr
                recon_credit_amount = -remaining_credit_amount_curr
            elif debit_line.currency_id == credit_line.currency_id \
                    and debit_line.currency_id != company_currency \
                    and (has_debit_zero_residual_currency or has_credit_zero_residual_currency):
                # Special case for exchange difference lines. In that case, both lines are sharing the same foreign
                # currency but at least one has no amount in foreign currency.
                # In that case, we don't want a rate for the opposite line because the exchange difference is supposed
                # to reduce only the amount in company currency but not the foreign one.
                recon_currency = company_currency
                debit_rate = None
                credit_rate = None
                recon_debit_amount = remaining_debit_amount
                recon_credit_amount = -remaining_credit_amount
            else:
                # Multiple involved foreign currencies. The reconciliation is done using the currency of the company.
                recon_currency = company_currency
                debit_rate = get_accounting_rate(debit_line)
                credit_rate = get_accounting_rate(credit_line)
                recon_debit_amount = remaining_debit_amount
                recon_credit_amount = -remaining_credit_amount

            # Check if there is something left to reconcile. Move to the next loop iteration if not.
            skip_reconciliation = False
            if recon_currency.is_zero(recon_debit_amount):
                debit_line = None
                skip_reconciliation = True
            if recon_currency.is_zero(recon_credit_amount):
                credit_line = None
                skip_reconciliation = True
            if skip_reconciliation:
                continue

            # ==== Match both lines together and compute amounts to reconcile ====

            # Determine which line is fully matched by the other.
            compare_amounts = recon_currency.compare_amounts(recon_debit_amount, recon_credit_amount)
            min_recon_amount = min(recon_debit_amount, recon_credit_amount)
            debit_fully_matched = compare_amounts <= 0
            credit_fully_matched = compare_amounts >= 0

            # ==== Computation of partial amounts ====
            if recon_currency == company_currency:
                # Compute the partial amount expressed in company currency.
                partial_amount = min_recon_amount

                # Compute the partial amount expressed in foreign currency.
                if debit_rate:
                    partial_debit_amount_currency = debit_line.currency_id.round(debit_rate * min_recon_amount)
                    partial_debit_amount_currency = min(partial_debit_amount_currency, remaining_debit_amount_curr)
                else:
                    partial_debit_amount_currency = 0.0
                if credit_rate:
                    partial_credit_amount_currency = credit_line.currency_id.round(credit_rate * min_recon_amount)
                    partial_credit_amount_currency = min(partial_credit_amount_currency, -remaining_credit_amount_curr)
                else:
                    partial_credit_amount_currency = 0.0

            else:
                # recon_currency != company_currency
                # Compute the partial amount expressed in company currency.
                if debit_rate:
                    partial_debit_amount = company_currency.round(min_recon_amount / debit_rate)
                    partial_debit_amount = min(partial_debit_amount, remaining_debit_amount)
                else:
                    partial_debit_amount = 0.0
                if credit_rate:
                    partial_credit_amount = company_currency.round(min_recon_amount / credit_rate)
                    partial_credit_amount = min(partial_credit_amount, -remaining_credit_amount)
                else:
                    partial_credit_amount = 0.0
                partial_amount = min(partial_debit_amount, partial_credit_amount)

                # Compute the partial amount expressed in foreign currency.
                # Take care to handle the case when a line expressed in company currency is mimicking the foreign
                # currency of the opposite line.
                if debit_line.currency_id == company_currency:
                    partial_debit_amount_currency = partial_amount
                else:
                    partial_debit_amount_currency = min_recon_amount
                if credit_line.currency_id == company_currency:
                    partial_credit_amount_currency = partial_amount
                else:
                    partial_credit_amount_currency = min_recon_amount

            # Computation of the partial exchange difference. You can skip this part using the
            # `no_exchange_difference` context key (when reconciling an exchange difference for example).
            if not self._context.get('no_exchange_difference'):
                exchange_lines_to_fix = self.env['account.move.line']
                amounts_list = []
                if recon_currency == company_currency:
                    if debit_fully_matched:
                        debit_exchange_amount = remaining_debit_amount_curr - partial_debit_amount_currency
                        if not debit_line.currency_id.is_zero(debit_exchange_amount):
                            exchange_lines_to_fix += debit_line
                            amounts_list.append({'amount_residual_currency': debit_exchange_amount})
                            remaining_credit_amount_curr -= debit_exchange_amount
                    if credit_fully_matched:
                        credit_exchange_amount = remaining_credit_amount_curr + partial_credit_amount_currency
                        if not credit_line.currency_id.is_zero(credit_exchange_amount):
                            exchange_lines_to_fix += credit_line
                            amounts_list.append({'amount_residual_currency': credit_exchange_amount})
                            remaining_credit_amount_curr += credit_exchange_amount

                else:
                    if debit_fully_matched:
                        # Create an exchange difference on the remaining amount expressed in company's currency.
                        debit_exchange_amount = remaining_debit_amount - partial_amount
                        if not debit_line.company_currency_id.is_zero(debit_exchange_amount):
                            exchange_lines_to_fix += debit_line
                            amounts_list.append({'amount_residual': debit_exchange_amount})
                            remaining_debit_amount -= debit_exchange_amount
                    else:
                        # Create an exchange difference ensuring the rate between the residual amounts expressed in
                        # both foreign and company's currency is still consistent regarding the rate between
                        # 'amount_currency' & 'balance'.
                        debit_exchange_amount = partial_debit_amount - partial_amount
                        if debit_line.company_currency_id.compare_amounts(debit_exchange_amount, 0.0) > 0:
                            exchange_lines_to_fix += debit_line
                            amounts_list.append({'amount_residual': debit_exchange_amount})
                            remaining_debit_amount -= debit_exchange_amount

                    if credit_fully_matched:
                        # Create an exchange difference on the remaining amount expressed in company's currency.
                        credit_exchange_amount = remaining_credit_amount + partial_amount
                        if not credit_line.company_currency_id.is_zero(credit_exchange_amount):
                            exchange_lines_to_fix += credit_line
                            amounts_list.append({'amount_residual': credit_exchange_amount})
                            remaining_credit_amount += credit_exchange_amount
                    else:
                        # Create an exchange difference ensuring the rate between the residual amounts expressed in
                        # both foreign and company's currency is still consistent regarding the rate between
                        # 'amount_currency' & 'balance'.
                        credit_exchange_amount = partial_amount - partial_credit_amount
                        if credit_line.company_currency_id.compare_amounts(credit_exchange_amount, 0.0) < 0:
                            exchange_lines_to_fix += credit_line
                            amounts_list.append({'amount_residual': credit_exchange_amount})
                            remaining_credit_amount -= credit_exchange_amount

                if exchange_lines_to_fix:
                    exchange_vals = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                        amounts_list,
                        exchange_date=max(debit_line.date, credit_line.date),
                    )
                    exchange_data[len(partials_vals_list)] = exchange_vals

            # ==== Create partials ====

            remaining_debit_amount -= partial_amount
            remaining_credit_amount += partial_amount
            remaining_debit_amount_curr -= partial_debit_amount_currency
            remaining_credit_amount_curr += partial_credit_amount_currency

            partials_vals_list.append({
                'amount': partial_amount,
                'debit_amount_currency': partial_debit_amount_currency,
                'credit_amount_currency': partial_credit_amount_currency,
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })

            if debit_fully_matched:
                debit_line = None
            if credit_fully_matched:
                credit_line = None
        return partials_vals_list, exchange_data

    def _create_reconciliation_partials(self):
        '''create the partial reconciliation between all the records in self
         :return: A recordset of account.partial.reconcile.
        '''
        partials_vals_list, exchange_data = self._prepare_reconciliation_partials()
        partials = self.env['account.partial.reconcile'].create(partials_vals_list)

        # ==== Create exchange difference moves ====
        for index, exchange_vals in exchange_data.items():
            partials[index].exchange_move_id = self._create_exchange_difference_move(exchange_vals)

        return partials

    def _prepare_exchange_difference_move_vals(self, amounts_list, company=None, exchange_date=None):
        """ Prepare values to create later the exchange difference journal entry.
        The exchange difference journal entry is there to fix the debit/credit of lines when the journal items are
        fully reconciled in foreign currency.

        :param amounts_list:    A list of dict, one for each aml.
        :param company:         The company in case there is no aml in self.
        :param exchange_date:   Optional date object providing the date to consider for the exchange difference.
        :return:                A python dictionary containing:
            * move_vals:    A dictionary to be passed to the account.move.create method.
            * to_reconcile: A list of tuple <move_line, sequence> in order to perform the reconciliation after the move
                            creation.
        """
        company = self.company_id or company
        if not company:
            return

        journal = company.currency_exchange_journal_id
        expense_exchange_account = company.expense_currency_exchange_account_id
        income_exchange_account = company.income_currency_exchange_account_id

        move_vals = {
            'move_type': 'entry',
            'date': max(exchange_date or date.min, company._get_user_fiscal_lock_date() + timedelta(days=1)),
            'journal_id': journal.id,
            'line_ids': [],
        }
        to_reconcile = []

        for line, amounts in zip(self, amounts_list):
            move_vals['date'] = max(move_vals['date'], line.date)

            if 'amount_residual' in amounts:
                amount_residual = amounts['amount_residual']
                amount_residual_currency = 0.0
                amount_residual_to_fix = amount_residual
                if line.company_currency_id.is_zero(amount_residual):
                    continue
            elif 'amount_residual_currency' in amounts:
                amount_residual = 0.0
                amount_residual_currency = amounts['amount_residual_currency']
                amount_residual_to_fix = amount_residual_currency
                if line.currency_id.is_zero(amount_residual_currency):
                    continue
            else:
                continue

            if amount_residual_to_fix > 0.0:
                exchange_line_account = expense_exchange_account
            else:
                exchange_line_account = income_exchange_account

            sequence = len(move_vals['line_ids'])
            move_vals['line_ids'] += [
                Command.create({
                    'name': _('Currency exchange rate difference'),
                    'debit': -amount_residual if amount_residual < 0.0 else 0.0,
                    'credit': amount_residual if amount_residual > 0.0 else 0.0,
                    'amount_currency': -amount_residual_currency,
                    'account_id': line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.partner_id.id,
                    'sequence': sequence,
                }),
                Command.create({
                    'name': _('Currency exchange rate difference'),
                    'debit': amount_residual if amount_residual > 0.0 else 0.0,
                    'credit': -amount_residual if amount_residual < 0.0 else 0.0,
                    'amount_currency': amount_residual_currency,
                    'account_id': exchange_line_account.id,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.partner_id.id,
                    'sequence': sequence + 1,
                }),
            ]
            to_reconcile.append((line, sequence))

        return {'move_vals': move_vals, 'to_reconcile': to_reconcile}

    @api.model
    def _create_exchange_difference_move(self, exchange_diff_vals):
        """ Create the exchange difference journal entry on the current journal items.
        :param exchange_diff_vals:  The current vals of the exchange difference journal entry created by the
                                    '_prepare_exchange_difference_move_vals' method.
        :return:                    An account.move record.
        """
        move_vals = exchange_diff_vals['move_vals']
        if not move_vals['line_ids']:
            return

        # Check the configuration of the exchange difference journal.
        journal = self.env['account.journal'].browse(move_vals['journal_id'])
        if not journal:
            raise UserError(_(
                "You should configure the 'Exchange Gain or Loss Journal' in your company settings, to manage"
                " automatically the booking of accounting entries related to differences between exchange rates."
            ))
        if not journal.company_id.expense_currency_exchange_account_id:
            raise UserError(_(
                "You should configure the 'Loss Exchange Rate Account' in your company settings, to manage"
                " automatically the booking of accounting entries related to differences between exchange rates."
            ))
        if not journal.company_id.income_currency_exchange_account_id.id:
            raise UserError(_(
                "You should configure the 'Gain Exchange Rate Account' in your company settings, to manage"
                " automatically the booking of accounting entries related to differences between exchange rates."
            ))

        # Create the move.
        exchange_move = self.env['account.move'].create(move_vals)
        exchange_move._post(soft=False)

        # Reconcile lines to the newly created exchange difference journal entry by creating more partials.
        for source_line, sequence in exchange_diff_vals['to_reconcile']:
            exchange_diff_line = exchange_move.line_ids[sequence]
            (exchange_diff_line + source_line).with_context(no_exchange_difference=True).reconcile()

        return exchange_move

    def _add_exchange_difference_cash_basis_vals(self, exchange_diff_vals):
        """ Generate the exchange difference values used to create the journal items
        in order to fix the cash basis lines using the transfer account in a multi-currencies
        environment when this account is not a reconcile one.

        When the tax cash basis journal entries are generated and all involved
        transfer account set on taxes are all reconcilable, the account balance
        will be reset to zero by the exchange difference journal items generated
        above. However, this mechanism will not work if there is any transfer
        accounts that are not reconcile and we are generating the cash basis
        journal items in a foreign currency. In that specific case, we need to
        generate extra journal items at the generation of the exchange difference
        journal entry to ensure this balance is reset to zero and then, will not
        appear on the tax report leading to erroneous tax base amount / tax amount.

        :param exchange_diff_vals:  The current vals of the exchange difference journal entry created by the
                                    '_prepare_exchange_difference_move_vals' method.
        """
        move_vals = exchange_diff_vals['move_vals']

        for move in self.move_id:
            account_vals_to_fix = {}

            move_values = move._collect_tax_cash_basis_values()

            # The cash basis doesn't need to be handled for this move because there is another payment term
            # line that is not yet fully paid.
            if not move_values or not move_values['is_fully_paid']:
                continue

            # ==========================================================================
            # Add the balance of all tax lines of the current move in order in order
            # to compute the residual amount for each of them.
            # ==========================================================================

            move_vals['date'] = max(move_vals['date'], move.date)
            for caba_treatment, line in move_values['to_process_lines']:

                vals = {
                    'currency_id': line.currency_id.id,
                    'partner_id': line.partner_id.id,
                    'tax_ids': [Command.set(line.tax_ids.ids)],
                    'tax_tag_ids': [Command.set(line.tax_tag_ids.ids)],
                    'debit': line.debit,
                    'credit': line.credit,
                }

                if caba_treatment == 'tax' and not line.reconciled:
                    # Tax line.
                    grouping_key = self.env['account.partial.reconcile']._get_cash_basis_tax_line_grouping_key_from_record(line)
                    if grouping_key in account_vals_to_fix:
                        debit = account_vals_to_fix[grouping_key]['debit'] + vals['debit']
                        credit = account_vals_to_fix[grouping_key]['credit'] + vals['credit']
                        balance = debit - credit

                        account_vals_to_fix[grouping_key].update({
                            'debit': balance if balance > 0 else 0,
                            'credit': -balance if balance < 0 else 0,
                            'tax_base_amount': account_vals_to_fix[grouping_key]['tax_base_amount'] + line.tax_base_amount,
                        })
                    else:
                        account_vals_to_fix[grouping_key] = {
                            **vals,
                            'account_id': line.account_id.id,
                            'tax_base_amount': line.tax_base_amount,
                            'tax_repartition_line_id': line.tax_repartition_line_id.id,
                        }
                elif caba_treatment == 'base':
                    # Base line.
                    account_to_fix = line.company_id.account_cash_basis_base_account_id
                    if not account_to_fix:
                        continue

                    grouping_key = self.env['account.partial.reconcile']._get_cash_basis_base_line_grouping_key_from_record(line, account=account_to_fix)

                    if grouping_key not in account_vals_to_fix:
                        account_vals_to_fix[grouping_key] = {
                            **vals,
                            'account_id': account_to_fix.id,
                        }
                    else:
                        # Multiple base lines could share the same key, if the same
                        # cash basis tax is used alone on several lines of the invoices
                        account_vals_to_fix[grouping_key]['debit'] += vals['debit']
                        account_vals_to_fix[grouping_key]['credit'] += vals['credit']

            # ==========================================================================
            # Subtract the balance of all previously generated cash basis journal entries
            # in order to retrieve the residual balance of each involved transfer account.
            # ==========================================================================

            cash_basis_moves = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', move.id)])
            for line in cash_basis_moves.line_ids:
                grouping_key = None
                if line.tax_repartition_line_id:
                    # Tax line.
                    grouping_key = self.env['account.partial.reconcile']._get_cash_basis_tax_line_grouping_key_from_record(
                        line,
                        account=line.tax_line_id.cash_basis_transition_account_id,
                    )
                elif line.tax_ids:
                    # Base line.
                    grouping_key = self.env['account.partial.reconcile']._get_cash_basis_base_line_grouping_key_from_record(
                        line,
                        account=line.company_id.account_cash_basis_base_account_id,
                    )

                if grouping_key not in account_vals_to_fix:
                    continue

                account_vals_to_fix[grouping_key]['debit'] -= line.debit
                account_vals_to_fix[grouping_key]['credit'] -= line.credit

            # ==========================================================================
            # Generate the exchange difference journal items:
            # - to reset the balance of all transfer account to zero.
            # - fix rounding issues on the tax account/base tax account.
            # ==========================================================================

            for values in account_vals_to_fix.values():
                balance = values['debit'] - values['credit']

                if move.company_currency_id.is_zero(balance):
                    continue

                if values.get('tax_repartition_line_id'):
                    # Tax line.
                    tax_repartition_line = self.env['account.tax.repartition.line'].browse(values['tax_repartition_line_id'])
                    account = tax_repartition_line.account_id or self.env['account.account'].browse(values['account_id'])

                    sequence = len(move_vals['line_ids'])
                    move_vals['line_ids'] += [
                        Command.create({
                            **values,
                            'name': _('Currency exchange rate difference (cash basis)'),
                            'debit': balance if balance > 0.0 else 0.0,
                            'credit': -balance if balance < 0.0 else 0.0,
                            'account_id': account.id,
                            'sequence': sequence,
                        }),
                        Command.create({
                            **values,
                            'name': _('Currency exchange rate difference (cash basis)'),
                            'debit': -balance if balance < 0.0 else 0.0,
                            'credit': balance if balance > 0.0 else 0.0,
                            'account_id': values['account_id'],
                            'tax_ids': [],
                            'tax_tag_ids': [],
                            'tax_repartition_line_id': False,
                            'sequence': sequence + 1,
                        }),
                    ]
                else:
                    # Base line.
                    sequence = len(move_vals['line_ids'])
                    move_vals['line_ids'] += [
                        Command.create({
                            **values,
                            'name': _('Currency exchange rate difference (cash basis)'),
                            'debit': balance if balance > 0.0 else 0.0,
                            'credit': -balance if balance < 0.0 else 0.0,
                            'sequence': sequence,
                        }),
                        Command.create({
                            **values,
                            'name': _('Currency exchange rate difference (cash basis)'),
                            'debit': -balance if balance < 0.0 else 0.0,
                            'credit': balance if balance > 0.0 else 0.0,
                            'tax_ids': [],
                            'tax_tag_ids': [],
                            'sequence': sequence + 1,
                        }),
                    ]

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * exchange_partials:    A recorset of all account.partial.reconcile created during the reconciliation
                                        with the exchange difference journal entries.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {'exchange_partials': self.env['account.partial.reconcile']}

        if not self:
            return results

        # List unpaid invoices
        not_paid_invoices = self.move_id.filtered(
            lambda move: move.is_invoice(include_receipts=True) and move.payment_state not in ('paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                                % line.account_id.display_name)
            if line.move_id.state != 'posted':
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))

        sorted_lines = self.sorted(key=lambda line: (line.date_maturity or line.date, line.currency_id, line.amount_currency))

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines
        involved_partials = self.env['account.partial.reconcile']
        current_lines = involved_lines
        current_partials = involved_partials
        while current_lines:
            current_partials = (current_lines.matched_debit_ids + current_lines.matched_credit_ids) - current_partials
            involved_partials += current_partials
            current_lines = (current_partials.debit_move_id + current_partials.credit_move_id) - current_lines
            involved_lines += current_lines

        # ==== Create partials ====

        partial_no_exch_diff = bool(self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))
        sorted_lines_ctx = sorted_lines.with_context(no_exchange_difference=self._context.get('no_exchange_difference') or partial_no_exch_diff)
        partials = sorted_lines_ctx._create_reconciliation_partials()
        results['partials'] = partials
        involved_partials += partials
        exchange_move_lines = partials.exchange_move_id.line_ids.filtered(lambda line: line.account_id == account)
        involved_lines += exchange_move_lines
        exchange_diff_partials = exchange_move_lines.matched_debit_ids + exchange_move_lines.matched_credit_ids
        involved_partials += exchange_diff_partials
        results['exchange_partials'] += exchange_diff_partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.user_type_id.type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        def is_line_reconciled(line):
            # Check if the journal item passed as parameter is now fully reconciled.
            return line.reconciled \
                   or line.currency_id.is_zero(line.amount_residual_currency) \
                   or line.company_currency_id.is_zero(line.amount_residual)

        if all(is_line_reconciled(line) for line in involved_lines):

            # ==== Create the exchange difference move ====
            # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
            # when importing a full accounting including the reconciliation like Winbooks.

            exchange_move = None
            if not self._context.get('no_exchange_difference'):
                # In normal cases, the exchange differences are already generated by the partial at this point meaning
                # there is no journal item left with a zero amount residual in one currency but not in the other.
                # However, after a migration coming from an older version with an older partial reconciliation or due to
                # some rounding issues (when dealing with different decimal places for example), we could need an extra
                # exchange difference journal entry to handle them.
                exchange_lines_to_fix = self.env['account.move.line']
                amounts_list = []
                exchange_max_date = date.min
                for line in involved_lines:
                    if not line.company_currency_id.is_zero(line.amount_residual):
                        exchange_lines_to_fix += line
                        amounts_list.append({'amount_residual': line.amount_residual})
                    elif not line.currency_id.is_zero(line.amount_residual_currency):
                        exchange_lines_to_fix += line
                        amounts_list.append({'amount_residual_currency': line.amount_residual_currency})
                    exchange_max_date = max(exchange_max_date, line.date)
                exchange_diff_vals = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    company=involved_lines[0].company_id,
                    exchange_date=exchange_max_date,
                )

                # Exchange difference for cash basis entries.
                is_cash_basis_needed = account.internal_type in ('receivable', 'payable')
                if is_cash_basis_needed:
                    involved_lines._add_exchange_difference_cash_basis_vals(exchange_diff_vals)

                # Create the exchange difference.
                if exchange_diff_vals['move_vals']['line_ids']:
                    exchange_move = involved_lines._create_exchange_difference_move(exchange_diff_vals)
                    if exchange_move:
                        exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                        # Track newly created lines.
                        involved_lines += exchange_move_lines

                        # Track newly created partials.
                        exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                                 + exchange_move_lines.matched_credit_ids
                        involved_partials += exchange_diff_partials
                        results['exchange_partials'] += exchange_diff_partials

            # ==== Create the full reconcile ====

            results['full_reconcile'] = self.env['account.full.reconcile'].create({
                'exchange_move_id': exchange_move and exchange_move.id,
                'partial_reconcile_ids': [(6, 0, involved_partials.ids)],
                'reconciled_line_ids': [(6, 0, involved_lines.ids)],
            })

        # Trigger action for paid invoices
        not_paid_invoices\
            .filtered(lambda move: move.payment_state in ('paid', 'in_payment'))\
            .action_invoice_paid()

        return results

    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        (self.matched_debit_ids + self.matched_credit_ids).unlink()

    def _copy_data_extend_business_fields(self, values):
        ''' Hook allowing copying business fields under certain conditions.
        E.g. The link to the sale order lines must be preserved in case of a refund.
        '''
        self.ensure_one()

    def copy_data(self, default=None):
        res = super(AccountMoveLine, self).copy_data(default=default)

        for line, values in zip(self, res):
            # Don't copy the name of a payment term line.
            if line.move_id.is_invoice() and line.account_id.user_type_id.type in ('receivable', 'payable'):
                values['name'] = ''
            # Don't copy restricted fields of notes
            if line.display_type in ('line_section', 'line_note'):
                values['amount_currency'] = 0
                values['debit'] = 0
                values['credit'] = 0
                values['account_id'] = False
            if self._context.get('include_business_fields'):
                line._copy_data_extend_business_fields(values)
        return res

    # -------------------------------------------------------------------------
    # MISC
    # -------------------------------------------------------------------------

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        is_invoice = self.move_id.is_invoice(include_receipts=True)
        sign = -1 if self.move_id.is_inbound(include_receipts=True) else 1

        if is_invoice:
            is_refund = self.move_id.move_type in ('out_refund', 'in_refund')
        else:
            tax_type = self.tax_ids[0].type_tax_use if self.tax_ids else None
            is_refund = (tax_type == 'sale' and self.balance > 0.0) or (tax_type == 'purchase' and self.balance < 0.0)

        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.partner_id,
            currency=self.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=self.price_unit if is_invoice else self.amount_currency,
            quantity=self.quantity if is_invoice else 1.0,
            discount=self.discount if is_invoice else 0.0,
            account=self.account_id,
            analytic_account=self.analytic_account_id,
            analytic_tags=self.analytic_tag_ids,
            price_subtotal=sign * self.amount_currency,
            is_refund=is_refund,
        )

    def _convert_to_tax_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        sign = -1 if self.move_id.is_inbound(include_receipts=True) else 1

        return self.env['account.tax']._convert_to_tax_line_dict(
            self,
            partner=self.partner_id,
            currency=self.currency_id,
            taxes=self.tax_ids,
            tax_tags=self.tax_tag_ids,
            tax_repartition_line=self.tax_repartition_line_id,
            group_tax=self.group_tax_id,
            account=self.account_id,
            analytic_account=self.analytic_account_id,
            analytic_tags=self.analytic_tag_ids,
            tax_amount=sign * self.amount_currency,
        )

    def _get_analytic_tag_ids(self):
        self.ensure_one()
        return self.analytic_tag_ids.filtered(lambda r: not r.active_analytic_distribution).ids

    def create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic account or an analytic distribution.
        """
        lines_to_create_analytic_entries = self.env['account.move.line']
        analytic_line_vals = []
        for obj_line in self:
            for tag in obj_line.analytic_tag_ids.filtered('active_analytic_distribution'):
                for distribution in tag.analytic_distribution_ids:
                    analytic_line_vals.append(obj_line._prepare_analytic_distribution_line(distribution))
            if obj_line.analytic_account_id:
                lines_to_create_analytic_entries |= obj_line

        # create analytic entries in batch
        if lines_to_create_analytic_entries:
            analytic_line_vals += lines_to_create_analytic_entries._prepare_analytic_line()

        self.env['account.analytic.line'].create(analytic_line_vals)

    def _prepare_analytic_line(self):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            an analytic account. This method is intended to be extended in other modules.
            :return list of values to create analytic.line
            :rtype list
        """
        result = []
        for move_line in self:
            amount = (move_line.credit or 0.0) - (move_line.debit or 0.0)
            default_name = move_line.name or (move_line.ref or '/' + ' -- ' + (move_line.partner_id and move_line.partner_id.name or '/'))
            category = 'other'
            if move_line.move_id.is_sale_document():
                category = 'invoice'
            elif move_line.move_id.is_purchase_document():
                category = 'vendor_bill'
            result.append({
                'name': default_name,
                'date': move_line.date,
                'account_id': move_line.analytic_account_id.id,
                'group_id': move_line.analytic_account_id.group_id.id,
                'tag_ids': [(6, 0, move_line._get_analytic_tag_ids())],
                'unit_amount': move_line.quantity,
                'product_id': move_line.product_id and move_line.product_id.id or False,
                'product_uom_id': move_line.product_uom_id and move_line.product_uom_id.id or False,
                'amount': amount,
                'general_account_id': move_line.account_id.id,
                'ref': move_line.ref,
                'move_id': move_line.id,
                'user_id': move_line.move_id.invoice_user_id.id or self._uid,
                'partner_id': move_line.partner_id.id,
                'company_id': move_line.analytic_account_id.company_id.id or move_line.move_id.company_id.id,
                'category': category,
            })
        return result

    def _prepare_analytic_distribution_line(self, distribution):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        amount = -self.balance * distribution.percentage / 100.0
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            'account_id': distribution.account_id.id,
            'group_id': distribution.account_id.group_id.id,
            'partner_id': self.partner_id.id,
            'tag_ids': [(6, 0, [distribution.tag_id.id] + self._get_analytic_tag_ids())],
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_id': self.id,
            'user_id': self.move_id.invoice_user_id.id or self._uid,
            'company_id': distribution.account_id.company_id.id or self.company_id.id or self.env.company.id,
        }

    @api.model
    def _query_get(self, domain=None):
        self.check_access_rights('read')

        context = dict(self._context or {})
        domain = domain or []
        if not isinstance(domain, (list, tuple)):
            domain = ast.literal_eval(domain)

        date_field = 'date'
        if context.get('aged_balance'):
            date_field = 'date_maturity'
        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += ['|', (date_field, '>=', context['date_from']), ('account_id.user_type_id.include_initial_balance', '=', True)]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('parent_state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]
        elif context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.companies.ids)]
        else:
            domain += [('company_id', '=', self.env.company.id)]

        if context.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|', ('matched_debit_ids.max_date', '>', context['reconcile_date']), ('matched_credit_ids.max_date', '>', context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('account_ids'):
            domain += [('account_id', 'in', context['account_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += [('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in', context['analytic_account_ids'].ids)]

        if context.get('partner_ids'):
            domain += [('partner_id', 'in', context['partner_ids'].ids)]

        if context.get('partner_categories'):
            domain += [('partner_id.category_id', 'in', context['partner_categories'].ids)]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            domain.append(('display_type', 'not in', ('line_section', 'line_note')))
            domain.append(('parent_state', '!=', 'cancel'))

            query = self._where_calc(domain)

            # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
            self._apply_ir_rules(query)

            tables, where_clause, where_clause_params = query.get_sql()
        return tables, where_clause, where_clause_params

    def _reconciled_lines(self):
        ids = []
        for aml in self.filtered('account_id.reconcile'):
            ids.extend([r.debit_move_id.id for r in aml.matched_debit_ids] if aml.credit > 0 else [r.credit_move_id.id for r in aml.matched_credit_ids])
            ids.append(aml.id)
        return ids

    def open_reconcile_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        ids = self._reconciled_lines()
        action['domain'] = [('id', 'in', ids)]
        return action

    def action_automatic_entry(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.account_automatic_entry_wizard_action')
        # Force the values of the move line in the context to avoid issues
        ctx = dict(self.env.context)
        ctx.pop('active_id', None)
        ctx.pop('default_journal_id', None)
        ctx['active_ids'] = self.ids
        ctx['active_model'] = 'account.move.line'
        action['context'] = ctx
        return action

    @api.model
    def _get_suspense_moves_domain(self):
        return [
            ('move_id.to_check', '=', True),
            ('full_reconcile_id', '=', False),
            ('statement_line_id', '!=', False),
        ]

    def _get_attachment_domains(self):
        self.ensure_one()
        domains = [[('res_model', '=', 'account.move'), ('res_id', '=', self.move_id.id)]]
        if self.statement_id:
            domains.append([('res_model', '=', 'account.bank.statement'), ('res_id', '=', self.statement_id.id)])
        if self.payment_id:
            domains.append([('res_model', '=', 'account.payment'), ('res_id', '=', self.payment_id.id)])
        return domains

    def _get_downpayment_lines(self):
        ''' Return the downpayment move lines associated with the move line.
        This method is overridden in the sale order module.
        '''
        return self.env['account.move.line']
