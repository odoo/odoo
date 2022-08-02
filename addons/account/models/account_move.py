# -*- coding: utf-8 -*-

from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch

from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision
from odoo.addons.account.tools import format_rf_reference
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    is_html_empty,
    sql
)


#forbidden fields
INTEGRITY_HASH_MOVE_FIELDS = ('date', 'journal_id', 'company_id')
INTEGRITY_HASH_LINE_FIELDS = ('debit', 'credit', 'account_id', 'partner_id')

TYPE_REVERSE_MAP = {
    'entry': 'entry',
    'out_invoice': 'out_refund',
    'out_refund': 'entry',
    'in_invoice': 'in_refund',
    'in_refund': 'entry',
    'out_receipt': 'entry',
    'in_receipt': 'entry',
}


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _description = "Journal Entry"
    _order = 'date desc, name desc, id desc'
    _mail_post_access = 'read'
    _check_company_auto = True
    _sequence_index = "journal_id"

    @property
    def _sequence_monthly_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_monthly_regex

    @property
    def _sequence_yearly_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_yearly_regex

    @property
    def _sequence_fixed_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_fixed_regex


    # ==============================================================================================
    #                                          JOURNAL ENTRY
    # ==============================================================================================

    # === Accounting fields === #
    name = fields.Char(
        string='Number',
        compute='_compute_name', readonly=False, store=True,
        copy=False,
        tracking=True,
        index='btree',
    )
    ref = fields.Char(string='Reference', copy=False, tracking=True)
    date = fields.Date(
        string='Date',
        index=True,
        compute='_compute_date', store=True, required=True, readonly=False, precompute=True,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
        copy=False,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default='draft',
    )
    move_type = fields.Selection(
        selection=[
            ('entry', 'Journal Entry'),
            ('out_invoice', 'Customer Invoice'),
            ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'Vendor Bill'),
            ('in_refund', 'Vendor Credit Note'),
            ('out_receipt', 'Sales Receipt'),
            ('in_receipt', 'Purchase Receipt'),
        ],
        string='Type',
        required=True,
        readonly=True,
        tracking=True,
        change_default=True,
        index=True,
        default="entry",
    )
    is_storno = fields.Boolean(
        compute='_compute_is_storno', store=True, readonly=False,
        copy=False,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        compute='_compute_journal_id', store=True, readonly=False, precompute=True,
        required=True,
        states={'draft': [('readonly', False)]},
        check_company=True,
        domain="[('id', 'in', suitable_journal_ids)]",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        compute='_compute_company_id', inverse='_inverse_company_id', store=True, readonly=False, precompute=True,
    )
    line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Journal Items',
        copy=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    # === Payment fields === #
    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string="Payment",
        index='btree_not_null',
        copy=False,
        check_company=True,
    )

    # === Statement fields === #
    statement_line_id = fields.Many2one(
        comodel_name='account.bank.statement.line',
        string="Statement Line",
        copy=False,
        check_company=True,
    )
    # used to open the linked bank statement from the edit button in a group by
    # view, or via the smart button on journal entries.
    statement_id = fields.Many2one(
        related='statement_line_id.statement_id',
        copy=False,
        readonly=True,
    )

    # === Cash basis feature fields === #
    # used to keep track of the tax cash basis reconciliation. This is needed
    # when cancelling the source: it will post the inverse journal entry to
    # cancel that part too.
    tax_cash_basis_rec_id = fields.Many2one(
        comodel_name='account.partial.reconcile',
        string='Tax Cash Basis Entry of',
    )
    tax_cash_basis_origin_move_id = fields.Many2one(
        comodel_name='account.move',
        index='btree_not_null',
        string="Cash Basis Origin",
        readonly=True,
        help="The journal entry from which this tax cash basis journal entry has been created.",
    )
    tax_cash_basis_created_move_ids = fields.One2many(
        string="Cash Basis Entries",
        comodel_name='account.move',
        inverse_name='tax_cash_basis_origin_move_id',
        help="The cash basis entries created from the taxes on this entry, when reconciling its lines.",
    )

    # used by cash basis taxes, telling the lines of the move are always
    # exigible. This happens if the move contains no payable or receivable line.
    always_tax_exigible = fields.Boolean(compute='_compute_always_tax_exigible', store=True)

    # === Misc fields === #
    auto_post = fields.Selection(
        string='Auto-post',
        selection=[
            ('no', 'No'),
            ('at_date', 'At Date'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        default='no', required=True, copy=False,
        help='Specify whether this entry is posted automatically on its accounting date, and any similar recurring invoices.')
    auto_post_until = fields.Date(
        string='Auto-post until',
        copy=False,
        compute='_compute_auto_post_until', store=True, readonly=False,
        help='This recurring move will be posted up to and including this date.')
    auto_post_origin_id = fields.Many2one(
        comodel_name='account.move',
        string='First recurring entry',
        readonly=True, copy=False,
    )
    hide_post_button = fields.Boolean(compute='_compute_hide_post_button', readonly=True)
    to_check = fields.Boolean(
        string='To Check',
        tracking=True,
        help="If this checkbox is ticked, it means that the user was not sure of all the related "
             "information at the time of the creation of the move and that the move needs to be "
             "checked again.",
    )
    posted_before = fields.Boolean(copy=False)
    suitable_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_suitable_journal_ids',
    )
    highest_name = fields.Char(compute='_compute_highest_name')
    made_sequence_hole = fields.Boolean(compute='_compute_made_sequence_hole')
    show_name_warning = fields.Boolean(store=False)
    type_name = fields.Char('Type Name', compute='_compute_type_name')
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', readonly=True)

    # === Hash Fields === #
    restrict_mode_hash_table = fields.Boolean(related='journal_id.restrict_mode_hash_table')
    secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True, copy=False)
    inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True)

    # ==============================================================================================
    #                                          INVOICE
    # ==============================================================================================

    invoice_line_ids = fields.One2many(  # /!\ invoice_line_ids is just a subset of line_ids.
        'account.move.line',
        'move_id',
        string='Invoice lines',
        copy=False,
        readonly=True,
        domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))],
        states={'draft': [('readonly', False)]},
    )

    # === Date fields === #
    invoice_date = fields.Date(
        string='Invoice/Bill Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
        index=True,
        copy=False,
    )
    invoice_date_due = fields.Date(
        string='Due Date',
        compute='_compute_invoice_date_due', store=True, readonly=False,
        states={'draft': [('readonly', False)]},
        index=True,
        copy=False,
    )
    invoice_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment Terms',
        compute='_compute_invoice_payment_term_id', store=True, readonly=False, precompute=True,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
        check_company=True,
    )
    needed_terms = fields.Binary(compute='_compute_needed_terms')
    needed_terms_dirty = fields.Boolean(compute='_compute_needed_terms')

    # === Partner fields === #
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=True,
        tracking=True,
        states={'draft': [('readonly', False)]},
        inverse='_inverse_partner_id',
        check_company=True,
        change_default=True,
        ondelete='restrict',
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        string='Commercial Entity',
        compute='_compute_commercial_partner_id', store=True, readonly=True,
        ondelete='restrict',
    )
    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        compute='_compute_partner_shipping_id', store=True, readonly=False, precompute=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Delivery address for current invoice.",
    )
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        string='Recipient Bank',
        compute='_compute_partner_bank_id', store=True, readonly=False,
        help="Bank Account Number to which the invoice will be paid. "
             "A Company bank account if this is a Customer Invoice or Vendor Credit Note, "
             "otherwise a Partner bank account number.",
        check_company=True,
    )
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        string='Fiscal Position',
        check_company=True,
        compute='_compute_fiscal_position_id', store=True, readonly=False, precompute=True,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
        domain="[('company_id', '=', company_id)]",
        ondelete="restrict",
        help="Fiscal positions are used to adapt taxes and accounts for particular "
             "customers or sales orders/invoices. The default value comes from the customer.",
    )

    # === Payment fields === #
    payment_reference = fields.Char(
        string='Payment Reference',
        index='trigram',
        copy=False,
        help="The payment reference to set on journal items.",
    )
    display_qr_code = fields.Boolean(
        string="Display QR-code",
        related='company_id.qr_code',
    )
    qr_code_method = fields.Selection(
        string="Payment QR-code", copy=False,
        selection=lambda self: self.env['res.partner.bank'].get_available_qr_methods_in_sequence(),
        help="Type of QR-code to be generated for the payment of this invoice, "
             "when printing it. If left blank, the first available and usable method "
             "will be used.",
    )

    # === Payment widget fields === #
    invoice_outstanding_credits_debits_widget = fields.Binary(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_to_reconcile_info',
    )
    invoice_has_outstanding = fields.Boolean(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_to_reconcile_info',
    )
    invoice_payments_widget = fields.Binary(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_reconciled_info',
    )

    # === Currency fields === #
    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        tracking=True,
        required=True,
        compute='_compute_currency_id', inverse='_inverse_currency_id', store=True, readonly=False, precompute=True,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
    )

    # === Amount fields === #
    direction_sign = fields.Integer(
        compute='_compute_direction_sign',
        help="Multiplicator depending on the document type, to convert a price into a balance",
    )
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amount', store=True, readonly=True,
        tracking=True,
    )
    amount_tax = fields.Monetary(
        string='Tax',
        compute='_compute_amount', store=True, readonly=True,
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amount', store=True, readonly=True,
        inverse='_inverse_amount_total',
    )
    amount_residual = fields.Monetary(
        string='Amount Due',
        compute='_compute_amount', store=True,
    )
    amount_untaxed_signed = fields.Monetary(
        string='Untaxed Amount Signed',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='company_currency_id',
    )
    amount_tax_signed = fields.Monetary(
        string='Tax Signed',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='company_currency_id',
    )
    amount_total_signed = fields.Monetary(
        string='Total Signed',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='company_currency_id',
    )
    amount_total_in_currency_signed = fields.Monetary(
        string='Total in Currency Signed',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='currency_id',
    )
    amount_residual_signed = fields.Monetary(
        string='Amount Due Signed',
        compute='_compute_amount', store=True,
        currency_field='company_currency_id',
    )
    tax_totals = fields.Binary(
        string="Invoice Totals",
        compute='_compute_tax_totals',
        inverse='_inverse_tax_totals',
        help='Edit Tax amounts if you encounter rounding issues.',
    )
    payment_state = fields.Selection(
        selection=[
            ('not_paid', 'Not Paid'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('partial', 'Partially Paid'),
            ('reversed', 'Reversed'),
            ('invoicing_legacy', 'Invoicing App Legacy'),
        ],
        string="Payment Status",
        compute='_compute_payment_state', store=True, readonly=True,
        copy=False,
        tracking=True,
    )

    # ==== Early payment cash discount field ====
    invoice_early_pay_amount_after_discount = fields.Monetary(
        compute='_compute_early_pay_amount_after_discount',
        help="Total amount left to pay after the discount was applied",
    )

    # === Reverse feature fields === #
    reversed_entry_id = fields.Many2one(
        comodel_name='account.move',
        string="Reversal of",
        index='btree_not_null',
        readonly=True,
        copy=False,
        check_company=True,
    )
    reversal_move_id = fields.One2many('account.move', 'reversed_entry_id')

    # === Vendor bill fields === #
    invoice_vendor_bill_id = fields.Many2one(
        'account.move',
        store=False,
        check_company=True,
        string='Vendor Bill',
        help="Auto-complete from a past bill.",
    )
    invoice_source_email = fields.Char(string='Source Email', tracking=True)
    invoice_partner_display_name = fields.Char(compute='_compute_invoice_partner_display_info', store=True)

    # === Fiduciary mode fields === #
    quick_edit_mode = fields.Boolean(compute='_compute_quick_edit_mode')
    quick_edit_total_amount = fields.Monetary(
        string='Total (Tax inc.)',
        help='Use this field to encode the total amount of the invoice.\n'
             'Odoo will automatically create one invoice line with default values to match it.',
    )

    # === Misc Information === #
    narration = fields.Html(
        string='Terms and Conditions',
        compute='_compute_narration', store=True, readonly=False,
    )
    is_move_sent = fields.Boolean(
        readonly=True,
        default=False,
        copy=False,
        tracking=True,
        help="It indicates that the invoice/payment has been sent.",
    )
    invoice_user_id = fields.Many2one(
        string='Salesperson',
        comodel_name='res.users',
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
    )
    # Technical field used to fit the generic behavior in mail templates.
    user_id = fields.Many2one(string='User', related='invoice_user_id')
    invoice_origin = fields.Char(
        string='Origin',
        readonly=True,
        tracking=True,
        help="The document(s) that generated the invoice.",
    )
    invoice_incoterm_id = fields.Many2one(
        comodel_name='account.incoterms',
        string='Incoterm',
        default=lambda self: self.env.company.incoterm_id,
        help='International Commercial Terms are a series of predefined commercial '
             'terms used in international transactions.',
    )
    invoice_cash_rounding_id = fields.Many2one(
        comodel_name='account.cash.rounding',
        string='Cash Rounding Method',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Defines the smallest coinage of the currency that can be used to pay by cash.',
    )

    # === Display purpose fields === #
    # used to have a dynamic domain on journal / taxes in the form view.
    invoice_filter_type_domain = fields.Char(compute='_compute_invoice_filter_type_domain')
    bank_partner_id = fields.Many2one(
        comodel_name='res.partner',
        compute='_compute_bank_partner_id',
        help='Technical field to get the domain on the bank',
    )
    # used to display a message when the invoice's accounting date is prior of the tax lock date
    tax_lock_date_message = fields.Char(compute='_compute_tax_lock_date_message')
    # used for tracking the status of the currency
    display_inactive_currency_warning = fields.Boolean(compute="_compute_display_inactive_currency_warning")
    tax_country_id = fields.Many2one(  # used to filter the available taxes depending on the fiscal country and fiscal position.
        comodel_name='res.country',
        compute='_compute_tax_country_id',
    )
    tax_country_code = fields.Char(compute="_compute_tax_country_code")
    has_reconciled_entries = fields.Boolean(compute="_compute_has_reconciled_entries")
    show_reset_to_draft_button = fields.Boolean(compute='_compute_show_reset_to_draft_button')
    partner_credit_warning = fields.Text(
        compute='_compute_partner_credit_warning',
        groups="account.group_account_invoice,account.group_account_readonly",
    )

    def _auto_init(self):
        super()._auto_init()
        if sql.install_pg_trgm(self._cr):
            # We need the btree index for unicity constraint (on field) AND this one for human searches
            sql.create_index(self._cr, 'account_move_name_trigram_index', self._table, ['"name" gin_trgm_ops'], 'gin')

        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS account_move_to_check_idx
            ON account_move(journal_id) WHERE to_check = true;
            CREATE INDEX IF NOT EXISTS account_move_payment_idx
            ON account_move(journal_id, state, payment_state, move_type, date);
        """)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('invoice_date', 'company_id')
    def _compute_date(self):
        for move in self:
            if not move.invoice_date:
                if not move.date:
                    move.date = fields.Date.context_today(self)
                continue
            accounting_date = move.invoice_date
            if not move.is_sale_document(include_receipts=True):
                accounting_date = move._get_accounting_date(move.invoice_date, move._affect_tax_report())
            if accounting_date and accounting_date != move.date:
                move.date = accounting_date
                # might be protected because `_get_accounting_date` requires the `name`
                self.env.add_to_compute(self._fields['name'], move)

    @api.depends('auto_post')
    def _compute_auto_post_until(self):
        for record in self:
            if record.auto_post in ('no', 'at_date'):
                record.auto_post_until = False

    @api.depends('date', 'auto_post')
    def _compute_hide_post_button(self):
        for record in self:
            record.hide_post_button = record.state != 'draft' \
                or record.auto_post != 'no' and record.date > fields.Date.today()

    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            company_id = move.journal_id.company_id or self.env.company
            if company_id != move.company_id:
                move.company_id = company_id

    @api.depends('move_type')
    def _compute_journal_id(self):
        for record in self:
            record.journal_id = record._search_default_journal()
            if not record.company_id or record.company_id != record.journal_id.company_id:
                self.env.add_to_compute(self._fields['company_id'], record)
            if not record.currency_id or record.journal_id.currency_id and record.currency_id != record.journal_id.currency_id:
                self.env.add_to_compute(self._fields['currency_id'], record)

    def _search_default_journal(self):
        if self.payment_id and self.payment_id.journal_id:
            return self.payment_id.journal_id
        if self.statement_line_id and self.statement_line_id.journal_id:
            return self.statement_line_id.journal_id

        if self.is_sale_document(include_receipts=True):
            journal_types = ['sale']
        elif self.is_purchase_document(include_receipts=True):
            journal_types = ['purchase']
        elif self.payment_id or self.env.context.get('is_payment'):
            journal_types = ['bank', 'cash']
        else:
            journal_types = ['general']

        company_id = (self.company_id or self.env.company).id
        domain = [('company_id', '=', company_id), ('type', 'in', journal_types)]

        journal = None
        currency_id = self.currency_id.id or self._context.get('default_currency_id')
        if currency_id and currency_id != self.company_id.currency_id.id:
            currency_domain = domain + [('currency_id', '=', currency_id)]
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

    @api.depends('move_type')
    def _compute_is_storno(self):
        for move in self:
            move.is_storno = move.is_storno or (move.move_type in ('out_refund', 'in_refund') and move.company_id.account_storno)

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
            elif (not move.name or move.name == '/') and move.quick_edit_mode:
                # We always suggest the next sequence as the default name of the new move
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

        self.filtered(lambda m: not m.name).name = '/'
        self._compute_split_sequence()

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

    @api.depends('move_type')
    def _compute_type_name(self):
        type_name_mapping = dict(
            self._fields['move_type']._description_selection(self.env),
            out_invoice=_('Invoice'),
            out_refund=_('Credit Note'),
        )

        for record in self:
            record.type_name = type_name_mapping[record.move_type]

    @api.depends('line_ids.account_id.account_type')
    def _compute_always_tax_exigible(self):
        for record in self:
            # We need to check is_invoice as well because always_tax_exigible is used to
            # set the tags as well, during the encoding. So, if no receivable/payable
            # line has been created yet, the invoice would be detected as always exigible,
            # and set the tags on some lines ; which would be wrong.
            record.always_tax_exigible = not record.is_invoice(True) \
                                         and not record._collect_tax_cash_basis_values()

    @api.depends('partner_id')
    def _compute_commercial_partner_id(self):
        for move in self:
            move.commercial_partner_id = move.partner_id.commercial_partner_id

    @api.depends('partner_id')
    def _compute_partner_shipping_id(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                addr = move.partner_id.address_get(['delivery'])
                move.partner_shipping_id = addr and addr.get('delivery')
            else:
                move.partner_shipping_id = False

    @api.depends('partner_id', 'partner_shipping_id', 'company_id')
    def _compute_fiscal_position_id(self):
        for move in self:
            delivery_partner = self.env['res.partner'].browse(
                move.partner_shipping_id.id
                or move.partner_id.address_get(['delivery'])['delivery']
            )
            move.fiscal_position_id = self.env['account.fiscal.position'].with_company(move.company_id)._get_fiscal_position(
                move.partner_id, delivery=delivery_partner)

    @api.depends('bank_partner_id')
    def _compute_partner_bank_id(self):
        for move in self:
            bank_ids = move.bank_partner_id.bank_ids.filtered(
                lambda bank: not bank.company_id or bank.company_id == move.company_id)
            move.partner_bank_id = bank_ids[0] if bank_ids else False

    @api.depends('partner_id')
    def _compute_invoice_payment_term_id(self):
        for move in self:
            if move.is_sale_document(include_receipts=True) and move.partner_id.property_payment_term_id:
                move.invoice_payment_term_id = move.partner_id.property_payment_term_id
            elif move.is_purchase_document(include_receipts=True) and move.partner_id.property_supplier_payment_term_id:
                move.invoice_payment_term_id = move.partner_id.property_supplier_payment_term_id

    @api.depends('needed_terms')
    def _compute_invoice_date_due(self):
        today = fields.Date.context_today(self)
        for move in self:
            move.invoice_date_due = move.needed_terms and max(
                (k['date_maturity'] for k in move.needed_terms.keys() if k),
                default=False,
            ) or move.invoice_date_due or today

    @api.depends('journal_id', 'statement_line_id')
    def _compute_currency_id(self):
        for invoice in self:
            currency = (
                invoice.statement_line_id.foreign_currency_id
                or invoice.journal_id.currency_id
                or invoice.journal_id.company_id.currency_id
            )
            invoice.currency_id = currency

    @api.depends('move_type')
    def _compute_direction_sign(self):
        for invoice in self:
            if invoice.move_type == 'entry' or invoice.is_outbound():
                invoice.direction_sign = 1
            else:
                invoice.direction_sign = -1

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding'):
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)

    @api.depends('amount_residual', 'move_type', 'state', 'company_id')
    def _compute_payment_state(self):
        stored_ids = tuple(self.ids)
        if stored_ids:
            self.env['account.partial.reconcile'].flush_model()
            self.env['account.payment'].flush_model(['is_matched'])

            queries = []
            for source_field, counterpart_field in (('debit', 'credit'), ('credit', 'debit')):
                queries.append(f'''
                    SELECT
                        source_line.id AS source_line_id,
                        source_line.move_id AS source_move_id,
                        account.account_type AS source_line_account_type,
                        ARRAY_AGG(counterpart_move.reversed_entry_id)
                            FILTER (WHERE counterpart_move.reversed_entry_id IS NOT NULL) AS counterpart_reversed_entry_ids,
                        ARRAY_AGG(counterpart_move.move_type)
                            FILTER (WHERE counterpart_move.reversed_entry_id IS NOT NULL) AS counterpart_move_types,
                        COALESCE(BOOL_AND(COALESCE(pay.is_matched, FALSE))
                            FILTER (WHERE counterpart_move.payment_id IS NOT NULL), TRUE) AS all_payments_matched
                    FROM account_partial_reconcile part
                    JOIN account_move_line source_line ON source_line.id = part.{source_field}_move_id
                    JOIN account_account account ON account.id = source_line.account_id
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

        for invoice in self:
            if invoice.payment_state == 'invoicing_legacy':
                # invoicing_legacy state is set via SQL when setting setting field
                # invoicing_switch_threshold (defined in account_accountant).
                # The only way of going out of this state is through this setting,
                # so we don't recompute it here.
                continue

            currencies = invoice._get_lines_onchange_currency().currency_id
            currency = currencies if len(currencies) == 1 else invoice.company_id.currency_id
            reconciliation_vals = payment_data.get(invoice.id, [])
            payment_state_matters = invoice.is_invoice(True)

            # Restrict on 'receivable'/'payable' lines for invoices/expense entries.
            if payment_state_matters:
                reconciliation_vals = [x for x in reconciliation_vals if x['source_line_account_type'] in ('asset_receivable', 'liability_payable')]

            new_pmt_state = 'not_paid'
            if invoice.state == 'posted':

                # Posted invoice/expense entry.
                if payment_state_matters:

                    if currency.is_zero(invoice.amount_residual):
                        # Check if the invoice/expense entry is fully paid or 'in_payment'.
                        if all(x['all_payments_matched'] for x in reconciliation_vals):
                            new_pmt_state = 'paid'
                        else:
                            new_pmt_state = invoice._get_invoice_in_payment_state()
                    elif reconciliation_vals:
                        new_pmt_state = 'partial'

                # Check if the journal entry is 'reversed' (1 on 1 full reconciliation with entries being of the opposite types)
                if new_pmt_state == 'paid':
                    reverse_move_types = []
                    for x in reconciliation_vals:
                        for rec_move_type, rec_reversed_entry_id in zip(x['counterpart_move_types'] or [], x['counterpart_reversed_entry_ids'] or []):
                            if rec_reversed_entry_id == invoice.id:
                                reverse_move_types.append(rec_move_type)

                    if (invoice.move_type in ('in_invoice', 'in_receipt') and reverse_move_types == ['in_refund']) \
                      or (invoice.move_type in ('out_invoice', 'out_receipt') and reverse_move_types == ['out_refund']) \
                      or (invoice.move_type in ('entry', 'out_refund', 'in_refund') and reverse_move_types == ['entry']):
                        new_pmt_state = 'reversed'

            invoice.payment_state = new_pmt_state

    @api.depends('invoice_payment_term_id', 'invoice_date', 'currency_id', 'amount_total_in_currency_signed', 'invoice_date_due')
    def _compute_needed_terms(self):
        for invoice in self:
            invoice.needed_terms = {}
            invoice.needed_terms_dirty = True
            if invoice.is_invoice(True):
                if invoice.invoice_payment_term_id:
                    for date, (company_amount, foreign_amount) in invoice.invoice_payment_term_id.compute(
                        company_value=invoice.amount_total_signed,
                        foreign_value=invoice.amount_total_in_currency_signed,
                        date_ref=invoice.invoice_date or invoice.date or fields.Date.today(),
                        currency=invoice.currency_id,
                    ):
                        key = frozendict({'move_id': invoice.id, 'date_maturity': fields.Date.to_date(date)})
                        values = {
                            'balance': company_amount,
                            'amount_currency': foreign_amount,
                            'name': invoice.payment_reference or '',
                        }
                        if key not in invoice.needed_terms:
                            invoice.needed_terms[key] = values
                        else:
                            invoice.needed_terms[key]['balance'] += values['balance']
                            invoice.needed_terms[key]['amount_currency'] += values['amount_currency']
                else:
                    invoice.needed_terms[frozendict({
                        'move_id': invoice.id,
                        'date_maturity': fields.Date.to_date(invoice.invoice_date_due),
                    })] = {
                        'balance': invoice.amount_total_signed,
                        'amount_currency': invoice.amount_total_in_currency_signed,
                        'name': invoice.payment_reference or '',
                    }

    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

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

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True

    @api.depends('move_type', 'line_ids.amount_residual')
    def _compute_payments_widget_reconciled_info(self):
        for move in self:
            payments_widget_vals = {'title': _('Less Payment'), 'outstanding': False, 'content': []}

            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                reconciled_vals = []
                reconciled_partials = move._get_all_reconciled_invoice_partials()
                for reconciled_partial in reconciled_partials:
                    counterpart_line = reconciled_partial['aml']
                    if counterpart_line.move_id.ref:
                        reconciliation_ref = '%s (%s)' % (counterpart_line.move_id.name, counterpart_line.move_id.ref)
                    else:
                        reconciliation_ref = counterpart_line.move_id.name

                    reconciled_vals.append({
                        'name': counterpart_line.name,
                        'journal_name': counterpart_line.journal_id.name,
                        'amount': reconciled_partial['amount'],
                        'currency': reconciled_partial['currency'].symbol,
                        'digits': [69, reconciled_partial['currency'].decimal_places],
                        'position': reconciled_partial['currency'].position,
                        'date': counterpart_line.date,
                        'partial_id': reconciled_partial['partial_id'],
                        'account_payment_id': counterpart_line.payment_id.id,
                        'payment_method_name': counterpart_line.payment_id.payment_method_line_id.name,
                        'move_id': counterpart_line.move_id.id,
                        'ref': reconciliation_ref,
                        # these are necessary for the views to change depending on the values
                        'is_exchange': reconciled_partial['is_exchange'],
                        'amount_company_currency': formatLang(self.env, abs(counterpart_line.balance), currency_obj=counterpart_line.company_id.currency_id),
                        'amount_foreign_currency': formatLang(self.env, abs(counterpart_line.amount_currency), currency_obj=counterpart_line.currency_id) if counterpart_line.currency_id != counterpart_line.company_id.currency_id else False
                    })
                payments_widget_vals['content'] = reconciled_vals

            if payments_widget_vals['content']:
                move.invoice_payments_widget = payments_widget_vals
            else:
                move.invoice_payments_widget = False

    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if move.is_invoice(include_receipts=True):
                kwargs = {
                    'base_lines': [
                        line._convert_to_tax_base_line_dict()
                        for line in move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                    ],
                    'currency': move.currency_id,
                }
                if move.id:
                    kwargs['tax_lines'] = [
                        line._convert_to_tax_line_dict()
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'tax')
                    ]
                move.tax_totals = self.env['account.tax']._prepare_tax_totals(**kwargs)
            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals = None

    def _get_report_early_payment_totals_values(self):
        self.ensure_one()

        if self.move_type not in ['out_invoice', 'out_receipt', 'in_invoice', 'in_receipt'] or \
                not self.payment_state == 'not_paid' or \
                not self.invoice_payment_term_id.has_early_payment:
            return

        base_lines = self.line_ids.filtered(lambda x: x.display_type == 'product')
        return self.env['account.tax']._prepare_tax_totals(
            [x._convert_to_tax_base_line_dict() for x in base_lines],
            self.currency_id,
            early_payment_term=self.invoice_payment_term_id,
        )

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

    @api.depends('move_type')
    def _compute_invoice_filter_type_domain(self):
        for move in self:
            if move.is_sale_document(include_receipts=True):
                move.invoice_filter_type_domain = 'sale'
            elif move.is_purchase_document(include_receipts=True):
                move.invoice_filter_type_domain = 'purchase'
            else:
                move.invoice_filter_type_domain = False

    @api.depends('commercial_partner_id')
    def _compute_bank_partner_id(self):
        for move in self:
            if move.is_inbound():
                move.bank_partner_id = move.company_id.partner_id
            else:
                move.bank_partner_id = move.commercial_partner_id

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

    @api.depends('currency_id')
    def _compute_display_inactive_currency_warning(self):
        for move in self.with_context(active_test=False):
            move.display_inactive_currency_warning = not move.currency_id.active

    @api.depends('company_id.account_fiscal_country_id', 'fiscal_position_id', 'fiscal_position_id.country_id', 'fiscal_position_id.foreign_vat')
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

    @api.depends('line_ids')
    def _compute_has_reconciled_entries(self):
        for move in self:
            move.has_reconciled_entries = len(move.line_ids._reconciled_lines()) > 1

    @api.depends('restrict_mode_hash_table', 'state')
    def _compute_show_reset_to_draft_button(self):
        for move in self:
            move.show_reset_to_draft_button = not move.restrict_mode_hash_table and move.state in ('posted', 'cancel')

    # EXTENDS portal portal.mixin
    def _compute_access_url(self):
        super()._compute_access_url()
        for move in self.filtered(lambda move: move.is_invoice()):
            move.access_url = '/my/invoices/%s' % (move.id)

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

    @api.depends('invoice_payment_term_id', 'amount_residual_signed', 'currency_id')
    def _compute_early_pay_amount_after_discount(self):
        for record in self:
            if record.invoice_payment_term_id.has_early_payment:
                percentage_to_discount = record.invoice_payment_term_id.percentage_to_discount
                discount_computation = self.invoice_payment_term_id.discount_computation

                discounted_amount_untaxed = (100 - percentage_to_discount) * record.amount_untaxed / 100
                if discount_computation == 'included':
                    discounted_amount_tax = (100 - percentage_to_discount) * record.amount_tax / 100
                else:
                    discounted_amount_tax = record.amount_tax
                record.invoice_early_pay_amount_after_discount = discounted_amount_untaxed + discounted_amount_tax
                if record.currency_id.compare_amounts(record.invoice_early_pay_amount_after_discount, 0.0) <= 0.0:
                    record.invoice_early_pay_amount_after_discount = 0
            else:
                record.invoice_early_pay_amount_after_discount = 0

    def _is_eligible_for_early_discount(self, payment_date):
        '''
        An early payment discount is possible if the option has been activated,
        no partial payment was registered,
        and the payment date is before the last early_payment_date possible.
        '''
        self.ensure_one()
        return self.move_type in ['out_invoice', 'out_receipt', 'in_invoice', 'in_receipt'] and \
               self.invoice_payment_term_id.has_early_payment and \
               self.payment_state == 'not_paid' and \
               payment_date <= self.invoice_payment_term_id._get_last_date_for_discount(self.invoice_date)

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

    @api.depends('journal_id.type', 'company_id')
    def _compute_quick_edit_mode(self):
        for move in self:
            quick_edit_mode = move.company_id.quick_edit_mode
            if move.journal_id.type == 'sale':
                move.quick_edit_mode = quick_edit_mode in ('out_invoices', 'out_and_in_invoices')
            elif move.journal_id.type == 'purchase':
                move.quick_edit_mode = quick_edit_mode in ('in_invoices', 'out_and_in_invoices')
            else:
                move.quick_edit_mode = False

    # -------------------------------------------------------------------------
    # INVERSE METHODS
    # -------------------------------------------------------------------------

    def _inverse_tax_totals(self):
        with self._sync_dynamic_line(
            existing_key_fname='term_key',
            needed_vals_fname='needed_terms',
            needed_dirty_fname='needed_terms_dirty',
            line_type='payment_term',
            container={'records': self},
        ):
            for move in self:
                if not move.is_invoice(include_receipts=True):
                    continue
                invoice_totals = move.tax_totals

                for amount_by_group_list in invoice_totals['groups_by_subtotal'].values():
                    for amount_by_group in amount_by_group_list:
                        tax_lines = move.line_ids.filtered(lambda line: line.tax_group_id.id == amount_by_group['tax_group_id'])

                        if tax_lines:
                            first_tax_line = tax_lines[0]
                            tax_group_old_amount = sum(tax_lines.mapped('amount_currency'))
                            sign = -1 if move.is_inbound() else 1
                            delta_amount = tax_group_old_amount * sign - amount_by_group['tax_group_amount']

                            if not move.currency_id.is_zero(delta_amount):
                                first_tax_line.amount_currency -= delta_amount * sign
            self._compute_amount()

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

    @api.onchange('partner_id')
    def _inverse_partner_id(self):
        for invoice in self:
            if invoice.is_invoice(True):
                for line in invoice.line_ids:
                    if line.partner_id != invoice.commercial_partner_id:
                        line.partner_id = invoice.commercial_partner_id
                        line._inverse_partner_id()

    @api.onchange('company_id')
    def _inverse_company_id(self):
        for move in self:
            if move.journal_id.company_id != move.company_id:
                self.env.add_to_compute(self._fields['journal_id'], move)

    @api.onchange('currency_id')
    def _inverse_currency_id(self):
        for invoice in self:
            if invoice.journal_id.currency_id and invoice.journal_id.currency_id != invoice.currency_id:
                self.env.add_to_compute(self._fields['journal_id'], invoice)

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('invoice_vendor_bill_id')
    def _onchange_invoice_vendor_bill(self):
        if self.invoice_vendor_bill_id:
            # Copy invoice lines.
            for line in self.invoice_vendor_bill_id.invoice_line_ids:
                copied_vals = line.copy_data()[0]
                self.invoice_line_ids += self.env['account.move.line'].new(copied_vals)

            self.currency_id = self.invoice_vendor_bill_id.currency_id
            self.fiscal_position_id = self.invoice_vendor_bill_id.fiscal_position_id

            # Reset
            self.invoice_vendor_bill_id = False

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

    @api.onchange('name', 'highest_name')
    def _onchange_name_warning(self):
        if self.name and self.name != '/' and self.name <= (self.highest_name or ''):
            self.show_name_warning = True
        else:
            self.show_name_warning = False

        origin_name = self._origin.name
        if not origin_name or origin_name == '/':
            origin_name = self.highest_name
        if (
            self.name and self.name != '/'
            and origin_name and origin_name != '/'
            and self.date == self._origin.date
            and self.journal_id == self._origin.journal_id
        ):
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

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if not self.quick_edit_mode and self._get_last_sequence(lock=False):
            self.name = '/'
            self._compute_name()

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        moves = self.filtered(lambda move: move.state == 'posted')
        if not moves:
            return

        self.flush_model(['name', 'journal_id', 'move_type', 'state'])

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

    @contextmanager
    def _check_balanced(self, container):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        with self._disable_recursion(container, 'check_move_validity', default=True, target=False) as disabled:
            yield
            if disabled:
                return

        moves = container['records'].filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush_model(['balance', 'currency_id', 'move_id'])
        self.env['account.move'].flush_model(['journal_id'])
        self._cr.execute('''
            WITH error_moves AS (
                SELECT line.move_id,
                       ROUND(SUM(line.balance), currency.decimal_places) balance
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
        ''', [tuple(moves.ids)])

        query_res = self._cr.fetchall()
        if query_res:
            error_msg = _("There was a problem with the following move(s):\n")
            for move in query_res:
                id_, balance = move
                error_msg += _("- Move with id %i\n", id_)
                if balance != 0.0:
                    error_msg += _("\tCannot create unbalanced journal entry. The balance is equal to %s\n",
                                   format_amount(self.env, balance, self.env['account.move'].browse(id_).currency_id))
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

    @api.constrains('auto_post', 'invoice_date')
    def _require_bill_date_for_autopost(self):
        """Vendor bills must have an invoice date set to be posted. Require it for auto-posted bills."""
        for record in self:
            if record.auto_post != 'no' and record.is_purchase_document() and not record.invoice_date:
                raise ValidationError(_("For this entry to be automatically posted, it required a bill date."))

    @api.constrains('journal_id', 'move_type')
    def _check_journal_move_type(self):
        for move in self:
            if move.is_purchase_document(include_receipts=True) and move.journal_id.type != 'purchase':
                raise ValidationError(_("Cannot create a purchase document in a non purchase journal"))
            if move.is_sale_document(include_receipts=True) and move.journal_id.type != 'sale':
                raise ValidationError(_("Cannot create a sale document in a non sale journal"))

    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id', 'invoice_date', 'state')
    def _check_duplicate_supplier_reference(self):
        moves = self.filtered(lambda move: move.state == 'posted' and move.is_purchase_document() and move.ref)
        if not moves:
            return

        self.env["account.move"].flush_model([
            "ref", "move_type", "invoice_date", "journal_id",
            "company_id", "partner_id", "commercial_partner_id",
        ])
        self.env["account.journal"].flush_model(["company_id"])
        self.env["res.partner"].flush_model(["commercial_partner_id"])

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
    # DYNAMIC LINES
    # -------------------------------------------------------------------------

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
                'balance': diff_balance,
                'partner_id': self.partner_id.id,
                'move_id': self.id,
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'company_currency_id': self.company_id.currency_id.id,
                'display_type': 'rounding',
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
                    'tax_ids': [Command.set(biggest_tax_line.tax_ids.ids)]
                })

            elif self.invoice_cash_rounding_id.strategy == 'add_invoice_line':
                if diff_balance > 0.0 and self.invoice_cash_rounding_id.loss_account_id:
                    account_id = self.invoice_cash_rounding_id.loss_account_id.id
                else:
                    account_id = self.invoice_cash_rounding_id.profit_account_id.id
                rounding_line_vals.update({
                    'name': self.invoice_cash_rounding_id.name,
                    'account_id': account_id,
                    'tax_ids': [Command.clear()]
                })

            # Create or update the cash rounding line.
            if cash_rounding_line:
                cash_rounding_line.write(rounding_line_vals)
            else:
                cash_rounding_line = self.env['account.move.line'].create(rounding_line_vals)

        existing_cash_rounding_line = self.line_ids.filtered(lambda line: line.display_type == 'rounding')

        # The cash rounding has been removed.
        if not self.invoice_cash_rounding_id:
            existing_cash_rounding_line.unlink()
            # self.line_ids -= existing_cash_rounding_line
            return

        # The cash rounding strategy has changed.
        if self.invoice_cash_rounding_id and existing_cash_rounding_line:
            strategy = self.invoice_cash_rounding_id.strategy
            old_strategy = 'biggest_tax' if existing_cash_rounding_line.tax_line_id else 'add_invoice_line'
            if strategy != old_strategy:
                # self.line_ids -= existing_cash_rounding_line
                existing_cash_rounding_line.unlink()
                existing_cash_rounding_line = self.env['account.move.line']

        others_lines = self.line_ids.filtered(lambda line: line.account_id.account_type not in ('asset_receivable', 'liability_payable'))
        others_lines -= existing_cash_rounding_line
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        diff_balance, diff_amount_currency = _compute_cash_rounding(self, total_amount_currency)

        # The invoice is already rounded.
        if self.currency_id.is_zero(diff_balance) and self.currency_id.is_zero(diff_amount_currency):
            existing_cash_rounding_line.unlink()
            # self.line_ids -= existing_cash_rounding_line
            return

        _apply_cash_rounding(self, diff_balance, diff_amount_currency, existing_cash_rounding_line)

    @contextmanager
    def _sync_rounding_lines(self, container):
        yield
        for invoice in container['records']:
            invoice._recompute_cash_rounding_lines()

    @contextmanager
    def _sync_dynamic_line(self, existing_key_fname, needed_vals_fname, needed_dirty_fname, line_type, container):
        def existing():
            return {
                line[existing_key_fname]: line
                for line in container['records'].line_ids
                if line[existing_key_fname]
            }
        def needed():
            res = {}
            for computed_needed in container['records'].mapped(needed_vals_fname):
                if computed_needed is False:
                    continue  # there was an invalidation, let's hope nothing needed to be changed...
                for key, values in computed_needed.items():
                    if key not in res:
                        res[key] = dict(values)
                    else:
                        ignore = True
                        for fname in res[key]:
                            if self.env['account.move.line']._fields[fname].type == 'monetary':
                                res[key][fname] += values[fname]
                                if res[key][fname]:
                                    ignore = False
                        if ignore:
                            del res[key]
            return res

        def dirty():
            *path, dirty_fname = needed_dirty_fname.split('.')
            dirty_recs = container['records'].mapped('.'.join(path)).filtered(dirty_fname)
            return dirty_recs, dirty_fname

        existing_before = existing()
        needed_before = needed()
        dirty_recs_before, dirty_fname = dirty()
        dirty_recs_before[dirty_fname] = False
        yield
        dirty_recs_after, dirty_fname = dirty()
        if dirty_recs_before and not dirty_recs_after:  # TODO improve filter
            return
        existing_after = existing()
        needed_after = needed()

        # old key to new key for the same line
        before2after = {
            before: after
            for before, bline in existing_before.items()
            for after, aline in existing_after.items()
            if bline == aline
        }

        # # do not alter manually inputted values if there is no change done in business field
        # if set(needed_before) == set(needed_after) and all(
        #     needed_before[key]['amount_currency'] == needed_after[key]['amount_currency']
        #     for key in needed_after
        #     if 'amount_currency' in needed_after[key]
        # ):
        #     for key in needed_after:
        #         if 'amount_currency' in needed_after[key]:
        #             del needed_after[key]['amount_currency']
        #             del needed_before[key]['amount_currency']
        if needed_after == needed_before:
            return

        to_delete = sorted({
            line.id
            for key, line in existing_before.items()
            if key not in needed_after
            and key in existing_after
            and before2after[key] not in needed_after
        } | {
            line.id
            for key, line in existing_after.items()
            if key not in needed_after
        })
        to_create = {
            key: values
            for key, values in needed_after.items()
            if key not in existing_after
        }
        to_write = {
            existing_after[key]: values
            for key, values in needed_after.items()
            if key in existing_after
            and any(
                self.env['account.move.line']._fields[fname].convert_to_write(existing_after[key][fname], self)
                != values[fname]
                for fname in values
            )
        }

        while to_delete and to_create:
            key, values = to_create.popitem()
            line_id = to_delete.pop()
            self.env['account.move.line'].browse(line_id).write(
                {**key, **values, 'display_type': line_type}
            )
        if to_delete:
            self.env['account.move.line'].browse(to_delete).with_context(dynamic_unlink=True).unlink()
        if to_create:
            self.env['account.move.line'].create([
                {**key, **values, 'display_type': line_type}
                for key, values in to_create.items()
            ])
        if to_write:
            for line, values in to_write.items():
                line.write(values)

    @contextmanager
    def _sync_invoice(self, container):
        def existing():
            return {
                move: {
                    'payment_reference': move.payment_reference,
                    'commercial_partner_id': move.commercial_partner_id,
                }
                for move in container['records'].filtered(lambda m: m.is_invoice(True))
            }

        def changed(fname):
            return move not in before or before[move][fname] != after[move][fname]

        before = existing()
        yield
        after = existing()

        for move in after:
            if changed('payment_reference'):
                move.line_ids.filtered(lambda l: l.display_type == 'payment_term').name = after[move]['payment_reference']
            if changed('commercial_partner_id'):
                move.line_ids.partner_id = after[move]['commercial_partner_id']

    @contextmanager
    def _sync_dynamic_lines(self, container):
        with self._disable_recursion(container, 'skip_invoice_sync') as disabled:
            if disabled:
                yield
                return
            # Only invoice-like and journal entries in "auto tax mode" are synced
            tax_filter = lambda m: (m.is_invoice(True) or m.line_ids.tax_ids and not m.tax_cash_basis_origin_move_id)
            invoice_filter = lambda m: (m.is_invoice(True))
            tax_container = {'records': container['records'].filtered(tax_filter)}
            invoice_container = {'records': container['records'].filtered(invoice_filter)}

            with ExitStack() as stack:
                stack.enter_context(self._sync_dynamic_line(
                    existing_key_fname='term_key',
                    needed_vals_fname='needed_terms',
                    needed_dirty_fname='needed_terms_dirty',
                    line_type='payment_term',
                    container=invoice_container,
                ))
                stack.enter_context(self._sync_rounding_lines(invoice_container))
                stack.enter_context(self._sync_dynamic_line(
                    existing_key_fname='tax_key',
                    needed_vals_fname='line_ids.compute_all_tax',
                    needed_dirty_fname='line_ids.compute_all_tax_dirty',
                    line_type='tax',
                    container=tax_container,
                ))
                stack.enter_context(self._sync_invoice(invoice_container))
                line_container = {'records': self.line_ids}
                with self.line_ids._sync_invoice(line_container):
                    yield
                    line_container['records'] = self.line_ids
                tax_container['records'] = container['records'].filtered(tax_filter)
                invoice_container['records'] = container['records'].filtered(invoice_filter)

            # Delete the tax lines if the journal entry is not in "auto tax mode" anymore
            for move in container['records']:
                if move.move_type == 'entry' and not move.line_ids.tax_ids:
                    move.line_ids.filtered(
                        lambda l: l.display_type == 'tax'
                    ).with_context(dynamic_unlink=True).unlink()

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def copy_data(self, default=None):
        data_list = super().copy_data(default)
        for data in data_list:
            data['line_ids'] = [
                (command, _id, line_vals)
                for command, _id, line_vals in data['line_ids']
                if command == 0
                and line_vals.get('display_type') not in ('payment_term', 'tax', 'rounding')
            ]
        if not self.journal_id.active and 'journal_id' in data_list:
            del default['journal_id']
        return data_list

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if (fields.Date.to_date(default.get('date')) or self.date) <= self.company_id._get_user_fiscal_lock_date():
            default['date'] = self.company_id._get_user_fiscal_lock_date() + timedelta(days=1)
        if self.move_type == 'entry':
            default['partner_id'] = False
        copied_am = super().copy(default)
        message_origin = '' if not copied_am.auto_post_origin_id else \
            '<br/>' + _('This recurring entry originated from %s', copied_am.auto_post_origin_id._get_html_link())
        copied_am._message_log(body=_(
            'This entry has been duplicated from %s%s',
            self._get_html_link(),
            message_origin,
        ))

        return copied_am

    def _sanitize_vals(self, vals):
        if 'invoice_line_ids' in vals and 'line_ids' in vals:
            # values can sometimes be in only one of the two fields, sometimes in
            # both fields, sometimes one field can be explicitely empty while the other
            # one is not, sometimes not...
            update_vals = {
                line_id: line_vals
                for command, line_id, line_vals in vals['invoice_line_ids']
                if command == Command.UPDATE
            }
            for command, line_id, line_vals in vals['line_ids']:
                if command == Command.UPDATE and line_id in update_vals:
                    line_vals.update(update_vals.pop(line_id))
            for line_id, line_vals in update_vals.items():
                vals['line_ids'] += [Command.update(line_id, line_vals)]
            for command, line_id, line_vals in vals['invoice_line_ids']:
                assert command not in (Command.SET, Command.CLEAR)
                if [command, line_id, line_vals] not in vals['line_ids']:
                    vals['line_ids'] += [(command, line_id, line_vals)]
            del vals['invoice_line_ids']
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        if any('state' in vals and vals.get('state') == 'posted' for vals in vals_list):
            raise UserError(_('You cannot create a move already in the posted state. Please create a draft move and post it after.'))
        container = {'records': self, 'self': self}
        with self._check_balanced(container),\
             self._sync_dynamic_lines(container):
            moves = super().create([self._sanitize_vals(vals) for vals in vals_list])
            container['records'] = moves
        for move, vals in zip(moves, vals_list):
            if 'tax_totals' in vals:
                move.tax_totals = vals['tax_totals']
            else:
                move._check_total_amount_on_new_line(vals)
        return moves

    def write(self, vals):
        if not vals:
            return True
        self._sanitize_vals(vals)
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
                    raise UserError(_('The Journal Entry sequence is not conform to the current format. Only the Accountant can change it.'))
                move.journal_id.sequence_override_regex = False

        container = {'records': self}
        with self._check_balanced(container):
            with self._sync_dynamic_lines(container):
                res = super(AccountMove, self.with_context(
                    skip_account_move_synchronization=True,
                )).write(vals)


                # Reset the name of draft moves when changing the journal.
                # Protected against holes in the pre-validation checks.
                if 'journal_id' in vals and 'name' not in vals:
                    self.name = False
                    self._compute_name()

                # You can't change the date of a not-locked move to a locked period.
                # You can't post a new journal entry inside a locked period.
                if 'date' in vals or 'state' in vals:
                    posted_move = self.filtered(lambda m: m.state == 'posted')
                    posted_move._check_fiscalyear_lock_date()
                    posted_move.line_ids._check_tax_lock_date()

                # Hash the move
                if vals.get('state') == 'posted':
                    for move in self.filtered(lambda m: m.restrict_mode_hash_table and not(m.secure_sequence_number or m.inalterable_hash)).sorted(lambda m: (m.date, m.ref or '', m.id)):
                        new_number = move.journal_id.secure_sequence_id.next_by_id()
                        res |= super(AccountMove, move).write({
                            'secure_sequence_number': new_number,
                            'inalterable_hash': move._get_new_hash(new_number),
                        })

            self._synchronize_business_models(set(vals.keys()))

            # Apply the rounding on the Quick Edit mode only when adding a new line
            for move in self:
                if 'tax_totals' in vals:
                    super(AccountMove, move).write({'tax_totals': vals['tax_totals']})
                else:
                    move._check_total_amount_on_new_line(vals)

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
        self = self.with_context(skip_invoice_sync=True, dynamic_unlink=True)  # no need to sync to delete everything
        self.line_ids.unlink()
        return super().unlink()

    def name_get(self):
        result = []
        for move in self:
            result.append((move.id, move._get_move_display_name(show_ref=True)))
        return result

    def onchange(self, values, field_name, field_onchange):
        if field_name in ('line_ids', 'invoice_line_ids'):
            # Since only one field can be changed at the same time (the record is saved when changing tabs)
            # we can avoid building the snapshots for the other field
            to_del = 'invoice_line_ids' if field_name == 'line_ids' else 'line_ids'
            for key in list(field_onchange):
                if key == to_del or key.startswith(f"{to_del}."):
                    del field_onchange[key]
            # test_01_account_tour
            # File "/data/build/odoo/addons/account/models/account_move.py", line 2127, in onchange
            # del values[to_del]
            # KeyError: 'line_ids'
            values.pop(to_del, None)
        return super().onchange(values, field_name, field_onchange)

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
            if line.account_type in ('asset_receivable', 'liability_payable'):
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
    # SEQUENCE MIXIN
    # -------------------------------------------------------------------------

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS account sequence.mixin
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
        # EXTENDS account sequence.mixin
        self.ensure_one()
        if self.journal_id.type == 'sale':
            starting_sequence = "%s/%04d/00000" % (self.journal_id.code, self.date.year)
        else:
            starting_sequence = "%s/%04d/%02d/0000" % (self.journal_id.code, self.date.year, self.date.month)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        return starting_sequence

    # -------------------------------------------------------------------------
    # PAYMENT REFERENCE
    # -------------------------------------------------------------------------

    def _get_invoice_reference_euro_invoice(self):
        """ This computes the reference based on the RF Creditor Reference.
            The data of the reference is the database id number of the invoice.
            For instance, if an invoice is issued with id 43, the check number
            is 07 so the reference will be 'RF07 43'.
        """
        self.ensure_one()
        return format_rf_reference(self.id)

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
        partner_ref_nr = re.sub(r'\D', '', partner_ref or '')[-21:] or str(self.partner_id.id)[-21:]
        partner_ref_nr = partner_ref_nr[-21:]
        return format_rf_reference(partner_ref_nr)

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
        ref_function = getattr(self, f'_get_invoice_reference_{self.journal_id.invoice_reference_model}_{self.journal_id.invoice_reference_type}', None)
        if ref_function is None:
            raise UserError(_("The combination of reference model and reference type on the journal is not implemented"))
        return ref_function()

    # -------------------------------------------------------------------------
    # QUICK ENCODING
    # -------------------------------------------------------------------------
    @api.model
    def _get_frequent_account_and_taxes(self, company_id, partner_id, move_type):
        """
        Returns the most used accounts and taxes for a given partner and company,
        eventually filtered according to the move type.
        """
        where_internal_group = ""
        if move_type in self.env['account.move'].get_inbound_types(include_receipts=True):
            where_internal_group = "AND account.internal_group = 'income'"
        elif move_type in self.env['account.move'].get_outbound_types(include_receipts=True):
            where_internal_group = "AND account.internal_group = 'expense'"
        self._cr.execute(f"""
            SELECT
               COUNT(foo.id), foo.account_id, foo.taxes
            FROM
               (
               SELECT
                   account.id AS account_id,
                   account.code,
                   aml.id,
                   ARRAY_AGG(tax_rel.account_tax_id) AS taxes
               FROM account_account account
                LEFT JOIN account_move_line aml
                  ON (account.id = aml.account_id
                   AND aml.partner_id = %s
                   AND aml.date >= now() - interval '2 years')
                LEFT JOIN account_move_line_account_tax_rel tax_rel ON (aml.id = tax_rel.account_move_line_id)
               WHERE
                   account.company_id = %s
                   AND account.deprecated = FALSE
                      {where_internal_group}
               GROUP BY account.id, account.code, aml.id
               ) AS foo
            GROUP BY foo.account_id, foo.code, foo.taxes
            ORDER BY COUNT(foo.id) DESC, foo.code
            LIMIT 1
        """, [partner_id, company_id])
        return self._cr.fetchone()

    def _get_quick_edit_suggestions(self):
        """
        Returns a dictionnary containing the suggested values when creating a new
        line with the quick_edit_total_amount set. We will compute the price_unit
        that has to be set with the correct that in order to match this total amount.
        If the vendor/customer is set, we will suggest the most frequently used account
        for that partner as the default one, otherwise the default of the journal.
        """
        self.ensure_one()
        if not self.quick_edit_total_amount:
            return False
        count, account_id, tax_ids = self._get_frequent_account_and_taxes(
            self.company_id.id,
            self.partner_id.id,
            self.move_type,
        )
        if count:
            taxes = self.env['account.tax'].browse(tax_ids)
        else:
            account_id = self.journal_id.default_account_id.id
            if self.journal_id.default_account_id.tax_ids:
                taxes = self.journal_id.default_account_id.tax_ids
            else:
                taxes = (
                    self.journal_id.company_id.account_sale_tax_id
                    if self.journal_id.type == 'sale' else
                    self.journal_id.company_id.account_purchase_tax_id
                )
            taxes = self.fiscal_position_id.map_tax(taxes)
        price_untaxed = taxes.with_context(force_price_include=True).compute_all(
            self.quick_edit_total_amount - self.amount_total)['total_excluded']
        return {'account_id': account_id, 'tax_ids': taxes.ids, 'price_unit': price_untaxed}

    @api.onchange('quick_edit_total_amount', 'partner_id')
    def _onchange_quick_edit_total_amount(self):
        """
        Creates a new line with the suggested values (for the account, the price_unit,
        and the tax) such that the total amount matches the quick total amount.
        """
        if (
            not self.partner_id
            or not self.quick_edit_total_amount
            or not self.quick_edit_mode
            or len(self.invoice_line_ids) > 0
        ):
            return
        suggestions = self._get_quick_edit_suggestions()
        self.invoice_line_ids = [Command.clear()]
        self.invoice_line_ids += self.env['account.move.line'].new({
            'partner_id': self.partner_id,
            'account_id': suggestions['account_id'],
            'currency_id': self.currency_id.id,
            'price_unit': suggestions['price_unit'],
            'tax_ids': [Command.set(suggestions['tax_ids'])],
        })
        self._check_total_amount(self.quick_edit_total_amount)

    def _check_total_amount(self, amount_total):
        """
        Verifies that the total amount corresponds to the quick total amount chosen as some
        rounding errors may appear. In such a case, we round up the tax such that the total
        is equal to the quick total amount set
        E.g.: 100€ including 21% tax: base = 82.64, tax = 17.35, total = 99.99
        The tax will be set to 17.36 in order to have a total of 100.00
        """
        if not self.tax_totals or not amount_total:
            return
        totals = self.tax_totals
        tax_amount_rounding_error = amount_total - totals['amount_total']
        if not float_is_zero(tax_amount_rounding_error, precision_rounding=self.currency_id.rounding):
            if 'Untaxed Amount' in totals['groups_by_subtotal']:
                totals['groups_by_subtotal']['Untaxed Amount'][0]['tax_group_amount'] += tax_amount_rounding_error
                totals['amount_total'] = amount_total
                self.tax_totals = totals

    def _check_total_amount_on_new_line(self, vals):
        if (
            self.quick_edit_total_amount
            and self.quick_edit_mode
            and any(command == Command.CREATE for command, *__ in vals.get('invoice_line_ids', []) + vals.get('line_ids', []))
        ):
            self._check_total_amount(self.quick_edit_total_amount)

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------

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
                                                separators=(',', ':'))

    # -------------------------------------------------------------------------
    # RECURRING ENTRIES
    # -------------------------------------------------------------------------

    @api.model
    def _apply_delta_recurring_entries(self, date, date_origin, period):
        '''Advances date by `period` months, maintaining original day of the month if possible.'''
        deltas = {'monthly': 1, 'quarterly': 3, 'yearly': 12}
        prev_months = (date.year - date_origin.year) * 12 + date.month - date_origin.month
        return date_origin + relativedelta(months=deltas[period] + prev_months)

    def _copy_recurring_entries(self):
        ''' Creates a copy of a recurring (periodic) entry and adjusts its dates for the next period.
        Meant to be called right after posting a periodic entry.
        Copies extra fields as defined by _get_fields_to_copy_recurring_entries().
        '''
        for record in self:
            record.auto_post_origin_id = record.auto_post_origin_id or record  # original entry references itself
            next_date = self._apply_delta_recurring_entries(record.date, record.auto_post_origin_id.date, record.auto_post)

            if not record.auto_post_until or next_date <= record.auto_post_until:  # recurrence continues
                record.copy(default=record._get_fields_to_copy_recurring_entries({'date': next_date}))

    def _get_fields_to_copy_recurring_entries(self, values):
        ''' Determines which extra fields to copy when copying a recurring entry.
        To be extended by modules that add fields with copy=False (implicit or explicit)
        whenever the opposite behavior is expected for recurring invoices.
        '''
        values.update({
            'auto_post': self.auto_post,  # copy=False to avoid mistakes but should be the same in recurring copies
            'auto_post_until': self.auto_post_until,  # same as above
            'auto_post_origin_id': self.auto_post_origin_id.id,  # same as above
            'invoice_user_id': self.invoice_user_id.id,  # otherwise user would be OdooBot
        })
        if self.invoice_date:
            values.update({'invoice_date': self._apply_delta_recurring_entries(self.invoice_date, self.auto_post_origin_id.invoice_date, self.auto_post)})
        if not self.invoice_payment_term_id and self.invoice_date_due:
            # no payment terms: maintain timedelta between due date and accounting date
            values.update({'invoice_date_due': values['date'] + (self.invoice_date_due - self.date)})
        return values

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _affect_tax_report(self):
        return any(line._affect_tax_report() for line in self.line_ids)

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
        return name + (f" ({shorten(self.ref, width=50)})" if show_ref and self.ref else '')

    def _get_reconciled_amls(self):
        """Helper used to retrieve the reconciled move lines on this journal entry"""
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        return reconciled_lines.mapped('matched_debit_ids.debit_move_id') + reconciled_lines.mapped('matched_credit_ids.credit_move_id')

    def _get_reconciled_payments(self):
        """Helper used to retrieve the reconciled payments on this journal entry"""
        return self._get_reconciled_amls().move_id.payment_id

    def _get_reconciled_statement_lines(self):
        """Helper used to retrieve the reconciled statement lines on this journal entry"""
        return self._get_reconciled_amls().move_id.statement_line_id

    def _get_reconciled_invoices(self):
        """Helper used to retrieve the reconciled invoices on this journal entry"""
        return self._get_reconciled_amls().move_id.filtered(lambda move: move.is_invoice(include_receipts=True))

    def _get_all_reconciled_invoice_partials(self):
        self.ensure_one()
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        if not reconciled_lines:
            return {}

        query = '''
            SELECT
                part.id,
                part.exchange_move_id,
                part.debit_amount_currency AS amount,
                part.credit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.debit_move_id IN %s

            UNION ALL

            SELECT
                part.id,
                part.exchange_move_id,
                part.credit_amount_currency AS amount,
                part.debit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.credit_move_id IN %s
        '''
        self._cr.execute(query, [tuple(reconciled_lines.ids)] * 2)

        partial_values_list = []
        counterpart_line_ids = set()
        exchange_move_ids = set()
        for values in self._cr.dictfetchall():
            partial_values_list.append({
                'aml_id': values['counterpart_line_id'],
                'partial_id': values['id'],
                'amount': values['amount'],
                'currency': self.currency_id,
            })
            counterpart_line_ids.add(values['counterpart_line_id'])
            if values['exchange_move_id']:
                exchange_move_ids.add(values['exchange_move_id'])

        if exchange_move_ids:
            query = '''
                SELECT
                    part.id,
                    part.credit_move_id AS counterpart_line_id
                FROM account_partial_reconcile part
                JOIN account_move_line credit_line ON credit_line.id = part.credit_move_id
                WHERE credit_line.move_id IN %s AND part.debit_move_id IN %s

                UNION ALL

                SELECT
                    part.id,
                    part.debit_move_id AS counterpart_line_id
                FROM account_partial_reconcile part
                JOIN account_move_line debit_line ON debit_line.id = part.debit_move_id
                WHERE debit_line.move_id IN %s AND part.credit_move_id IN %s
            '''
            self._cr.execute(query, [tuple(exchange_move_ids), tuple(counterpart_line_ids)] * 2)

            for values in self._cr.dictfetchall():
                counterpart_line_ids.add(values['counterpart_line_id'])
                partial_values_list.append({
                    'aml_id': values['counterpart_line_id'],
                    'partial_id': values['id'],
                    'currency': self.company_id.currency_id,
                })

        counterpart_lines = {x.id: x for x in self.env['account.move.line'].browse(counterpart_line_ids)}
        for partial_values in partial_values_list:
            partial_values['aml'] = counterpart_lines[partial_values['aml_id']]
            partial_values['is_exchange'] = partial_values['aml'].move_id.id in exchange_move_ids
            if partial_values['is_exchange']:
                partial_values['amount'] = abs(partial_values['aml'].balance)

        return partial_values_list

    def _get_reconciled_invoices_partials(self):
        ''' Helper to retrieve the details about reconciled invoices.
        :return A list of tuple (partial, amount, invoice_line).
        '''
        self.ensure_one()
        pay_term_lines = self.line_ids\
            .filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
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

        reverse_moves = self.env['account.move']
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'move_type': TYPE_REVERSE_MAP[move.move_type],
                'reversed_entry_id': move.id,
            })
            reverse_moves += move.with_context(
                move_reverse_cancel=cancel,
                include_business_fields=True,
                skip_invoice_sync=bool(move.tax_cash_basis_origin_move_id),
            ).copy(default_values)

        reverse_moves.with_context(skip_invoice_sync=cancel).write({'line_ids': [
            Command.update(line.id, {
                'balance': -line.balance,
                'amount_currency': -line.amount_currency,
            })
            for line in reverse_moves.line_ids
            if line.move_id.move_type == 'entry' or line.display_type == 'cogs'
        ]})

        # Reconcile moves together to cancel the previous one.
        if cancel:
            reverse_moves.with_context(move_reverse_cancel=cancel)._post(soft=False)
            for move, reverse_move in zip(self, reverse_moves):
                group = defaultdict(list)
                for line in (move.line_ids + reverse_move.line_ids).filtered(lambda l: not l.reconciled):
                    group[(line.account_id, line.currency_id)].append(line.id)
                for (account, dummy), line_ids in group.items():
                    if account.reconcile or account.account_type in ('asset_cash', 'liability_credit_card'):
                        self.env['account.move.line'].browse(line_ids).with_context(move_reverse_cancel=cancel).reconcile()

        return reverse_moves

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
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))

        for invoice in self.filtered(lambda move: move.is_invoice(include_receipts=True)):
            if invoice.quick_edit_mode and invoice.quick_edit_total_amount and invoice.quick_edit_total_amount != invoice.amount_total:
                raise UserError(_(
                    "The current total is %s but the expected total is %s. In order to post the invoice/bill, "
                    "you can adjust its lines or the expected Total (tax inc.).",
                    formatLang(self.env, invoice.amount_total, currency_obj=invoice.currency_id),
                    formatLang(self.env, invoice.quick_edit_total_amount, currency_obj=invoice.currency_id),
                ))
            if invoice.partner_bank_id and not invoice.partner_bank_id.active:
                raise UserError(_(
                    "The recipient bank account linked to this invoice is archived.\n"
                    "So you cannot confirm the invoice."
                ))
            if float_compare(invoice.amount_total, 0.0, precision_rounding=invoice.currency_id.rounding) < 0:
                raise UserError(_(
                    "You cannot validate an invoice with a negative total amount. "
                    "You should create a credit note instead. "
                    "Use the action menu to transform it into a credit note or refund."
                ))

            if not invoice.partner_id:
                if invoice.is_sale_document():
                    raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
                elif invoice.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

            # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
            # lines are recomputed accordingly.
            if not invoice.invoice_date:
                if invoice.is_sale_document(include_receipts=True):
                    invoice.invoice_date = fields.Date.context_today(self)
                elif invoice.is_purchase_document(include_receipts=True):
                    raise UserError(_("The Bill/Refund date is required to validate this document."))

        if soft:
            future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
            for move in future_moves:
                if move.auto_post == 'no':
                    move.auto_post = 'at_date'
                msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
                move.message_post(body=msg)
            to_post = self - future_moves
        else:
            to_post = self

        for move in to_post:
            if move.state == 'posted':
                raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
            if not move.line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
                raise UserError(_('You need to add a line before posting.'))
            if move.auto_post != 'no' and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                raise UserError(_("This move is configured to be auto-posted on %s", date_msg))
            if not move.journal_id.active:
                raise UserError(_(
                    "You cannot post an entry in an archived journal (%(journal)s)",
                    journal=move.journal_id.display_name,
                ))
            if move.display_inactive_currency_warning:
                raise UserError(_(
                    "You cannot validate a document with an inactive currency: %s",
                    move.currency_id.name
                ))

            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report)

        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        to_post.mapped('line_ids').create_analytic_lines()
        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        # Trigger copying for recurring invoices
        to_post.filtered(lambda m: m.auto_post not in ('no', 'at_date'))._copy_recurring_entries()

        for invoice in to_post:
            # Fix inconsistencies that may occure if the OCR has been editing the invoice at the same time of a user. We force the
            # partner on the lines to be the same as the one on the move, because that's the only one the user can see/edit.
            wrong_lines = invoice.is_invoice() and invoice.line_ids.filtered(lambda aml:
                aml.partner_id != invoice.commercial_partner_id
                and aml.display_type not in ('line_note', 'line_section')
            )
            if wrong_lines:
                wrong_lines.write({'partner_id': invoice.commercial_partner_id.id})

            invoice.message_subscribe([
                p.id
                for p in [invoice.partner_id]
                if p not in invoice.sudo().message_partner_ids
            ])

            # Compute 'ref' for 'out_invoice'.
            if invoice.move_type == 'out_invoice' and not invoice.payment_reference:
                to_write = {
                    'payment_reference': invoice._get_invoice_computed_reference(),
                    'line_ids': []
                }
                for line in invoice.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')):
                    to_write['line_ids'].append((1, line.id, {'name': to_write['payment_reference']}))
                invoice.write(to_write)

            if (
                invoice.is_sale_document()
                and invoice.journal_id.sale_activity_type_id
                and (invoice.journal_id.sale_activity_user_id or invoice.invoice_user_id).id not in (self.env.ref('base.user_root').id, False)
            ):
                invoice.activity_schedule(
                    date_deadline=min((date for date in invoice.line_ids.mapped('date_maturity') if date), default=invoice.date),
                    activity_type_id=invoice.journal_id.sale_activity_type_id.id,
                    summary=invoice.journal_id.sale_activity_note,
                    user_id=invoice.journal_id.sale_activity_user_id.id or invoice.invoice_user_id.id,
                )

        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for invoice in to_post:
            if invoice.is_sale_document():
                customer_count[invoice.partner_id] += 1
            elif invoice.is_purchase_document():
                supplier_count[invoice.partner_id] += 1
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

        # Trigger action for paid invoices if amount is zero
        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        )._invoice_paid_hook()

        return to_post

    # -------------------------------------------------------------------------
    # PUBLIC ACTIONS
    # -------------------------------------------------------------------------

    def open_reconcile_view(self):
        return self.line_ids.open_reconcile_view()

    def open_move(self):
        if self.payment_id:
            return self.open_payment_view()
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
            }

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

    def action_switch_invoice_into_refund_credit_note(self):
        if any(move.move_type not in ('in_invoice', 'out_invoice') for move in self):
            raise ValidationError(_("This action isn't available for this document."))

        for move in self:
            move.write({
                'move_type': move.move_type.replace('invoice', 'refund'),
                'partner_bank_id': False,
                'currency_id': move.currency_id.id,
            })
            move.write({
                'line_ids': [
                    Command.update(line.id, {
                        'quantity': -line.quantity,
                    })
                    for line in move.line_ids
                    if line.display_type == 'product' and line.quantity < 0
                ]
            })

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

    def action_duplicate(self):
        # offer the possibility to duplicate thanks to a button instead of a hidden menu, which is more visible
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['context'] = dict(self.env.context)
        action['context']['form_view_initial_mode'] = 'edit'
        action['context']['view_no_maturity'] = False
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.copy().id
        return action

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

    def preview_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def action_reverse(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_view_account_move_reversal")

        if self.is_invoice():
            action['name'] = _('Credit Note')

        return action

    def action_post(self):
        if self.payment_id:
            self.payment_id.action_post()
        else:
            self._post(soft=False)
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
            if move.restrict_mode_hash_table and move.state == 'posted':
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft', 'is_move_sent': False})

    def button_cancel(self):
        self.write({'auto_post': 'no', 'state': 'cancel'})

    def action_activate_currency(self):
        self.currency_id.filtered(lambda currency: not currency.active).write({'active': True})

    def _get_mail_template(self):
        """
        :return: the correct mail template based on the current move type
        """
        return (
            'account.email_template_edi_credit_note'
            if all(move.move_type == 'out_refund' for move in self)
            else 'account.email_template_edi_invoice'
        )

    def _get_report_base_filename(self):
        return self._get_move_display_name()

    # -------------------------------------------------------------------------
    # CRON
    # -------------------------------------------------------------------------

    def _autopost_draft_entries(self):
        ''' This method is called from a cron job.
        It is used to post entries such as those created by the module
        account_asset and recurring entries created in _post().
        '''
        records = self.search([
            ('state', '=', 'draft'),
            ('date', '<=', fields.Date.context_today(self)),
            ('auto_post', '!=', 'no'),
        ], limit=100)
        records._post()

        if len(records) == 100:  # assumes there are more whenever search hits limit
            self.env.ref('account.ir_cron_auto_post_draft_entry')._trigger()

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def get_invoice_types(self, include_receipts=False):
        return self.get_sale_types(include_receipts) + self.get_purchase_types(include_receipts)

    def is_invoice(self, include_receipts=False):
        return self.is_sale_document(include_receipts) or self.is_purchase_document(include_receipts)

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

    def _generate_qr_code(self):
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
            for candidate_method, _candidate_name in self.env['res.partner.bank'].get_available_qr_methods_in_sequence():
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

    @contextmanager
    def _get_edi_creation(self):
        """Get an environment to import documents from other sources.

        Allow to edit the current move or create a new one.
        This will prevent computing the dynamic lines at each invoice line added and only
        compute everything at the end.
        """
        container = {'records': self}
        with self._check_balanced(container),\
             self._disable_discount_precision(),\
             self._sync_dynamic_lines(container):
            move = self or self.create({})
            yield move
            container['records'] = move

    @contextmanager
    def _disable_discount_precision(self):
        """Disable the user defined precision for discounts.

        This is useful for importing documents coming from other softwares and providers.
        The reasonning is that if the document that we are importing has a discount, it
        shouldn't be rounded to the local settings.
        """
        original_precision_get = DecimalPrecision.precision_get
        def precision_get(self, application):
            if application == 'Discount':
                return 100
            return original_precision_get(self, application)
        with patch('odoo.addons.base.models.decimal_precision.DecimalPrecision.precision_get', new=precision_get):
            yield

    # -------------------------------------------------------------------------
    # TOOLING
    # -------------------------------------------------------------------------

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
        for field_name in vals.keys():
            if not self._field_will_change(record, vals, field_name):
                del cleaned_vals[field_name]
        return cleaned_vals

    @contextmanager
    def _disable_recursion(self, container, key, default=None, target=True):
        previous_env = {key: container[key].env for key in container}
        previous_key = previous_env['records'].context.get(key, default)

        for recordset in container.values():
            recordset.env = recordset.with_context(**{key: target}).env
        try:
            yield previous_key == target
        finally:
            for key, recordset in container.items():
                recordset.env = previous_env[key]

    # ------------------------------------------------------------
    # MAIL.THREAD
    # ------------------------------------------------------------

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # EXTENDS mail mail.thread
        # Add custom behavior when receiving a new invoice through the mail's gateway.
        if (custom_values or {}).get('move_type', 'entry') not in ('out_invoice', 'in_invoice'):
            return super().message_new(msg_dict, custom_values=custom_values)

        def is_internal_partner(partner):
            # Helper to know if the partner is an internal one.
            return partner.user_ids and all(user._is_internal() for user in partner.user_ids)

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
        # EXTENDS mail mail.thread
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
        if attachments and self.invoice_line_ids:
            self.message_post(body=_('The invoice already contains lines, it was not updated from the attachment.'),
                              message_type='comment',
                              subtype_xmlid='mail.mt_note',
                              author_id=odoobot.id)
            return res

        decoders = self.env['account.move']._get_update_invoice_from_attachment_decoders(self)
        with self._disable_discount_precision():
            for decoder in sorted(decoders, key=lambda d: d[0]):
                # start with message_main_attachment_id, that way if OCR is installed, only that one will be parsed.
                # this is based on the fact that the ocr will be the last decoder.
                for attachment in attachments.sorted(lambda x: x != self.message_main_attachment_id):
                    invoice = decoder[1](attachment, self)
                    if invoice:
                        return res

        return res

    def _creation_subtype(self):
        # EXTENDS mail mail.thread
        if self.move_type in ('out_invoice', 'out_receipt'):
            return self.env.ref('account.mt_invoice_created')
        else:
            return super()._creation_subtype()

    def _track_subtype(self, init_values):
        # EXTENDS mail mail.thread
        # add custom subtype depending of the state.
        self.ensure_one()

        if not self.is_invoice(include_receipts=True):
            if self.payment_id and 'state' in init_values:
                self.payment_id._message_track(['state'], {self.payment_id.id: init_values})
            return super()._track_subtype(init_values)

        if 'payment_state' in init_values and self.payment_state == 'paid':
            return self.env.ref('account.mt_invoice_paid')
        elif 'state' in init_values and self.state == 'posted' and self.is_sale_document(include_receipts=True):
            return self.env.ref('account.mt_invoice_validated')
        return super()._track_subtype(init_values)

    def _creation_message(self):
        # EXTENDS mail mail.thread
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
        # EXTENDS mail mail.thread
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

    # -------------------------------------------------------------------------
    # HOOKS
    # -------------------------------------------------------------------------

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

    def _invoice_paid_hook(self):
        ''' Hook to be overrided called when the invoice moves to the paid state. '''

    def _get_lines_onchange_currency(self):
        # Override needed for COGS
        return self.line_ids

    @api.model
    def _get_invoice_in_payment_state(self):
        ''' Hook to give the state when the invoice becomes fully paid. This is necessary because the users working
        with only invoicing don't want to see the 'in_payment' state. Then, this method will be overridden in the
        accountant module to enable the 'in_payment' state. '''
        return 'paid'

    def _get_name_invoice_report(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'account.report_invoice_document'

    def _get_create_document_from_attachment_decoders(self):
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

    def _is_downpayment(self):
        ''' Return true if the invoice is a downpayment.
        Down-payments can be created from a sale order. This method is overridden in the sale order module.
        '''
        return False
