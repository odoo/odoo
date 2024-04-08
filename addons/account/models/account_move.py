# -*- coding: utf-8 -*-

from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from json import dumps
import math
import re
from textwrap import shorten

from odoo import api, fields, models, _, Command
from odoo.addons.account.tools import format_rf_reference
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    is_html_empty,
    sql
)


MAX_HASH_VERSION = 3

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
]

TYPE_REVERSE_MAP = {
    'entry': 'entry',
    'out_invoice': 'out_refund',
    'out_refund': 'entry',
    'in_invoice': 'in_refund',
    'in_refund': 'entry',
    'out_receipt': 'out_refund',
    'in_receipt': 'in_refund',
}

EMPTY = object()


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _description = "Journal Entry"
    _order = 'date desc, name desc, id desc'
    _mail_post_access = 'read'
    _check_company_auto = True
    _sequence_index = "journal_id"
    _rec_names_search = ['name', 'partner_id.name', 'ref']

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
        compute='_compute_name', inverse='_inverse_name', readonly=False, store=True,
        copy=False,
        tracking=True,
        index='trigram',
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
        compute='_compute_journal_id', inverse='_inverse_journal_id', store=True, readonly=False, precompute=True,
        required=True,
        states={'draft': [('readonly', False)]},
        check_company=True,
        domain="[('id', 'in', suitable_journal_ids)]",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        compute='_compute_company_id', inverse='_inverse_company_id', store=True, readonly=False, precompute=True,
        index=True,
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

    # === Cash basis feature fields === #
    # used to keep track of the tax cash basis reconciliation. This is needed
    # when cancelling the source: it will post the inverse journal entry to
    # cancel that part too.
    tax_cash_basis_rec_id = fields.Many2one(
        comodel_name='account.partial.reconcile',
        index='btree_not_null',
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
    always_tax_exigible = fields.Boolean(compute='_compute_always_tax_exigible', store=True, readonly=False)

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
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'account.move')], string='Attachments')

    # === Hash Fields === #
    restrict_mode_hash_table = fields.Boolean(related='journal_id.restrict_mode_hash_table')
    secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True, copy=False, index=True)
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
    needed_terms = fields.Binary(compute='_compute_needed_terms', exportable=False)
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
        index=True,
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
        tracking=True,
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
        tracking=True,
        compute='_compute_payment_reference', inverse='_inverse_payment_reference', store=True, readonly=False,
    )
    display_qr_code = fields.Boolean(
        string="Display QR-code",
        compute='_compute_display_qr_code',
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
        exportable=False,
    )
    invoice_has_outstanding = fields.Boolean(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_to_reconcile_info',
    )
    invoice_payments_widget = fields.Binary(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_reconciled_info',
        exportable=False,
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
        exportable=False,
    )
    payment_state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION,
        string="Payment Status",
        compute='_compute_payment_state', store=True, readonly=True,
        copy=False,
        tracking=True,
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
    quick_encoding_vals = fields.Binary(compute='_compute_quick_encoding_vals', exportable=False)

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
    duplicated_ref_ids = fields.Many2many(comodel_name='account.move', compute='_compute_duplicated_ref_ids')

    # used to display the various dates and amount dues on the invoice's PDF
    payment_term_details = fields.Binary(compute="_compute_payment_term_details", exportable=False)
    show_payment_term_details = fields.Boolean(compute="_compute_show_payment_term_details")
    show_discount_details = fields.Boolean(compute="_compute_show_payment_term_details")

    def _auto_init(self):
        super()._auto_init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS account_move_to_check_idx
            ON account_move(journal_id) WHERE to_check = true;
            CREATE INDEX IF NOT EXISTS account_move_payment_idx
            ON account_move(journal_id, state, payment_state, move_type, date);
            -- Used for gap detection in list views
            CREATE INDEX IF NOT EXISTS account_move_sequence_index3
            ON account_move (journal_id, sequence_prefix desc, (sequence_number+1) desc);
        """)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    def _compute_payment_reference(self):
        for move in self.filtered(lambda m: (
            m.state == 'posted'
            and m.move_type == 'out_invoice'
            and not m.payment_reference
        )):
            move.payment_reference = move._get_invoice_computed_reference()
        self._inverse_payment_reference()

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
                # _affect_tax_report may trigger premature recompute of line_ids.date
                self.env.add_to_compute(move.line_ids._fields['date'], move.line_ids)
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
                or record.auto_post != 'no' and record.date > fields.Date.context_today(record)

    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            company_id = move.journal_id.company_id or self.env.company
            if company_id != move.company_id:
                move.company_id = company_id

    @api.depends('move_type')
    def _compute_journal_id(self):
        for record in self.filtered(lambda r: r.journal_id.type not in r._get_valid_journal_types()):
            record.journal_id = record._search_default_journal()

    def _get_valid_journal_types(self):
        if self.is_sale_document(include_receipts=True):
            return ['sale']
        elif self.is_purchase_document(include_receipts=True):
            return ['purchase']
        elif self.payment_id or self.env.context.get('is_payment'):
            return ['bank', 'cash']
        return ['general']

    def _search_default_journal(self):
        if self.payment_id and self.payment_id.journal_id:
            return self.payment_id.journal_id
        if self.statement_line_id and self.statement_line_id.journal_id:
            return self.statement_line_id.journal_id
        if self.statement_line_ids.statement_id.journal_id:
            return self.statement_line_ids.statement_id.journal_id[:1]

        journal_types = self._get_valid_journal_types()
        company_id = (self.company_id or self.env.company).id
        domain = [('company_id', '=', company_id), ('type', 'in', journal_types)]

        journal = None
        # the currency is not a hard dependence, it triggers via manual add_to_compute
        # avoid computing the currency before all it's dependences are set (like the journal...)
        if self.env.cache.contains(self, self._fields['currency_id']):
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
        self = self.sorted(lambda m: (m.date, m.ref or '', m.id))

        for move in self:
            if move.state == 'cancel':
                continue

            move_has_name = move.name and move.name != '/'
            if move_has_name or move.state != 'posted':
                if not move.posted_before and not move._sequence_matches_date():
                    if move._get_last_sequence(lock=False):
                        # The name does not match the date and the move is not the first in the period:
                        # Reset to draft
                        move.name = False
                        continue
                else:
                    if move_has_name and move.posted_before or not move_has_name and move._get_last_sequence(lock=False):
                        # The move either
                        # - has a name and was posted before, or
                        # - doesn't have a name, but is not the first in the period
                        # so we don't recompute the name
                        continue
            if move.date and (not move_has_name or not move._sequence_matches_date()):
                move._set_next_sequence()

        self.filtered(lambda m: not m.name and not move.quick_edit_mode).name = '/'
        self._inverse_name()


    @api.depends('journal_id', 'date')
    def _compute_highest_name(self):
        for record in self:
            record.highest_name = record._get_last_sequence(lock=False)

    @api.depends('name', 'journal_id')
    def _compute_made_sequence_hole(self):
        self.env.cr.execute("""
            SELECT this.id
              FROM account_move this
              JOIN res_company company ON company.id = this.company_id
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
            else:
                move.invoice_payment_term_id = False

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
                or invoice.currency_id
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
        'line_ids.full_reconcile_id',
        'state')
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
                        ARRAY_AGG(counterpart_move.move_type) AS counterpart_move_types,
                        COALESCE(BOOL_AND(COALESCE(pay.is_matched, FALSE))
                            FILTER (WHERE counterpart_move.payment_id IS NOT NULL), TRUE) AS all_payments_matched,
                        BOOL_OR(COALESCE(BOOL(pay.id), FALSE)) as has_payment,
                        BOOL_OR(COALESCE(BOOL(counterpart_move.statement_line_id), FALSE)) as has_st_line
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
                        if any(x['has_payment'] or x['has_st_line'] for x in reconciliation_vals):

                            # Check if the invoice/expense entry is fully paid or 'in_payment'.
                            if all(x['all_payments_matched'] for x in reconciliation_vals):
                                new_pmt_state = 'paid'
                            else:
                                new_pmt_state = invoice._get_invoice_in_payment_state()

                        else:
                            new_pmt_state = 'paid'

                            reverse_move_types = set()
                            for x in reconciliation_vals:
                                for move_type in x['counterpart_move_types']:
                                    reverse_move_types.add(move_type)

                            in_reverse = (invoice.move_type in ('in_invoice', 'in_receipt')
                                          and (reverse_move_types == {'in_refund'} or reverse_move_types == {'in_refund', 'entry'}))
                            out_reverse = (invoice.move_type in ('out_invoice', 'out_receipt')
                                           and (reverse_move_types == {'out_refund'} or reverse_move_types == {'out_refund', 'entry'}))
                            misc_reverse = (invoice.move_type in ('entry', 'out_refund', 'in_refund')
                                            and reverse_move_types == {'entry'})
                            if in_reverse or out_reverse or misc_reverse:
                                new_pmt_state = 'reversed'

                    elif reconciliation_vals:
                        new_pmt_state = 'partial'

            invoice.payment_state = new_pmt_state

    @api.depends('invoice_payment_term_id', 'invoice_date', 'currency_id', 'amount_total_in_currency_signed', 'invoice_date_due')
    def _compute_needed_terms(self):
        for invoice in self:
            is_draft = invoice.id != invoice._origin.id
            invoice.needed_terms = {}
            invoice.needed_terms_dirty = True
            sign = 1 if invoice.is_inbound(include_receipts=True) else -1
            if invoice.is_invoice(True) and invoice.invoice_line_ids:
                if invoice.invoice_payment_term_id:
                    if is_draft:
                        tax_amount_currency = 0.0
                        untaxed_amount_currency = 0.0
                        for line in invoice.invoice_line_ids:
                            untaxed_amount_currency += line.price_subtotal
                            for tax_result in (line.compute_all_tax or {}).values():
                                tax_amount_currency += -sign * tax_result.get('amount_currency', 0.0)
                        untaxed_amount = untaxed_amount_currency
                        tax_amount = tax_amount_currency
                    else:
                        tax_amount_currency = invoice.amount_tax * sign
                        tax_amount = invoice.amount_tax_signed
                        untaxed_amount_currency = invoice.amount_untaxed * sign
                        untaxed_amount = invoice.amount_untaxed_signed
                    invoice_payment_terms = invoice.invoice_payment_term_id._compute_terms(
                        date_ref=invoice.invoice_date or invoice.date or fields.Date.context_today(invoice),
                        currency=invoice.currency_id,
                        tax_amount_currency=tax_amount_currency,
                        tax_amount=tax_amount,
                        untaxed_amount_currency=untaxed_amount_currency,
                        untaxed_amount=untaxed_amount,
                        company=invoice.company_id,
                        sign=sign
                    )
                    for term in invoice_payment_terms:
                        key = frozendict({
                            'move_id': invoice.id,
                            'date_maturity': fields.Date.to_date(term.get('date')),
                            'discount_date': term.get('discount_date'),
                            'discount_percentage': term.get('discount_percentage'),
                        })
                        values = {
                            'balance': term['company_amount'],
                            'amount_currency': term['foreign_amount'],
                            'discount_amount_currency': term['discount_amount_currency'] or 0.0,
                            'discount_balance': term['discount_balance'] or 0.0,
                            'discount_date': term['discount_date'],
                            'discount_percentage': term['discount_percentage'],
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
                        'discount_date': False,
                        'discount_percentage': 0
                    })] = {
                        'balance': invoice.amount_total_signed,
                        'amount_currency': invoice.amount_total_in_currency_signed,
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
                    'currency_id': move.currency_id.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
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
                    if counterpart_line.amount_currency and counterpart_line.currency_id != counterpart_line.company_id.currency_id:
                        foreign_currency = counterpart_line.currency_id
                    else:
                        foreign_currency = False

                    reconciled_vals.append({
                        'name': counterpart_line.name,
                        'journal_name': counterpart_line.journal_id.name,
                        'amount': reconciled_partial['amount'],
                        'currency_id': move.company_id.currency_id.id if reconciled_partial['is_exchange'] else reconciled_partial['currency'].id,
                        'date': counterpart_line.date,
                        'partial_id': reconciled_partial['partial_id'],
                        'account_payment_id': counterpart_line.payment_id.id,
                        'payment_method_name': counterpart_line.payment_id.payment_method_line_id.name,
                        'move_id': counterpart_line.move_id.id,
                        'ref': reconciliation_ref,
                        # these are necessary for the views to change depending on the values
                        'is_exchange': reconciled_partial['is_exchange'],
                        'amount_company_currency': formatLang(self.env, abs(counterpart_line.balance), currency_obj=counterpart_line.company_id.currency_id),
                        'amount_foreign_currency': foreign_currency and formatLang(self.env, abs(counterpart_line.amount_currency), currency_obj=foreign_currency)
                    })
                payments_widget_vals['content'] = reconciled_vals

            if payments_widget_vals['content']:
                move.invoice_payments_widget = payments_widget_vals
            else:
                move.invoice_payments_widget = False

    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                base_line_values_list = [line._convert_to_tax_base_line_dict() for line in base_lines]
                sign = move.direction_sign
                if move.id:
                    # The invoice is stored so we can add the early payment discount lines directly to reduce the
                    # tax amount without touching the untaxed amount.
                    base_line_values_list += [
                        {
                            **line._convert_to_tax_base_line_dict(),
                            'handle_price_include': False,
                            'quantity': 1.0,
                            'price_unit': sign * line.amount_currency,
                        }
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'epd')
                    ]

                kwargs = {
                    'base_lines': base_line_values_list,
                    'currency': move.currency_id or move.journal_id.currency_id or move.company_id.currency_id,
                }

                if move.id:
                    kwargs['tax_lines'] = [
                        line._convert_to_tax_line_dict()
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'tax')
                    ]
                else:
                    # In case the invoice isn't yet stored, the early payment discount lines are not there. Then,
                    # we need to simulate them.
                    epd_aggregated_values = {}
                    for base_line in base_lines:
                        if not base_line.epd_needed:
                            continue
                        for grouping_dict, values in base_line.epd_needed.items():
                            epd_values = epd_aggregated_values.setdefault(grouping_dict, {'price_subtotal': 0.0})
                            epd_values['price_subtotal'] += values['price_subtotal']

                    for grouping_dict, values in epd_aggregated_values.items():
                        taxes = None
                        if grouping_dict.get('tax_ids'):
                            taxes = self.env['account.tax'].browse(grouping_dict['tax_ids'][0][2])

                        kwargs['base_lines'].append(self.env['account.tax']._convert_to_tax_base_line_dict(
                            None,
                            partner=move.partner_id,
                            currency=move.currency_id,
                            taxes=taxes,
                            price_unit=values['price_subtotal'],
                            quantity=1.0,
                            account=self.env['account.account'].browse(grouping_dict['account_id']),
                            analytic_distribution=values.get('analytic_distribution'),
                            price_subtotal=values['price_subtotal'],
                            is_refund=move.move_type in ('out_refund', 'in_refund'),
                            handle_price_include=False,
                            extra_context={'_extra_grouping_key_': 'epd'},
                        ))
                move.tax_totals = self.env['account.tax']._prepare_tax_totals(**kwargs)
                if move.invoice_cash_rounding_id:
                    rounding_amount = move.invoice_cash_rounding_id.compute_difference(move.currency_id, move.tax_totals['amount_total'])
                    totals = move.tax_totals
                    totals['display_rounding'] = True
                    if rounding_amount:
                        if move.invoice_cash_rounding_id.strategy == 'add_invoice_line':
                            totals['rounding_amount'] = rounding_amount
                            totals['formatted_rounding_amount'] = formatLang(self.env, totals['rounding_amount'], currency_obj=move.currency_id)
                            totals['amount_total_rounded'] = totals['amount_total'] + rounding_amount
                            totals['formatted_amount_total_rounded'] = formatLang(self.env, totals['amount_total_rounded'], currency_obj=move.currency_id)
                        elif move.invoice_cash_rounding_id.strategy == 'biggest_tax':
                            if totals['subtotals_order']:
                                max_tax_group = max((
                                    tax_group
                                    for tax_groups in totals['groups_by_subtotal'].values()
                                    for tax_group in tax_groups
                                ), key=lambda tax_group: tax_group['tax_group_amount'])
                                max_tax_group['tax_group_amount'] += rounding_amount
                                max_tax_group['formatted_tax_group_amount'] = formatLang(self.env, max_tax_group['tax_group_amount'], currency_obj=move.currency_id)
                                totals['amount_total'] += rounding_amount
                                totals['formatted_amount_total'] = formatLang(self.env, totals['amount_total'], currency_obj=move.currency_id)
            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals = None

    @api.depends('show_payment_term_details')
    def _compute_payment_term_details(self):
        '''
        Returns an [] containing the payment term's information to be displayed on the invoice's PDF.
        '''
        for invoice in self:
            invoice.payment_term_details = False
            if invoice.show_payment_term_details:
                sign = 1 if invoice.is_inbound(include_receipts=True) else -1
                payment_term_details = []
                for line in invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').sorted('date_maturity'):
                    payment_term_details.append({
                        'date': format_date(self.env, line.date_maturity),
                        'amount': sign * line.amount_currency,
                        'discount_date': format_date(self.env, line.discount_date),
                        'discount_amount_currency': sign * line.discount_amount_currency,
                    })
                invoice.payment_term_details = payment_term_details

    @api.depends('move_type', 'payment_state', 'invoice_payment_term_id')
    def _compute_show_payment_term_details(self):
        '''
        Determines :
        - whether or not an additional table should be added at the end of the invoice to display the various
        - whether or not there is an early pay discount in this invoice that should be displayed
        '''
        for invoice in self:
            if invoice.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt') and invoice.payment_state in ('not_paid', 'partial'):
                payment_term_lines = invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term')
                invoice.show_discount_details = any(line.discount_date for line in payment_term_lines)
                invoice.show_payment_term_details = len(payment_term_lines) > 1 or invoice.show_discount_details
            else:
                invoice.show_discount_details = False
                invoice.show_payment_term_details = False

    @api.depends('partner_id', 'invoice_source_email', 'partner_id.display_name')
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

    @api.depends('date', 'line_ids.debit', 'line_ids.credit', 'line_ids.tax_line_id', 'line_ids.tax_ids', 'line_ids.tax_tag_ids',
                 'invoice_line_ids.debit', 'invoice_line_ids.credit', 'invoice_line_ids.tax_line_id', 'invoice_line_ids.tax_ids', 'invoice_line_ids.tax_tag_ids')
    def _compute_tax_lock_date_message(self):
        for move in self:
            accounting_date = move.date or fields.Date.context_today(move)
            affects_tax_report = move._affect_tax_report()
            move.tax_lock_date_message = move._get_lock_date_message(accounting_date, affects_tax_report)

    @api.depends('currency_id')
    def _compute_display_inactive_currency_warning(self):
        for move in self.with_context(active_test=False):
            move.display_inactive_currency_warning = move.state == 'draft' and move.currency_id and not move.currency_id.active

    @api.depends('company_id.account_fiscal_country_id', 'fiscal_position_id', 'fiscal_position_id.country_id', 'fiscal_position_id.foreign_vat')
    def _compute_tax_country_id(self):
        foreign_vat_records = self.filtered(lambda r: r.fiscal_position_id.foreign_vat)
        for fiscal_position_id, record_group in groupby(foreign_vat_records, key=lambda r: r.fiscal_position_id):
            self.env['account.move'].concat(*record_group).tax_country_id = fiscal_position_id.country_id
        for company_id, record_group in groupby((self-foreign_vat_records), key=lambda r: r.company_id):
            self.env['account.move'].concat(*record_group).tax_country_id = company_id.account_fiscal_country_id

    @api.depends('tax_country_id')
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

    @api.depends('company_id', 'partner_id', 'tax_totals', 'currency_id')
    def _compute_partner_credit_warning(self):
        for move in self:
            move.with_company(move.company_id)
            move.partner_credit_warning = ''
            show_warning = move.state == 'draft' and \
                           move.move_type == 'out_invoice' and \
                           move.company_id.account_use_credit_limit
            if show_warning:
                amount_total_currency = move.currency_id._convert(move.tax_totals['amount_total'], move.company_currency_id, move.company_id, move.date)
                updated_credit = move.partner_id.commercial_partner_id.credit + amount_total_currency
                move.partner_credit_warning = self._build_credit_warning_message(move, updated_credit)

    def _build_credit_warning_message(self, record, updated_credit):
        ''' Build the warning message that will be displayed in a yellow banner on top of the current record
            if the partner exceeds a credit limit (set on the company or the partner itself).
            :param record:                  The record where the warning will appear (Invoice, Sales Order...).
            :param updated_credit (float):  The partner's updated credit limit including the current record.
            :return (str):                  The warning message to be showed.
        '''
        partner_id = record.partner_id.commercial_partner_id
        if not partner_id.credit_limit or updated_credit <= partner_id.credit_limit:
            return ''
        msg = _('%s has reached its Credit Limit of : %s\nTotal amount due ',
                partner_id.name,
                formatLang(self.env, partner_id.credit_limit, currency_obj=record.company_id.currency_id))
        if updated_credit > partner_id.credit:
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

    @api.depends('quick_edit_total_amount', 'invoice_line_ids.price_total', 'tax_totals')
    def _compute_quick_encoding_vals(self):
        for move in self:
            move.quick_encoding_vals = move._get_quick_edit_suggestions()

    @api.depends('ref', 'move_type', 'partner_id', 'invoice_date')
    def _compute_duplicated_ref_ids(self):
        move_to_duplicate_move = self._fetch_duplicate_supplier_reference()
        for move in self:
            # Uses move._origin.id to handle records in edition/existing records and 0 for new records
            move.duplicated_ref_ids = move_to_duplicate_move.get(move._origin, self.env['account.move'])

    def _fetch_duplicate_supplier_reference(self, only_posted=False):
        moves = self.filtered(lambda m: m.is_purchase_document() and m.ref)
        if not moves:
            return {}

        used_fields = ("company_id", "partner_id", "commercial_partner_id", "ref", "move_type", "invoice_date", "state")
        self.env["account.move"].flush_model(used_fields)

        move_table_and_alias = "account_move AS move"
        place_holders = {}
        if not moves[0].id:  # check if record is under creation/edition in UI
            # New record aren't searchable in the DB and record in edition aren't up to date yet
            # Replace the table by safely injecting the values in the query
            place_holders = {
                "id": moves._origin.id or 0,
                **{
                    field_name: moves._fields[field_name].convert_to_write(moves[field_name], moves) or None
                    for field_name in used_fields
                },
            }
            casted_values = ", ".join([f"%({field_name})s::{moves._fields[field_name].column_type[0]}" for field_name in place_holders])
            move_table_and_alias = f'(VALUES ({casted_values})) AS move({", ".join(place_holders)})'

        self.env.cr.execute(f"""
            SELECT
                   move.id AS move_id,
                   array_agg(duplicate_move.id) AS duplicate_ids
              FROM {move_table_and_alias}
              JOIN account_move AS duplicate_move ON
                   move.company_id = duplicate_move.company_id
               AND move.commercial_partner_id = duplicate_move.commercial_partner_id
               AND move.ref = duplicate_move.ref
               AND move.move_type = duplicate_move.move_type
               AND move.id != duplicate_move.id
               AND (move.invoice_date = duplicate_move.invoice_date OR NOT %(only_posted)s)
               AND duplicate_move.state != 'cancel'
               AND (duplicate_move.state = 'posted' OR NOT %(only_posted)s)
             WHERE move.id IN %(moves)s
             GROUP BY move.id
        """, {
            "only_posted": only_posted,
            "moves": tuple(moves.ids or [0]),
            **place_holders
        })
        return {
            self.env['account.move'].browse(res['move_id']): self.env['account.move'].browse(res['duplicate_ids'])
            for res in self.env.cr.dictfetchall()
        }

    @api.depends('company_id')
    def _compute_display_qr_code(self):
        for record in self:
            record.display_qr_code = (
                record.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt')
                and record.company_id.qr_code
            )

    # -------------------------------------------------------------------------
    # INVERSE METHODS
    # -------------------------------------------------------------------------

    def _inverse_tax_totals(self):
        if self.env.context.get('skip_invoice_sync'):
            return
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
            balance = move.currency_id._convert(amount_currency, move.company_currency_id, move.company_id, move.invoice_date or move.date)

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
                for line in invoice.line_ids + invoice.invoice_line_ids:
                    if line.partner_id != invoice.commercial_partner_id:
                        line.partner_id = invoice.commercial_partner_id
                        line._inverse_partner_id()

    @api.onchange('company_id')
    def _inverse_company_id(self):
        self._conditional_add_to_compute('journal_id', lambda m: (
            m.journal_id.company_id != m.company_id
        ))

    @api.onchange('currency_id')
    def _inverse_currency_id(self):
        self._conditional_add_to_compute('journal_id', lambda m: (
            m.journal_id.currency_id
            and m.journal_id.currency_id != m.currency_id
        ))
        (self.line_ids | self.invoice_line_ids)._conditional_add_to_compute('currency_id', lambda l: (
            l.move_id.is_invoice(True)
            and l.move_id.currency_id != l.currency_id
        ))

    @api.onchange('journal_id')
    def _inverse_journal_id(self):
        self._conditional_add_to_compute('company_id', lambda m: (
            not m.company_id
            or m.company_id != m.journal_id.company_id
        ))
        self._conditional_add_to_compute('currency_id', lambda m: (
            not m.currency_id
            or m.journal_id.currency_id and m.currency_id != m.journal_id.currency_id
        ))

    def _inverse_payment_reference(self):
        self.line_ids._conditional_add_to_compute('name', lambda line: (
            line.display_type == 'payment_term'
        ))

    def _inverse_name(self):
        self._conditional_add_to_compute('payment_reference', lambda move: (
            move.name and move.name != '/'
        ))

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('date')
    def _onchange_date(self):
        if not self.is_invoice(True):
            self.line_ids._inverse_amount_currency()

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
<<<<<<< HEAD
                return {'warning': warning}
||||||| parent of a2822764d045 (temp)
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
        bank_ids = self.bank_partner_id.bank_ids.filtered(lambda bank: bank.company_id is False or bank.company_id == self.company_id)
        self.partner_bank_id = bank_ids and bank_ids[0]

        # Find the new fiscal position.
        delivery_partner_id = self._get_invoice_delivery_partner_id()
        self.fiscal_position_id = self.env['account.fiscal.position'].get_fiscal_position(
            self.partner_id.id, delivery_id=delivery_partner_id)
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
                self._onchange_currency()

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

    @api.onchange('invoice_cash_rounding_id')
    def _onchange_invoice_cash_rounding_id(self):
        for move in self:
            if move.invoice_cash_rounding_id.strategy == 'add_invoice_line' and not move.invoice_cash_rounding_id.profit_account_id:
                return {'warning':{
                    'title': _("Warning for Cash Rounding Method: %s", move.invoice_cash_rounding_id.name),
                    'message': _("You must specify the Profit Account (company dependent)")
                }}

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        ''' Create the dictionary based on a tax line that will be used as key to group taxes together.
        /!\ Must be consistent with '_get_tax_grouping_key_from_base_line'.
        :param tax_line:    An account.move.line being a tax line (with 'tax_repartition_line_id' set then).
        :return:            A dictionary containing all fields on which the tax will be grouped.
        '''
        return {
            'tax_repartition_line_id': tax_line.tax_repartition_line_id.id,
            'group_tax_id': tax_line.group_tax_id.id,
            'account_id': tax_line.account_id.id,
            'currency_id': tax_line.currency_id.id,
            'analytic_tag_ids': [(6, 0, tax_line.tax_line_id.analytic and tax_line.analytic_tag_ids.ids or [])],
            'analytic_account_id': tax_line.tax_line_id.analytic and tax_line.analytic_account_id.id,
            'tax_ids': [(6, 0, tax_line.tax_ids.ids)],
            'tax_tag_ids': [(6, 0, tax_line.tax_tag_ids.ids)],
            'partner_id': tax_line.partner_id.id,
        }

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        ''' Create the dictionary based on a base line that will be used as key to group taxes together.
        /!\ Must be consistent with '_get_tax_grouping_key_from_tax_line'.
        :param base_line:   An account.move.line being a base line (that could contains something in 'tax_ids').
        :param tax_vals:    An element of compute_all(...)['taxes'].
        :return:            A dictionary containing all fields on which the tax will be grouped.
        '''
        tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
        account = base_line._get_default_tax_account(tax_repartition_line) or base_line.account_id
        return {
            'tax_repartition_line_id': tax_vals['tax_repartition_line_id'],
            'group_tax_id': tax_vals['group'].id if tax_vals['group'] else False,
            'account_id': account.id,
            'currency_id': base_line.currency_id.id,
            'analytic_tag_ids': [(6, 0, tax_vals['analytic'] and base_line.analytic_tag_ids.ids or [])],
            'analytic_account_id': tax_vals['analytic'] and base_line.analytic_account_id.id,
            'tax_ids': [(6, 0, tax_vals['tax_ids'])],
            'tax_tag_ids': [(6, 0, tax_vals['tag_ids'])],
            'partner_id': base_line.partner_id.id,
        }

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

    def _preprocess_taxes_map(self, taxes_map):
        """ Useful in case we want to pre-process taxes_map """
        return taxes_map

    def _recompute_tax_lines(self, recompute_tax_base_amount=False, tax_rep_lines_to_recompute=None):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: Flag forcing only the recomputation of the `tax_base_amount` field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            return base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=move.always_tax_exigible,
            )

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line, tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # Don't create tax lines with zero balance.
            if currency.is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line'] and not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id, self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            balance = currency._convert(
                taxes_map_entry['amount'],
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )
            amount_currency = currency.round(taxes_map_entry['amount'])
            sign = -1 if self.is_inbound() else 1
            to_write_on_line = {
                'amount_currency': amount_currency,
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
                'price_total': sign * amount_currency,
                'price_subtotal': sign * amount_currency,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                if tax_rep_lines_to_recompute and taxes_map_entry['tax_line'].tax_repartition_line_id not in tax_rep_lines_to_recompute:
                    continue

                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                # Create a new tax line.
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)

                if tax_rep_lines_to_recompute and tax_repartition_line not in tax_rep_lines_to_recompute:
                    continue

                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'company_id': self.company_id.id,
                    'company_currency_id': self.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))

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
                'debit': diff_balance > 0.0 and diff_balance or 0.0,
                'credit': diff_balance < 0.0 and -diff_balance or 0.0,
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
            else:
                accounts = {
                    account_type: acc or self.env['account.account'].search([
                        ('company_id', '=', self.company_id.id),
                        ('internal_type', '=', account_type),
                        ('deprecated', '=', False),
                    ], limit=1)
                    for acc, account_type in [(self.partner_id.property_account_payable_id, 'payable'), (self.partner_id.property_account_receivable_id, 'receivable')]}
                account_map = (self.fiscal_position_id or self.env['account.fiscal.position']).map_accounts(accounts)
                if self.is_sale_document(include_receipts=True):
                    return account_map['receivable']
                elif self.is_purchase_document(include_receipts=True):
                    return account_map['payable']

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
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.payment_reference or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
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
            has_taxes = False
            for line in invoice.line_ids:
                if line.recompute_tax_line:
                    inv_recompute_all_taxes = True
                    line.recompute_tax_line = False
                if line.tax_repartition_line_id:
                    current_tax_rep_lines.add(line.tax_repartition_line_id._origin)
                elif line.tax_ids:
                    has_taxes = True
                    if invoice.is_invoice(include_receipts=True):
                        is_refund = invoice.move_type in ('out_refund', 'in_refund')
                    else:
                        tax_type = line.tax_ids[0].type_tax_use
                        is_refund = (tax_type == 'sale' and line.debit) or (tax_type == 'purchase' and line.credit)
                    taxes = line.tax_ids._origin.flatten_taxes_hierarchy().filtered(
                        lambda tax: (
                                tax.amount_type == 'fixed' and not invoice.company_id.currency_id.is_zero(tax.amount)
                                or not float_is_zero(tax.amount, precision_digits=4)
                        )
                    )
                    if is_refund:
                        tax_rep_lines = taxes.refund_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    else:
                        tax_rep_lines = taxes.invoice_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    for tax_rep_line in tax_rep_lines:
                        expected_tax_rep_lines.add(tax_rep_line)
            delta_tax_rep_lines = expected_tax_rep_lines - current_tax_rep_lines

            # Compute taxes.
            if has_taxes or current_tax_rep_lines:
                if inv_recompute_all_taxes:
                    invoice._recompute_tax_lines()
                elif recompute_tax_base_amount:
                    invoice._recompute_tax_lines(recompute_tax_base_amount=True)
                elif delta_tax_rep_lines and not self._context.get('move_reverse_cancel'):
                    invoice._recompute_tax_lines(tax_rep_lines_to_recompute=delta_tax_rep_lines)

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

        # Group the moves by journal and month
        for move in self:
            if move.state == 'cancel':
                continue

            move_has_name = move.name and move.name != '/'
            if move_has_name or move.state != 'posted':
                try:
                    if not move.posted_before:
                        # The move was never posted, so the name can potentially be changed.
                        move._constrains_date_sequence()
                    # Either the move was posted before, or the name already matches the date (or no name or date).
                    # We can skip recalculating the name when either
                    # - the move already has a name, or
                    # - the move has no name, but is in a period with other moves (so name should be `/`), or
                    # - the move has (temporarily) no date set
                    if (
                        move_has_name and move.posted_before
                        or not move_has_name and move._get_last_sequence(lock=False)
                        or not move.date
                    ):
                        continue
                except ValidationError:
                    # The move was never posted and the current name doesn't match the date. We should calculate the
                    # name later on, unless ...
                    if move._get_last_sequence(lock=False):
                        # ... we are in a period already containing moves: reset the name to `/` (draft)
                        move.name = '/'
                        continue
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
=======
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
        bank_ids = self.bank_partner_id.bank_ids.filtered(lambda bank: bank.company_id is False or bank.company_id == self.company_id)
        self.partner_bank_id = bank_ids and bank_ids[0]

        # Find the new fiscal position.
        delivery_partner_id = self._get_invoice_delivery_partner_id()
        self.fiscal_position_id = self.env['account.fiscal.position'].get_fiscal_position(
            self.partner_id.id, delivery_id=delivery_partner_id)
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
                self._onchange_currency()

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

    @api.onchange('invoice_cash_rounding_id')
    def _onchange_invoice_cash_rounding_id(self):
        for move in self:
            if move.invoice_cash_rounding_id.strategy == 'add_invoice_line' and not move.invoice_cash_rounding_id.profit_account_id:
                return {'warning':{
                    'title': _("Warning for Cash Rounding Method: %s", move.invoice_cash_rounding_id.name),
                    'message': _("You must specify the Profit Account (company dependent)")
                }}

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        r''' Create the dictionary based on a tax line that will be used as key to group taxes together.
        /!\ Must be consistent with '_get_tax_grouping_key_from_base_line'.
        :param tax_line:    An account.move.line being a tax line (with 'tax_repartition_line_id' set then).
        :return:            A dictionary containing all fields on which the tax will be grouped.
        '''
        return {
            'tax_repartition_line_id': tax_line.tax_repartition_line_id.id,
            'group_tax_id': tax_line.group_tax_id.id,
            'account_id': tax_line.account_id.id,
            'currency_id': tax_line.currency_id.id,
            'analytic_tag_ids': [(6, 0, tax_line.tax_line_id.analytic and tax_line.analytic_tag_ids.ids or [])],
            'analytic_account_id': tax_line.tax_line_id.analytic and tax_line.analytic_account_id.id,
            'tax_ids': [(6, 0, tax_line.tax_ids.ids)],
            'tax_tag_ids': [(6, 0, tax_line.tax_tag_ids.ids)],
            'partner_id': tax_line.partner_id.id,
        }

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        r''' Create the dictionary based on a base line that will be used as key to group taxes together.
        /!\ Must be consistent with '_get_tax_grouping_key_from_tax_line'.
        :param base_line:   An account.move.line being a base line (that could contains something in 'tax_ids').
        :param tax_vals:    An element of compute_all(...)['taxes'].
        :return:            A dictionary containing all fields on which the tax will be grouped.
        '''
        tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
        account = base_line._get_default_tax_account(tax_repartition_line) or base_line.account_id
        return {
            'tax_repartition_line_id': tax_vals['tax_repartition_line_id'],
            'group_tax_id': tax_vals['group'].id if tax_vals['group'] else False,
            'account_id': account.id,
            'currency_id': base_line.currency_id.id,
            'analytic_tag_ids': [(6, 0, tax_vals['analytic'] and base_line.analytic_tag_ids.ids or [])],
            'analytic_account_id': tax_vals['analytic'] and base_line.analytic_account_id.id,
            'tax_ids': [(6, 0, tax_vals['tax_ids'])],
            'tax_tag_ids': [(6, 0, tax_vals['tag_ids'])],
            'partner_id': base_line.partner_id.id,
        }

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

    def _preprocess_taxes_map(self, taxes_map):
        """ Useful in case we want to pre-process taxes_map """
        return taxes_map

    def _recompute_tax_lines(self, recompute_tax_base_amount=False, tax_rep_lines_to_recompute=None):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: Flag forcing only the recomputation of the `tax_base_amount` field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            return base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=move.always_tax_exigible,
            )

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line, tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # Don't create tax lines with zero balance.
            if currency.is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line'] and not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id, self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            balance = currency._convert(
                taxes_map_entry['amount'],
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )
            amount_currency = currency.round(taxes_map_entry['amount'])
            sign = -1 if self.is_inbound() else 1
            to_write_on_line = {
                'amount_currency': amount_currency,
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
                'price_total': sign * amount_currency,
                'price_subtotal': sign * amount_currency,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                if tax_rep_lines_to_recompute and taxes_map_entry['tax_line'].tax_repartition_line_id not in tax_rep_lines_to_recompute:
                    continue

                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                # Create a new tax line.
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)

                if tax_rep_lines_to_recompute and tax_repartition_line not in tax_rep_lines_to_recompute:
                    continue

                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'company_id': self.company_id.id,
                    'company_currency_id': self.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))

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
                'debit': diff_balance > 0.0 and diff_balance or 0.0,
                'credit': diff_balance < 0.0 and -diff_balance or 0.0,
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
            else:
                accounts = {
                    account_type: acc or self.env['account.account'].search([
                        ('company_id', '=', self.company_id.id),
                        ('internal_type', '=', account_type),
                        ('deprecated', '=', False),
                    ], limit=1)
                    for acc, account_type in [(self.partner_id.property_account_payable_id, 'payable'), (self.partner_id.property_account_receivable_id, 'receivable')]}
                account_map = (self.fiscal_position_id or self.env['account.fiscal.position']).map_accounts(accounts)
                if self.is_sale_document(include_receipts=True):
                    return account_map['receivable']
                elif self.is_purchase_document(include_receipts=True):
                    return account_map['payable']

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
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.payment_reference or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
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
            has_taxes = False
            for line in invoice.line_ids:
                if line.recompute_tax_line:
                    inv_recompute_all_taxes = True
                    line.recompute_tax_line = False
                if line.tax_repartition_line_id:
                    current_tax_rep_lines.add(line.tax_repartition_line_id._origin)
                elif line.tax_ids:
                    has_taxes = True
                    if invoice.is_invoice(include_receipts=True):
                        is_refund = invoice.move_type in ('out_refund', 'in_refund')
                    else:
                        tax_type = line.tax_ids[0].type_tax_use
                        is_refund = (tax_type == 'sale' and line.debit) or (tax_type == 'purchase' and line.credit)
                    taxes = line.tax_ids._origin.flatten_taxes_hierarchy().filtered(
                        lambda tax: (
                                tax.amount_type == 'fixed' and not invoice.company_id.currency_id.is_zero(tax.amount)
                                or not float_is_zero(tax.amount, precision_digits=4)
                        )
                    )
                    if is_refund:
                        tax_rep_lines = taxes.refund_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    else:
                        tax_rep_lines = taxes.invoice_repartition_line_ids._origin.filtered(lambda x: x.repartition_type == "tax")
                    for tax_rep_line in tax_rep_lines:
                        expected_tax_rep_lines.add(tax_rep_line)
            delta_tax_rep_lines = expected_tax_rep_lines - current_tax_rep_lines

            # Compute taxes.
            if has_taxes or current_tax_rep_lines:
                if inv_recompute_all_taxes:
                    invoice._recompute_tax_lines()
                elif recompute_tax_base_amount:
                    invoice._recompute_tax_lines(recompute_tax_base_amount=True)
                elif delta_tax_rep_lines and not self._context.get('move_reverse_cancel'):
                    invoice._recompute_tax_lines(tax_rep_lines_to_recompute=delta_tax_rep_lines)

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

        # Group the moves by journal and month
        for move in self:
            if move.state == 'cancel':
                continue

            move_has_name = move.name and move.name != '/'
            if move_has_name or move.state != 'posted':
                try:
                    if not move.posted_before:
                        # The move was never posted, so the name can potentially be changed.
                        move._constrains_date_sequence()
                    # Either the move was posted before, or the name already matches the date (or no name or date).
                    # We can skip recalculating the name when either
                    # - the move already has a name, or
                    # - the move has no name, but is in a period with other moves (so name should be `/`), or
                    # - the move has (temporarily) no date set
                    if (
                        move_has_name and move.posted_before
                        or not move_has_name and move._get_last_sequence(lock=False)
                        or not move.date
                    ):
                        continue
                except ValidationError:
                    # The move was never posted and the current name doesn't match the date. We should calculate the
                    # name later on, unless ...
                    if move._get_last_sequence(lock=False):
                        # ... we are in a period already containing moves: reset the name to `/` (draft)
                        move.name = '/'
                        continue
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
>>>>>>> a2822764d045 (temp)

    @api.onchange('name', 'highest_name')
    def _onchange_name_warning(self):
        if self.name and self.name != '/' and self.name <= (self.highest_name or '') and not self.quick_edit_mode:
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
                or dict(new_format_values, year=0, month=0, seq=0) != dict(origin_format_values, year=0, month=0, seq=0)
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
                elif reset == 'year_range':
                    detected = _(
                        "The sequence will restart at 1 at the start of every financial year.\n"
                        "The financial start year detected here is '%(year)s'.\n"
                        "The financial end year detected here is '%(year_end)s'.\n"
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
        if not self.quick_edit_mode:
            self.name = '/'
            self._compute_name()

    @api.onchange('invoice_cash_rounding_id')
    def _onchange_invoice_cash_rounding_id(self):
        for move in self:
            if move.invoice_cash_rounding_id.strategy == 'add_invoice_line' and not move.invoice_cash_rounding_id.profit_account_id:
                return {'warning': {
                    'title': _("Warning for Cash Rounding Method: %s", move.invoice_cash_rounding_id.name),
                    'message': _("You must specify the Profit Account (company dependent)")
                }}

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

        unbalanced_moves = self._get_unbalanced_moves(container)
        if unbalanced_moves:
            error_msg = _("An error has occurred.")
            for move_id, sum_debit, sum_credit in unbalanced_moves:
                move = self.browse(move_id)
                error_msg += _(
                    "\n\n"
                    "The move (%s) is not balanced.\n"
                    "The total of debits equals %s and the total of credits equals %s.\n"
                    "You might want to specify a default account on journal \"%s\" to automatically balance each move.",
                    move.display_name,
                    format_amount(self.env, sum_debit, move.company_id.currency_id),
                    format_amount(self.env, sum_credit, move.company_id.currency_id),
                    move.journal_id.name)
            raise UserError(error_msg)

    def _get_unbalanced_moves(self, container):
        moves = container['records'].filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend on computed stored fields.
        # It happens as the ORM calls create() with the 'no_recompute' statement.
        self.env['account.move.line'].flush_model(['debit', 'credit', 'balance', 'currency_id', 'move_id'])
        self._cr.execute('''
            SELECT line.move_id,
                   ROUND(SUM(line.debit), currency.decimal_places) debit,
                   ROUND(SUM(line.credit), currency.decimal_places) credit
              FROM account_move_line line
              JOIN account_move move ON move.id = line.move_id
              JOIN res_company company ON company.id = move.company_id
              JOIN res_currency currency ON currency.id = company.currency_id
             WHERE line.move_id IN %s
          GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.balance), currency.decimal_places) != 0
        ''', [tuple(moves.ids)])

        return self._cr.fetchall()

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
        """ Assert the move which is about to be posted isn't a duplicated move from another posted entry"""
        move_to_duplicate_moves = self.filtered(lambda m: m.state == 'posted')._fetch_duplicate_supplier_reference(only_posted=True)
        if any(duplicate_move for duplicate_move in move_to_duplicate_moves.values()):
            duplicate_move_ids = list(set(
                move_id
                for move_ids in (move.ids + duplicate.ids for move, duplicate in move_to_duplicate_moves.items() if duplicate)
                for move_id in move_ids
            ))
            action = self.env['ir.actions.actions']._for_xml_id('account.action_move_line_form')
            action['domain'] = [('id', 'in', duplicate_move_ids)]
            action['views'] = [((view_id, 'list') if view_type == 'tree' else (view_id, view_type)) for view_id, view_type in action['views']]
            raise RedirectWarning(
                message=_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note."),
                action=action,
                button_text=_("Open list"),
            )

    @api.constrains('line_ids', 'fiscal_position_id', 'company_id')
    def _validate_taxes_country(self):
        """ By playing with the fiscal position in the form view, it is possible to keep taxes on the invoices from
        a different country than the one allowed by the fiscal country or the fiscal position.
        This contrains ensure such account.move cannot be kept, as they could generate inconsistencies in the reports.
        """
        self._compute_tax_country_id() # We need to ensure this field has been computed, as we use it in our check
        for record in self:
            amls = record.line_ids
            impacted_countries = amls.tax_ids.country_id | amls.tax_line_id.country_id
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
                diff_balance = self.currency_id._convert(diff_amount_currency, self.company_id.currency_id, self.company_id, self.invoice_date or self.date)
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
                'amount_currency': diff_amount_currency,
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
                    if not biggest_tax_line or abs(tax_line.balance) > abs(biggest_tax_line.balance):
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

        # No update needed
        if existing_cash_rounding_line \
            and float_compare(existing_cash_rounding_line.balance, diff_balance, precision_rounding=self.currency_id.rounding) == 0 \
            and float_compare(existing_cash_rounding_line.amount_currency, diff_amount_currency, precision_rounding=self.currency_id.rounding) == 0:
            return

        _apply_cash_rounding(self, diff_balance, diff_amount_currency, existing_cash_rounding_line)

    @contextmanager
    def _sync_unbalanced_lines(self, container):
        yield
        # Skip posted moves.
        for invoice in (x for x in container['records'] if x.state != 'posted'):

            # Unlink tax lines if all taxes have been removed.
            if not invoice.line_ids.tax_ids:
                # if there isn't any tax but there remains a tax_line_id, it means we are currently in the process of
                # removing the taxes from the entry. Thus, we want the automatic balancing to happen in order  to have
                # a smooth process for tax deletion
                if not invoice.line_ids.filtered('tax_line_id'):
                    continue
                invoice.line_ids.filtered('tax_line_id').unlink()

            # Set the balancing line's balance and amount_currency to zero,
            # so that it does not interfere with _get_unbalanced_moves() below.
            balance_name = _('Automatic Balancing Line')
            existing_balancing_line = invoice.line_ids.filtered(lambda line: line.name == balance_name)
            if existing_balancing_line:
                existing_balancing_line.balance = existing_balancing_line.amount_currency = 0.0

            # Create an automatic balancing line to make sure the entry can be saved/posted.
            # If such a line already exists, we simply update its amounts.
            unbalanced_moves = self._get_unbalanced_moves({'records': invoice})
            if isinstance(unbalanced_moves, list) and len(unbalanced_moves) == 1:
                dummy, debit, credit = unbalanced_moves[0]

                vals = {'balance': credit - debit}
                if existing_balancing_line:
                    existing_balancing_line.write(vals)
                else:
                    vals.update({
                        'name': balance_name,
                        'move_id': invoice.id,
                        'account_id': invoice.company_id.account_journal_suspense_account_id.id,
                        'currency_id': invoice.currency_id.id,
                    })
                    self.env['account.move.line'].create(vals)

    @contextmanager
    def _sync_rounding_lines(self, container):
        yield
        for invoice in container['records']:
            if invoice.state != 'posted':
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

            # Convert float values to their "ORM cache" one to prevent different rounding calculations
            for dict_key in res:
                move_id = dict_key.get('move_id')
                if not move_id:
                    continue
                record = self.env['account.move'].browse(move_id)
                for fname, current_value in res[dict_key].items():
                    field = self.env['account.move.line']._fields[fname]
                    if isinstance(current_value, float):
                        new_value = field.convert_to_cache(current_value, record)
                        res[dict_key][fname] = new_value

            return res

        def dirty():
            *path, dirty_fname = needed_dirty_fname.split('.')
            eligible_recs = container['records'].mapped('.'.join(path))
            if eligible_recs._name == 'account.move.line':
                eligible_recs = eligible_recs.filtered(lambda l: l.display_type != 'cogs')
            dirty_recs = eligible_recs.filtered(dirty_fname)
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

        # Filter out deleted lines from `needed_before` to not recompute lines if not necessary or wanted
        line_ids = set(self.env['account.move.line'].browse(k['id'] for k in needed_before if 'id' in k).exists().ids)
        needed_before = {k: v for k, v in needed_before.items() if 'id' not in k or k['id'] in line_ids}

        # old key to new key for the same line
        inv_existing_before = {v: k for k, v in existing_before.items()}
        inv_existing_after = {v: k for k, v in existing_after.items()}
        before2after = {
            before: inv_existing_after[bline]
            for bline, before in inv_existing_before.items()
            if bline in inv_existing_after
        }

        if needed_after == needed_before:
            return

        to_delete = [
            line.id
            for key, line in existing_before.items()
            if key not in needed_after
            and key in existing_after
            and before2after[key] not in needed_after
        ]
        to_delete_set = set(to_delete)
        to_delete.extend(line.id
            for key, line in existing_after.items()
            if key not in needed_after and line.id not in to_delete_set
        )
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
            if changed('commercial_partner_id'):
                move.line_ids.partner_id = after[move]['commercial_partner_id']

    @contextmanager
    def _sync_dynamic_lines(self, container):
        with self._disable_recursion(container, 'skip_invoice_sync') as disabled:
            if disabled:
                yield
                return
            def update_containers():
                # Only invoice-like and journal entries in "auto tax mode" are synced
                tax_container['records'] = container['records'].filtered(lambda m: (m.is_invoice(True) or m.line_ids.tax_ids and not m.tax_cash_basis_origin_move_id))
                invoice_container['records'] = container['records'].filtered(lambda m: m.is_invoice(True))
                misc_container['records'] = container['records'].filtered(lambda m: m.move_type == 'entry' and not m.tax_cash_basis_origin_move_id)

            tax_container, invoice_container, misc_container = ({} for __ in range(3))
            update_containers()
            with ExitStack() as stack:
                stack.enter_context(self._sync_dynamic_line(
                    existing_key_fname='term_key',
                    needed_vals_fname='needed_terms',
                    needed_dirty_fname='needed_terms_dirty',
                    line_type='payment_term',
                    container=invoice_container,
                ))
                stack.enter_context(self._sync_unbalanced_lines(misc_container))
                stack.enter_context(self._sync_rounding_lines(invoice_container))
                stack.enter_context(self._sync_dynamic_line(
                    existing_key_fname='tax_key',
                    needed_vals_fname='line_ids.compute_all_tax',
                    needed_dirty_fname='line_ids.compute_all_tax_dirty',
                    line_type='tax',
                    container=tax_container,
                ))
                stack.enter_context(self._sync_dynamic_line(
                    existing_key_fname='epd_key',
                    needed_vals_fname='line_ids.epd_needed',
                    needed_dirty_fname='line_ids.epd_dirty',
                    line_type='epd',
                    container=invoice_container,
                ))
                stack.enter_context(self._sync_invoice(invoice_container))
                line_container = {'records': self.line_ids}
                with self.line_ids._sync_invoice(line_container):
                    yield
                    line_container['records'] = self.line_ids
                update_containers()

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def check_field_access_rights(self, operation, field_names):
        result = super().check_field_access_rights(operation, field_names)
        if not field_names:
            weirdos = ['needed_terms', 'quick_encoding_vals', 'payment_term_details']
            result = [fname for fname in result if fname not in weirdos]
        return result

    def copy_data(self, default=None):
        data_list = super().copy_data(default)
        for move, data in zip(self, data_list):
            if move.move_type in ('out_invoice', 'in_invoice'):
                data['line_ids'] = [
                    (command, _id, line_vals)
                    for command, _id, line_vals in data['line_ids']
                    if command == Command.CREATE
                ]
            elif move.move_type == 'entry':
                if 'partner_id' not in data:
                    data['partner_id'] = False
        if not self.journal_id.active and 'journal_id' in data_list:
            del default['journal_id']
        return data_list

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if (fields.Date.to_date(default.get('date')) or self.date) <= self.company_id._get_user_fiscal_lock_date():
            default['date'] = self.company_id._get_user_fiscal_lock_date() + timedelta(days=1)
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
        if vals.get('invoice_line_ids') and vals.get('line_ids'):
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

    def _stolen_move(self, vals):
        for command in vals.get('line_ids', ()):
            if command[0] == Command.LINK:
                yield self.env['account.move.line'].browse(command[1]).move_id.id
            if command[0] == Command.SET:
                yield from self.env['account.move.line'].browse(command[2]).move_id.ids

    @api.model_create_multi
    def create(self, vals_list):
        if any('state' in vals and vals.get('state') == 'posted' for vals in vals_list):
            raise UserError(_('You cannot create a move already in the posted state. Please create a draft move and post it after.'))
        container = {'records': self}
        with self._check_balanced(container):
            with self._sync_dynamic_lines(container):
                for vals in vals_list:
                    self._sanitize_vals(vals)
                stolen_moves = self.browse(set(move for vals in vals_list for move in self._stolen_move(vals)))
                moves = super().create(vals_list)
                container['records'] = moves | stolen_moves
            for move, vals in zip(moves, vals_list):
                if 'tax_totals' in vals:
                    move.tax_totals = vals['tax_totals']
        return moves

    def write(self, vals):
        if not vals:
            return True
        self._sanitize_vals(vals)
        for move in self:
            if (move.restrict_mode_hash_table and move.state == "posted" and set(vals).intersection(move._get_integrity_hash_fields())):
                raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(move._get_integrity_hash_fields()))
            if (move.restrict_mode_hash_table and move.inalterable_hash and 'inalterable_hash' in vals) or (move.secure_sequence_number and 'secure_sequence_number' in vals):
                raise UserError(_('You cannot overwrite the values ensuring the inalterability of the accounting.'))
            if (move.posted_before and 'journal_id' in vals and move.journal_id.id != vals['journal_id']):
                raise UserError(_('You cannot edit the journal of an account move if it has been posted once.'))
            if (move.name and move.name != '/' and move.sequence_number not in (0, 1) and 'journal_id' in vals and move.journal_id.id != vals['journal_id']):
                raise UserError(_('You cannot edit the journal of an account move if it already has a sequence number assigned.'))

            # You can't change the date or name of a move being inside a locked period.
            if move.state == "posted" and (
                    ('name' in vals and move.name != vals['name'])
                    or ('date' in vals and move.date != vals['date'])
            ):
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

        to_protect = []
        for fname in vals:
            field = self._fields[fname]
            if field.compute and not field.readonly:
                to_protect.append(field)
        stolen_moves = self.browse(set(move for move in self._stolen_move(vals)))
        container = {'records': self | stolen_moves}
        with self.env.protecting(to_protect, self), self._check_balanced(container):
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
                    self.flush_recordset()  # Ensure that the name is correctly computed before it is used to generate the hash
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

        if 'journal_id' in vals:
            self.line_ids._check_constrains_account_id_journal_id()

        return res

    def check_move_sequence_chain(self):
        return self.filtered(lambda move: move.name != '/')._is_end_of_seq_chain()

    @api.ondelete(at_uninstall=False)
    def _unlink_forbid_parts_of_chain(self):
        """ For a user with Billing/Bookkeeper rights, when the fidu mode is deactivated,
        moves with a sequence number can only be deleted if they are the last element of a chain of sequence.
        If they are not, deleting them would create a gap. If the user really wants to do this, he still can
        explicitly empty the 'name' field of the move; but we discourage that practice.
        If a user is a Billing Administrator/Accountant or if fidu mode is activated, we show a warning,
        but they can delete the moves even if it creates a sequence gap.
        """
        if not (
            self.user_has_groups('account.group_account_manager')
            or self.company_id.quick_edit_mode
            or self._context.get('force_delete')
            or self.check_move_sequence_chain()
        ):
            raise UserError(_(
                "You cannot delete this entry, as it has already consumed a sequence number and is not the last one in the chain. "
                "You should probably revert it instead."
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
        if field_name and not isinstance(field_name, list):
            field_name = [field_name]
        with self.env.protecting([self._fields[fname] for fname in field_name or []], self):
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

    def _must_check_constrains_date_sequence(self):
        # OVERRIDES sequence.mixin
        return not self.quick_edit_mode

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS account sequence.mixin
        self.ensure_one()
        if not self.date or not self.journal_id:
            return "WHERE FALSE", {}
        where_string = "WHERE journal_id = %(journal_id)s AND name != '/'"
        param = {'journal_id': self.journal_id.id}
        is_payment = self.payment_id or self._context.get('is_payment')

        if not relaxed:
            domain = [('journal_id', '=', self.journal_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]
            if self.journal_id.refund_sequence:
                refund_types = ('out_refund', 'in_refund')
                domain += [('move_type', 'in' if self.move_type in refund_types else 'not in', refund_types)]
            if self.journal_id.payment_sequence:
                domain += [('payment_id', '!=' if is_payment else '=', False)]
            reference_move_name = self.search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
            if not reference_move_name:
                reference_move_name = self.search(domain, order='date asc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(reference_move_name)
            date_start, date_end = self._get_sequence_date_range(sequence_number_reset)
            where_string += """ AND date BETWEEN %(date_start)s AND %(date_end)s"""
            param['date_start'] = date_start
            param['date_end'] = date_end
            if sequence_number_reset in ('year', 'year_range'):
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
            elif sequence_number_reset == 'never':
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

            if param.get('anti_regex') and not self.journal_id.sequence_override_regex:
                where_string += " AND sequence_prefix !~ %(anti_regex)s "

        if self.journal_id.refund_sequence:
            if self.move_type in ('out_refund', 'in_refund'):
                where_string += " AND move_type IN ('out_refund', 'in_refund') "
            else:
                where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "
        elif self.journal_id.payment_sequence:
            if is_payment:
                where_string += " AND payment_id IS NOT NULL "
            else:
                where_string += " AND payment_id IS NULL "

        return where_string, param

    def _get_starting_sequence(self):
        # EXTENDS account sequence.mixin
        self.ensure_one()
        is_payment = self.payment_id or self._context.get('is_payment')
        if self.journal_id.type in ['sale', 'bank', 'cash']:
            starting_sequence = "%s/%04d/00000" % (self.journal_id.code, self.date.year)
        else:
            starting_sequence = "%s/%04d/%02d/0000" % (self.journal_id.code, self.date.year, self.date.month)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        if self.journal_id.payment_sequence and is_payment:
            starting_sequence = "P" + starting_sequence
        return starting_sequence

    def _get_sequence_date_range(self, reset):
        if reset == 'year_range':
            company = self.company_id
            return date_utils.get_fiscal_year(self.date, day=company.fiscalyear_last_day, month=int(company.fiscalyear_last_month))
        return super()._get_sequence_date_range(reset)

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
        if not partner_id:
            return 0, False, False
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
                   AND aml.display_type = 'product'
                      {where_internal_group}
               GROUP BY account.id, account.code, aml.id
               ) AS foo
            GROUP BY foo.account_id, foo.code, foo.taxes
            ORDER BY COUNT(foo.id) DESC, foo.code
            LIMIT 1
        """, [partner_id, company_id])
        return self._cr.fetchone() or (None, None, None)

    def _get_quick_edit_suggestions(self):
        """
        Returns a dictionnary containing the suggested values when creating a new
        line with the quick_edit_total_amount set. We will compute the price_unit
        that has to be set with the correct that in order to match this total amount.
        If the vendor/customer is set, we will suggest the most frequently used account
        for that partner as the default one, otherwise the default of the journal.
        """
        self.ensure_one()
        if not self.quick_edit_mode or not self.quick_edit_total_amount:
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
            if self.is_sale_document(include_receipts=True):
                taxes = self.journal_id.default_account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'sale')
            else:
                taxes = self.journal_id.default_account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'purchase')
            if not taxes:
                taxes = (
                    self.journal_id.company_id.account_sale_tax_id
                    if self.journal_id.type == 'sale' else
                    self.journal_id.company_id.account_purchase_tax_id
                )
            taxes = self.fiscal_position_id.map_tax(taxes)

        # When a payment term has an early payment discount and the company's epd computation is set to 'mixed', recomputing
        # the untaxed amount should take in consideration the discount percentage otherwise we'd get a wrong value.
        # Since in a payment term we can have multiple lines with multiple discounts, handling all cases can get
        # complicated. For this we check that we have only one line with one discount and handle only this case.
        # We also check that we have one percentage tax for the same reason.
        # In one example: let's say: base = 100, discount = 2%, tax = 21%
        # the total will be calculated as: total = base + (base * (1 - discount)) * tax
        # If we manipulate the equation to get the base from the total, we'll have base = total / ((1 - discount) * tax + 1)
        term_lines = self.invoice_payment_term_id.line_ids
        discount_percentage = term_lines.discount_percentage if len(term_lines) == 1 else 0
        remaining_amount = self.quick_edit_total_amount - self.tax_totals['amount_total']

        if (
                discount_percentage
                and self.company_id.early_pay_discount_computation == 'mixed'
                and len(taxes) == 1
                and taxes.amount_type == 'percent'
        ):
            price_untaxed = self.currency_id.round(
                remaining_amount / (((1.0 - discount_percentage / 100.0) * (taxes.amount / 100.0)) + 1.0))
        else:
            price_untaxed = taxes.with_context(force_price_include=True).compute_all(remaining_amount)['total_excluded']
        return {'account_id': account_id, 'tax_ids': taxes.ids, 'price_unit': price_untaxed}

    @api.onchange('quick_edit_mode', 'journal_id', 'company_id')
    def _quick_edit_mode_suggest_invoice_date(self):
        """Suggest the Customer Invoice/Vendor Bill date based on previous invoice and lock dates"""
        for record in self:
            if record.quick_edit_mode and not record.invoice_date:
                invoice_date = fields.Date.context_today(self)
                prev_move = self.search([('state', '=', 'posted'),
                                         ('journal_id', '=', record.journal_id.id),
                                         ('company_id', '=', record.company_id.id),
                                         ('invoice_date', '!=', False)],
                                        limit=1)
                if prev_move:
                    invoice_date = self._get_accounting_date(prev_move.invoice_date, False)
                record.invoice_date = invoice_date

    @api.onchange('quick_edit_total_amount', 'partner_id')
    def _onchange_quick_edit_total_amount(self):
        """
        Creates a new line with the suggested values (for the account, the price_unit,
        and the tax) such that the total amount matches the quick total amount.
        """
        if (
            not self.quick_edit_total_amount
            or not self.quick_edit_mode
            or len(self.invoice_line_ids) > 0
        ):
            return
        suggestions = self.quick_encoding_vals
        self.invoice_line_ids = [Command.clear()]
        self.invoice_line_ids += self.env['account.move.line'].new({
            'partner_id': self.partner_id,
            'account_id': suggestions['account_id'],
            'currency_id': self.currency_id.id,
            'price_unit': suggestions['price_unit'],
            'tax_ids': [Command.set(suggestions['tax_ids'])],
        })
        self._check_total_amount(self.quick_edit_total_amount)

    @api.onchange('invoice_line_ids')
    def _onchange_quick_edit_line_ids(self):
        quick_encode_suggestion = self.env.context.get('quick_encoding_vals')
        if (
            not self.quick_edit_total_amount
            or not self.quick_edit_mode
            or not self.invoice_line_ids
            or not quick_encode_suggestion
            or not quick_encode_suggestion['price_unit'] == self.invoice_line_ids[-1].price_unit
        ):
            return
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
            if _('Untaxed Amount') in totals['groups_by_subtotal']:
                totals['groups_by_subtotal'][_('Untaxed Amount')][0]['tax_group_amount'] += tax_amount_rounding_error
                totals['amount_total'] = amount_total
                self.tax_totals = totals

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------

    def _get_integrity_hash_fields(self):
        # Use the latest hash version by default, but keep the old one for backward compatibility when generating the integrity report.
        hash_version = self._context.get('hash_version', MAX_HASH_VERSION)
        if hash_version == 1:
            return ['date', 'journal_id', 'company_id']
        elif hash_version in (2, 3):
            return ['name', 'date', 'journal_id', 'company_id']
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

    def _get_integrity_hash_fields_and_subfields(self):
        return self._get_integrity_hash_fields() + [f'line_ids.{subfield}' for subfield in self.line_ids._get_integrity_hash_fields()]

    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on journal entries when they get posted"""
        self.ensure_one()
        #get the only one exact previous move in the securisation sequence
        prev_move = self.sudo().search([('state', '=', 'posted'),
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

    @api.depends(lambda self: self._get_integrity_hash_fields_and_subfields())
    @api.depends_context('hash_version')
    def _compute_string_to_hash(self):
        def _getattrstring(obj, field_str):
            hash_version = self._context.get('hash_version', MAX_HASH_VERSION)
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            if obj._fields[field_str].type == 'monetary' and hash_version >= 3:
                return float_repr(field_value, obj.currency_id.decimal_places)
            return str(field_value)

        for move in self:
            values = {}
            for field in move._get_integrity_hash_fields():
                values[field] = _getattrstring(move, field)

            for line in move.line_ids:
                for field in line._get_integrity_hash_fields():
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

    def _prepare_invoice_aggregated_taxes(self, filter_invl_to_apply=None, filter_tax_values_to_apply=None, grouping_key_generator=None):
        self.ensure_one()

        base_lines = [
            x._convert_to_tax_base_line_dict()
            for x in self.line_ids.filtered(lambda x: x.display_type == 'product' and (not filter_invl_to_apply or filter_invl_to_apply(x)))
        ]

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self.env['account.tax']._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        # Handle manually changed tax amounts (via quick-edit or journal entry manipulation):
        # For each tax repartition line we compute the difference between the following 2 amounts
        #     * Manual tax amount:
        #       The sum of the amounts on the tax lines belonging to the tax repartition line.
        #       These amounts may have been manually changed.
        #     * Computed tax amount:
        #       The sum of the amounts on the items in 'tax_values_list' in 'to_process' belonging to the tax repartition line.
        # This difference is then distributed evenly across the 'tax_values_list' in 'to_process'
        # such that the manual and computed tax amounts match.
        # The updated tax information is later used by '_aggregate_taxes' to compute the right tax amounts (consistently on all levels).
        tax_lines = self.line_ids.filtered(lambda x: x.display_type == 'tax')
        sign = -1 if self.is_inbound(include_receipts=True) else 1

        # Collect the tax_amount_currency/balance from tax lines.
        current_tax_amount_per_rep_line = {}
        for tax_line in tax_lines:
            tax_rep_amounts = current_tax_amount_per_rep_line.setdefault(tax_line.tax_repartition_line_id.id, {
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
            })
            tax_rep_amounts['tax_amount_currency'] += sign * tax_line.amount_currency
            tax_rep_amounts['tax_amount'] += sign * tax_line.balance

        # Collect the computed tax_amount_currency/tax_amount from the taxes computation.
        tax_details_per_rep_line = {}
        for _base_line, _to_update_vals, tax_values_list in to_process:
            for tax_values in tax_values_list:
                tax_rep_id = tax_values['tax_repartition_line_id']
                tax_rep_amounts = tax_details_per_rep_line.setdefault(tax_rep_id, {
                    'tax_amount_currency': 0.0,
                    'tax_amount': 0.0,
                    'distribute_on': [],
                })
                tax_rep_amounts['tax_amount_currency'] += tax_values['tax_amount_currency']
                tax_rep_amounts['tax_amount'] += tax_values['tax_amount']
                tax_rep_amounts['distribute_on'].append(tax_values)

        # Dispatch the delta on tax_values.
        for key, currency in (('tax_amount_currency', self.currency_id), ('tax_amount', self.company_currency_id)):
            for tax_rep_id, computed_tax_rep_amounts in tax_details_per_rep_line.items():
                current_tax_rep_amounts = current_tax_amount_per_rep_line.get(tax_rep_id, computed_tax_rep_amounts)
                diff = current_tax_rep_amounts[key] - computed_tax_rep_amounts[key]
                abs_diff = abs(diff)

                if currency.is_zero(abs_diff):
                    continue

                diff_sign = -1 if diff < 0 else 1
                nb_error = math.ceil(abs_diff / currency.rounding)
                nb_cents_per_tax_values = math.floor(nb_error / len(computed_tax_rep_amounts['distribute_on']))
                nb_extra_cent = nb_error % len(computed_tax_rep_amounts['distribute_on'])
                for tax_values in computed_tax_rep_amounts['distribute_on']:

                    if currency.is_zero(abs_diff):
                        break

                    nb_amount_curr_cent = nb_cents_per_tax_values
                    if nb_extra_cent:
                        nb_amount_curr_cent += 1
                        nb_extra_cent -= 1

                    # We can have more than one cent to distribute on a single tax_values.
                    abs_delta_to_add = min(abs_diff, currency.rounding * nb_amount_curr_cent)
                    tax_values[key] += diff_sign * abs_delta_to_add
                    abs_diff -= abs_delta_to_add

        return self.env['account.tax']._aggregate_taxes(
            to_process,
            filter_tax_values_to_apply=filter_tax_values_to_apply,
            grouping_key_generator=grouping_key_generator,
        )

    def _get_invoice_counterpart_amls_for_early_payment_discount_per_payment_term_line(self):
        """ Helper to get the values to create the counterpart journal items on the register payment wizard and the
        bank reconciliation widget in case of an early payment discount. When the early payment discount computation
        is included, we need to compute the base amounts / tax amounts for each receivable / payable but we need to
        take care about the rounding issues. For others computations, we need to balance the discount you get.

        :return: A list of values to create the counterpart journal items split in 3 categories:
            * term_lines:   The journal items containing the discount amounts for each receivable line when the
                            discount computation is excluded / mixed.
            * tax_lines:    The journal items acting as tax lines when the discount computation is included.
            * base_lines:   The journal items acting as base for tax lines when the discount computation is included.
        """
        self.ensure_one()

        def grouping_key_generator(base_line, tax_values):
            return self.env['account.tax']._get_generation_dict_from_base_line(base_line, tax_values)

        def inverse_tax_rep(tax_rep):
            tax = tax_rep.tax_id
            index = list(tax.invoice_repartition_line_ids).index(tax_rep)
            return tax.refund_repartition_line_ids[index]

        # Get the current tax amounts in the current invoice.
        tax_amounts = {
            inverse_tax_rep(line.tax_repartition_line_id).id: {
                'amount_currency': line.amount_currency,
                'balance': line.balance,
            }
            for line in self.line_ids.filtered(lambda x: x.display_type == 'tax')
        }

        product_lines = self.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [
            {
                **x._convert_to_tax_base_line_dict(),
                'is_refund': True,
            }
            for x in product_lines
        ]
        for base_line in base_lines:
            base_line['taxes'] = base_line['taxes'].filtered(lambda t: t.amount_type != 'fixed')

        if self.is_inbound(include_receipts=True):
            cash_discount_account = self.company_id.account_journal_early_pay_discount_loss_account_id
        else:
            cash_discount_account = self.company_id.account_journal_early_pay_discount_gain_account_id

        res = {
            'term_lines': defaultdict(lambda: {}),
            'tax_lines': defaultdict(lambda: {}),
            'base_lines': defaultdict(lambda: {}),
        }

        early_pay_discount_computation = self.company_id.early_pay_discount_computation

        base_per_percentage = {}
        tax_computation_per_percentage = {}
        for aml in self.line_ids.filtered(lambda x: x.display_type == 'payment_term'):
            if not aml.discount_percentage:
                continue

            term_amount_currency = aml.amount_currency - aml.discount_amount_currency
            term_balance = aml.balance - aml.discount_balance

            if early_pay_discount_computation == 'included' and product_lines.tax_ids:

                # Compute the amounts for each percentage.
                if aml.discount_percentage not in tax_computation_per_percentage:

                    # Compute the base amounts.
                    base_per_percentage[aml.discount_percentage] = resulting_delta_base_details = {}
                    to_process = []
                    for base_line in base_lines:
                        invoice_line = base_line['record']
                        to_update_vals, tax_values_list = self.env['account.tax']._compute_taxes_for_single_line(
                            base_line,
                            early_pay_discount_computation=early_pay_discount_computation,
                            early_pay_discount_percentage=aml.discount_percentage,
                        )
                        to_process.append((base_line, to_update_vals, tax_values_list))

                        grouping_dict = {
                            'tax_ids': [Command.set(base_line['taxes'].ids)],
                            'tax_tag_ids': to_update_vals['tax_tag_ids'],
                            'partner_id': base_line['partner'].id,
                            'currency_id': base_line['currency'].id,
                            'account_id': cash_discount_account.id,
                            'analytic_distribution': base_line['analytic_distribution'],
                        }
                        base_detail = resulting_delta_base_details.setdefault(frozendict(grouping_dict), {
                            'balance': 0.0,
                            'amount_currency': 0.0,
                        })

                        amount_currency = self.currency_id\
                            .round(self.direction_sign * to_update_vals['price_subtotal'] - invoice_line.amount_currency)
                        balance = self.company_currency_id\
                            .round(amount_currency / base_line['rate'])

                        base_detail['balance'] += balance
                        base_detail['amount_currency'] += amount_currency

                    # Compute the tax amounts.
                    tax_details_with_epd = self.env['account.tax']._aggregate_taxes(
                        to_process,
                        grouping_key_generator=grouping_key_generator,
                    )

                    tax_computation_per_percentage[aml.discount_percentage] = resulting_delta_tax_details = {}
                    for tax_detail in tax_details_with_epd['tax_details'].values():
                        tax_amount_without_epd = tax_amounts.get(tax_detail['tax_repartition_line_id'])
                        if not tax_amount_without_epd:
                            continue

                        tax_amount_currency = self.currency_id\
                            .round(self.direction_sign * tax_detail['tax_amount_currency'] - tax_amount_without_epd['amount_currency'])
                        tax_amount = self.company_currency_id\
                            .round(self.direction_sign * tax_detail['tax_amount'] - tax_amount_without_epd['balance'])

                        if self.currency_id.is_zero(tax_amount_currency) and self.company_currency_id.is_zero(tax_amount):
                            continue

                        resulting_delta_tax_details[tax_detail['tax_repartition_line_id']] = {
                            **tax_detail,
                            'amount_currency': tax_amount_currency,
                            'balance': tax_amount,
                        }

                # Multiply each amount by the percentage paid by the current payment term line.
                percentage_paid = abs(aml.amount_residual_currency / self.amount_total)
                for tax_detail in tax_computation_per_percentage[aml.discount_percentage].values():
                    tax_rep = self.env['account.tax.repartition.line'].browse(tax_detail['tax_repartition_line_id'])
                    tax = tax_rep.tax_id

                    grouping_dict = {
                        'account_id': tax_detail['account_id'],
                        'partner_id': tax_detail['partner_id'],
                        'currency_id': tax_detail['currency_id'],
                        'analytic_distribution': tax_detail['analytic_distribution'],
                        'tax_repartition_line_id': tax_rep.id,
                        'tax_ids': tax_detail['tax_ids'],
                        'tax_tag_ids': tax_detail['tax_tag_ids'],
                        'group_tax_id': tax_detail['tax_id'] if tax_detail['tax_id'] != tax.id else None,
                    }

                    res['tax_lines'][aml][frozendict(grouping_dict)] = {
                        'name': _("Early Payment Discount (%s)", tax.name),
                        'amount_currency': aml.currency_id.round(tax_detail['amount_currency'] * percentage_paid),
                        'balance': aml.company_currency_id.round(tax_detail['balance'] * percentage_paid),
                    }

                for grouping_dict, base_detail in base_per_percentage[aml.discount_percentage].items():
                    res['base_lines'][aml][grouping_dict] = {
                        'name': _("Early Payment Discount"),
                        'amount_currency': aml.currency_id.round(base_detail['amount_currency'] * percentage_paid),
                        'balance': aml.company_currency_id.round(base_detail['balance'] * percentage_paid),
                    }

                # Fix the rounding issue if any.
                delta_amount_currency = term_amount_currency \
                                        - sum(x['amount_currency'] for x in res['base_lines'][aml].values()) \
                                        - sum(x['amount_currency'] for x in res['tax_lines'][aml].values())
                delta_balance = term_balance \
                                - sum(x['balance'] for x in res['base_lines'][aml].values()) \
                                - sum(x['balance'] for x in res['tax_lines'][aml].values())

                last_tax_line = (list(res['tax_lines'][aml].values()) or list(res['base_lines'][aml].values()))[-1]
                last_tax_line['amount_currency'] += delta_amount_currency
                last_tax_line['balance'] += delta_balance

            else:
                grouping_dict = {'account_id': cash_discount_account.id}

                res['term_lines'][aml][frozendict(grouping_dict)] = {
                    'name': _("Early Payment Discount"),
                    'partner_id': aml.partner_id.id,
                    'currency_id': aml.currency_id.id,
                    'amount_currency': term_amount_currency,
                    'balance': term_balance,
                }

        return res

    @api.model
    def _get_invoice_counterpart_amls_for_early_payment_discount(self, aml_values_list, open_balance):
        """ Helper to get the values to create the counterpart journal items on the register payment wizard and the
        bank reconciliation widget in case of an early payment discount by taking care of the payment term lines we
        are matching and the exchange difference in case of multi-currencies.

        :param aml_values_list: A list of dictionaries containing:
            * aml:              The payment term line we match.
            * amount_currency:  The matched amount_currency for this line.
            * balance:          The matched balance for this line (could be different in case of multi-currencies).
        :param open_balance:    The current open balance to be covered by the early payment discount.
        :return: A list of values to create the counterpart journal items split in 3 categories:
            * term_lines:       The journal items containing the discount amounts for each receivable line when the
                                discount computation is excluded / mixed.
            * tax_lines:        The journal items acting as tax lines when the discount computation is included.
            * base_lines:       The journal items acting as base for tax lines when the discount computation is included.
            * exchange_lines:   The journal items representing the exchange differences in case of multi-currencies.
        """
        res = {
            'base_lines': {},
            'tax_lines': {},
            'term_lines': {},
            'exchange_lines': {},
        }

        res_per_invoice = {}
        for aml_values in aml_values_list:
            aml = aml_values['aml']
            invoice = aml.move_id

            if invoice not in res_per_invoice:
                res_per_invoice[invoice] = invoice._get_invoice_counterpart_amls_for_early_payment_discount_per_payment_term_line()

            for key in ('base_lines', 'tax_lines', 'term_lines'):
                for grouping_dict, vals in res_per_invoice[invoice][key][aml].items():
                    line_vals = res[key].setdefault(grouping_dict, {
                        **vals,
                        'amount_currency': 0.0,
                        'balance': 0.0,
                    })
                    line_vals['amount_currency'] += vals['amount_currency']
                    line_vals['balance'] += vals['balance']

                    # Track the balance to handle the exchange difference.
                    open_balance -= vals['balance']

        exchange_diff_sign = aml.company_currency_id.compare_amounts(open_balance, 0.0)
        if exchange_diff_sign != 0.0:

            if exchange_diff_sign > 0.0:
                exchange_line_account = aml.company_id.expense_currency_exchange_account_id
            else:
                exchange_line_account = aml.company_id.income_currency_exchange_account_id

            grouping_dict = {
                'account_id': exchange_line_account.id,
                'currency_id': aml.currency_id.id,
                'partner_id': aml.partner_id.id,
            }
            line_vals = res['exchange_lines'].setdefault(frozendict(grouping_dict), {
                **grouping_dict,
                'name': _("Early Payment Discount (Exchange Difference)"),
                'amount_currency': 0.0,
                'balance': 0.0,
            })
            line_vals['balance'] += open_balance

        return {
            key: [
                {
                    **grouping_dict,
                    **vals,
                }
                for grouping_dict, vals in mapping.items()
            ]
            for key, mapping in res.items()
        }

    def _affect_tax_report(self):
        return any(line._affect_tax_report() for line in (self.line_ids | self.invoice_line_ids))

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
            if self.env.context.get('input_full_display_name'):
                if self.partner_id:
                    name += f', {self.partner_id.name}'
                if self.date:
                    name += f', {format_date(self.env, self.date)}'
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

        self.env['account.partial.reconcile'].flush_model([
            'credit_amount_currency', 'credit_move_id', 'debit_amount_currency',
            'debit_move_id', 'exchange_move_id',
        ])
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
            self.env['account.move.line'].flush_model(['move_id'])
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
                'partner_id': move.partner_id.id,
            })
            reverse_moves += move.with_context(
                move_reverse_cancel=cancel,
                include_business_fields=True,
                skip_invoice_sync=move.move_type == 'entry',
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
            if (
                invoice.quick_edit_mode
                and invoice.quick_edit_total_amount
                and invoice.currency_id.compare_amounts(invoice.quick_edit_total_amount, invoice.amount_total) != 0
            ):
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

        for move in self:
            if move.state == 'posted':
                raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
            if not move.line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
                raise UserError(_('You need to add a line before posting.'))
            if not soft and move.auto_post != 'no' and move.date > fields.Date.context_today(self):
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

            if move.line_ids.account_id.filtered(lambda account: account.deprecated):
                raise UserError(_("A line of this move is using a deprecated account, you cannot post it."))

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
            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report)

        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        to_post.line_ids._create_analytic_lines()

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

        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        for invoice in to_post:
            invoice.message_subscribe([
                p.id
                for p in [invoice.partner_id]
                if p not in invoice.sudo().message_partner_ids
            ])

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
            elif invoice.move_type == 'entry':
                sale_amls = invoice.line_ids.filtered(lambda line: line.partner_id and line.account_id.account_type == 'asset_receivable')
                for partner in sale_amls.mapped('partner_id'):
                    customer_count[partner] += 1
                purchase_amls = invoice.line_ids.filtered(lambda line: line.partner_id and line.account_id.account_type == 'liability_payable')
                for partner in purchase_amls.mapped('partner_id'):
                    supplier_count[partner] += 1
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

        # Trigger action for paid invoices if amount is zero
        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        )._invoice_paid_hook()

        return to_post

    def _find_and_set_purchase_orders(self, po_references, partner_id, amount_total, prefer_purchase_line=False, timeout=10):
        # hook to be used with purchase, so that vendor bills are sync/autocompleted with purchase orders
        self.ensure_one()

    def _link_invoice_origin_to_purchase_orders(self, timeout=10):
        for move in self.filtered(lambda m: m.move_type in self.get_purchase_types()):
            references = [move.invoice_origin] if move.invoice_origin else []
            move._find_and_set_purchase_orders(references, move.partner_id.id, move.amount_total, timeout=timeout)
        return self

    # -------------------------------------------------------------------------
    # PUBLIC ACTIONS
    # -------------------------------------------------------------------------

    def open_reconcile_view(self):
        return self.line_ids.open_reconcile_view()

    def action_open_business_doc(self):
        self.ensure_one()
        if self.payment_id:
            name = _("Payment")
            res_model = 'account.payment'
            res_id = self.payment_id.id
        elif self.statement_line_id:
            name = _("Bank Transaction")
            res_model = 'account.bank.statement.line'
            res_id = self.statement_line_id.id
        else:
            name = _("Journal Entry")
            res_model = 'account.move'
            res_id = self.id

        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': res_model,
            'res_id': res_id,
            'target': 'current',
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

    def open_duplicated_ref_bill_view(self):
        moves = self + self.duplicated_ref_ids
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_line_form")
        action['domain'] = [('id', 'in', moves.ids)]
        return action

    def action_switch_invoice_into_refund_credit_note(self):
        for move in self:
            if move.posted_before:
                raise ValidationError(_("You cannot switch the type of a posted document."))
            if move.move_type == 'entry':
                raise ValidationError(_("This action isn't available for this document."))
            in_out, old_move_type = move.move_type.split('_')
            new_move_type = f"{in_out}_{'invoice' if old_move_type == 'refund' else 'refund'}"
            move.name = False
            move.write({
                'move_type': new_move_type,
                'partner_bank_id': False,
                'currency_id': move.currency_id.id,
            })
            if move.amount_total < 0:
                move.write({
                    'line_ids': [
                        Command.update(line.id, {'quantity': -line.quantity})
                        for line in move.line_ids
                        if line.display_type == 'product'
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
                'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
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
            default_email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True,
            active_ids=self.ids,
        )

        report_action = {
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

        if self.env.is_admin() and not self.env.company.external_report_layout_id and not self.env.context.get('discard_logo_check'):
            return self.env['ir.actions.report']._action_configure_external_report_layout(report_action)

        return report_action

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
        exchange_move_ids = set()
        if self:
            self.env['account.full.reconcile'].flush_model(['exchange_move_id'])
            self.env['account.partial.reconcile'].flush_model(['exchange_move_id'])
            self._cr.execute(
                """
                    SELECT DISTINCT sub.exchange_move_id
                    FROM (
                        SELECT exchange_move_id
                        FROM account_full_reconcile
                        WHERE exchange_move_id IN %s

                        UNION ALL

                        SELECT exchange_move_id
                        FROM account_partial_reconcile
                        WHERE exchange_move_id IN %s
                    ) AS sub
                """,
                [tuple(self.ids), tuple(self.ids)],
            )
            exchange_move_ids = set([row[0] for row in self._cr.fetchall()])

        for move in self:
            if move.id in exchange_move_ids:
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

    def _notify_get_recipients_groups(self, msg_vals=None):
        groups = super()._notify_get_recipients_groups(msg_vals)
        self.ensure_one()

        if self.move_type != 'entry':
            local_msg_vals = dict(msg_vals or {})
            self._portal_ensure_token()
            access_link = self._notify_get_action_link('view', **local_msg_vals, access_token=self.access_token)

            # Create a new group for partners that have been manually added as recipients.
            # Those partners should have access to the invoice.
            button_access = {'url': access_link} if access_link else {}
            recipient_group = (
                'additional_intended_recipient',
                lambda pdata: pdata['id'] in local_msg_vals.get('partner_ids', []) and pdata['id'] != self.partner_id.id,
                {
                    'has_button_access': True,
                    'button_access': button_access,
                }
            )
            groups.insert(0, recipient_group)

        return groups

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
        moves = self.search([
            ('state', '=', 'draft'),
            ('date', '<=', fields.Date.context_today(self)),
            ('auto_post', '!=', 'no'),
            ('to_check', '=', False),
        ], limit=100)

        try:  # try posting in batch
            with self.env.cr.savepoint():
                moves._post()
        except UserError:  # if at least one move cannot be posted, handle moves one by one
            for move in moves:
                try:
                    with self.env.cr.savepoint():
                        move._post()
                except UserError as e:
                    move.to_check = True
                    msg = _('The move could not be posted for the following reason: %(error_message)s', error_message=e)
                    move.message_post(body=msg, message_type='comment')

        if len(moves) == 100:  # assumes there are more whenever search hits limit
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
        today = fields.Date.context_today(self)
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

    def _get_lock_date_message(self, invoice_date, has_tax):
        """Get a message describing the latest lock date affecting the specified date.
        :param invoice_date: The date to be checked
        :param has_tax: If any taxes are involved in the lines of the invoice
        :return: a message describing the latest lock date affecting this move and the date it will be
                 accounted on if posted, or False if no lock dates affect this move.
        """
        lock_dates = self._get_violated_lock_dates(invoice_date, has_tax)
        if lock_dates:
            invoice_date = self._get_accounting_date(invoice_date, has_tax)
            lock_date, lock_type = lock_dates[-1]
            tax_lock_date_message = _(
                "The date is being set prior to the %(lock_type)s lock date %(lock_date)s. "
                "The Journal Entry will be accounted on %(invoice_date)s upon posting.",
                lock_type=lock_type,
                lock_date=format_date(self.env, lock_date),
                invoice_date=format_date(self.env, invoice_date))
            return tax_lock_date_message
        return False

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

    def _generate_qr_code(self, silent_errors=False):
        """ Generates and returns a QR-code generation URL for this invoice,
        raising an error message if something is misconfigured.

        The chosen QR generation method is the one set in qr_method field if there is one,
        or the first eligible one found. If this search had to be performed and
        and eligible method was found, qr_method field is set to this method before
        returning the URL. If no eligible QR method could be found, we return None.
        """
        self.ensure_one()

        if not self.display_qr_code:
            return None

        qr_code_method = self.qr_code_method
        if qr_code_method:
            # If the user set a qr code generator manually, we check that we can use it
            if not self.partner_bank_id._eligible_for_qr_code(self.qr_code_method, self.partner_id, self.currency_id):
                raise UserError(_("The chosen QR-code type is not eligible for this invoice."))
        else:
            # Else we find one that's eligible and assign it to the invoice
            for candidate_method, _candidate_name in self.env['res.partner.bank'].get_available_qr_methods_in_sequence():
                if self.partner_bank_id._eligible_for_qr_code(candidate_method, self.partner_id, self.currency_id, raises_error=False):
                    qr_code_method = candidate_method
                    break

        if not qr_code_method:
            # No eligible method could be found; we can't generate the QR-code
            return None

        unstruct_ref = self.ref if self.ref else self.name
        rslt = self.partner_bank_id.build_qr_code_base64(self.amount_residual, unstruct_ref, self.payment_reference, self.currency_id, self.partner_id, qr_code_method, silent_errors=silent_errors)

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
        with self._disable_recursion({'records': self}, 'ignore_discount_precision'):
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
        """Apply the context key to all environments inside this context manager.

        If this context key is already set on the recordsets, yield `True`.
        The recordsets modified are the one in the container, as well as all the
        `self` recordsets of the calling stack.
        This more or less gives the wanted context to all records inside of the
        context manager.

        :param container: A mutable dict that needs to at least contain the key
                          `records`. Can contain other items if changing the env
                          is needed.
        :param key: The context key to apply to the recordsets.
        :param default: the default value of the context key, if it isn't defined
                        yet in the context
        :param target: the value of the context key meaning that we shouldn't
                       recurse
        :return: True iff we should just exit the context manager
        """

        disabled = container['records'].env.context.get(key, default) == target
        previous_values = {}
        previous_envs = set(self.env.transaction.envs)
        if not disabled:  # it wasn't disabled yet, disable it now
            for env in self.env.transaction.envs:
                previous_values[env] = env.context.get(key, EMPTY)
                env.context = frozendict({**env.context, key: target})
        try:
            yield disabled
        finally:
            for env, val in previous_values.items():
                if val != EMPTY:
                    env.context = frozendict({**env.context, key: val})
                else:
                    env.context = frozendict({k: v for k, v in env.context.items() if k != key})
            for env in (self.env.transaction.envs - previous_envs):
                if key in env.context:
                    env.context = frozendict({k: v for k, v in env.context.items() if k != key})

    # ------------------------------------------------------------
    # MAIL.THREAD
    # ------------------------------------------------------------

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # EXTENDS mail mail.thread
        # Add custom behavior when receiving a new invoice through the mail's gateway.
        if (custom_values or {}).get('move_type', 'entry') not in ('out_invoice', 'in_invoice'):
            return super().message_new(msg_dict, custom_values=custom_values)

        company = self.env['res.company'].browse(custom_values['company_id']) if custom_values.get('company_id') else self.env.company

        def is_internal_partner(partner):
            # Helper to know if the partner is an internal one.
            return partner == company.partner_id or (partner.user_ids and all(user._is_internal() for user in partner.user_ids))

        extra_domain = False
        if custom_values.get('company_id'):
            extra_domain = ['|', ('company_id', '=', custom_values['company_id']), ('company_id', '=', False)]

        # Search for partners in copy.
        cc_mail_addresses = email_split(msg_dict.get('cc', ''))
        followers = [partner for partner in self._mail_find_partner_from_emails(cc_mail_addresses, extra_domain=extra_domain) if partner]

        # Search for partner that sent the mail.
        from_mail_addresses = email_split(msg_dict.get('from', ''))
        senders = partners = [partner for partner in self._mail_find_partner_from_emails(from_mail_addresses, extra_domain=extra_domain) if partner]

        # Search for partners using the user.
        if not senders:
            senders = partners = list(self._mail_search_on_user(from_mail_addresses))

        if partners:
            # Check we are not in the case when an internal user forwarded the mail manually.
            if is_internal_partner(partners[0]):
                # Search for partners in the mail's body.
                body_mail_addresses = set(email_re.findall(msg_dict.get('body')))
                partners = [
                    partner
                    for partner in self._mail_find_partner_from_emails(body_mail_addresses, extra_domain=extra_domain)
                    if not is_internal_partner(partner) and partner.company_id.id in (False, company.id)
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

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        # EXTENDS mail mail.thread
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        subtitles = [render_context['record'].name]
        if self.invoice_date_due and self.payment_state not in ('in_payment', 'paid'):
            subtitles.append(_('%(amount)s due\N{NO-BREAK SPACE}%(date)s',
                           amount=format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang')),
                           date=format_date(self.env, self.invoice_date_due, date_format='short', lang_code=render_context.get('lang'))
                          ))
        else:
            subtitles.append(format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang')))
        render_context['subtitles'] = subtitles
        return render_context

    # -------------------------------------------------------------------------
    # TOOLING
    # -------------------------------------------------------------------------

    def _conditional_add_to_compute(self, fname, condition):
        field = self._fields[fname]
        to_reset = self.filtered(lambda move:
            condition(move)
            and not self.env.is_protected(field, move._origin)
            and (move._origin or not move[fname])
        )
        to_reset.invalidate_recordset([fname])
        self.env.add_to_compute(field, to_reset)

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

    @api.model
    def get_invoice_localisation_fields_required_to_invoice(self, country_id):
        """ Returns the list of fields that needs to be filled when creating an invoice for the selected country.
        This is required for some flows that would allow a user to request an invoice from the portal.
        Using these, we can get their information and dynamically create form inputs based for the fields required legally for the company country_id.
        The returned fields must be of type ir.model.fields in order to handle translations

        :param country_id: The country for which we want the fields.
        :return: an array of ir.model.fields for which the user should provide values.
        """
<<<<<<< HEAD
        return []
||||||| parent of a2822764d045 (temp)
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
            line.debit = balance if balance > 0.0 else 0.0
            line.credit = -balance if balance < 0.0 else 0.0

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

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if res.get('cumulated_balance'):
            res['cumulated_balance']['exportable'] = False
        return res

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

    @api.depends('debit', 'credit', 'amount_currency', 'account_id', 'currency_id', 'parent_state', 'company_id',
                 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if line.id and (line.account_id.reconcile or line.account_id.internal_type == 'liquidity'):
                reconciled_balance = sum(line.matched_credit_ids.mapped('amount')) \
                                     - sum(line.matched_debit_ids.mapped('amount'))
                reconciled_amount_currency = sum(line.matched_credit_ids.mapped('debit_amount_currency'))\
                                             - sum(line.matched_debit_ids.mapped('credit_amount_currency'))

                line.amount_residual = line.balance - reconciled_balance

                if line.currency_id:
                    line.amount_residual_currency = line.amount_currency - reconciled_amount_currency
                else:
                    line.amount_residual_currency = 0.0

                line.reconciled = (
                    line.company_currency_id.is_zero(line.amount_residual)
                    and (not line.currency_id or line.currency_id.is_zero(line.amount_residual_currency))
                    and (line.matched_debit_ids or line.matched_credit_ids)
                )
            else:
                # Must not have any reconciliation since the line is not eligible for that.
                line.amount_residual = 0.0
                line.amount_residual_currency = 0.0
                line.reconciled = False

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

                if record.tax_ids and record.move_id.reversed_entry_id:
                    is_refund = not is_refund

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

            failed_check = False
            if journal.type_control_ids or journal.account_control_ids:
                failed_check = True
                if journal.type_control_ids:
                    failed_check = account.user_type_id not in journal.type_control_ids
                if failed_check and journal.account_control_ids:
                    failed_check = account not in journal.account_control_ids

            if failed_check:
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

    @api.constrains('product_uom_id')
    def _check_product_uom_category_id(self):
        for line in self:
            if line.product_uom_id and line.product_id and line.product_uom_id.category_id != line.product_id.product_tmpl_id.uom_id.category_id:
                raise UserError(_(
                    "The Unit of Measure (UoM) '%s' you have selected for product '%s', "
                    "is incompatible with its category : %s.",
                    line.product_uom_id.name,
                    line.product_id.name,
                    line.product_id.product_tmpl_id.uom_id.category_id.name
                ))

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
                if not move.is_invoice(include_receipts=True) and vals.get('debit') is False and vals.get('credit') is False:
                    vals['balance'] = move.currency_id._convert(vals['amount_currency'], move.company_id.currency_id, move.company_id, move.date)
                    vals['debit'] = vals['balance'] if vals['balance'] > 0.0 else 0.0
                    vals['credit'] = -vals['balance'] if vals['balance'] < 0.0 else 0.0

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

        inalterable_fields = set(self._get_integrity_hash_fields()).union({'inalterable_hash', 'secure_sequence_number'})
        hashed_moves = self.move_id.filtered('inalterable_hash')
        violated_fields = set(vals) & inalterable_fields
        if hashed_moves and violated_fields:
            raise UserError(_(
                "You cannot edit the following fields: %s.\n"
                "The following entries are already hashed:\n%s",
                ', '.join(f['string'] for f in self.fields_get(violated_fields).values()),
                '\n'.join(hashed_moves.mapped('name')),
            ))
        for line in self:
            if line.parent_state == 'posted':
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
                        msg = f"{html_escape(_('Journal Item'))} <a href=# data-oe-model=account.move.line data-oe-id={line.id}>#{line.id}</a> {html_escape(_('updated'))}"
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
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator == 'ilike':
            domain = ['|', '|',
                    ('name', 'ilike', name),
                    ('move_id', 'ilike', name),
                    ('product_id', 'ilike', name)]
            return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

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

        :return: A recordset of account.partial.reconcile.
        '''
        def fix_remaining_cent(currency, abs_residual, partial_amount):
            if abs_residual - currency.rounding <= partial_amount <= abs_residual + currency.rounding:
                return abs_residual
            else:
                return partial_amount

        debit_lines = iter(self.filtered(lambda line: line.balance > 0.0 or line.amount_currency > 0.0 and not line.reconciled))
        credit_lines = iter(self.filtered(lambda line: line.balance < 0.0 or line.amount_currency < 0.0 and not line.reconciled))
        void_lines = iter(self.filtered(lambda line: not line.balance and not line.amount_currency and not line.reconciled))
        debit_line = None
        credit_line = None

        debit_amount_residual = 0.0
        debit_amount_residual_currency = 0.0
        credit_amount_residual = 0.0
        credit_amount_residual_currency = 0.0
        debit_line_currency = None
        credit_line_currency = None

        partials_vals_list = []

        while True:

            # Move to the next available debit line.
            if not debit_line:
                debit_line = next(debit_lines, None) or next(void_lines, None)
                if not debit_line:
                    break
                debit_amount_residual = debit_line.amount_residual

                if debit_line.currency_id:
                    debit_amount_residual_currency = debit_line.amount_residual_currency
                    debit_line_currency = debit_line.currency_id
                else:
                    debit_amount_residual_currency = debit_amount_residual
                    debit_line_currency = debit_line.company_currency_id

            # Move to the next available credit line.
            if not credit_line:
                credit_line = next(void_lines, None) or next(credit_lines, None)
                if not credit_line:
                    break
                credit_amount_residual = credit_line.amount_residual

                if credit_line.currency_id:
                    credit_amount_residual_currency = credit_line.amount_residual_currency
                    credit_line_currency = credit_line.currency_id
                else:
                    credit_amount_residual_currency = credit_amount_residual
                    credit_line_currency = credit_line.company_currency_id

            min_amount_residual = min(debit_amount_residual, -credit_amount_residual)

            if debit_line_currency == credit_line_currency:
                # Reconcile on the same currency.

                min_amount_residual_currency = min(debit_amount_residual_currency, -credit_amount_residual_currency)
                min_debit_amount_residual_currency = min_amount_residual_currency
                min_credit_amount_residual_currency = min_amount_residual_currency

            else:
                # Reconcile on the company's currency.

                min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
                    min_amount_residual,
                    debit_line.currency_id,
                    credit_line.company_id,
                    credit_line.date,
                )
                min_debit_amount_residual_currency = fix_remaining_cent(
                    debit_line.currency_id,
                    debit_amount_residual_currency,
                    min_debit_amount_residual_currency,
                )
                min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
                    min_amount_residual,
                    credit_line.currency_id,
                    debit_line.company_id,
                    debit_line.date,
                )
                min_credit_amount_residual_currency = fix_remaining_cent(
                    credit_line.currency_id,
                    -credit_amount_residual_currency,
                    min_credit_amount_residual_currency,
                )

            debit_amount_residual -= min_amount_residual
            debit_amount_residual_currency -= min_debit_amount_residual_currency
            credit_amount_residual += min_amount_residual
            credit_amount_residual_currency += min_credit_amount_residual_currency

            partials_vals_list.append({
                'amount': min_amount_residual,
                'debit_amount_currency': min_debit_amount_residual_currency,
                'credit_amount_currency': min_credit_amount_residual_currency,
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })

            has_debit_residual_left = not debit_line.company_currency_id.is_zero(debit_amount_residual) and debit_amount_residual > 0.0
            has_credit_residual_left = not credit_line.company_currency_id.is_zero(credit_amount_residual) and credit_amount_residual < 0.0
            has_debit_residual_curr_left = not debit_line_currency.is_zero(debit_amount_residual_currency) and debit_amount_residual_currency > 0.0
            has_credit_residual_curr_left = not credit_line_currency.is_zero(credit_amount_residual_currency) and credit_amount_residual_currency < 0.0

            if debit_line_currency == credit_line_currency:
                # The debit line is now fully reconciled because:
                # - either amount_residual & amount_residual_currency are at 0.
                # - either the credit_line is not an exchange difference one.
                if not has_debit_residual_curr_left and (has_credit_residual_curr_left or not has_debit_residual_left):
                    debit_line = None

                # The credit line is now fully reconciled because:
                # - either amount_residual & amount_residual_currency are at 0.
                # - either the debit is not an exchange difference one.
                if not has_credit_residual_curr_left and (has_debit_residual_curr_left or not has_credit_residual_left):
                    credit_line = None

            else:
                # The debit line is now fully reconciled since amount_residual is 0.
                if not has_debit_residual_left:
                    debit_line = None

                # The credit line is now fully reconciled since amount_residual is 0.
                if not has_credit_residual_left:
                    credit_line = None

        return partials_vals_list

    def _create_exchange_difference_move(self):
        ''' Create the exchange difference journal entry on the current journal items.
        :return: An account.move record.
        '''

        def _add_lines_to_exchange_difference_vals(lines, exchange_diff_move_vals):
            ''' Generate the exchange difference values used to create the journal items
            in order to fix the residual amounts and add them into 'exchange_diff_move_vals'.

            1) When reconciled on the same foreign currency, the journal items are
            fully reconciled regarding this currency but it could be not the case
            of the balance that is expressed using the company's currency. In that
            case, we need to create exchange difference journal items to ensure this
            residual amount reaches zero.

            2) When reconciled on the company currency but having different foreign
            currencies, the journal items are fully reconciled regarding the company
            currency but it's not always the case for the foreign currencies. In that
            case, the exchange difference journal items are created to ensure this
            residual amount in foreign currency reaches zero.

            :param lines:                   The account.move.lines to which fix the residual amounts.
            :param exchange_diff_move_vals: The current vals of the exchange difference journal entry.
            :return:                        A list of pair <line, sequence> to perform the reconciliation
                                            at the creation of the exchange difference move where 'line'
                                            is the account.move.line to which the 'sequence'-th exchange
                                            difference line will be reconciled with.
            '''
            journal = self.env['account.journal'].browse(exchange_diff_move_vals['journal_id'])
            to_reconcile = []

            for line in lines:

                exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], line.date)

                if not line.company_currency_id.is_zero(line.amount_residual):
                    # amount_residual_currency == 0 and amount_residual has to be fixed.

                    if line.amount_residual > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id

                elif line.currency_id and not line.currency_id.is_zero(line.amount_residual_currency):
                    # amount_residual == 0 and amount_residual_currency has to be fixed.

                    if line.amount_residual_currency > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id
                else:
                    continue

                sequence = len(exchange_diff_move_vals['line_ids'])
                exchange_diff_move_vals['line_ids'] += [
                    (0, 0, {
                        'name': _('Currency exchange rate difference'),
                        'debit': -line.amount_residual if line.amount_residual < 0.0 else 0.0,
                        'credit': line.amount_residual if line.amount_residual > 0.0 else 0.0,
                        'amount_currency': -line.amount_residual_currency,
                        'account_id': line.account_id.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence,
                    }),
                    (0, 0, {
                        'name': _('Currency exchange rate difference'),
                        'debit': line.amount_residual if line.amount_residual > 0.0 else 0.0,
                        'credit': -line.amount_residual if line.amount_residual < 0.0 else 0.0,
                        'amount_currency': line.amount_residual_currency,
                        'account_id': exchange_line_account.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence + 1,
                    }),
                ]

                to_reconcile.append((line, sequence))

            return to_reconcile

        def _add_cash_basis_lines_to_exchange_difference_vals(lines, exchange_diff_move_vals):
            ''' Generate the exchange difference values used to create the journal items
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

            :param lines:                   The account.move.lines to which fix the residual amounts.
            :param exchange_diff_move_vals: The current vals of the exchange difference journal entry.
            '''
            for move in lines.move_id:
                account_vals_to_fix = {}

                move_values = move._collect_tax_cash_basis_values()

                # The cash basis doesn't need to be handle for this move because there is another payment term
                # line that is not yet fully paid.
                if not move_values or not move_values['is_fully_paid']:
                    continue

                # ==========================================================================
                # Add the balance of all tax lines of the current move in order in order
                # to compute the residual amount for each of them.
                # ==========================================================================

                for caba_treatment, line in move_values['to_process_lines']:

                    vals = {
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                        'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
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

                        sequence = len(exchange_diff_move_vals['line_ids'])
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                                'account_id': account.id,
                                'sequence': sequence,
                            }),
                            (0, 0, {
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
                        sequence = len(exchange_diff_move_vals['line_ids'])
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                                'sequence': sequence,
                            }),
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': -balance if balance < 0.0 else 0.0,
                                'credit': balance if balance > 0.0 else 0.0,
                                'tax_ids': [],
                                'tax_tag_ids': [],
                                'sequence': sequence + 1,
                            }),
                        ]

        if not self:
            return self.env['account.move']

        company = self[0].company_id
        journal = company.currency_exchange_journal_id

        exchange_diff_move_vals = {
            'move_type': 'entry',
            'date': date.min,
            'journal_id': journal.id,
            'line_ids': [],
            'always_tax_exigible': True, # Enforce exigibility in case some cash basis adjustments were made in this exchange difference
        }

        # Fix residual amounts.
        to_reconcile = _add_lines_to_exchange_difference_vals(self, exchange_diff_move_vals)

        # Fix cash basis entries.
        # If we are fully reversing the entry, no need to fix anything since the journal entry
        # is exactly the mirror of the source journal entry.
        is_cash_basis_needed = self[0].account_internal_type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            _add_cash_basis_lines_to_exchange_difference_vals(self, exchange_diff_move_vals)

        # ==========================================================================
        # Create move and reconcile.
        # ==========================================================================

        if exchange_diff_move_vals['line_ids']:
            # Check the configuration of the exchange difference journal.
            if not journal:
                raise UserError(_("You should configure the 'Exchange Gain or Loss Journal' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not journal.company_id.expense_currency_exchange_account_id:
                raise UserError(_("You should configure the 'Loss Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not journal.company_id.income_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Gain Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))

            exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], company._get_user_fiscal_lock_date() + timedelta(days=1))

            exchange_move = self.env['account.move'].create(exchange_diff_move_vals)
        else:
            return None

        # Reconcile lines to the newly created exchange difference journal entry by creating more partials.
        partials_vals_list = []
        for source_line, sequence in to_reconcile:
            exchange_diff_line = exchange_move.line_ids[sequence]

            if source_line.company_currency_id.is_zero(source_line.amount_residual):
                exchange_field = 'amount_residual_currency'
            else:
                exchange_field = 'amount_residual'

            if exchange_diff_line[exchange_field] > 0.0:
                debit_line = exchange_diff_line
                credit_line = source_line
            else:
                debit_line = source_line
                credit_line = exchange_diff_line

            partials_vals_list.append({
                'amount': abs(source_line.amount_residual),
                'debit_amount_currency': abs(debit_line.amount_residual_currency),
                'credit_amount_currency': abs(credit_line.amount_residual_currency),
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })

        self.env['account.partial.reconcile'].create(partials_vals_list)

        return exchange_move

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {}

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

        sorted_lines = self.sorted(key=lambda line: (line.date_maturity or line.date, line.currency_id))

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

        partials = self.env['account.partial.reconcile'].create(sorted_lines._prepare_reconciliation_partials())

        # Track newly created partials.
        results['partials'] = partials
        involved_partials += partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.company_id.tax_exigibility and account.user_type_id.type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        if involved_lines[0].currency_id and all(line.currency_id == involved_lines[0].currency_id for line in involved_lines):
            is_full_needed = all(line.currency_id.is_zero(line.amount_residual_currency) for line in involved_lines)
        else:
            is_full_needed = all(line.company_currency_id.is_zero(line.amount_residual) for line in involved_lines)

        if is_full_needed:

            # ==== Create the exchange difference move ====

            if self._context.get('no_exchange_difference'):
                exchange_move = None
            else:
                exchange_move = involved_lines._create_exchange_difference_move()
                if exchange_move:
                    exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                    # Track newly created lines.
                    involved_lines += exchange_move_lines

                    # Track newly created partials.
                    exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                             + exchange_move_lines.matched_credit_ids
                    involved_partials += exchange_diff_partials
                    results['partials'] += exchange_diff_partials

                    exchange_move._post(soft=False)

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
            'category': 'invoice' if self.move_id.is_sale_document() else 'vendor_bill' if self.move_id.is_purchase_document() else 'other',
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
=======
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
        r''' Recompute 'tax_ids' based on 'account_id'.
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
            line.debit = balance if balance > 0.0 else 0.0
            line.credit = -balance if balance < 0.0 else 0.0

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

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if res.get('cumulated_balance'):
            res['cumulated_balance']['exportable'] = False
        return res

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

    @api.depends('debit', 'credit', 'amount_currency', 'account_id', 'currency_id', 'parent_state', 'company_id',
                 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if line.id and (line.account_id.reconcile or line.account_id.internal_type == 'liquidity'):
                reconciled_balance = sum(line.matched_credit_ids.mapped('amount')) \
                                     - sum(line.matched_debit_ids.mapped('amount'))
                reconciled_amount_currency = sum(line.matched_credit_ids.mapped('debit_amount_currency'))\
                                             - sum(line.matched_debit_ids.mapped('credit_amount_currency'))

                line.amount_residual = line.balance - reconciled_balance

                if line.currency_id:
                    line.amount_residual_currency = line.amount_currency - reconciled_amount_currency
                else:
                    line.amount_residual_currency = 0.0

                line.reconciled = (
                    line.company_currency_id.is_zero(line.amount_residual)
                    and (not line.currency_id or line.currency_id.is_zero(line.amount_residual_currency))
                    and (line.matched_debit_ids or line.matched_credit_ids)
                )
            else:
                # Must not have any reconciliation since the line is not eligible for that.
                line.amount_residual = 0.0
                line.amount_residual_currency = 0.0
                line.reconciled = False

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

                if record.tax_ids and record.move_id.reversed_entry_id:
                    is_refund = not is_refund

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

            failed_check = False
            if journal.type_control_ids or journal.account_control_ids:
                failed_check = True
                if journal.type_control_ids:
                    failed_check = account.user_type_id not in journal.type_control_ids
                if failed_check and journal.account_control_ids:
                    failed_check = account not in journal.account_control_ids

            if failed_check:
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

    @api.constrains('product_uom_id')
    def _check_product_uom_category_id(self):
        for line in self:
            if line.product_uom_id and line.product_id and line.product_uom_id.category_id != line.product_id.product_tmpl_id.uom_id.category_id:
                raise UserError(_(
                    "The Unit of Measure (UoM) '%s' you have selected for product '%s', "
                    "is incompatible with its category : %s.",
                    line.product_uom_id.name,
                    line.product_id.name,
                    line.product_id.product_tmpl_id.uom_id.category_id.name
                ))

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
                if not move.is_invoice(include_receipts=True) and vals.get('debit') is False and vals.get('credit') is False:
                    vals['balance'] = move.currency_id._convert(vals['amount_currency'], move.company_id.currency_id, move.company_id, move.date)
                    vals['debit'] = vals['balance'] if vals['balance'] > 0.0 else 0.0
                    vals['credit'] = -vals['balance'] if vals['balance'] < 0.0 else 0.0

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

        inalterable_fields = set(self._get_integrity_hash_fields()).union({'inalterable_hash', 'secure_sequence_number'})
        hashed_moves = self.move_id.filtered('inalterable_hash')
        violated_fields = set(vals) & inalterable_fields
        if hashed_moves and violated_fields:
            raise UserError(_(
                "You cannot edit the following fields: %s.\n"
                "The following entries are already hashed:\n%s",
                ', '.join(f['string'] for f in self.fields_get(violated_fields).values()),
                '\n'.join(hashed_moves.mapped('name')),
            ))
        for line in self:
            if line.parent_state == 'posted':
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
                        msg = f"{html_escape(_('Journal Item'))} <a href=# data-oe-model=account.move.line data-oe-id={line.id}>#{line.id}</a> {html_escape(_('updated'))}"
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
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator == 'ilike':
            domain = ['|', '|',
                    ('name', 'ilike', name),
                    ('move_id', 'ilike', name),
                    ('product_id', 'ilike', name)]
            return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

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
        r''' Prepare the partials on the current journal items to perform the reconciliation.
        /!\ The order of records in self is important because the journal items will be reconciled using this order.

        :return: A recordset of account.partial.reconcile.
        '''
        def fix_remaining_cent(currency, abs_residual, partial_amount):
            if abs_residual - currency.rounding <= partial_amount <= abs_residual + currency.rounding:
                return abs_residual
            else:
                return partial_amount

        debit_lines = iter(self.filtered(lambda line: line.balance > 0.0 or line.amount_currency > 0.0 and not line.reconciled))
        credit_lines = iter(self.filtered(lambda line: line.balance < 0.0 or line.amount_currency < 0.0 and not line.reconciled))
        void_lines = iter(self.filtered(lambda line: not line.balance and not line.amount_currency and not line.reconciled))
        debit_line = None
        credit_line = None

        debit_amount_residual = 0.0
        debit_amount_residual_currency = 0.0
        credit_amount_residual = 0.0
        credit_amount_residual_currency = 0.0
        debit_line_currency = None
        credit_line_currency = None

        partials_vals_list = []

        while True:

            # Move to the next available debit line.
            if not debit_line:
                debit_line = next(debit_lines, None) or next(void_lines, None)
                if not debit_line:
                    break
                debit_amount_residual = debit_line.amount_residual

                if debit_line.currency_id:
                    debit_amount_residual_currency = debit_line.amount_residual_currency
                    debit_line_currency = debit_line.currency_id
                else:
                    debit_amount_residual_currency = debit_amount_residual
                    debit_line_currency = debit_line.company_currency_id

            # Move to the next available credit line.
            if not credit_line:
                credit_line = next(void_lines, None) or next(credit_lines, None)
                if not credit_line:
                    break
                credit_amount_residual = credit_line.amount_residual

                if credit_line.currency_id:
                    credit_amount_residual_currency = credit_line.amount_residual_currency
                    credit_line_currency = credit_line.currency_id
                else:
                    credit_amount_residual_currency = credit_amount_residual
                    credit_line_currency = credit_line.company_currency_id

            min_amount_residual = min(debit_amount_residual, -credit_amount_residual)

            if debit_line_currency == credit_line_currency:
                # Reconcile on the same currency.

                min_amount_residual_currency = min(debit_amount_residual_currency, -credit_amount_residual_currency)
                min_debit_amount_residual_currency = min_amount_residual_currency
                min_credit_amount_residual_currency = min_amount_residual_currency

            else:
                # Reconcile on the company's currency.

                min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
                    min_amount_residual,
                    debit_line.currency_id,
                    credit_line.company_id,
                    credit_line.date,
                )
                min_debit_amount_residual_currency = fix_remaining_cent(
                    debit_line.currency_id,
                    debit_amount_residual_currency,
                    min_debit_amount_residual_currency,
                )
                min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
                    min_amount_residual,
                    credit_line.currency_id,
                    debit_line.company_id,
                    debit_line.date,
                )
                min_credit_amount_residual_currency = fix_remaining_cent(
                    credit_line.currency_id,
                    -credit_amount_residual_currency,
                    min_credit_amount_residual_currency,
                )

            debit_amount_residual -= min_amount_residual
            debit_amount_residual_currency -= min_debit_amount_residual_currency
            credit_amount_residual += min_amount_residual
            credit_amount_residual_currency += min_credit_amount_residual_currency

            partials_vals_list.append({
                'amount': min_amount_residual,
                'debit_amount_currency': min_debit_amount_residual_currency,
                'credit_amount_currency': min_credit_amount_residual_currency,
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })

            has_debit_residual_left = not debit_line.company_currency_id.is_zero(debit_amount_residual) and debit_amount_residual > 0.0
            has_credit_residual_left = not credit_line.company_currency_id.is_zero(credit_amount_residual) and credit_amount_residual < 0.0
            has_debit_residual_curr_left = not debit_line_currency.is_zero(debit_amount_residual_currency) and debit_amount_residual_currency > 0.0
            has_credit_residual_curr_left = not credit_line_currency.is_zero(credit_amount_residual_currency) and credit_amount_residual_currency < 0.0

            if debit_line_currency == credit_line_currency:
                # The debit line is now fully reconciled because:
                # - either amount_residual & amount_residual_currency are at 0.
                # - either the credit_line is not an exchange difference one.
                if not has_debit_residual_curr_left and (has_credit_residual_curr_left or not has_debit_residual_left):
                    debit_line = None

                # The credit line is now fully reconciled because:
                # - either amount_residual & amount_residual_currency are at 0.
                # - either the debit is not an exchange difference one.
                if not has_credit_residual_curr_left and (has_debit_residual_curr_left or not has_credit_residual_left):
                    credit_line = None

            else:
                # The debit line is now fully reconciled since amount_residual is 0.
                if not has_debit_residual_left:
                    debit_line = None

                # The credit line is now fully reconciled since amount_residual is 0.
                if not has_credit_residual_left:
                    credit_line = None

        return partials_vals_list

    def _create_exchange_difference_move(self):
        ''' Create the exchange difference journal entry on the current journal items.
        :return: An account.move record.
        '''

        def _add_lines_to_exchange_difference_vals(lines, exchange_diff_move_vals):
            ''' Generate the exchange difference values used to create the journal items
            in order to fix the residual amounts and add them into 'exchange_diff_move_vals'.

            1) When reconciled on the same foreign currency, the journal items are
            fully reconciled regarding this currency but it could be not the case
            of the balance that is expressed using the company's currency. In that
            case, we need to create exchange difference journal items to ensure this
            residual amount reaches zero.

            2) When reconciled on the company currency but having different foreign
            currencies, the journal items are fully reconciled regarding the company
            currency but it's not always the case for the foreign currencies. In that
            case, the exchange difference journal items are created to ensure this
            residual amount in foreign currency reaches zero.

            :param lines:                   The account.move.lines to which fix the residual amounts.
            :param exchange_diff_move_vals: The current vals of the exchange difference journal entry.
            :return:                        A list of pair <line, sequence> to perform the reconciliation
                                            at the creation of the exchange difference move where 'line'
                                            is the account.move.line to which the 'sequence'-th exchange
                                            difference line will be reconciled with.
            '''
            journal = self.env['account.journal'].browse(exchange_diff_move_vals['journal_id'])
            to_reconcile = []

            for line in lines:

                exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], line.date)

                if not line.company_currency_id.is_zero(line.amount_residual):
                    # amount_residual_currency == 0 and amount_residual has to be fixed.

                    if line.amount_residual > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id

                elif line.currency_id and not line.currency_id.is_zero(line.amount_residual_currency):
                    # amount_residual == 0 and amount_residual_currency has to be fixed.

                    if line.amount_residual_currency > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id
                else:
                    continue

                sequence = len(exchange_diff_move_vals['line_ids'])
                exchange_diff_move_vals['line_ids'] += [
                    (0, 0, {
                        'name': _('Currency exchange rate difference'),
                        'debit': -line.amount_residual if line.amount_residual < 0.0 else 0.0,
                        'credit': line.amount_residual if line.amount_residual > 0.0 else 0.0,
                        'amount_currency': -line.amount_residual_currency,
                        'account_id': line.account_id.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence,
                    }),
                    (0, 0, {
                        'name': _('Currency exchange rate difference'),
                        'debit': line.amount_residual if line.amount_residual > 0.0 else 0.0,
                        'credit': -line.amount_residual if line.amount_residual < 0.0 else 0.0,
                        'amount_currency': line.amount_residual_currency,
                        'account_id': exchange_line_account.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence + 1,
                    }),
                ]

                to_reconcile.append((line, sequence))

            return to_reconcile

        def _add_cash_basis_lines_to_exchange_difference_vals(lines, exchange_diff_move_vals):
            ''' Generate the exchange difference values used to create the journal items
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

            :param lines:                   The account.move.lines to which fix the residual amounts.
            :param exchange_diff_move_vals: The current vals of the exchange difference journal entry.
            '''
            for move in lines.move_id:
                account_vals_to_fix = {}

                move_values = move._collect_tax_cash_basis_values()

                # The cash basis doesn't need to be handle for this move because there is another payment term
                # line that is not yet fully paid.
                if not move_values or not move_values['is_fully_paid']:
                    continue

                # ==========================================================================
                # Add the balance of all tax lines of the current move in order in order
                # to compute the residual amount for each of them.
                # ==========================================================================

                for caba_treatment, line in move_values['to_process_lines']:

                    vals = {
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                        'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
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

                        sequence = len(exchange_diff_move_vals['line_ids'])
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                                'account_id': account.id,
                                'sequence': sequence,
                            }),
                            (0, 0, {
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
                        sequence = len(exchange_diff_move_vals['line_ids'])
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                                'sequence': sequence,
                            }),
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': -balance if balance < 0.0 else 0.0,
                                'credit': balance if balance > 0.0 else 0.0,
                                'tax_ids': [],
                                'tax_tag_ids': [],
                                'sequence': sequence + 1,
                            }),
                        ]

        if not self:
            return self.env['account.move']

        company = self[0].company_id
        journal = company.currency_exchange_journal_id

        exchange_diff_move_vals = {
            'move_type': 'entry',
            'date': date.min,
            'journal_id': journal.id,
            'line_ids': [],
            'always_tax_exigible': True, # Enforce exigibility in case some cash basis adjustments were made in this exchange difference
        }

        # Fix residual amounts.
        to_reconcile = _add_lines_to_exchange_difference_vals(self, exchange_diff_move_vals)

        # Fix cash basis entries.
        # If we are fully reversing the entry, no need to fix anything since the journal entry
        # is exactly the mirror of the source journal entry.
        is_cash_basis_needed = self[0].account_internal_type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            _add_cash_basis_lines_to_exchange_difference_vals(self, exchange_diff_move_vals)

        # ==========================================================================
        # Create move and reconcile.
        # ==========================================================================

        if exchange_diff_move_vals['line_ids']:
            # Check the configuration of the exchange difference journal.
            if not journal:
                raise UserError(_("You should configure the 'Exchange Gain or Loss Journal' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not journal.company_id.expense_currency_exchange_account_id:
                raise UserError(_("You should configure the 'Loss Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not journal.company_id.income_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Gain Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))

            exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], company._get_user_fiscal_lock_date() + timedelta(days=1))

            exchange_move = self.env['account.move'].create(exchange_diff_move_vals)
        else:
            return None

        # Reconcile lines to the newly created exchange difference journal entry by creating more partials.
        partials_vals_list = []
        for source_line, sequence in to_reconcile:
            exchange_diff_line = exchange_move.line_ids[sequence]

            if source_line.company_currency_id.is_zero(source_line.amount_residual):
                exchange_field = 'amount_residual_currency'
            else:
                exchange_field = 'amount_residual'

            if exchange_diff_line[exchange_field] > 0.0:
                debit_line = exchange_diff_line
                credit_line = source_line
            else:
                debit_line = source_line
                credit_line = exchange_diff_line

            partials_vals_list.append({
                'amount': abs(source_line.amount_residual),
                'debit_amount_currency': abs(debit_line.amount_residual_currency),
                'credit_amount_currency': abs(credit_line.amount_residual_currency),
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })

        self.env['account.partial.reconcile'].create(partials_vals_list)

        return exchange_move

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {}

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

        sorted_lines = self.sorted(key=lambda line: (line.date_maturity or line.date, line.currency_id))

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

        partials = self.env['account.partial.reconcile'].create(sorted_lines._prepare_reconciliation_partials())

        # Track newly created partials.
        results['partials'] = partials
        involved_partials += partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.company_id.tax_exigibility and account.user_type_id.type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        if involved_lines[0].currency_id and all(line.currency_id == involved_lines[0].currency_id for line in involved_lines):
            is_full_needed = all(line.currency_id.is_zero(line.amount_residual_currency) for line in involved_lines)
        else:
            is_full_needed = all(line.company_currency_id.is_zero(line.amount_residual) for line in involved_lines)

        if is_full_needed:

            # ==== Create the exchange difference move ====

            if self._context.get('no_exchange_difference'):
                exchange_move = None
            else:
                exchange_move = involved_lines._create_exchange_difference_move()
                if exchange_move:
                    exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                    # Track newly created lines.
                    involved_lines += exchange_move_lines

                    # Track newly created partials.
                    exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                             + exchange_move_lines.matched_credit_ids
                    involved_partials += exchange_diff_partials
                    results['partials'] += exchange_diff_partials

                    exchange_move._post(soft=False)

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
            'category': 'invoice' if self.move_id.is_sale_document() else 'vendor_bill' if self.move_id.is_purchase_document() else 'other',
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
>>>>>>> a2822764d045 (temp)
