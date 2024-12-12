# -*- coding: utf-8 -*-
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from json import dumps
import logging
from markupsafe import Markup
import math
import psycopg2
import re
from textwrap import shorten

from odoo import api, fields, models, _, Command, SUPERUSER_ID, modules, tools
from odoo.addons.account.tools import format_structured_reference_iso
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
    index_exists,
    is_html_empty,
    create_index,
)

_logger = logging.getLogger(__name__)


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
    'out_refund': 'out_invoice',
    'in_invoice': 'in_refund',
    'in_refund': 'in_invoice',
    'out_receipt': 'out_refund',
    'in_receipt': 'in_refund',
}

ALLOWED_MIMETYPES = {
    'text/plain',
    'text/csv',
    'application/pdf',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

EMPTY = object()


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['portal.mixin', 'mail.thread.main.attachment', 'mail.activity.mixin', 'sequence.mixin']
    _description = "Journal Entry"
    _order = 'date desc, name desc, invoice_date desc, id desc'
    _mail_post_access = 'read'
    _check_company_auto = True
    _sequence_index = "journal_id"
    _rec_names_search = ['name', 'partner_id.name', 'ref']
    _systray_view = 'activity'

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
    ref = fields.Char(
        string='Reference',
        copy=False,
        tracking=True,
        index='trigram',
    )
    date = fields.Date(
        string='Date',
        index=True,
        compute='_compute_date', store=True, required=True, readonly=False, precompute=True,
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
        index='btree_not_null',
    )
    statement_id = fields.Many2one(
        related="statement_line_id.statement_id"
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
        index='btree_not_null',
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
        domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))],
    )

    # === Date fields === #
    invoice_date = fields.Date(
        string='Invoice/Bill Date',
        index=True,
        copy=False,
    )
    invoice_date_due = fields.Date(
        string='Due Date',
        compute='_compute_invoice_date_due', store=True, readonly=False,
        index=True,
        copy=False,
    )
    delivery_date = fields.Date(
        string='Delivery Date',
        copy=False,
        store=True,
        compute='_compute_delivery_date',
    )
    show_delivery_date = fields.Boolean(compute='_compute_show_delivery_date')
    invoice_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment Terms',
        compute='_compute_invoice_payment_term_id', store=True, readonly=False, precompute=True,
        inverse='_inverse_invoice_payment_term_id',
        check_company=True,
    )
    needed_terms = fields.Binary(compute='_compute_needed_terms', exportable=False)
    needed_terms_dirty = fields.Boolean(compute='_compute_needed_terms')
    tax_calculation_rounding_method = fields.Selection(
        related='company_id.tax_calculation_rounding_method',
        string='Tax calculation rounding method', readonly=True)
    # === Partner fields === #
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=False,
        tracking=True,
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
        check_company=True,
    )
    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        compute='_compute_partner_shipping_id', store=True, readonly=False, precompute=True,
        check_company=True,
        help="The delivery address will be used in the computation of the fiscal position.",
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
        ondelete='restrict',
    )
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        string='Fiscal Position',
        check_company=True,
        compute='_compute_fiscal_position_id', store=True, readonly=False, precompute=True,
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
    amount_total_words = fields.Char(
        string="Amount total in words",
        compute="_compute_amount_total_words",
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
    quick_encoding_vals = fields.Json(compute='_compute_quick_encoding_vals', exportable=False)

    # === Misc Information === #
    narration = fields.Html(
        string='Terms and Conditions',
        compute='_compute_narration', store=True, readonly=False,
    )
    is_move_sent = fields.Boolean(
        readonly=True,
        copy=False,
        tracking=True,
        help="It indicates that the invoice/payment has been sent or the PDF has been generated.",
    )
    is_being_sent = fields.Boolean(
        help="Is the move being sent asynchronously",
        compute='_compute_is_being_sent'
    )

    invoice_user_id = fields.Many2one(
        string='Salesperson',
        comodel_name='res.users',
        copy=False,
        tracking=True,
        compute='_compute_invoice_default_sale_person',
        store=True,
        readonly=False,
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
    incoterm_location = fields.Char(
        string='Incoterm Location',
        compute='_compute_incoterm_location',
        readonly=False,
        store=True,
    )
    invoice_cash_rounding_id = fields.Many2one(
        comodel_name='account.cash.rounding',
        string='Cash Rounding Method',
        help='Defines the smallest coinage of the currency that can be used to pay by cash.',
    )
    send_and_print_values = fields.Json(copy=False)
    invoice_pdf_report_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="PDF Attachment",
        compute=lambda self: self._compute_linked_attachment_id('invoice_pdf_report_id', 'invoice_pdf_report_file'),
        depends=['invoice_pdf_report_file']
    )
    invoice_pdf_report_file = fields.Binary(
        attachment=True,
        string="PDF File",
        copy=False,
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
    partner_credit = fields.Monetary(compute='_compute_partner_credit')
    duplicated_ref_ids = fields.Many2many(comodel_name='account.move', compute='_compute_duplicated_ref_ids')
    need_cancel_request = fields.Boolean(compute='_compute_need_cancel_request')

    show_update_fpos = fields.Boolean(string="Has Fiscal Position Changed", store=False)  # True if the fiscal position was changed

    # used to display the various dates and amount dues on the invoice's PDF
    payment_term_details = fields.Binary(compute="_compute_payment_term_details", exportable=False)
    show_payment_term_details = fields.Boolean(compute="_compute_show_payment_term_details")
    show_discount_details = fields.Boolean(compute="_compute_show_payment_term_details")

    _sql_constraints = [(
        'unique_name', "", "Another entry with the same name already exists.",
    )]

    def _auto_init(self):
        super()._auto_init()
        if not index_exists(self.env.cr, 'account_move_to_check_idx'):
            self.env.cr.execute("""
                CREATE INDEX account_move_to_check_idx
                          ON account_move(journal_id)
                       WHERE to_check = true
            """)
        if not index_exists(self.env.cr, 'account_move_payment_idx'):
            self.env.cr.execute("""
                CREATE INDEX account_move_payment_idx
                          ON account_move(journal_id, state, payment_state, move_type, date)
            """)
        if not index_exists(self.env.cr, 'account_move_unique_name'):
            self.env.cr.execute("""
                CREATE UNIQUE INDEX account_move_unique_name
                                 ON account_move(name, journal_id)
                              WHERE (state = 'posted' AND name != '/')
            """)
        if not index_exists(self.env.cr, 'account_move_sequence_index3'):
            # Used for gap detection in list views
            self.env.cr.execute("""
                CREATE INDEX account_move_sequence_index3
                          ON account_move (journal_id, sequence_prefix desc, (sequence_number+1) desc)
            """)

    def init(self):
        super().init()
        create_index(self.env.cr,
                     indexname='account_move_journal_id_company_id_idx',
                     tablename='account_move',
                     expressions=['journal_id', 'company_id', 'date'])

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type')
    def _compute_invoice_default_sale_person(self):
        # We want to modify the sale person only when we don't have one and if the move type corresponds to this condition
        # If the move doesn't correspond, we remove the sale person
        for move in self:
            if move.is_sale_document(include_receipts=True):
                move.invoice_user_id = move.invoice_user_id or self.env.user
            else:
                move.invoice_user_id = False

    def _compute_is_being_sent(self):
        for move in self:
            move.is_being_sent = bool(move.send_and_print_values)

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
            if move.journal_id.company_id not in move.company_id.parent_ids:
                move.company_id = (move.journal_id.company_id or self.env.company)._accessible_branches()[:1]

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
        company = self.company_id or self.env.company
        domain = [
            *self.env['account.journal']._check_company_domain(company),
            ('type', 'in', journal_types),
        ]

        journal = None
        # the currency is not a hard dependence, it triggers via manual add_to_compute
        # avoid computing the currency before all it's dependences are set (like the journal...)
        if self.env.cache.contains(self, self._fields['currency_id']):
            currency_id = self.currency_id.id or self._context.get('default_currency_id')
            if currency_id and currency_id != company.currency_id.id:
                currency_domain = domain + [('currency_id', '=', currency_id)]
                journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
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
            company = m.company_id or self.env.company
            m.suitable_journal_ids = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', journal_type),
            ])

    @api.depends('posted_before', 'state', 'journal_id', 'date', 'move_type', 'payment_id')
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m._origin.id))

        for move in self:
            if move.state == 'cancel':
                continue

            move_has_name = move.name and move.name != '/'
            if move_has_name or move.state != 'posted':
                if not move.posted_before and not move._sequence_matches_date():
                    if move._get_last_sequence():
                        # The name does not match the date and the move is not the first in the period:
                        # Reset to draft
                        move.name = False
                        continue
                else:
                    if move_has_name and move.posted_before or not move_has_name and move._get_last_sequence():
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
            record.highest_name = record._get_last_sequence()

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
        for record in self.with_context(prefetch_fields=False):
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
            # This will get the bank account from the partner in an order with the trusted first
            bank_ids = move.bank_partner_id.bank_ids.filtered(
                lambda bank: not bank.company_id or bank.company_id == move.company_id
            ).sorted(lambda bank: not bank.allow_out_payment)
            move.partner_bank_id = bank_ids[:1]

    @api.depends('partner_id')
    def _compute_invoice_payment_term_id(self):
        for move in self:
            move = move.with_company(move.company_id)
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

    def _compute_delivery_date(self):
        pass

    @api.depends('delivery_date')
    def _compute_show_delivery_date(self):
        for move in self:
            move.show_delivery_date = move.delivery_date and move.is_sale_document()

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
                    GROUP BY source_line.id, source_line.move_id, account.account_type
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
        for invoice in self.with_context(bin_size=False):
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
                        cash_rounding=invoice.invoice_cash_rounding_id,
                        sign=sign
                    )
                    for term_line in invoice_payment_terms['line_ids']:
                        key = frozendict({
                            'move_id': invoice.id,
                            'date_maturity': fields.Date.to_date(term_line.get('date')),
                            'discount_date': invoice_payment_terms.get('discount_date'),
                        })
                        values = {
                            'balance': term_line['company_amount'],
                            'amount_currency': term_line['foreign_amount'],
                            'discount_date': invoice_payment_terms.get('discount_date'),
                            'discount_balance': invoice_payment_terms.get('discount_balance') or 0.0,
                            'discount_amount_currency': invoice_payment_terms.get('discount_amount_currency') or 0.0,
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
                        'discount_balance': 0.0,
                        'discount_amount_currency': 0.0
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
                reconciled_partials = move.sudo()._get_all_reconciled_invoice_partials()
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
                        'company_name': counterpart_line.journal_id.company_id.name if counterpart_line.journal_id.company_id != move.company_id else False,
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
                kwargs['is_company_currency_requested'] = move.currency_id != move.company_id.currency_id
                move.tax_totals = self.env['account.tax']._prepare_tax_totals(**kwargs)
                if move.invoice_cash_rounding_id:
                    rounding_amount = move.invoice_cash_rounding_id.compute_difference(move.currency_id, move.tax_totals['amount_total'])
                    totals = move.tax_totals
                    totals['display_rounding'] = True
                    if rounding_amount:
                        if move.invoice_cash_rounding_id.strategy == 'add_invoice_line':
                            totals['rounding_amount'] = rounding_amount
                            totals['formatted_rounding_amount'] = formatLang(self.env, totals['rounding_amount'], currency_obj=move.currency_id)
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
                invoice.show_discount_details = invoice.invoice_payment_term_id.early_discount
                invoice.show_payment_term_details = len(payment_term_lines) > 1 or invoice.show_discount_details
            else:
                invoice.show_discount_details = False
                invoice.show_payment_term_details = False

    def _need_cancel_request(self):
        """ Hook allowing a localization to prevent the user to reset draft an invoice that has been already sent
        to the government and thus, must remain untouched except if its cancellation is approved.

        :return: True if the cancel button is displayed instead of draft button, False otherwise.
        """
        self.ensure_one()
        return False

    @api.depends('country_code')
    def _compute_need_cancel_request(self):
        for move in self:
            move.need_cancel_request = move._need_cancel_request()

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
            move.show_reset_to_draft_button = (
                not move.restrict_mode_hash_table \
                and (move.state == 'cancel' or (move.state == 'posted' and not move.need_cancel_request))
            )

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

    def _get_partner_credit_warning_exclude_amount(self):
        # to extend in module 'sale'; see there for details
        self.ensure_one()
        return 0

    @api.depends('company_id', 'partner_id', 'tax_totals', 'currency_id')
    def _compute_partner_credit_warning(self):
        for move in self:
            move.with_company(move.company_id)
            move.partner_credit_warning = ''
            show_warning = move.state == 'draft' and \
                           move.move_type == 'out_invoice' and \
                           move.company_id.account_use_credit_limit
            if show_warning:
                total_field = 'amount_total' if move.currency_id == move.company_currency_id else 'amount_total_company_currency'
                current_amount = move.tax_totals[total_field]
                move.partner_credit_warning = self._build_credit_warning_message(
                    move,
                    current_amount=current_amount,
                    exclude_amount=move._get_partner_credit_warning_exclude_amount(),
                )

    @api.depends('partner_id')
    def _compute_partner_credit(self):
        for move in self:
            move.partner_credit = move.partner_id.commercial_partner_id.credit

    def _build_credit_warning_message(self, record, current_amount=0.0, exclude_current=False, exclude_amount=0.0):
        """ Build the warning message that will be displayed in a yellow banner on top of the current record
            if the partner exceeds a credit limit (set on the company or the partner itself).
            :param record:                  The record where the warning will appear (Invoice, Sales Order...).
            :param current_amount (float):  The partner's outstanding credit amount from the current document.
            :param exclude_current (bool):  DEPRECATED in favor of parameter `exclude_amount`:
                                            Whether to exclude `current_amount` from the credit to invoice.
            :param exclude_amount (float):  The amount to subtract from the partner's `credit_to_invoice`.
                                            Consider the warning on a draft invoice created from a sales order.
                                            After confirming the invoice the (partial) amount (on the invoice)
                                            stemming from sales orders will be substracted from the `credit_to_invoice`.
                                            This will reduce the total credit of the partner.
                                            This parameter is used to reflect this amount.
            :return (str):                  The warning message to be showed.
        """
        partner_id = record.partner_id.commercial_partner_id
        credit_to_invoice = partner_id.credit_to_invoice - exclude_amount
        total_credit = partner_id.credit + credit_to_invoice + current_amount
        if not partner_id.credit_limit or total_credit <= partner_id.credit_limit:
            return ''
        msg = _(
            '%(partner_name)s has reached its credit limit of: %(credit_limit)s',
            partner_name=partner_id.name,
            credit_limit=formatLang(self.env, partner_id.credit_limit, currency_obj=record.company_id.currency_id)
        )
        total_credit_formatted = formatLang(self.env, total_credit, currency_obj=record.company_id.currency_id)
        if credit_to_invoice > 0 and current_amount > 0:
            return msg + '\n' + _(
                'Total amount due (including sales orders and this document): %(total_credit)s',
                total_credit=total_credit_formatted
            )
        elif credit_to_invoice > 0:
            return msg + '\n' + _(
                'Total amount due (including sales orders): %(total_credit)s',
                total_credit=total_credit_formatted
            )
        elif current_amount > 0:
            return msg + '\n' + _(
                'Total amount due (including this document): %(total_credit)s',
                total_credit=total_credit_formatted
            )
        else:
            return msg + '\n' + _(
                'Total amount due: %(total_credit)s',
                total_credit=total_credit_formatted
            )

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
        for move in self:
            move.display_qr_code = (
                move.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt')
                and move.company_id.qr_code
            )

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for move in self:
            move.amount_total_words = move.currency_id.amount_to_text(move.amount_total).replace(',', '')

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        """Helper to retreive Attachment from Binary fields
        This is needed because fields.Many2one('ir.attachment') makes all
        attachments available to the user.
        """
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('res_field', '=', binary_field)
        ])
        move_vals = {att.res_id: att for att in attachments}
        for move in self:
            move[attachment_field] = move_vals.get(move._origin.id, False)

    def _compute_incoterm_location(self):
        pass

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
        for move in self:
            # This can't be caught by a python constraint as it is only triggered at save and the compute method that
            # needs this data to be set correctly before saving
            if not move.company_id:
                raise ValidationError(_("We can't leave this document without any company. Please select a company for this document."))
        self._conditional_add_to_compute('journal_id', lambda m: (
            not m.journal_id.filtered_domain(self.env['account.journal']._check_company_domain(m.company_id))
        ))

    @api.onchange('currency_id')
    def _inverse_currency_id(self):
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

    @api.onchange('payment_reference')
    def _inverse_payment_reference(self):
        self.line_ids._conditional_add_to_compute('name', lambda line: (
            line.display_type == 'payment_term'
        ))

    @api.onchange('invoice_payment_term_id')
    def _inverse_invoice_payment_term_id(self):
        self.line_ids._conditional_add_to_compute('name', lambda l: (
            l.display_type == 'payment_term'
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

    @api.onchange('fiscal_position_id')
    def _onchange_fpos_id_show_update_fpos(self):
        self.show_update_fpos = self.line_ids and self._origin.fiscal_position_id != self.fiscal_position_id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self = self.with_company((self.journal_id.company_id or self.env.company)._accessible_branches()[:1])

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
    # EARLY PAYMENT DISCOUNT
    # -------------------------------------------------------------------------
    def _is_eligible_for_early_payment_discount(self, currency, reference_date):
        self.ensure_one()
        return self.currency_id == currency \
            and self.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt') \
            and self.invoice_payment_term_id.early_discount \
            and (not reference_date or reference_date <= self.invoice_payment_term_id._get_last_discount_date(self.invoice_date)) \
            and self.payment_state == 'not_paid'

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
                line: line[existing_key_fname]
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

        def filter_trivial(mapping):
            return {k: v for k, v in mapping.items() if 'id' not in v}

        inv_existing_before = existing()
        needed_before = needed()
        dirty_recs_before, dirty_fname = dirty()
        dirty_recs_before[dirty_fname] = False
        yield
        dirty_recs_after, dirty_fname = dirty()
        if not dirty_recs_after:  # TODO improve filter
            return
        inv_existing_after = existing()
        needed_after = needed()

        # Filter out deleted lines from `needed_before` to not recompute lines if not necessary or wanted
        line_ids = set(self.env['account.move.line'].browse(k['id'] for k in needed_before if 'id' in k).exists().ids)
        needed_before = {k: v for k, v in needed_before.items() if 'id' not in k or k['id'] in line_ids}

        # old key to new key for the same line
        before2after = {
            before: inv_existing_after[bline]
            for bline, before in inv_existing_before.items()
            if bline in inv_existing_after
        }

        if needed_after == needed_before:
            return  # do not modify user input if nothing changed in the needs
        if not needed_before and (filter_trivial(inv_existing_after) != filter_trivial(inv_existing_before)):
            return  # do not modify user input if already created manually

        existing_after = defaultdict(list)
        for k, v in inv_existing_after.items():
            existing_after[v].append(k)
        to_delete = [
            line.id
            for line, key in inv_existing_before.items()
            if key not in needed_after
            and key in existing_after
            and before2after[key] not in needed_after
        ]
        to_delete_set = set(to_delete)
        to_delete.extend(line.id
            for line, key in inv_existing_after.items()
            if key not in needed_after and line.id not in to_delete_set
        )
        to_create = {
            key: values
            for key, values in needed_after.items()
            if key not in existing_after
        }
        to_write = {
            line: values
            for key, values in needed_after.items()
            for line in existing_after[key]
            if any(
                self.env['account.move.line']._fields[fname].convert_to_write(line[fname], self)
                != values[fname]
                for fname in values
            )
        }

        while to_delete and to_create:
            key = next(iter(to_create)) if len(to_create) > 1 else to_create
            values = to_create.pop(key)
            line_id = to_delete.pop(0)
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
                misc_container['records'] = container['records'].filtered(lambda m: m.is_entry() and not m.tax_cash_basis_origin_move_id)

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
                    existing_key_fname='discount_allocation_key',
                    needed_vals_fname='line_ids.discount_allocation_needed',
                    needed_dirty_fname='line_ids.discount_allocation_dirty',
                    line_type='discount',
                    container=invoice_container,
                ))
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
            (Markup('<br/>') + _('This recurring entry originated from %s', copied_am.auto_post_origin_id._get_html_link()))
        message_content = _('This entry has been reversed from %s', self._get_html_link()) if default.get('reversed_entry_id') else _('This entry has been duplicated from %s', self._get_html_link())
        copied_am._message_log(body=message_content + message_origin)

        return copied_am

    def _sanitize_vals(self, vals):
        if vals.get('invoice_line_ids') and vals.get('line_ids'):
            # values can sometimes be in only one of the two fields, sometimes in
            # both fields, sometimes one field can be explicitely empty while the other
            # one is not, sometimes not...
            update_vals = {
                line_id: line_vals[0]
                for command, line_id, *line_vals in vals['invoice_line_ids']
                if command == Command.UPDATE
            }
            for command, line_id, *line_vals in vals['line_ids']:
                if command == Command.UPDATE and line_id in update_vals:
                    line_vals[0].update(update_vals.pop(line_id))
            for line_id, line_vals in update_vals.items():
                vals['line_ids'] += [Command.update(line_id, line_vals)]
            for command, line_id, *line_vals in vals['invoice_line_ids']:
                assert command not in (Command.SET, Command.CLEAR)
                if [command, line_id, *line_vals] not in vals['line_ids']:
                    vals['line_ids'] += [(command, line_id, *line_vals)]
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
                raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the journal: %s.", ', '.join(move._get_integrity_hash_fields())))
            if (move.restrict_mode_hash_table and move.inalterable_hash and 'inalterable_hash' in vals) or (move.secure_sequence_number and 'secure_sequence_number' in vals):
                raise UserError(_('You cannot overwrite the values ensuring the inalterability of the accounting.'))
            if (move.posted_before and 'journal_id' in vals and move.journal_id.id != vals['journal_id']):
                raise UserError(_('You cannot edit the journal of an account move if it has been posted once.'))
            if (move.name and move.name != '/' and move.sequence_number not in (0, 1) and 'journal_id' in vals and move.journal_id.id != vals['journal_id'] and not move.quick_edit_mode):
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
            or any(self.company_id.mapped('quick_edit_mode'))
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

    @api.depends('partner_id', 'date', 'state', 'move_type')
    @api.depends_context('input_full_display_name')
    def _compute_display_name(self):
        for move in self:
            move.display_name = move._get_move_display_name(show_ref=True)

    def onchange(self, values, field_names, fields_spec):
        # Since only one field can be changed at the same time (the record is
        # saved when changing tabs) we can avoid building the snapshots for the
        # other field
        if 'line_ids' in field_names:
            values = {key: val for key, val in values.items() if key != 'invoice_line_ids'}
            fields_spec = {key: val for key, val in fields_spec.items() if key != 'invoice_line_ids'}
        elif 'invoice_line_ids' in field_names:
            values = {key: val for key, val in values.items() if key != 'line_ids'}
            fields_spec = {key: val for key, val in fields_spec.items() if key != 'line_ids'}
        return super().onchange(values, field_names, fields_spec)

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
        return self.state == 'posted' and not self.quick_edit_mode

    def _get_last_sequence_domain(self, relaxed=False):
        #pylint: disable=sql-injection
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
            if self.journal_id.payment_sequence:
                domain += [('payment_id', '!=' if self.payment_id else '=', False)]
            reference_move_name = self.sudo().search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
            if not reference_move_name:
                reference_move_name = self.sudo().search(domain, order='date asc', limit=1).name
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
            if self.payment_id:
                where_string += " AND payment_id IS NOT NULL "
            else:
                where_string += " AND payment_id IS NULL "

        return where_string, param

    def _get_starting_sequence(self):
        # EXTENDS account sequence.mixin
        self.ensure_one()
        if self.journal_id.type in ['sale', 'bank', 'cash']:
            starting_sequence = "%s/%04d/00000" % (self.journal_id.code, self.date.year)
        else:
            starting_sequence = "%s/%04d/%02d/0000" % (self.journal_id.code, self.date.year, self.date.month)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        if self.journal_id.payment_sequence and self.payment_id:
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
        return format_structured_reference_iso(self.id)

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
        return format_structured_reference_iso(partner_ref_nr)

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
        domain = [
            *self.env['account.move.line']._check_company_domain(company_id),
            ('partner_id', '=', partner_id),
            ('account_id.deprecated', '=', False),
            ('date', '>=', date.today() - timedelta(days=365 * 2)),
        ]
        if move_type in self.env['account.move'].get_inbound_types(include_receipts=True):
            domain.append(('account_id.internal_group', '=', 'income'))
        elif move_type in self.env['account.move'].get_outbound_types(include_receipts=True):
            domain.append(('account_id.internal_group', '=', 'expense'))

        query = self.env['account.move.line']._where_calc(domain)
        from_clause, where_clause, params = query.get_sql()
        self._cr.execute(f"""
            SELECT COUNT(foo.id), foo.account_id, foo.taxes
              FROM (
                         SELECT account_move_line__account_id.id AS account_id,
                                account_move_line__account_id.code,
                                account_move_line.id,
                                ARRAY_AGG(tax_rel.account_tax_id) FILTER (WHERE tax_rel.account_tax_id IS NOT NULL) AS taxes
                           FROM {from_clause}
                      LEFT JOIN account_move_line_account_tax_rel tax_rel ON account_move_line.id = tax_rel.account_move_line_id
                          WHERE {where_clause}
                       GROUP BY account_move_line__account_id.id,
                                account_move_line.id
                   ) AS foo
          GROUP BY foo.account_id, foo.code, foo.taxes
          ORDER BY COUNT(foo.id) DESC, foo.code, taxes ASC NULLS LAST
             LIMIT 1
        """, params)
        return self._cr.fetchone() or (0, False, False)

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

        # When a payment term has an early payment discount with the epd computation set to 'mixed', recomputing
        # the untaxed amount should take in consideration the discount percentage otherwise we'd get a wrong value.
        # We check that we have only one percentage tax as computing from multiple taxes with different types can get complicated.
        # In one example: let's say: base = 100, discount = 2%, tax = 21%
        # the total will be calculated as: total = base + (base * (1 - discount)) * tax
        # If we manipulate the equation to get the base from the total, we'll have base = total / ((1 - discount) * tax + 1)
        term = self.invoice_payment_term_id
        discount_percentage = term.discount_percentage if term.early_discount else 0
        remaining_amount = self.quick_edit_total_amount - self.tax_totals['amount_total']

        if (
                discount_percentage
                and term.early_pay_discount_computation == 'mixed'
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
    # EDI
    # -------------------------------------------------------------------------

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

    def _get_edi_decoder(self, file_data, new=False):
        """To be extended with decoding capabilities.
        :returns:  Function to be later used to import the file.
                   Function' args:
                   - invoice: account.move
                   - file_data: attachemnt information / value
                   - new: whether the invoice is newly created
                   returns True if was able to process the invoice
        """
        if file_data['type'] in ('pdf', 'binary'):
            return lambda *args: False
        return

    def _extend_with_attachments(self, attachments, new=False):
        """Main entry point to extend/enhance invoices with attachments.

        Either coming from:
        - The chatter when the user drops an attachment on an existing invoice.
        - The journal when the user drops one or multiple attachments from the dashboard.
        - The server mail alias when an alias is configured on the journal.

        It will unwrap all attachments by priority then try to decode until it succeed.

        :param attachments: A recordset of ir.attachment.
        :param new:         Indicate if the current invoice is a fresh one or an existing one.
        :returns:           True if at least one document is successfully imported
        """
        def close_file(file_data):
            if file_data.get('on_close'):
                file_data['on_close']()

        def add_file_data_results(file_data, invoice):
            passed_file_data_list.append(file_data)
            attachment = file_data.get('attachment') or file_data.get('originator_pdf')
            if attachment:
                if attachments_by_invoice.get(attachment):
                    attachments_by_invoice[attachment] |= invoice
                else:
                    attachments_by_invoice[attachment] = invoice
                if not attachment.res_id:
                    attachment.write({
                        'res_id': invoice.id,
                        'res_model': invoice._name,
                    })

        file_data_list = attachments._unwrap_edi_attachments()
        attachments_by_invoice = {}
        invoices = self
        current_invoice = self
        passed_file_data_list = []
        for file_data in file_data_list:

            # Rogue binaries from mail alias are skipped and unlinked.
            if (
                file_data['type'] == 'binary'
                and self._context.get('from_alias')
                and not attachments_by_invoice.get(file_data['attachment'])
                and file_data['attachment'].mimetype not in ALLOWED_MIMETYPES
            ):
                close_file(file_data)
                continue

            # The invoice has already been decoded by an embedded file.
            if attachments_by_invoice.get(file_data['attachment']):
                add_file_data_results(file_data, attachments_by_invoice[file_data['attachment']])
                close_file(file_data)
                continue

            # When receiving multiple files, if they have a different type, we supposed they are all linked
            # to the same invoice.
            if (
                passed_file_data_list
                and passed_file_data_list[-1]['filename'] != file_data['filename']
                and passed_file_data_list[-1]['sort_weight'] != file_data['sort_weight']
            ):
                add_file_data_results(file_data, invoices[-1])
                close_file(file_data)
                continue

            if passed_file_data_list and not new:
                add_file_data_results(file_data, invoices[-1])
                close_file(file_data)
                continue

            extend_with_existing_lines = file_data.get('process_if_existing_lines', False)
            if current_invoice.invoice_line_ids and not extend_with_existing_lines:
                continue

            decoder = (current_invoice or current_invoice.new(self.default_get(['move_type', 'journal_id'])))._get_edi_decoder(file_data, new=new)
            if decoder:
                try:
                    with self.env.cr.savepoint():
                        invoice = current_invoice or self.create({})
                        success = decoder(invoice, file_data, new)

                        if success or file_data['attachment'].mimetype in ALLOWED_MIMETYPES:
                            invoice._link_bill_origin_to_purchase_orders(timeout=4)
                            invoices |= invoice
                            current_invoice = self.env['account.move']
                            add_file_data_results(file_data, invoice)

                except RedirectWarning:
                    raise
                except Exception:
                    message = _("Error importing attachment '%s' as invoice (decoder=%s)", file_data['filename'], decoder.__name__)
                    current_invoice.sudo().message_post(body=message)
                    _logger.exception(message)

            passed_file_data_list.append(file_data)
            close_file(file_data)

        return attachments_by_invoice

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

        bases_details = {}
        payment_term_line = self.line_ids.filtered(lambda x: x.display_type == 'payment_term')
        discount_percentage = payment_term_line.move_id.invoice_payment_term_id.discount_percentage
        if not discount_percentage:
            return res
        early_pay_discount_computation = payment_term_line.move_id.invoice_payment_term_id.early_pay_discount_computation
        term_amount_currency = payment_term_line.amount_currency - payment_term_line.discount_amount_currency
        term_balance = payment_term_line.balance - payment_term_line.discount_balance
        if early_pay_discount_computation == 'included' and product_lines.tax_ids:
            # Compute the base amounts.
            resulting_delta_base_details = {}
            resulting_delta_tax_details = {}
            to_process = []
            for base_line in base_lines:
                invoice_line = base_line['record']
                to_update_vals, tax_values_list = self.env['account.tax']._compute_taxes_for_single_line(
                    base_line,
                    early_pay_discount_computation=early_pay_discount_computation,
                    early_pay_discount_percentage=discount_percentage,
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

                bases_details[frozendict(grouping_dict)] = base_detail

                # Compute the tax amounts.
                tax_details_with_epd = self.env['account.tax']._aggregate_taxes(
                    to_process,
                    grouping_key_generator=grouping_key_generator,
                )

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

            # Multiply the amount by the percentage
            percentage_paid = abs(payment_term_line.amount_residual_currency / self.amount_total)
            for tax_detail in resulting_delta_tax_details.values():
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

                res['tax_lines'][payment_term_line][frozendict(grouping_dict)] = {
                    'name': _("Early Payment Discount (%s)", tax.name),
                    'amount_currency': payment_term_line.currency_id.round(tax_detail['amount_currency'] * percentage_paid),
                    'balance': payment_term_line.company_currency_id.round(tax_detail['balance'] * percentage_paid),
                }

            for grouping_dict, base_detail in bases_details.items():
                res['base_lines'][payment_term_line][grouping_dict] = {
                    'name': _("Early Payment Discount"),
                    'amount_currency': payment_term_line.currency_id.round(base_detail['amount_currency'] * percentage_paid),
                    'balance': payment_term_line.company_currency_id.round(base_detail['balance'] * percentage_paid),
                }

            # Fix the rounding issue if any.
            delta_amount_currency = term_amount_currency \
                                    - sum(x['amount_currency'] for x in res['base_lines'][payment_term_line].values()) \
                                    - sum(x['amount_currency'] for x in res['tax_lines'][payment_term_line].values())
            delta_balance = term_balance \
                            - sum(x['balance'] for x in res['base_lines'][payment_term_line].values()) \
                            - sum(x['balance'] for x in res['tax_lines'][payment_term_line].values())

            biggest_base_line = max(list(res['base_lines'][payment_term_line].values()), key=lambda x: x['amount_currency'])
            biggest_base_line['amount_currency'] += delta_amount_currency
            biggest_base_line['balance'] += delta_balance

        else:
            grouping_dict = {'account_id': cash_discount_account.id}

            res['term_lines'][payment_term_line][frozendict(grouping_dict)] = {
                'name': _("Early Payment Discount"),
                'partner_id': payment_term_line.partner_id.id,
                'currency_id': payment_term_line.currency_id.id,
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
                        'display_type': 'epd',  # Used to compute tax_tag_invert for early payment discount lines
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
            if self.id:
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

    def _reconcile_reversed_moves(self, reverse_moves, move_reverse_cancel):
        ''' Reconciles moves in self and reverse moves
        :param move_reverse_cancel: parameter used when lines are reconciled
                                    will determine whether the tax cash basis journal entries should be created
        :param reverse_moves:       An account.move recordset, reverse of the current self.
        :return:                    An account.move recordset, reverse of the current self.
        '''
        for move, reverse_move in zip(self, reverse_moves):
            group = (move.line_ids + reverse_move.line_ids) \
                .filtered(lambda l: not l.reconciled) \
                .grouped(lambda l: (l.account_id, l.currency_id))
            for (account, _currency), lines in group.items():
                if account.reconcile or account.account_type in ('asset_cash', 'liability_credit_card'):
                    lines.with_context(move_reverse_cancel=move_reverse_cancel).reconcile()
        return reverse_moves


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

        return reverse_moves

    def _can_be_unlinked(self):
        self.ensure_one()
        lock_date = self.company_id._get_user_fiscal_lock_date()
        return not self.inalterable_hash and self.date > lock_date

    def _is_protected_by_audit_trail(self):
        return False

    def _unlink_or_reverse(self):
        if not self:
            return
        to_unlink = self.env['account.move']
        to_cancel = self.env['account.move']
        to_reverse = self.env['account.move']
        for move in self:
            if not move._can_be_unlinked():
                to_reverse += move
            elif move._is_protected_by_audit_trail():
                to_cancel += move
            else:
                to_unlink += move
        to_unlink.filtered(lambda m: m.state in ('posted', 'cancel')).button_draft()
        to_unlink.filtered(lambda m: m.state == 'draft').unlink()
        to_cancel.button_cancel()
        return to_reverse._reverse_moves(cancel=True)

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
            if move.state in ['posted', 'cancel']:
                raise UserError(_('The entry %s (id %s) must be in draft.', move.name, move.id))
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

            if move.line_ids.account_id.filtered(lambda account: account.deprecated) and not self._context.get('skip_account_deprecation_check'):
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

        # reconcile if state is in draft and move has reversal_entry_id set
        draft_reverse_moves = to_post.filtered(lambda move: move.reversed_entry_id and move.reversed_entry_id.state == 'posted')

        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        draft_reverse_moves.reversed_entry_id._reconcile_reversed_moves(draft_reverse_moves, self._context.get('move_reverse_cancel', False))
        to_post.line_ids._reconcile_marked()

        for invoice in to_post:
            partner_id = invoice.partner_id
            subscribers = [partner_id.id] if partner_id and partner_id not in invoice.sudo().message_partner_ids else None
            invoice.message_subscribe(subscribers)

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

    def _find_and_set_purchase_orders(self, po_references, partner_id, amount_total, from_ocr=False, timeout=10):
        # hook to be used with purchase, so that vendor bills are sync/autocompleted with purchase orders
        self.ensure_one()

    def _link_bill_origin_to_purchase_orders(self, timeout=10):
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

    def action_update_fpos_values(self):
        self.invoice_line_ids._compute_tax_ids()
        self.line_ids._compute_account_id()

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

    def action_switch_move_type(self):
        if any(move.posted_before for move in self):
            raise ValidationError(_("You cannot switch the type of a posted document."))
        if any(move.move_type == "entry" for move in self):
            raise ValidationError(_("This action isn't available for this document."))

        for move in self:
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
        return self.line_ids.action_register_payment()

    def action_duplicate(self):
        # offer the possibility to duplicate thanks to a button instead of a hidden menu, which is more visible
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['context'] = dict(self.env.context)
        action['context']['view_no_maturity'] = False
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.copy().id
        return action

    def action_send_and_print(self):
        template = self.env.ref(self._get_mail_template(), raise_if_not_found=False)

        if any(not x.is_sale_document(include_receipts=True) for x in self):
            raise UserError(_("You can only send sales documents"))

        return {
            'name': _("Send"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.send',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'default_mail_template_id': template and template.id or False,
            },
        }

    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()

        report_action = self.action_send_and_print()
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
        if any(move.state not in ('cancel', 'posted') for move in self):
            raise UserError(_("Only posted/cancelled journal entries can be reset to draft."))
        if any(move.need_cancel_request for move in self):
            raise UserError(_("You can't reset to draft those journal entries. You need to request a cancellation instead."))

        self._check_draftable()
        # We remove all the analytics entries for this journal
        self.mapped('line_ids.analytic_line_ids').unlink()
        self.mapped('line_ids').remove_move_reconcile()
        self.state = 'draft'

    def _check_draftable(self):
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

    def button_request_cancel(self):
        """ Hook allowing the localizations to request a cancellation from the government before cancelling the invoice. """
        self.ensure_one()
        if not self.need_cancel_request:
            raise UserError(_("You can only request a cancellation for invoice sent to the government."))

    def button_cancel(self):
        # Shortcut to move from posted to cancelled directly. This is useful for E-invoices that must not be changed
        # when sent to the government.
        moves_to_reset_draft = self.filtered(lambda x: x.state == 'posted')
        if moves_to_reset_draft:
            moves_to_reset_draft.button_draft()

        if any(move.state != 'draft' for move in self):
            raise UserError(_("Only draft journal entries can be cancelled."))

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

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(message, model_description, msg_vals=msg_vals)
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
                lambda pdata: pdata['id'] in local_msg_vals.get('partner_ids', []) and pdata['id'] != self.partner_id.id and pdata['type'] != 'user',
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

    @api.model
    def _cron_account_move_send(self, job_count=10):
        """ Handle Send & Print async processing.
        :param job_count: maximum number of jobs to process if specified.
        """
        def get_account_notification(partner, moves, is_success):
            return [
                partner,
                'account_notification',
                {
                    'type': 'success' if is_success else 'warning',
                    'title': _('Invoices sent') if is_success else _('Invoices in error'),
                    'message': _('Invoices sent successfully.') if is_success else _(
                        "One or more invoices couldn't be processed."),
                    'action_button': {
                        'name': _('Open'),
                        'action_name': _('Sent invoices') if is_success else _('Invoices in error'),
                        'model': 'account.move',
                        'res_ids': moves.ids,
                    },
                },
            ]

        limit = job_count + 1
        to_process = self.env['account.move'].search(
            [('send_and_print_values', '!=', False)],
            limit=limit,
        )
        need_retrigger = len(to_process) > job_count
        if not to_process:
            return

        all_moves = to_process[:job_count]
        for _company, moves in all_moves.grouped('company_id').items():
            try:
                # Lock moves
                with self.env.cr.savepoint(flush=False):
                    self._cr.execute('SELECT * FROM account_move WHERE id IN %s FOR UPDATE NOWAIT', [tuple(moves.ids)])

            except psycopg2.errors.LockNotAvailable:
                _logger.debug('Another transaction already locked documents rows. Cannot process documents.')
                continue

            # Collect moves by res.partner that executed the Send & Print wizard, must be done before the _process
            # that modify send_and_print_values.
            moves_by_partner = moves.grouped(lambda m: m.send_and_print_values['sp_partner_id'])

            self.env['account.move.send']._process_send_and_print(moves)

            notifications = []
            for partner_id, partner_moves in moves_by_partner.items():
                partner = self.env['res.partner'].browse(partner_id)
                partner_moves_error = partner_moves.filtered(lambda m: m.send_and_print_values and m.send_and_print_values.get('error'))
                if partner_moves_error:
                    notifications.append(get_account_notification(partner, partner_moves_error, False))
                partner_moves_success = partner_moves - partner_moves_error
                if partner_moves_success:
                    notifications.append(get_account_notification(partner, partner_moves_success, True))
                partner_moves_error.send_and_print_values = False

            self.env['bus.bus']._sendmany(notifications)

        if need_retrigger:
            self.env.ref('account.ir_cron_account_move_send')._trigger()

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def get_invoice_types(self, include_receipts=False):
        return self.get_sale_types(include_receipts) + self.get_purchase_types(include_receipts)

    def is_invoice(self, include_receipts=False):
        return self.is_sale_document(include_receipts) or self.is_purchase_document(include_receipts)

    def is_entry(self):
        return self.move_type == 'entry'

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
        highest_name = self.highest_name or self._get_last_sequence(relaxed=True)
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
        return self.company_id._get_violated_lock_dates(invoice_date, has_tax)

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
            error_msg = self.partner_bank_id._get_error_messages_for_qr(self.qr_code_method, self.partner_id, self.currency_id)
            if error_msg:
                raise UserError(error_msg)
        else:
            # Else we find one that's eligible and assign it to the invoice
            for candidate_method, _candidate_name in self.env['res.partner.bank'].get_available_qr_methods_in_sequence():
                error_msg = self.partner_bank_id._get_error_messages_for_qr(candidate_method, self.partner_id, self.currency_id)
                if not error_msg:
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

    def _get_pdf_and_send_invoice_vals(self, template, **kwargs):
        return {
            'mail_template_id': template.id,
            'move_ids': self.ids,
            'checkbox_send_mail': True,
            'checkbox_download': False,
            **kwargs,
        }

    def _generate_pdf_and_send_invoice(self, template, force_synchronous=True, allow_fallback_pdf=True, bypass_download=False, **kwargs):
        """ Generate the pdf for the current invoices and send them by mail using the send & print wizard.
        :param force_synchronous:   Flag indicating if the method should be done synchronously.
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        :param bypass_download: Don't trigger the action from action_send_and_print and get generated attachments_ids instead.
        """
        composer_vals = self._get_pdf_and_send_invoice_vals(template, **kwargs)
        composer = self.env['account.move.send'].create(composer_vals)
        return composer.action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf, bypass_download=bypass_download)

    def _get_invoice_legal_documents(self):
        """ Return existing attachments or a temporary Pro Forma pdf. """
        self.ensure_one()
        if self.invoice_pdf_report_id:
            attachments = self.env['account.move.send']._get_invoice_extra_attachments(self)
        else:
            content, _ = self.env['ir.actions.report']._render('account.account_invoices', self.ids, data={'proforma': True})
            attachments = self.env['ir.attachment'].new({
                'raw': content,
                'name': self._get_invoice_proforma_pdf_report_filename(),
                'mimetype': 'application/pdf',
                'res_model': self._name,
                'res_id': self.id,
            })
        return attachments

    def get_invoice_pdf_report_attachment(self):
        if len(self) < 2 and self.invoice_pdf_report_id:
            # if the Send & Print succeeded
            return self.invoice_pdf_report_id.raw, self.invoice_pdf_report_id.name
        elif len(self) < 2 and self.message_main_attachment_id:
            # if the Send & Print failed with fallback=True -> proforma PDF
            return self.message_main_attachment_id.raw, self.message_main_attachment_id.name
        # all other cases
        pdf_content = self.env['ir.actions.report']._render('account.account_invoices', self.ids)[0]
        pdf_name = self._get_invoice_report_filename() if len(self) == 1 else "Invoices.pdf"
        return pdf_content, pdf_name

    def _get_invoice_report_filename(self, extension='pdf'):
        """ Get the filename of the generated invoice report with extension file. """
        self.ensure_one()
        return f"{self.name.replace('/', '_')}.{extension}"

    def _get_invoice_proforma_pdf_report_filename(self):
        """ Get the filename of the generated proforma PDF invoice report. """
        self.ensure_one()
        return f"{self.name.replace('/', '_')}_proforma.pdf"

    def _prepare_edi_vals_to_export(self):
        ''' The purpose of this helper is to prepare values in order to export an invoice through the EDI system.
        This includes the computation of the tax details for each invoice line that could be very difficult to
        handle regarding the computation of the base amount.

        :return: A python dict containing default pre-processed values.
        '''
        self.ensure_one()

        res = {
            'record': self,
            'balance_multiplicator': -1 if self.is_inbound() else 1,
            'invoice_line_vals_list': [],
        }

        # Invoice lines details.
        for index, line in enumerate(self.invoice_line_ids.filtered(lambda line: line.display_type == 'product'), start=1):
            line_vals = line._prepare_edi_vals_to_export()
            line_vals['index'] = index
            res['invoice_line_vals_list'].append(line_vals)

        # Totals.
        res.update({
            'total_price_subtotal_before_discount': sum(x['price_subtotal_before_discount'] for x in res['invoice_line_vals_list']),
            'total_price_discount': sum(x['price_discount'] for x in res['invoice_line_vals_list']),
        })

        return res

    def _get_discount_allocation_account(self):
        if self.is_sale_document(include_receipts=True) and self.company_id.account_discount_expense_allocation_id:
            return self.company_id.account_discount_expense_allocation_id
        if self.is_purchase_document(include_receipts=True) and self.company_id.account_discount_income_allocation_id:
            return self.company_id.account_discount_income_allocation_id
        return None

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
            msg_dict['body'] = Markup('<div><div><h3>%s</h3></div>%s</div>') % (msg_dict['subject'], msg_dict['body'])

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
        attachments_per_invoice = defaultdict(lambda: self.env['ir.attachment'])

        checked_attachment = self._check_and_decode_attachment(attachments)
        if not checked_attachment:
            return res

        for attachment_in_res, invoices in checked_attachment.items():
            invoices = invoices or self
            for invoice in invoices:
                attachments_per_invoice[invoice] |= attachment_in_res

        for invoice, attachments in attachments_per_invoice.items():
            if invoice == self:
                invoice.attachment_ids |= attachments
                new_message.attachment_ids = attachments.ids
                message_values.update({'res_id': self.id, 'attachment_ids': [Command.link(attachment.id) for attachment in attachments]})
                super(AccountMove, invoice)._message_post_after_hook(new_message, message_values)
            else:
                sub_new_message = new_message.copy({'attachment_ids': attachments.ids})
                sub_message_values = {
                    **message_values,
                    'res_id': invoice.id,
                    'attachment_ids': [Command.link(attachment.id) for attachment in attachments],
                }
                invoice.attachment_ids |= attachments
                invoice.message_ids = [Command.set(sub_new_message.id)]
                super(AccountMove, invoice)._message_post_after_hook(sub_new_message, sub_message_values)

        return res

    def _check_and_decode_attachment(self, attachments):
        if not attachments or self.env.context.get('no_new_invoice') or not self.is_invoice(include_receipts=True):
            return False
        if self.state != 'draft':
            self.with_user(SUPERUSER_ID).message_post(
                body=_('The invoice is not a draft, it was not updated from the attachment.'),
                message_type='comment',
            )
            return False

        # As we are coming from the mail, we assume that ONE of the attachments
        # will enhance the invoice thanks to EDI / OCR / .. capabilities
        move_per_decodable_attachment = self._extend_with_attachments(attachments, new=bool(self._context.get('from_alias')))
        if self.invoice_line_ids and not move_per_decodable_attachment:
            self.with_user(SUPERUSER_ID).message_post(
                body=_('The invoice already contains lines, it was not updated from the attachment.'),
                message_type='comment',
            )
            return False
        attachments_in_invoices = self.env['ir.attachment']
        for attachment in move_per_decodable_attachment:
            attachments_in_invoices += attachment
        # Unlink the unused attachments (prevents storing marketing images sent with emails)
        if self._context.get('from_alias'):
            (attachments - attachments_in_invoices).unlink()
        return move_per_decodable_attachment

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
        if (
            self.invoice_date_due
            and self.is_invoice(include_receipts=True)
            and self.payment_state not in ('in_payment', 'paid')
        ):
            subtitles.append(_('%(amount)s due\N{NO-BREAK SPACE}%(date)s',
                           amount=format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang')),
                           date=format_date(self.env, self.invoice_date_due, date_format='short', lang_code=render_context.get('lang'))
                          ))
        else:
            subtitles.append(format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang')))
        render_context['subtitles'] = subtitles
        return render_context

    def _get_mail_thread_data_attachments(self):
        res = super()._get_mail_thread_data_attachments()
        # else, attachments with 'res_field' get excluded
        return res | self.env['account.move.send']._get_invoice_extra_attachments(self)

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

    def _can_force_cancel(self):
        """ Hook to indicate whether it should be possible to force-cancel this invoice,
        that is, cancel it without waiting for the cancellation request to succeed.
        """
        self.ensure_one()
        return False

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

    def _is_downpayment(self):
        ''' Return true if the invoice is a downpayment.
        Down-payments can be created from a sale order. This method is overridden in the sale order module.
        '''
        return False

    def _refunds_origin_required(self):
        return False

    def _set_reversed_entry(self, credit_note):
        """ Try to find the original invoice for a single credit_note. """
        if len(credit_note) != 1 or credit_note.move_type != 'out_refund':
            return

        original_invoice = self.filtered(lambda inv: inv.move_type == 'out_invoice'
                                         and credit_note.invoice_line_ids.sale_line_ids in inv.invoice_line_ids.sale_line_ids)
        if len(original_invoice) == 1 and original_invoice._refunds_origin_required():
            credit_note.reversed_entry_id = original_invoice.id

    @api.model
    def get_invoice_localisation_fields_required_to_invoice(self, country_id):
        """ Returns the list of fields that needs to be filled when creating an invoice for the selected country.
        This is required for some flows that would allow a user to request an invoice from the portal.
        Using these, we can get their information and dynamically create form inputs based for the fields required legally for the company country_id.
        The returned fields must be of type ir.model.fields in order to handle translations

        :param country_id: The country for which we want the fields.
        :return: an array of ir.model.fields for which the user should provide values.
        """
        return []

    @staticmethod
    def _can_commit():
        """ Helper to know if we can commit the current transaction or not.

        :returns: True if commit is acceptable, False otherwise.
        """
        return not tools.config['test_enable'] and not modules.module.current_test
