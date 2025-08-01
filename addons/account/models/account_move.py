# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import calendar
from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from json import dumps
import logging
from markupsafe import Markup
import re
import os
from textwrap import shorten

from odoo import api, fields, models, _, modules
from odoo.tools.sql import column_exists, create_column
from odoo.addons.account.tools import format_structured_reference_iso
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.fields import Command, Domain
from odoo.tools.misc import clean_context
from odoo.tools import (
    date_utils,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    OrderedSet,
    SQL,
)
from odoo.tools.mail import email_re, email_split, is_html_empty, generate_tracking_message_id
from odoo.tools.misc import StackMap


_logger = logging.getLogger(__name__)


MAX_HASH_VERSION = 4

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('blocked', 'Blocked'),
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

EMPTY = object()
BYPASS_LOCK_CHECK = object()


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['portal.mixin', 'mail.thread.main.attachment', 'mail.activity.mixin', 'sequence.mixin', 'product.catalog.mixin', 'account.document.import.mixin']
    _description = "Journal Entry"
    _order = 'date desc, name desc, invoice_date desc, id desc'
    _mail_post_access = 'read'
    _check_company_auto = True
    _sequence_index = "journal_id"
    _rec_names_search = ['name', 'partner_id.name', 'ref']
    _mailing_enabled = True

    @property
    def _sequence_monthly_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_monthly_regex

    @property
    def _sequence_yearly_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_yearly_regex

    @property
    def _sequence_year_range_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_year_range_regex

    @property
    def _sequence_fixed_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_fixed_regex

    @property
    def _sequence_year_range_monthly_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_year_range_monthly_regex

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
    name_placeholder = fields.Char(compute='_compute_name_placeholder')
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
    journal_group_id = fields.Many2one(
        'account.journal.group',
        string='Ledger',
        store=False,
        search='_search_journal_group_id',
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
        string='Account Move Line Items',
        copy=True,
    )

    journal_line_ids = fields.One2many(  # /!\ journal_line_ids is just a subset of line_ids.
        comodel_name='account.move.line',
        inverse_name='move_id',
        string='Journal Items',
        copy=False,
        domain=[('display_type', 'not in', ('line_section', 'line_subsection', 'line_note'))],
    )

    # === Link to the partial that created this exchange move === #
    exchange_diff_partial_ids = fields.One2many(
        comodel_name='account.partial.reconcile',
        inverse_name='exchange_move_id',
        string='Related reconciliation',
    )

    # === Payment fields === #
    origin_payment_id = fields.Many2one(  # the payment this is the journal entry of
        comodel_name='account.payment',
        string="Payment",
        index='btree_not_null',
        copy=False,
        check_company=True,
    )
    matched_payment_ids = fields.Many2many(  # the payments linked to this invoice
        string="Matched Payments",
        comodel_name='account.payment',
        relation='account_move__account_payment',
        column1='invoice_id',
        column2='payment_id',
        copy=False,
    )
    payment_count = fields.Integer(compute='_compute_payment_count')

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

    # === Adjusting Entries fields === #
    adjusting_entry_origin_move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='adjusting_entries__account_move',
        column1='move_id',
        column2='adjusting_entry_move_id',
        string="Adjusting Entry Origin Moves",
    )
    adjusting_entry_origin_label = fields.Char(compute="_compute_adjusting_entry_origin_label")
    adjusting_entry_origin_moves_count = fields.Integer(
        string="Adjusting Entry Origin Moves Count",
        compute='_compute_adjusting_entry_origin_moves_count',
    )
    adjusting_entries_move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='adjusting_entries__account_move',
        column1='adjusting_entry_move_id',
        column2='move_id',
        string="Created Adjusting Entries",
    )
    adjusting_entries_count = fields.Integer(
        string="Adjusting Entries Count",
        compute='_compute_adjusting_entries_count',
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
    checked = fields.Boolean(
        string='Reviewed',
        compute='_compute_checked',
        store=True, readonly=False, tracking=True, copy=False,
    )
    posted_before = fields.Boolean(copy=False)
    suitable_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_suitable_journal_ids',
    )
    highest_name = fields.Char(compute='_compute_highest_name')
    made_sequence_gap = fields.Boolean(compute='_compute_made_sequence_gap', store=True)  # store wether this is the first move breaking the natural sequencing
    show_name_warning = fields.Boolean(store=False)
    type_name = fields.Char('Type Name', compute='_compute_type_name')
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', readonly=True)
    company_price_include = fields.Selection(related='company_id.account_price_include', readonly=True)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'account.move')], string='Attachments')
    audit_trail_message_ids = fields.One2many(
        'mail.message',
        'res_id',
        domain=[
            ('model', '=', 'account.move'),
            ('message_type', '=', 'notification'),
        ],
        string='Audit Trail Messages',
    )

    # === Hash Fields === #
    restrict_mode_hash_table = fields.Boolean(related='journal_id.restrict_mode_hash_table')
    secure_sequence_number = fields.Integer(string="Inalterability No Gap Sequence #", readonly=True, copy=False, index=True)
    inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False, index='btree_not_null')
    secured = fields.Boolean(
        compute="_compute_secured",
        search='_search_secured',
        help="The entry is secured with an inalterable hash."
    )

    # ==============================================================================================
    #                                          INVOICE
    # ==============================================================================================

    invoice_line_ids = fields.One2many(  # /!\ invoice_line_ids is just a subset of line_ids.
        'account.move.line',
        'move_id',
        string='Invoice lines',
        copy=False,
        domain=[('display_type', 'in', ('product', 'line_section', 'line_subsection', 'line_note'))],
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
        precompute=True,
        readonly=False,
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
        index='btree_not_null',
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
    display_link_qr_code = fields.Boolean(
        string="Display Link QR-code",
        compute='_compute_display_link_qr_code',
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
        compute='_compute_invoice_has_outstanding',
    )
    invoice_payments_widget = fields.Binary(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_reconciled_info',
        exportable=False,
    )

    preferred_payment_method_line_id = fields.Many2one(
        string="Preferred Payment Method Line",
        comodel_name='account.payment.method.line',
        compute='_compute_preferred_payment_method_line_id',
        store=True,
        readonly=False,
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
    expected_currency_rate = fields.Float(
        compute="_compute_expected_currency_rate",
        digits=0,
    )
    invoice_currency_rate = fields.Float(
        string='Currency Rate',
        compute='_compute_invoice_currency_rate', store=True, precompute=True,
        readonly=False,
        copy=False,
        digits=0,
        help="Currency rate from company currency to document currency.",
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
    amount_untaxed_in_currency_signed = fields.Monetary(
        string="Untaxed Amount Signed Currency",
        compute='_compute_amount', store=True, readonly=True,
        currency_field='currency_id',
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
    status_in_payment = fields.Selection(
        selection=PAYMENT_STATE_SELECTION + [
            ('draft', "Draft"),
            ('posted', 'Posted'),
            ('sent', "Sent"),
            ('cancel', "Cancelled"),
        ],
        compute='_compute_status_in_payment',
        copy=False,
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
    reversal_move_ids = fields.One2many('account.move', 'reversed_entry_id')

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
    is_manually_modified = fields.Boolean()

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
        help="It indicates that the invoice/payment has been sent or the PDF has been generated.",
    )
    is_being_sent = fields.Boolean(
        help="Is the move being sent asynchronously",
        compute='_compute_is_being_sent'
    )

    move_sent_values = fields.Selection(
        selection=[
            ('sent', 'Sent'),
            ('not_sent', 'Not Sent'),
        ],
        string='Sent',
        compute='compute_move_sent_values',
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
    sending_data = fields.Json(copy=False)
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
    duplicated_ref_ids = fields.Many2many(comodel_name='account.move', compute='_compute_duplicated_ref_ids')
    need_cancel_request = fields.Boolean(compute='_compute_need_cancel_request')

    show_update_fpos = fields.Boolean(string="Has Fiscal Position Changed", store=False)  # True if the fiscal position was changed

    # used to display the various dates and amount dues on the invoice's PDF
    payment_term_details = fields.Binary(compute="_compute_payment_term_details", exportable=False)
    show_payment_term_details = fields.Boolean(compute="_compute_show_payment_term_details")
    show_discount_details = fields.Boolean(compute="_compute_show_payment_term_details")

    abnormal_amount_warning = fields.Text(compute='_compute_abnormal_warnings')
    abnormal_date_warning = fields.Text(compute='_compute_abnormal_warnings')
    alerts = fields.Json(compute='_compute_alerts')

    taxes_legal_notes = fields.Html(string='Taxes Legal Notes', compute='_compute_taxes_legal_notes')

    # payment_date is the minimum payment_date of the unpaid lines of the move.
    next_payment_date = fields.Date(
        string='Next Payment Date',
        compute='_compute_next_payment_date',
        search='_search_next_payment_date',
    )

    display_send_button = fields.Boolean(compute='_compute_display_send_button')
    highlight_send_button = fields.Boolean(compute='_compute_highlight_send_button')

    _checked_idx = models.Index("(journal_id) WHERE (checked IS NOT TRUE)")
    _payment_idx = models.Index("(journal_id, state, payment_state, move_type, date)")
    _unique_name = models.UniqueIndex(
        "(name, journal_id) WHERE (state = 'posted'AND name != '/')",
        "Another entry with the same name already exists.",
    )
    _journal_id_company_id_idx = models.Index('(journal_id, company_id, date)')
    # used in <account.journal>._query_has_sequence_holes
    _made_gaps = models.Index('(journal_id, state, payment_state, move_type, date) WHERE (made_sequence_gap IS TRUE)')
    _duplicate_bills_idx = models.Index("(ref) WHERE (move_type IN ('in_invoice', 'in_refund'))")

    def _auto_init(self):
        super()._auto_init()
        if not column_exists(self.env.cr, "account_move", "preferred_payment_method_line_id"):
            create_column(self.env.cr, "account_move", "preferred_payment_method_line_id", "int4")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'partner_id')
    def _compute_invoice_default_sale_person(self):
        # We want to modify the sale person only when we don't have one and if the move type corresponds to this condition
        # If the move doesn't correspond, we remove the sale person
        for move in self:
            if move.is_sale_document(include_receipts=True):
                if move.partner_id:
                    move.invoice_user_id = (
                        move.invoice_user_id
                        or move.partner_id.user_id
                        or move.partner_id.commercial_partner_id.user_id
                        or self.env.user
                    )
            else:
                move.invoice_user_id = False

    @api.depends('sending_data')
    def _compute_is_being_sent(self):
        for move in self:
            move.is_being_sent = bool(move.sending_data)

    @api.depends('is_move_sent')
    def compute_move_sent_values(self):
        for move in self:
            move.move_sent_values = 'sent' if move.is_move_sent else 'not_sent'

    def _compute_payment_reference(self):
        for move in self.filtered(lambda m: (
            m.state == 'posted'
            and m.move_type == 'out_invoice'
            and not m.payment_reference
        )):
            move.payment_reference = move._get_invoice_computed_reference()
        self._inverse_payment_reference()

    @api.depends('invoice_date', 'company_id', 'move_type')
    def _compute_date(self):
        for move in self:
            if not move.invoice_date or not move.is_invoice(include_receipts=True):
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
                or record.auto_post != 'no' and \
                record.date and record.date > fields.Date.context_today(record)

    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            if move.journal_id.company_id not in move.company_id.parent_ids:
                move.company_id = (move.journal_id.company_id or self.env.company)._accessible_branches()[:1]

    @api.depends('move_type', 'origin_payment_id', 'statement_line_id')
    def _compute_journal_id(self):
        for move in self.filtered(lambda r: r.journal_id.type not in r._get_valid_journal_types()):
            move.journal_id = move._search_default_journal()

    def _get_valid_journal_types(self):
        if self.is_sale_document(include_receipts=True):
            return ['sale']
        elif self.is_purchase_document(include_receipts=True):
            return ['purchase']
        elif self.origin_payment_id or self.statement_line_id or self.env.context.get('is_payment') or self.env.context.get('is_statement_line'):
            return ['bank', 'cash', 'credit']
        return ['general']

    def _search_default_journal(self):
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
            currency_id = self.currency_id.id or self.env.context.get('default_currency_id')
            if currency_id and currency_id != company.currency_id.id:
                currency_domain = domain + [('currency_id', '=', currency_id)]
                journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            error_msg = self.env['account.journal']._build_no_journal_error_msg(company.display_name, journal_types)
            raise UserError(error_msg)

        return journal

    @api.depends('move_type')
    def _compute_is_storno(self):
        for move in self:
            move.is_storno = move.is_storno or (move.move_type in ('out_refund', 'in_refund') and move.company_id.account_storno)

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            m.suitable_journal_ids = self._get_suitable_journal_ids(m.move_type, m.company_id)

    @api.depends('posted_before', 'state', 'journal_id', 'date', 'move_type', 'origin_payment_id')
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m._origin.id))

        for move in self:
            if move.state == 'cancel':
                continue

            move_has_name = move.name and move.name != '/'
            if not move.posted_before and not move._sequence_matches_date():
                # The name does not match the date and the move is not the first in the period:
                # Reset to draft
                move.name = False
                continue
            if move.date and not move_has_name and move.state != 'draft':
                move._set_next_sequence()

        self._inverse_name()

    @api.depends('date', 'journal_id', 'move_type', 'name', 'posted_before', 'sequence_number', 'sequence_prefix', 'state')
    def _compute_name_placeholder(self):
        for move in self:
            if (not move.name or move.name == '/') and move.date and not move._get_last_sequence():
                sequence_format_string, sequence_format_values = move._get_next_sequence_format()
                sequence_format_values['seq'] = sequence_format_values['seq'] + 1
                move.name_placeholder = sequence_format_string.format(**sequence_format_values)
            else:
                move.name_placeholder = False

    @api.depends('journal_id', 'date')
    def _compute_highest_name(self):
        for record in self:
            record.highest_name = record._get_last_sequence()

    @api.depends('journal_id', 'sequence_number', 'sequence_prefix', 'state')
    def _compute_made_sequence_gap(self):
        unposted = self.filtered(lambda move: move.sequence_number != 0 and move.state != 'posted')
        unposted.made_sequence_gap = True
        for (journal, prefix), moves in (self - unposted).grouped(lambda m: (m.journal_id, m.sequence_prefix)).items():
            previous_numbers = set(self.env['account.move'].sudo().search([
                ('journal_id', '=', journal.id),
                ('sequence_prefix', '=', prefix),
                ('sequence_number', '>=', min(moves.mapped('sequence_number')) - 1),
                ('sequence_number', '<=', max(moves.mapped('sequence_number')) - 1),
            ]).mapped('sequence_number'))
            for move in moves:
                move.made_sequence_gap = move.sequence_number > 1 and (move.sequence_number - 1) not in previous_numbers

    @api.depends_context('lang')
    @api.depends('move_type')
    def _compute_type_name(self):
        type_name_mapping = dict(
            self._fields['move_type']._description_selection(self.env),
            out_invoice=_('Invoice'),
            out_refund=_('Credit Note'),
        )

        for record in self:
            record.type_name = type_name_mapping[record.move_type]

    @api.depends('inalterable_hash')
    def _compute_secured(self):
        for move in self:
            move.secured = bool(move.inalterable_hash)

    def _search_secured(self, operator, value):
        if operator != 'in':
            return NotImplemented
        assert list(value) == [True]
        return [('inalterable_hash', '!=', False)]

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

    def _get_invoice_currency_rate_date(self):
        self.ensure_one()
        return self.invoice_date or fields.Date.context_today(self)

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date')
    def _compute_expected_currency_rate(self):
        for move in self:
            if move.currency_id:
                move.expected_currency_rate = move.env['res.currency']._get_conversion_rate(
                    from_currency=move.company_currency_id,
                    to_currency=move.currency_id,
                    company=move.company_id,
                    date=move._get_invoice_currency_rate_date(),
                )
            else:
                move.expected_currency_rate = 1

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date')
    def _compute_invoice_currency_rate(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                move.invoice_currency_rate = move.expected_currency_rate

    @api.depends('move_type')
    def _compute_direction_sign(self):
        for invoice in self:
            if invoice.move_type == 'entry' or invoice.is_outbound():
                invoice.direction_sign = 1
            else:
                invoice.direction_sign = -1

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
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
                    if line.display_type in ('tax', 'non_deductible_tax') or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding', 'non_deductible_product', 'non_deductible_product_total'):
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
            move.amount_untaxed_in_currency_signed = -total_untaxed_currency
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)

    @api.depends('amount_residual', 'move_type', 'state', 'company_id', 'matched_payment_ids.state')
    def _compute_payment_state(self):
        def _invoice_qualifies(move):
            currency = move.currency_id or move.company_id.currency_id or self.env.company.currency_id
            return move.is_invoice(True) and (
                move.state == 'posted'
                or (move.state == 'draft' and not currency.is_zero(move.amount_total))
            )

        groups = self.grouped(lambda move:
            'legacy' if move.payment_state == 'invoicing_legacy' else
            'invoices' if _invoice_qualifies(move) else
            'blocked' if move.payment_state == 'blocked' else
            'unpaid'
        )
        groups.get('unpaid', self.browse()).payment_state = 'not_paid'
        invoices = groups.get('invoices', self.browse())

        stored_ids = tuple(invoices.ids)
        if stored_ids:
            self.env['account.partial.reconcile'].flush_model()
            self.env['account.payment'].flush_model(['is_matched'])

            queries = []
            for source_field, counterpart_field in (
                ('debit_move_id', 'credit_move_id'),
                ('credit_move_id', 'debit_move_id'),
            ):
                queries.append(SQL('''
                    SELECT
                        source_line.id AS source_line_id,
                        source_line.move_id AS source_move_id,
                        account.account_type AS source_line_account_type,
                        ARRAY_AGG(counterpart_move.move_type) AS counterpart_move_types,
                        COALESCE(BOOL_AND(COALESCE(pay.is_matched, FALSE))
                            FILTER (WHERE counterpart_move.origin_payment_id IS NOT NULL), TRUE) AS all_payments_matched,
                        BOOL_OR(COALESCE(BOOL(pay.id), FALSE)) as has_payment,
                        BOOL_OR(COALESCE(BOOL(counterpart_move.statement_line_id), FALSE)) as has_st_line
                    FROM account_partial_reconcile part
                    JOIN account_move_line source_line ON source_line.id = part.%s
                    JOIN account_account account ON account.id = source_line.account_id
                    JOIN account_move_line counterpart_line ON counterpart_line.id = part.%s
                    JOIN account_move counterpart_move ON counterpart_move.id = counterpart_line.move_id
                    LEFT JOIN account_payment pay ON pay.id = counterpart_move.origin_payment_id
                    WHERE source_line.move_id IN %s AND counterpart_line.move_id != source_line.move_id
                    GROUP BY source_line.id, source_line.move_id, account.account_type
                ''', SQL.identifier(source_field), SQL.identifier(counterpart_field), stored_ids))

            payment_data = defaultdict(list)
            for row in self.env.execute_query_dict(SQL(" UNION ALL ").join(queries)):
                payment_data[row['source_move_id']].append(row)
        else:
            payment_data = {}

        for invoice in invoices:
            currency = invoice.currency_id or invoice.company_id.currency_id or self.env.company.currency_id
            reconciliation_vals = payment_data.get(invoice.id, [])

            # Restrict on 'receivable'/'payable' lines for invoices/expense entries.
            reconciliation_vals = [x for x in reconciliation_vals if x['source_line_account_type'] in ('asset_receivable', 'liability_payable')]

            new_pmt_state = 'not_paid'
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
            elif invoice.state == 'posted' and invoice.matched_payment_ids.filtered(lambda p: not p.move_id and p.state == 'in_process'):
                new_pmt_state = invoice._get_invoice_in_payment_state()
            elif reconciliation_vals:
                new_pmt_state = 'partial'
            elif invoice.state == 'posted' and invoice.matched_payment_ids.filtered(lambda p: not p.move_id and p.state == 'paid'):
                new_pmt_state = invoice._get_invoice_in_payment_state()
            invoice.payment_state = new_pmt_state

    @api.depends('payment_state', 'state', 'is_move_sent')
    def _compute_status_in_payment(self):
        for move in self:
            if move.state == 'posted' and move.payment_state == 'not_paid' and move.is_move_sent:
                move.status_in_payment = 'sent'
            elif move.state == 'posted' and move.payment_state in ('partial', 'in_payment', 'paid', 'reversed'):
                move.status_in_payment = move.payment_state
            else:
                move.status_in_payment = move.state

    @api.depends('matched_payment_ids')
    def _compute_payment_count(self):
        for invoice in self:
            invoice.payment_count = len(invoice.matched_payment_ids)

    @api.depends('adjusting_entries_move_ids')
    def _compute_adjusting_entries_count(self):
        for move in self:
            move.adjusting_entries_count = len(move.adjusting_entries_move_ids)

    @api.depends('adjusting_entry_origin_move_ids')
    def _compute_adjusting_entry_origin_moves_count(self):
        for move in self:
            move.adjusting_entry_origin_moves_count = len(move.adjusting_entry_origin_move_ids)

    @api.depends_context('lang')
    @api.depends('adjusting_entry_origin_move_ids')
    def _compute_adjusting_entry_origin_label(self):
        for move in self:
            if len(move.adjusting_entry_origin_move_ids) == 1:
                move.adjusting_entry_origin_label = dict(self._fields['move_type'].selection)[move.adjusting_entry_origin_move_ids.move_type]
            else:
                move.adjusting_entry_origin_label = False

    @api.depends('invoice_payment_term_id', 'invoice_date', 'currency_id', 'amount_total_in_currency_signed', 'invoice_date_due')
    def _compute_needed_terms(self):
        AccountTax = self.env['account.tax']
        for invoice in self.with_context(bin_size=False):
            is_draft = invoice.id != invoice._origin.id
            invoice.needed_terms = {}
            invoice.needed_terms_dirty = True
            sign = 1 if invoice.is_inbound(include_receipts=True) else -1
            if invoice.is_invoice(True) and invoice.invoice_line_ids:
                if invoice.invoice_payment_term_id:
                    if is_draft:
                        tax_amount_currency = 0.0
                        tax_amount = tax_amount_currency
                        untaxed_amount_currency = 0.0
                        untaxed_amount = untaxed_amount_currency
                        sign = invoice.direction_sign
                        base_lines, _tax_lines = invoice._get_rounded_base_and_tax_lines(round_from_tax_lines=False)
                        AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, invoice.company_id, include_caba_tags=invoice.always_tax_exigible)
                        tax_results = AccountTax._prepare_tax_lines(base_lines, invoice.company_id)
                        for _base_line, to_update in tax_results['base_lines_to_update']:
                            untaxed_amount_currency += sign * to_update['amount_currency']
                            untaxed_amount += sign * to_update['balance']
                        for tax_line_vals in tax_results['tax_lines_to_add']:
                            tax_amount_currency += sign * tax_line_vals['amount_currency']
                            tax_amount += sign * tax_line_vals['balance']
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

            if move.state not in {'draft', 'posted'} \
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
                ('balance', '<' if move.is_inbound() else '>', 0.0),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {
                'outstanding': True,
                'content': [],
                'move_id': move.id,
                'title': _('Outstanding credits') if move.is_inbound() else _('Outstanding debits')
            }

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

            if payments_widget_vals['content']:
                move.invoice_outstanding_credits_debits_widget = payments_widget_vals

    @api.depends('invoice_outstanding_credits_debits_widget')
    def _compute_invoice_has_outstanding(self):
        for move in self:
            move.invoice_has_outstanding = bool(move.invoice_outstanding_credits_debits_widget)

    @api.depends('partner_id', 'company_id')
    def _compute_preferred_payment_method_line_id(self):
        for move in self:
            partner = move.partner_id.with_company(move.company_id)
            if move.is_sale_document():
                move.preferred_payment_method_line_id = partner.property_inbound_payment_method_line_id
            else:
                move.preferred_payment_method_line_id = partner.property_outbound_payment_method_line_id

    @api.depends('move_type', 'line_ids.amount_residual')
    def _compute_payments_widget_reconciled_info(self):
        for move in self:
            payments_widget_vals = {'title': _('Less Payment'), 'outstanding': False, 'content': []}

            if move.state in {'draft', 'posted'} and move.is_invoice(include_receipts=True):
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
                        'is_refund': counterpart_line.move_id.move_type in ['in_refund', 'out_refund'],
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

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        """ Convert an account.move.line having display_type='product' into a base line for the taxes computation.

        :param product_line: An account.move.line.
        :return: A base line returned by '_prepare_base_line_for_taxes_computation'.
        """
        self.ensure_one()
        is_invoice = self.is_invoice(include_receipts=True)
        sign = self.direction_sign if is_invoice else 1
        if is_invoice:
            rate = self.invoice_currency_rate
        else:
            rate = (abs(product_line.amount_currency) / abs(product_line.balance)) if product_line.balance else 0.0

        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            product_line,
            price_unit=product_line.price_unit if is_invoice else product_line.amount_currency,
            quantity=product_line.quantity if is_invoice else 1.0,
            discount=product_line.discount if is_invoice else 0.0,
            rate=rate,
            sign=sign,
            special_mode=False if is_invoice else 'total_excluded',
        )

    def _prepare_epd_base_line_for_taxes_computation(self, epd_line):
        """ Convert an account.move.line having display_type='epd' into a base line for the taxes computation.

        :param epd_line: An account.move.line.
        :return: A base line returned by '_prepare_base_line_for_taxes_computation'.
        """
        self.ensure_one()
        sign = self.direction_sign
        rate = self.invoice_currency_rate

        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            epd_line,
            price_unit=sign * epd_line.amount_currency,
            quantity=1.0,
            sign=sign,
            special_mode='total_excluded',
            special_type='early_payment',

            is_refund=self.move_type in ('out_refund', 'in_refund'),
            rate=rate,
        )

    def _prepare_epd_base_lines_for_taxes_computation_from_base_lines(self, base_lines):
        """ Anticipate the epd lines to be generated from the base lines passed as parameter.
        When the record is in draft (not saved), the accounting items are not there so we can't
        call '_prepare_epd_base_line_for_taxes_computation'.

        :param base_lines: The base lines generated by '_prepare_product_base_line_for_taxes_computation'.
        :return: A list of base lines representing the epd lines.
        """
        self.ensure_one()
        aggregated_results = self._sync_dynamic_line_needed_values(base_lines.mapped('epd_needed'))
        sign = self.direction_sign
        rate = self.invoice_currency_rate
        epd_lines = []
        for grouping_key, values in aggregated_results.items():
            all_values = {**grouping_key, **values}
            epd_lines.append(self.env['account.tax']._prepare_base_line_for_taxes_computation(
                all_values,
                id=grouping_key,
                tax_ids=self.env['account.tax'].browse(all_values['tax_ids'][0][2]),
                price_unit=sign * values['amount_currency'],
                quantity=1.0,
                currency_id=self.currency_id,
                sign=1,
                special_mode='total_excluded',
                special_type='early_payment',

                partner_id=self.commercial_partner_id,
                account_id=self.env['account.account'].browse(all_values['account_id']),
                is_refund=self.move_type in ('out_refund', 'in_refund'),
                rate=rate,
            ))
        return epd_lines

    def _prepare_cash_rounding_base_line_for_taxes_computation(self, cash_rounding_line):
        """ Convert an account.move.line having display_type='rounding' into a base line for the taxes computation.

        :param cash_rounding_line: An account.move.line.
        :return: A base line returned by '_prepare_base_line_for_taxes_computation'.
        """
        self.ensure_one()
        sign = self.direction_sign
        rate = self.invoice_currency_rate

        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            cash_rounding_line,
            price_unit=sign * cash_rounding_line.amount_currency,
            quantity=1.0,
            sign=sign,
            special_mode='total_excluded',
            special_type='cash_rounding',

            is_refund=self.move_type in ('out_refund', 'in_refund'),
            rate=rate,
        )

    def _prepare_tax_line_for_taxes_computation(self, tax_line):
        """ Convert an account.move.line having display_type='tax' into a tax line for the taxes computation.

        :param tax_line: An account.move.line.
        :return: A tax line returned by '_prepare_tax_line_for_taxes_computation'.
        """
        self.ensure_one()
        return self.env['account.tax']._prepare_tax_line_for_taxes_computation(
            tax_line,
            sign=self.direction_sign,
        )

    def _prepare_non_deductible_base_line_for_taxes_computation(self, non_deductible_line):
        """ Convert an account.move.line having display_type='non_deductible' into a base line for the taxes computation.

        :param non_deductible_line: An account.move.line.
        :return: A base line returned by '_prepare_base_line_for_taxes_computation'.
        """
        self.ensure_one()
        sign = self.direction_sign
        rate = self.invoice_currency_rate
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            non_deductible_line,
            price_unit=sign * non_deductible_line.amount_currency,
            quantity=1.0,
            sign=sign,
            special_mode='total_excluded',
            special_type='non_deductible',

            is_refund=self.move_type in ('out_refund', 'in_refund'),
            rate=rate,
        )

    def _prepare_non_deductible_base_lines_for_taxes_computation_from_base_lines(self, base_lines):
        """ Anticipate the non deductible lines to be generated from the base lines passed as parameter.
        When the record is in draft (not saved), the accounting items are not there so we can't
        call '_prepare_non_deductible_base_line_for_taxes_computation'.

        :param base_lines: The base lines generated by '_prepare_product_base_line_for_taxes_computation'.
        :return: A list of base lines representing the non deductible lines.
        """
        self.ensure_one()
        non_deductible_product_lines = base_lines.filtered(lambda line: line.display_type == 'product' and float_compare(line.deductible_amount, 100, precision_digits=2))
        if not non_deductible_product_lines:
            return []

        sign = self.direction_sign
        rate = self.invoice_currency_rate

        non_deductible_lines_base_total_currency = 0.0
        non_deductible_lines = []
        for line in non_deductible_product_lines:
            percentage = 1 - line.deductible_amount / 100
            non_deductible_subtotal = line.currency_id.round(line.price_subtotal * percentage)
            non_deductible_base_currency = line.company_currency_id.round(sign * non_deductible_subtotal / rate) if rate else 0.0
            non_deductible_lines_base_total_currency += non_deductible_base_currency

            non_deductible_lines += [
                self.env['account.tax']._prepare_base_line_for_taxes_computation(
                    None,
                    price_unit=-non_deductible_base_currency,
                    quantity=1.0,
                    sign=1,
                    special_mode='total_excluded',
                    special_type='non_deductible',
                    tax_ids=line.tax_ids.filtered(lambda tax: tax.amount_type != 'fixed'),
                    currency_id=self.currency_id,
                )
            ]
        non_deductible_lines += [
            self.env['account.tax']._prepare_base_line_for_taxes_computation(
                None,
                price_unit=non_deductible_lines_base_total_currency,
                quantity=1.0,
                sign=1,
                special_mode='total_excluded',
                special_type=False,
                currency_id=self.currency_id,
            )
        ]
        return non_deductible_lines

    def _get_rounded_base_and_tax_lines(self, round_from_tax_lines=True):
        """ Small helper to extract the base and tax lines for the taxes computation from the current move.
        The move could be stored or not and could have some features generating extra journal items acting as
        base lines for the taxes computation (e.g. epd, rounding lines).

        :param round_from_tax_lines:    Indicate if the manual tax amounts of tax journal items should be kept or not.
                                        It only works when the move is stored.
        :return:                        A tuple <base_lines, tax_lines> for the taxes computation.
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        is_invoice = self.is_invoice(include_receipts=True)

        if self.id or not is_invoice:
            base_amls = self.line_ids.filtered(lambda line: line.display_type == 'product')
        else:
            base_amls = self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
        base_lines = [self._prepare_product_base_line_for_taxes_computation(line) for line in base_amls]

        tax_lines = []
        if self.id:
            # The move is stored so we can add the early payment discount lines directly to reduce the
            # tax amount without touching the untaxed amount.
            epd_amls = self.line_ids.filtered(lambda line: line.display_type == 'epd')
            base_lines += [self._prepare_epd_base_line_for_taxes_computation(line) for line in epd_amls]
            cash_rounding_amls = self.line_ids \
                .filtered(lambda line: line.display_type == 'rounding' and not line.tax_repartition_line_id)
            base_lines += [self._prepare_cash_rounding_base_line_for_taxes_computation(line) for line in cash_rounding_amls]
            non_deductible_base_lines = self.line_ids.filtered(lambda line: line.display_type in ('non_deductible_product', 'non_deductible_product_total'))
            base_lines += [self._prepare_non_deductible_base_line_for_taxes_computation(line) for line in non_deductible_base_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            tax_amls = self.line_ids.filtered('tax_repartition_line_id')
            tax_lines = [self._prepare_tax_line_for_taxes_computation(tax_line) for tax_line in tax_amls]
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id, tax_lines=tax_lines if round_from_tax_lines else [])
        else:
            # The move is not stored yet so the only thing we have is the invoice lines.
            base_lines += self._prepare_epd_base_lines_for_taxes_computation_from_base_lines(base_amls)
            base_lines += self._prepare_non_deductible_base_lines_for_taxes_computation_from_base_lines(base_amls)
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        return base_lines, tax_lines

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
                base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
                move.tax_totals = self.env['account.tax']._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=move.currency_id,
                    company=move.company_id,
                    cash_rounding=move.invoice_cash_rounding_id,
                )
                move.tax_totals['display_in_company_currency'] = (
                    move.company_id.display_invoice_tax_company_currency
                    and move.company_currency_id != move.currency_id
                    and move.tax_totals['has_tax_groups']
                    and move.is_sale_document(include_receipts=True)
                )
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
            move.invoice_filter_type_domain = self._get_invoice_filter_type_domain(move.move_type)

    @api.depends('commercial_partner_id', 'company_id', 'move_type')
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

    @api.depends('restrict_mode_hash_table', 'state', 'inalterable_hash')
    def _compute_show_reset_to_draft_button(self):
        for move in self:
            move.show_reset_to_draft_button = (
                not self._is_move_restricted(move) \
                and not move.inalterable_hash
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
        invoice_to_update_terms = self.filtered(lambda m: use_invoice_terms and m.is_sale_document(include_receipts=True))
        for move in invoice_to_update_terms:
            lang = move.partner_id.lang or self.env.user.lang
            if move.company_id.terms_type != 'html':
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
                total_field = 'total_amount_currency' if move.currency_id == move.company_currency_id else 'total_amount'
                current_amount = move.tax_totals[total_field]
                move.partner_credit_warning = self._build_credit_warning_message(
                    move,
                    current_amount=current_amount,
                    exclude_amount=move._get_partner_credit_warning_exclude_amount(),
                )

    def _build_credit_warning_message(self, record, current_amount=0.0, exclude_current=False, exclude_amount=0.0):
        """ Build the warning message that will be displayed in a yellow banner on top of the current record
            if the partner exceeds a credit limit (set on the company or the partner itself).
            :param record:                  The record where the warning will appear (Invoice, Sales Order...).
            :param float current_amount:    The partner's outstanding credit amount from the current document.
            :param bool exclude_current:    DEPRECATED in favor of parameter `exclude_amount`:
                                            Whether to exclude `current_amount` from the credit to invoice.
            :param float exclude_amount:    The amount to subtract from the partner's `credit_to_invoice`.
                                            Consider the warning on a draft invoice created from a sales order.
                                            After confirming the invoice the (partial) amount (on the invoice)
                                            stemming from sales orders will be substracted from the `credit_to_invoice`.
                                            This will reduce the total credit of the partner.
                                            This parameter is used to reflect this amount.
            :return:                        The warning message to be showed.
            :rtype: str
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

    @api.depends('ref', 'move_type', 'partner_id', 'invoice_date', 'tax_totals')
    def _compute_duplicated_ref_ids(self):
        move_to_duplicate_move = self._fetch_duplicate_reference()
        for move in self:
            # Uses move._origin.id to handle records in edition/existing records and 0 for new records
            move.duplicated_ref_ids = move_to_duplicate_move.get(move._origin, self.env['account.move'])

    def _fetch_duplicate_reference(self, matching_states=('draft', 'posted')):
        moves = self.filtered(lambda m: m.is_sale_document() or m.is_purchase_document() and m.ref)

        if not moves:
            return {}

        used_fields = ("company_id", "partner_id", "commercial_partner_id", "ref", "move_type", "invoice_date", "state", "amount_total")

        self.env["account.move"].flush_model(used_fields)

        move_table_and_alias = SQL("account_move AS move")
        if not moves[0].id:  # check if record is under creation/edition in UI
            # New record aren't searchable in the DB and record in edition aren't up to date yet
            # Replace the table by safely injecting the values in the query
            values = {
                field_name: moves._fields[field_name].convert_to_write(moves[field_name], moves) or None
                for field_name in used_fields
            }
            values["id"] = moves._origin.id or 0
            # The amount total depends on the field line_ids and is calculated upon saving, we needed a way to get it even when the
            # invoices has not been saved yet.
            values['amount_total'] = self.tax_totals.get('total_amount_currency', 0)
            casted_values = SQL(', ').join(
                SQL("%s::%s", value, SQL.identifier(moves._fields[field_name].column_type[0]))
                for field_name, value in values.items()
            )
            column_names = SQL(', ').join(SQL.identifier(field_name) for field_name in values)
            move_table_and_alias = SQL("(VALUES (%s)) AS move(%s)", casted_values, column_names)

        to_query = []
        out_moves = moves.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund'))
        if out_moves:
            out_moves_sql_condition = SQL("""
                move.move_type in ('out_invoice', 'out_refund')
                AND (
                   move.amount_total = duplicate_move.amount_total
                   AND move.invoice_date = duplicate_move.invoice_date
                )
            """)
            to_query.append((out_moves, out_moves_sql_condition))

        in_moves = moves.filtered(lambda m: m.move_type in ('in_invoice', 'in_refund'))
        if in_moves:
            in_moves_sql_condition = SQL("""
                move.move_type in ('in_invoice', 'in_refund')
                AND duplicate_move.move_type in ('in_invoice', 'in_refund')
                AND (
                   move.ref = duplicate_move.ref
                   AND (
                       move.invoice_date IS NULL
                       OR
                       duplicate_move.invoice_date IS NULL
                       OR
                       date_part('year', move.invoice_date) = date_part('year', duplicate_move.invoice_date)
                   )
                )
            """)
            to_query.append((in_moves, in_moves_sql_condition))

        result = []
        for moves, move_type_sql_condition in to_query:
            result.extend(self.env.execute_query(SQL("""
                SELECT move.id AS move_id,
                       array_agg(duplicate_move.id) AS duplicate_ids
                  FROM %(move_table_and_alias)s
                  JOIN account_move AS duplicate_move
                    ON move.company_id = duplicate_move.company_id
                   AND move.id != duplicate_move.id
                   AND duplicate_move.state IN %(matching_states)s
                   AND move.move_type = duplicate_move.move_type
                   AND (
                           move.commercial_partner_id = duplicate_move.commercial_partner_id
                           OR (move.commercial_partner_id IS NULL AND duplicate_move.state = 'draft')
                       )
                   AND (%(move_type_sql_condition)s)
                 WHERE move.id IN %(moves)s
                 GROUP BY move.id
                """,
                matching_states=tuple(matching_states),
                moves=tuple(moves.ids or [0]),
                move_table_and_alias=move_table_and_alias,
                move_type_sql_condition=move_type_sql_condition,
            )))
        return {
            self.env['account.move'].browse(move_id): self.env['account.move'].browse(duplicate_ids)
            for move_id, duplicate_ids in result
        }

    @api.depends('company_id')
    def _compute_display_qr_code(self):
        for move in self:
            move.display_qr_code = (
                move.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt')
                and move.company_id.qr_code
            )

    @api.depends('company_id')
    def _compute_display_link_qr_code(self):
        for move in self:
            move.display_link_qr_code = (
                move.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt')
                and move.company_id.link_qr_code
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

    @api.depends('partner_id', 'invoice_date', 'amount_total')
    def _compute_abnormal_warnings(self):
        """Assign warning fields based on historical data.

        The last invoices (between 10 and 30) are used to compute the normal distribution.
        If the amount or days between invoices of the current invoice falls outside of the boundaries
        of the Bell curve, we warn the user.
        """
        if self.env.context.get('disable_abnormal_invoice_detection'):
            draft_invoices = self.browse()
        else:
            draft_invoices = self.filtered(lambda m:
                m.is_purchase_document()
                and m.state == 'draft'
                and m.amount_total
                and not (m.partner_id.ignore_abnormal_invoice_date and m.partner_id.ignore_abnormal_invoice_amount)
            )
        other_moves = self - draft_invoices
        other_moves.abnormal_amount_warning = False
        other_moves.abnormal_date_warning = False
        if not draft_invoices:
            return
        draft_invoices.flush_recordset(['invoice_date', 'date', 'amount_total', 'partner_id', 'move_type', 'company_id'])
        today = fields.Date.context_today(self)
        self.env.cr.execute("""
            WITH previous_invoices AS (
                  SELECT this.id,
                         other.invoice_date,
                         other.amount_total,
                         LAG(other.invoice_date) OVER invoice - other.invoice_date AS date_diff
                    FROM account_move this
                    JOIN account_move other USING (partner_id, move_type, company_id, currency_id)
                   WHERE other.state = 'posted'
                     AND other.invoice_date <= COALESCE(this.invoice_date, this.date, %(today)s)
                     AND this.id = ANY(%(move_ids)s)
                     AND this.id != other.id
                  WINDOW invoice AS (PARTITION BY this.id ORDER BY other.invoice_date DESC)
            ), stats AS (
                  SELECT id,
                         MAX(invoice_date)          OVER invoice AS last_invoice_date,
                         AVG(date_diff)             OVER invoice AS date_diff_mean,
                         STDDEV_SAMP(date_diff)     OVER invoice AS date_diff_deviation,
                         AVG(amount_total)          OVER invoice AS amount_mean,
                         STDDEV_SAMP(amount_total)  OVER invoice AS amount_deviation,
                         ROW_NUMBER()               OVER invoice AS row_number
                    FROM previous_invoices
                  WINDOW invoice AS (PARTITION BY id ORDER BY invoice_date DESC)
            )
              SELECT id, last_invoice_date, date_diff_mean, date_diff_deviation, amount_mean, amount_deviation
                FROM stats
               WHERE row_number BETWEEN 10 AND 30
            ORDER BY row_number ASC
        """, {
            'today': today,
            'move_ids': draft_invoices.ids,
        })
        result = {invoice: vals for invoice, *vals in self.env.cr.fetchall()}
        for move in draft_invoices:
            invoice_date = move.invoice_date or today
            (
                last_invoice_date, date_diff_mean, date_diff_deviation,
                amount_mean, amount_deviation,
            ) = result.get(move._origin.id, (invoice_date, 0, 10000000000, 0, 10000000000))

            if date_diff_mean > 25:
                # Correct for varying days per month and leap years
                # If we have a recurring invoice every month, the mean will be ~30.5 days, and the deviation ~1 day.
                # We need to add some wiggle room for the month of February otherwise it will trigger because 28 days is outside of the range
                date_diff_deviation += 1

            wiggle_room_date = 2 * date_diff_deviation
            move.abnormal_date_warning = (
                not move.partner_id.ignore_abnormal_invoice_date
                and (invoice_date - last_invoice_date).days < int(date_diff_mean - wiggle_room_date)
            ) and _(
                "The billing frequency for %(partner_name)s appears unusual. Based on your historical data, "
                "the expected next invoice date is not before %(expected_date)s (every %(mean)s (± %(wiggle)s) days).\n"
                "Please verify if this date is accurate.",
                partner_name=move.partner_id.display_name,
                expected_date=format_date(self.env, fields.Date.add(last_invoice_date, days=int(date_diff_mean - wiggle_room_date))),
                mean=int(date_diff_mean),
                wiggle=int(wiggle_room_date),
            )

            wiggle_room_amount = 2 * amount_deviation
            move.abnormal_amount_warning = (
                not move.partner_id.ignore_abnormal_invoice_amount
                and not (amount_mean - wiggle_room_amount <= move.amount_total <= amount_mean + wiggle_room_amount)
            ) and _(
                "The amount for %(partner_name)s appears unusual. Based on your historical data, the expected amount is %(mean)s (± %(wiggle)s).\n"
                "Please verify if this amount is accurate.",
                partner_name=move.partner_id.display_name,
                mean=move.currency_id.format(amount_mean),
                wiggle=move.currency_id.format(wiggle_room_amount),
            )

    @api.depends(
        'state',
        'invoice_line_ids',
        'tax_lock_date_message',
        'auto_post',
        'auto_post_until',
        'is_being_sent',
        'partner_credit_warning',
        'abnormal_amount_warning',
        'abnormal_date_warning',
    )
    def _compute_alerts(self):
        for move in self:
            move.alerts = move._get_alerts()

    @api.depends('line_ids.tax_ids')
    def _compute_taxes_legal_notes(self):
        for move in self:
            move.taxes_legal_notes = ''.join(
                tax.invoice_legal_notes
                for tax in OrderedSet(move.line_ids.tax_ids)
                if not is_html_empty(tax.invoice_legal_notes)
            )

    @api.depends('line_ids.payment_date', 'line_ids.reconciled')
    def _compute_next_payment_date(self):
        for move in self:
            move.next_payment_date = min([line.payment_date for line in move.line_ids.filtered(lambda l: l.payment_date and not l.reconciled)], default=False)

    @api.depends('move_type', 'state')
    def _compute_display_send_button(self):
        for move in self:
            move.display_send_button = move.is_sale_document() and move.state == 'posted'

    @api.depends('is_being_sent', 'invoice_pdf_report_id')
    def _compute_highlight_send_button(self):
        for move in self:
            move.highlight_send_button = not move.is_being_sent and not move.invoice_pdf_report_id

    def _search_next_payment_date(self, operator, value):
        if operator not in ('in', '<', '<='):
            return NotImplemented
        return [('line_ids', 'any', [('reconciled', '=', False), ('payment_date', operator, value)])]

    @api.depends('state', 'journal_id.type')
    def _compute_checked(self):
        for move in self:
            move.checked = move.state == 'posted' and (move.journal_id.type == 'general' or move._is_user_able_to_review())

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self):
        self.ensure_one()
        alerts = {}
        has_account_group = self.env.user.has_groups('account.group_account_readonly,account.group_account_invoice')

        if self.state == 'draft':
            if has_account_group and self.tax_lock_date_message:
                alerts['account_tax_lock_date'] = {
                    'level': 'warning',
                    'message': self.tax_lock_date_message,
                }
            if self.auto_post == 'at_date':
                alerts['account_auto_post_at_date'] = {
                    'level': 'info',
                    'message': _("This move is configured to be posted automatically at the accounting date: %s.", self.date),
                }
            if self.auto_post in ('yearly', 'quarterly', 'monthly'):
                message = _(
                    "%(auto_post_name)s auto-posting enabled. Next accounting date: %(move_date)s.",
                    auto_post_name=self.auto_post,
                    move_date=self.date,
                )
                if self.auto_post_until:
                    message += " "
                    message += _("The recurrence will end on %s (included).", self.auto_post_until)
                alerts['account_auto_post_on_period'] = {
                    'level': 'info',
                    'message': message,
                }
            if (
                self.is_purchase_document(include_receipts=True)
                and (zero_lines := self.invoice_line_ids.filtered(lambda line: line.price_total == 0))
                and len(zero_lines) >= 2
            ):
                alerts['account_remove_empty_lines'] = {
                    'level': 'info',
                    'message': _("We've noticed some empty lines on your invoice."),
                    'action_text': _("Remove empty lines"),
                    'action_call': ('account.move.line', 'unlink', zero_lines.ids),
                }

        if self.is_being_sent:
            alerts['account_is_being_sent'] = {
                'level': 'info',
                'message': _("This invoice is being sent in the background."),
            }
        if has_account_group and self.partner_credit_warning:
            alerts['account_partner_credit_warning'] = {
                'level': 'warning',
                'message': self.partner_credit_warning,
            }
        if self.abnormal_amount_warning:
            alerts['account_abnormal_amount_warning'] = {
                'level': 'warning',
                'message': self.abnormal_amount_warning,
            }
        if self.abnormal_date_warning:
            alerts['account_abnormal_date_warning'] = {
                'level': 'warning',
                'message': self.abnormal_date_warning,
            }

        return alerts

    # -------------------------------------------------------------------------
    # SEARCH METHODS
    # -------------------------------------------------------------------------

    def _search_journal_group_id(self, operator, value):
        field = 'name' if 'like' in operator else 'id'
        journal_groups = self.env['account.journal.group'].search([(field, operator, value)])
        return [('journal_id', 'not in', journal_groups.excluded_journal_ids.ids)]
    # -------------------------------------------------------------------------
    # INVERSE METHODS
    # -------------------------------------------------------------------------

    def _inverse_tax_totals(self):
        with self._disable_recursion({'records': self}, 'skip_invoice_sync') as disabled:
            if disabled:
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

                for subtotal in invoice_totals['subtotals']:
                    for tax_group in subtotal['tax_groups']:
                        tax_lines = move.line_ids.filtered(lambda line: line.tax_group_id.id == tax_group['id'])

                        if tax_lines:
                            first_tax_line = tax_lines[0]
                            tax_group_old_amount = sum(tax_lines.mapped('amount_currency'))
                            sign = -1 if move.is_inbound() else 1
                            delta_amount = (tax_group_old_amount - tax_group.get('non_deductible_tax_amount_currency', 0.0)) * sign - tax_group['tax_amount_currency']

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
        self._set_next_made_sequence_gap(False)

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

        if self.partner_id:
            rec_account = self.partner_id.property_account_receivable_id
            pay_account = self.partner_id.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

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
                elif reset == 'year_range_month':
                    detected = _(
                        "The sequence will restart at 1 at the start of every month.\n"
                        "The financial start year detected here is '%(year)s'.\n"
                        "The financial end year detected here is '%(year_end)s'.\n"
                        "The month detected here is '%(month)s'.\n"
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
            self.name = False
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

        if unbalanced_moves := self._get_unbalanced_moves(container):
            if len(unbalanced_moves) == 1:
                raise UserError(_("The entry is not balanced."))

            error_msg = _("The following entries are unbalanced:\n\n")
            for move in unbalanced_moves:
                error_msg += f"  - {self.browse(move[0]).name}\n"
                raise UserError(error_msg)

    def _get_unbalanced_moves(self, container):
        moves = container['records'].filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend on computed stored fields.
        # It happens as the ORM calls create() with the 'no_recompute' statement.
        self.env['account.move.line'].flush_model(['debit', 'credit', 'balance', 'currency_id', 'move_id'])
        return self.env.execute_query(SQL('''
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
        ''', tuple(moves.ids)))

    def _check_fiscal_lock_dates(self):
        if self.env.context.get('bypass_lock_check') is BYPASS_LOCK_CHECK:
            return
        for move in self:
            journal = move.journal_id
            violated_lock_dates = move.company_id._get_lock_date_violations(
                move.date,
                fiscalyear=True,
                sale=journal and journal.type == 'sale',
                purchase=journal and journal.type == 'purchase',
                tax=False,
                hard=True,
            )
            if violated_lock_dates:
                message = _("You cannot add/modify entries prior to and inclusive of: %(lock_date_info)s.",
                            lock_date_info=self.env['res.company']._format_lock_dates(violated_lock_dates))
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
    # CATALOG
    # -------------------------------------------------------------------------
    def action_add_from_catalog(self):
        res = super().action_add_from_catalog()
        if res['context'].get('product_catalog_order_model') == 'account.move':
            res['search_view_id'] = [self.env.ref('account.product_view_search_catalog').id, 'search']
        return res

    def _get_action_add_from_catalog_extra_context(self):
        res = super()._get_action_add_from_catalog_extra_context()
        if self.is_purchase_document() and self.partner_id:
            res['search_default_seller_ids'] = self.partner_id.name

        res['product_catalog_currency_id'] = self.currency_id.id
        res['product_catalog_digits'] = self.line_ids._fields['price_unit'].get_digits(self.env)
        return res

    def _get_product_catalog_domain(self):
        domain = super()._get_product_catalog_domain()
        if self.is_sale_document():
            return domain & Domain('sale_ok', '=', True)
        elif self.is_purchase_document():
            return domain & Domain('purchase_ok', '=', True)
        else:  # In case of an entry
            return domain

    def _default_order_line_values(self, child_field=False):
        default_data = super()._default_order_line_values(child_field)
        new_default_data = self.env['account.move.line']._get_product_catalog_lines_data()
        return {**default_data, **new_default_data}

    def _get_product_catalog_order_data(self, products, **kwargs):
        product_catalog = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            product_catalog[product.id] |= self._get_product_price_and_data(product)
        return product_catalog

    def _get_product_price_and_data(self, product):
        """
            This function will return a dict containing the price of the product. If the product is a sale document then
            we return the list price (which is the "Sales Price" in a product) otherwise we return the standard_price
            (which is the "Cost" in a product).
            In case of a purchase document, it's possible that we have special price for certain partner.
            We will check the sellers set on the product and update the price and min_qty for it if needed.
        """
        self.ensure_one()
        product_infos = {'price': product.list_price if self.is_sale_document() else product.standard_price}

        # Check if there is a price and a minimum quantity for the order's vendor.
        if self.is_purchase_document() and self.partner_id:
            seller = product._select_seller(
                partner_id=self.partner_id,
                quantity=None,
                date=self.invoice_date,
                uom_id=product.uom_id,
                ordered_by='min_qty',
                params={'order_id': self}
            )
            if seller:
                product_infos.update(
                    price=seller.price,
                    min_qty=seller.min_qty,
                )
        return product_infos

    def _get_product_catalog_record_lines(self, product_ids, *, selected_section_id=False, **kwargs):
        grouped_lines = defaultdict(lambda: self.env['account.move.line'])
        for line in self.line_ids:
            if (
                line.section_line_id.id == selected_section_id
                and line.display_type == 'product'
                and line.product_id.id in product_ids
            ):
                grouped_lines[line.product_id] |= line
        return grouped_lines

    def _update_order_line_info(
            self,
            product_id,
            quantity,
            *,
            selected_section_id=False,
            child_field='line_ids',
            **kwargs,
        ):
        """ Update account_move_line information for a given product or create a
        new one if none exists yet.
        :param int product_id: The product, as a `product.product` id.
        :param int quantity: The quantity selected in the catalog
        :param int selected_section_id: The id of section selected in the catalog.
        :return: The unit price of the product, based on the pricelist of the
                 sale order and the quantity selected.
        :rtype: float
        """
        move_line = self.line_ids.filtered_domain([
            ('product_id', '=', product_id),
            ('section_line_id', '=', selected_section_id),
        ])
        if move_line:
            if quantity != 0:
                move_line.quantity = quantity
            elif self.state in {'draft', 'sent'}:
                price_unit = self._get_product_price_and_data(move_line.product_id)['price']
                # The catalog is designed to allow the user to select products quickly.
                # Therefore, sometimes they may select the wrong product or decide to remove
                # some of them from the quotation. The unlink is there for that reason.
                move_line.unlink()
                return price_unit
            else:
                move_line.quantity = 0
        elif quantity > 0:
            move_line = self.env['account.move.line'].create({
                'move_id': self.id,
                'quantity': quantity,
                'product_id': product_id,
                'sequence': self._get_new_line_sequence(child_field, selected_section_id),
            })
        return move_line.price_unit

    def _is_readonly(self):
        """
            Check if the move has been canceled
        """
        self.ensure_one()
        return self.state == 'cancel'

    def _get_section_model_info(self):
        """ Override of `product` to return the model name and parent field for the move lines.

        :return: line_model, parent_field
        """
        return 'account.move.line', 'move_id'

    def _is_line_valid_for_section_line_count(self, line):
        """ Override of `product` to check if a line is valid for inclusion in the section's line
            count.

        :param recordset line: A record of an order line.
        :return: True if this line is a valid, else False.
        :rtype: bool
        """
        return (
            line.product_id
            and line.product_id.product_tmpl_id.type != 'combo'
            and line.quantity > 0
        )

    # -------------------------------------------------------------------------
    # EARLY PAYMENT DISCOUNT
    # -------------------------------------------------------------------------
    def _is_eligible_for_early_payment_discount(self, currency, reference_date):
        self.ensure_one()
        payment_terms = self.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        return self.currency_id == currency \
            and self.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt') \
            and self.invoice_payment_term_id.early_discount \
            and (
                not reference_date
                or not self.invoice_date
                or reference_date <= self.invoice_payment_term_id._get_last_discount_date(self.invoice_date)
            ) \
            and not (payment_terms.sudo().matched_debit_ids + payment_terms.sudo().matched_credit_ids)

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
        if self.env.context.get('skip_account_move_synchronization'):
            return

        self_sudo = self.sudo()
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
                    'name': _("%(tax_name)s (rounding)", tax_name=biggest_tax_line.name),
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

    def _get_automatic_balancing_account(self):
        """ Small helper for special cases where we want to auto balance a move with a specific account. """
        self.ensure_one()
        if self.journal_id.default_account_id:
            return self.journal_id.default_account_id.id
        return self.company_id.account_journal_suspense_account_id.id

    @contextmanager
    def _sync_unbalanced_lines(self, container):
        def has_tax(move):
            return bool(move.line_ids.tax_ids)

        move_had_tax = {move: has_tax(move) for move in container['records']}
        yield
        # Skip posted moves.
        for move in (x for x in container['records'] if x.state != 'posted'):
            if not has_tax(move) and not move_had_tax.get(move):
                continue  # only manage automatically unbalanced when taxes are involved
            if move_had_tax.get(move) and not has_tax(move):
                # taxes have been removed, the tax sync is deactivated so we need to clear everything here
                move.line_ids.filtered('tax_line_id').unlink()
                move.line_ids.tax_tag_ids = [Command.set([])]

            # Set the balancing line's balance and amount_currency to zero,
            # so that it does not interfere with _get_unbalanced_moves() below.
            balance_name = _('Automatic Balancing Line')
            existing_balancing_line = move.line_ids.filtered(lambda line: line.name == balance_name)
            if existing_balancing_line:
                existing_balancing_line.balance = existing_balancing_line.amount_currency = 0.0

            # Create an automatic balancing line to make sure the entry can be saved/posted.
            # If such a line already exists, we simply update its amounts.
            unbalanced_moves = self._get_unbalanced_moves({'records': move})
            if isinstance(unbalanced_moves, list) and len(unbalanced_moves) == 1:
                dummy, debit, credit = unbalanced_moves[0]

                vals = {'balance': credit - debit}
                if existing_balancing_line:
                    existing_balancing_line.write(vals)
                else:
                    vals.update({
                        'name': balance_name,
                        'move_id': move.id,
                        'account_id': move._get_automatic_balancing_account(),
                        'currency_id': move.currency_id.id,
                        # A balancing line should never have default taxes applied to it, it doesn't work well and wouldn't make much sense.
                        'tax_ids': False,
                    })
                    self.env['account.move.line'].create(vals)

    @contextmanager
    def _sync_rounding_lines(self, container):
        yield
        for invoice in container['records']:
            if invoice.state != 'posted':
                invoice._recompute_cash_rounding_lines()

    @api.model
    def _sync_dynamic_line_needed_values(self, values_list):
        res = {}
        for computed_needed in values_list:
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
        for key, values in res.items():
            move_id = key.get('move_id')
            if not move_id:
                continue
            record = self.env['account.move'].browse(move_id)
            for fname, current_value in values.items():
                field = self.env['account.move.line']._fields[fname]
                if isinstance(current_value, float):
                    values[fname] = field.convert_to_cache(current_value, record)

        return res

    @contextmanager
    def _sync_tax_lines(self, container):
        AccountTax = self.env['account.tax']
        fake_base_line = AccountTax._prepare_base_line_for_taxes_computation(None)

        def get_base_lines(move):
            return move.line_ids.filtered(lambda line: line.display_type in ('product', 'epd', 'rounding', 'cogs', 'non_deductible_product'))

        def get_tax_lines(move):
            return move.line_ids.filtered('tax_repartition_line_id')

        def get_value(record, field):
            return self.env['account.move.line']._fields[field].convert_to_write(record[field], record)

        def get_tax_line_tracked_fields(line):
            return ('amount_currency', 'balance', 'analytic_distribution')

        def get_base_line_tracked_fields(line):
            grouping_key = AccountTax._prepare_base_line_grouping_key(fake_base_line)
            if line.move_id.is_invoice(include_receipts=True):
                extra_fields = ['price_unit', 'quantity', 'discount']
            else:
                extra_fields = ['amount_currency']
            return list(grouping_key.keys()) + extra_fields

        def field_has_changed(values, record, field):
            return get_value(record, field) != values.get(record, {}).get(field)

        def get_changed_lines(values, records, fields=None):
            return (
                record
                for record in records
                if record not in values
                or any(field_has_changed(values, record, field) for field in values[record] if not fields or field in fields)
            )

        def any_field_has_changed(values, records, fields=None):
            return any(record for record in get_changed_lines(values, records, fields))

        def is_write_needed(line, values):
            return any(
                self.env['account.move.line']._fields[fname].convert_to_write(line[fname], self) != values[fname]
                for fname in values
            )

        moves_values_before = {
            move: {
                field: get_value(move, field)
                for field in ('currency_id', 'partner_id', 'move_type')
            }
            for move in container['records']
            if move.state == 'draft'
        }
        base_lines_values_before = {
            move: {
                line: {
                    field: get_value(line, field)
                    for field in get_base_line_tracked_fields(line)
                }
                for line in get_base_lines(move)
            }
            for move in container['records']
        }
        tax_lines_values_before = {
            move: {
                line: {
                    field: get_value(line, field)
                    for field in get_tax_line_tracked_fields(line)
                }
                for line in get_tax_lines(move)
            }
            for move in container['records']
        }
        yield

        to_delete = []
        to_create = []
        for move in container['records']:
            if move.state != 'draft':
                continue

            tax_lines = get_tax_lines(move)
            base_lines = get_base_lines(move)
            move_tax_lines_values_before = tax_lines_values_before.get(move, {})
            move_base_lines_values_before = base_lines_values_before.get(move, {})
            if (
                move.is_invoice(include_receipts=True)
                and (
                    field_has_changed(moves_values_before, move, 'currency_id')
                    or field_has_changed(moves_values_before, move, 'move_type')
                )
            ):
                # Changing the type of an invoice using 'switch to refund' feature or just changing the currency.
                round_from_tax_lines = False
            elif changed_lines := list(get_changed_lines(move_base_lines_values_before, base_lines)):
                # A base line has been modified.
                round_from_tax_lines = (
                    # The changed lines don't affect the taxes.
                    all(
                        not line.tax_ids and not move_base_lines_values_before.get(line, {}).get('tax_ids')
                        for line in changed_lines
                    )
                    # Keep the tax lines amounts if an amount has been manually computed.
                    or (
                        list(move_tax_lines_values_before) != list(tax_lines)
                        or any(
                            self.env.is_protected(line._fields[fname], line)
                            for line in tax_lines
                            for fname in move_tax_lines_values_before[line]
                        )
                    )
                )

                # If the move has been created with all lines including the tax ones and the balance/amount_currency are provided on
                # base lines, we don't need to recompute anything.
                if (
                    round_from_tax_lines
                    and any(line[field] for line in changed_lines for field in ('amount_currency', 'balance'))
                ):
                    continue
            elif any(line not in base_lines for line, values in move_base_lines_values_before.items() if values['tax_ids']):
                # Removed a base line affecting the taxes.
                round_from_tax_lines = any_field_has_changed(move_tax_lines_values_before, tax_lines)
            else:
                continue

            base_lines_values, tax_lines_values = move._get_rounded_base_and_tax_lines(round_from_tax_lines=round_from_tax_lines)
            AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines_values, move.company_id, include_caba_tags=move.always_tax_exigible)
            tax_results = AccountTax._prepare_tax_lines(base_lines_values, move.company_id, tax_lines=tax_lines_values)

            non_deductible_tax_line = move.line_ids.filtered(lambda line: line.display_type == 'non_deductible_tax')
            non_deductible_lines_values = [
                line_values
                for line_values in base_lines_values
                if line_values['special_type'] == 'non_deductible'
                and line_values['tax_ids']
            ]

            if not non_deductible_lines_values and non_deductible_tax_line:
                to_delete.append(non_deductible_tax_line.id)

            elif non_deductible_lines_values:
                non_deductible_tax_values = {
                    'tax_amount': 0.0,
                    'tax_amount_currency': 0.0,
                }
                for line_values in non_deductible_lines_values:
                    non_deductible_tax_values['tax_amount'] += -line_values['sign'] * (line_values['tax_details']['total_included'] - line_values['tax_details']['total_excluded'])
                    non_deductible_tax_values['tax_amount_currency'] += -line_values['sign'] * (line_values['tax_details']['total_included_currency'] - line_values['tax_details']['total_excluded_currency'])

                # Update the non-deductible tax lines values
                non_deductable_tax_line_values = {
                    'move_id': move.id,
                    'account_id': (
                        non_deductible_tax_line.account_id
                        or move.journal_id.non_deductible_account_id
                        or move.journal_id.default_account_id
                    ).id,
                    'display_type': 'non_deductible_tax',
                    'name': _('private part (taxes)'),
                    'balance': non_deductible_tax_values['tax_amount'],
                    'amount_currency': non_deductible_tax_values['tax_amount_currency'],
                    'sequence': max(move.line_ids.mapped('sequence')) + 1,
                }
                if non_deductible_tax_line:
                    tax_results['tax_lines_to_update'].append((
                        {'record': non_deductible_tax_line},
                        'unused_grouping_key',
                        {
                            'amount_currency': non_deductable_tax_line_values['amount_currency'],
                            'balance': non_deductable_tax_line_values['balance'],
                        }
                    ))
                else:
                    to_create.append(non_deductable_tax_line_values)

            for base_line, to_update in tax_results['base_lines_to_update']:
                line = base_line['record']
                if is_write_needed(line, to_update):
                    line.write(to_update)

            for tax_line_vals in tax_results['tax_lines_to_delete']:
                to_delete.append(tax_line_vals['record'].id)

            for tax_line_vals in tax_results['tax_lines_to_add']:
                to_create.append({
                    **tax_line_vals,
                    'display_type': 'tax',
                    'move_id': move.id,
                })

            for tax_line_vals, _grouping_key, to_update in tax_results['tax_lines_to_update']:
                line = tax_line_vals['record']
                if is_write_needed(line, to_update):
                    line.write(to_update)

        if to_delete:
            self.env['account.move.line'].browse(to_delete).with_context(dynamic_unlink=True).unlink()
        if to_create:
            self.env['account.move.line'].create(to_create)

    @contextmanager
    def _sync_non_deductible_base_lines(self, container):
        def has_non_deductible_lines(move):
            return (
                move.state == 'draft'
                and move.is_purchase_document()
                and any(move.line_ids.filtered(lambda line: line.display_type == 'product' and line.deductible_amount < 100))
            )

        # Collect data to avoid recomputing value unecessarily
        product_lines_before = {
            move: Counter(
                (line.name, line.price_subtotal, line.tax_ids, line.deductible_amount)
                for line in move.line_ids
                if line.display_type == 'product'
            )
            for move in container['records']
        }

        yield

        to_delete = []
        to_create = []
        for move in container['records']:
            product_lines_now = Counter(
                (line.name, line.price_subtotal, line.tax_ids, line.deductible_amount)
                for line in move.line_ids
                if line.display_type == 'product'
            )

            has_changed_product_lines = bool(
                product_lines_before.get(move, Counter()) - product_lines_now
                or product_lines_now - product_lines_before.get(move, Counter())
            )
            if not has_changed_product_lines:
                # No difference between before and now, then nothing to do
                continue

            non_deductible_base_lines = move.line_ids.filtered(lambda line: line.display_type in ('non_deductible_product', 'non_deductible_product_total'))
            to_delete += non_deductible_base_lines.ids

            if not has_non_deductible_lines(move):
                continue

            non_deductible_base_total = 0.0
            non_deductible_base_currency_total = 0.0

            sign = move.direction_sign
            rate = move.invoice_currency_rate

            for line in move.line_ids.filtered(lambda line: line.display_type == 'product'):
                if float_compare(line.deductible_amount, 100, precision_rounding=2) == 0:
                    continue

                percentage = (1 - line.deductible_amount / 100)
                non_deductible_subtotal = line.currency_id.round(line.price_subtotal * percentage)
                non_deductible_base = line.currency_id.round(sign * non_deductible_subtotal)
                non_deductible_base_currency = line.company_currency_id.round(sign * non_deductible_subtotal / rate) if rate else 0.0
                non_deductible_base_total += non_deductible_base
                non_deductible_base_currency_total += non_deductible_base_currency

                to_create.append({
                    'move_id': move.id,
                    'account_id': line.account_id.id,
                    'display_type': 'non_deductible_product',
                    'name': line.name,
                    'balance': -1 * non_deductible_base,
                    'amount_currency': -1 * non_deductible_base_currency,
                    'tax_ids': [Command.set(line.tax_ids.filtered(lambda tax: tax.amount_type != 'fixed').ids)],
                    'sequence': line.sequence + 1,
                })

            to_create.append({
                'move_id': move.id,
                'account_id': (
                    move.journal_id.non_deductible_account_id
                    or move.journal_id.default_account_id
                ).id,
                'display_type': 'non_deductible_product_total',
                'name': _('private part'),
                'balance': non_deductible_base_total,
                'amount_currency': non_deductible_base_currency_total,
                'tax_ids': [Command.clear()],
                'sequence': max(move.line_ids.mapped('sequence')) + 1,
            })

        while to_create and to_delete:
            line_data = to_create.pop()
            line_id = to_delete.pop()
            self.env['account.move.line'].browse(line_id).write(line_data)
        if to_create:
            self.env['account.move.line'].create(to_create)
        if to_delete:
            self.env['account.move.line'].browse(to_delete).with_context(dynamic_unlink=True).unlink()

    @contextmanager
    def _sync_dynamic_line(self, existing_key_fname, needed_vals_fname, needed_dirty_fname, line_type, container):
        def existing():
            return {
                line: line[existing_key_fname]
                for line in container['records'].line_ids
                if line[existing_key_fname]
            }

        def needed():
            return self._sync_dynamic_line_needed_values(container['records'].mapped(needed_vals_fname))

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
            key, values = to_create.popitem()
            line_id = to_delete.pop()
            self.env['account.move.line'].browse(line_id).write(
                {**key, **values, 'display_type': line_type}
            )
        if to_delete:
            self.env['account.move.line'].browse(to_delete).with_context(dynamic_unlink=True).unlink()
        if to_create:
            self.env['account.move.line'].with_context(clean_context(self.env.context)).create([
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

    def _get_sync_stack(self, container):
        tax_container, invoice_container, misc_container = ({} for _ in range(3))

        def update_containers():
            # Only invoice-like and journal entries in "auto tax mode" are synced
            tax_container['records'] = container['records'].filtered(lambda m: m.is_invoice(True) or m.line_ids.tax_ids or m.line_ids.tax_repartition_line_id)
            invoice_container['records'] = container['records'].filtered(lambda m: m.is_invoice(True))
            misc_container['records'] = container['records'].filtered(lambda m: m.is_entry() and not m.tax_cash_basis_origin_move_id)

            return tax_container, invoice_container, misc_container

        update_containers()

        stack = [
            (10, self._sync_dynamic_line(
                    existing_key_fname='term_key',
                    needed_vals_fname='needed_terms',
                    needed_dirty_fname='needed_terms_dirty',
                    line_type='payment_term',
                    container=invoice_container,
                )),
            (20, self._sync_unbalanced_lines(misc_container)),
            (30, self._sync_rounding_lines(invoice_container)),
            (40, self._sync_dynamic_line(
                    existing_key_fname='discount_allocation_key',
                    needed_vals_fname='line_ids.discount_allocation_needed',
                    needed_dirty_fname='line_ids.discount_allocation_dirty',
                    line_type='discount',
                    container=invoice_container,
                )),
            (50, self._sync_tax_lines(tax_container)),
            (60, self._sync_non_deductible_base_lines(invoice_container)),
            (70, self._sync_dynamic_line(
                    existing_key_fname='epd_key',
                    needed_vals_fname='line_ids.epd_needed',
                    needed_dirty_fname='line_ids.epd_dirty',
                    line_type='epd',
                    container=invoice_container,
                )),
            (80, self._sync_invoice(invoice_container)),
        ]

        return stack, update_containers

    @contextmanager
    def _sync_dynamic_lines(self, container):
        with self._disable_recursion(container, 'skip_invoice_sync') as disabled:
            if disabled:
                yield
                return

            stack_list, update_containers = self._get_sync_stack(container)
            update_containers()
            with ExitStack() as stack:
                stack_list.sort()
                for _seq, contextmgr in stack_list:
                    stack.enter_context(contextmgr)

                line_container = {'records': self.line_ids}
                with self.line_ids._sync_invoice(line_container):
                    yield
                    line_container['records'] = self.line_ids
                update_containers()

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model
    def check_field_access_rights(self, operation, field_names):
        result = super().check_field_access_rights(operation, field_names)
        if not field_names:
            weirdos = ['needed_terms', 'quick_encoding_vals', 'payment_term_details']
            result = [fname for fname in result if fname not in weirdos]
        return result

    @api.model
    def _get_default_read_fields(self):
        weirdos = {'needed_terms', 'quick_encoding_vals', 'payment_term_details'}
        return [fname for fname in self.fields_get(attributes=()) if fname not in weirdos]

    def read(self, fields=None, load='_classic_read'):
        fields = fields or self._get_default_read_fields()
        return super().read(fields, load)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        fields = fields or self._get_default_read_fields()
        return super().search_read(domain, fields, offset, limit, order, **read_kwargs)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default)
        default_date = fields.Date.to_date(default.get('date'))
        for move, vals in zip(self, vals_list):
            if move.move_type in ('out_invoice', 'in_invoice'):
                vals['line_ids'] = [
                    (command, _id, line_vals)
                    for command, _id, line_vals in vals['line_ids']
                    if command == Command.CREATE
                ]
            elif move.move_type == 'entry':
                if 'partner_id' not in vals:
                    vals['partner_id'] = False
            user_fiscal_lock_date = move.company_id._get_user_fiscal_lock_date(move.journal_id)
            if (default_date or move.date) <= user_fiscal_lock_date:
                vals['date'] = user_fiscal_lock_date + timedelta(days=1)
            if not move.journal_id.active and 'journal_id' in vals:
                del vals['journal_id']
        return vals_list

    def copy(self, default=None):
        default = dict(default or {})
        new_moves = super().copy(default)
        bodies = {}
        for old_move, new_move in zip(self, new_moves):
            message_origin = '' if not new_move.auto_post_origin_id else \
                (Markup('<br/>') + _('This recurring entry originated from %s', new_move.auto_post_origin_id._get_html_link()))
            message_content = _('This entry has been reversed from %s', old_move._get_html_link()) if default.get('reversed_entry_id') else _('This entry has been duplicated from %s', old_move._get_html_link())
            bodies[new_move.id] = message_content + message_origin
        new_moves._message_log_batch(bodies=bodies)
        return new_moves

    def _sanitize_vals(self, vals):
        if vals.get('invoice_line_ids') and vals.get('journal_line_ids'):
            # values can sometimes be in only one of the two fields, sometimes in
            # both fields, sometimes one field can be explicitely empty while the other
            # one is not, sometimes not...
            update_vals = {
                line_id: line_vals[0]
                for command, line_id, *line_vals in vals['invoice_line_ids']
                if command == Command.UPDATE
            }
            for command, line_id, *line_vals in vals['journal_line_ids']:
                if command == Command.UPDATE and line_id in update_vals:
                    line_vals[0].update(update_vals.pop(line_id))
            for line_id, line_vals in update_vals.items():
                vals['journal_line_ids'] += [Command.update(line_id, line_vals)]
            for command, line_id, *line_vals in vals['invoice_line_ids']:
                assert command not in (Command.SET, Command.CLEAR)
                if [command, line_id, *line_vals] not in vals['journal_line_ids']:
                    vals['journal_line_ids'] += [(command, line_id, *line_vals)]
            del vals['invoice_line_ids']
        return vals

    def _stolen_move(self, vals):
        for command in vals.get('line_ids', ()):
            if command[0] == Command.LINK:
                yield self.env['account.move.line'].browse(command[1]).move_id.id
            if command[0] == Command.SET:
                yield from self.env['account.move.line'].browse(command[2]).move_id.ids

    def _get_protected_vals(self, vals, records):
        protected = set()
        for fname in vals:
            field = records._fields[fname]
            if field.inverse or (field.compute and not field.readonly):
                protected.update(self.pool.field_computed.get(field, [field]))
        return [(protected, rec) for rec in records] if protected else []

    @api.model_create_multi
    def create(self, vals_list):
        if any('state' in vals and vals.get('state') == 'posted' for vals in vals_list):
            raise UserError(_('You cannot create a move already in the posted state. Please create a draft move and post it after.'))
        container = {'records': self}
        with self._check_balanced(container):
            with ExitStack() as exit_stack, self._sync_dynamic_lines(container):
                for vals in vals_list:
                    self._sanitize_vals(vals)
                stolen_moves = self.browse(set(move for vals in vals_list for move in self._stolen_move(vals)))
                moves = super().create(vals_list)
                exit_stack.enter_context(self.env.protecting([protected for vals, move in zip(vals_list, moves) for protected in self._get_protected_vals(vals, move)]))
                container['records'] = moves | stolen_moves
            for move, vals in zip(moves, vals_list):
                if 'tax_totals' in vals:
                    move.tax_totals = vals['tax_totals']
            moves.is_manually_modified = False
        return moves

    def write(self, vals):
        if not vals:
            return True
        self._sanitize_vals(vals)

        for move in self:
            if vals.get('checked') and not move._is_user_able_to_review():
                raise AccessError(_("You don't have the access rights to perform this action."))
            if vals.get('state') == 'draft' and move.checked and not move._is_user_able_to_review():
                raise ValidationError(_("Validated entries can only be changed by your accountant."))

            violated_fields = set(vals).intersection(move._get_integrity_hash_fields() + ['inalterable_hash'])
            if move.inalterable_hash and violated_fields:
                raise UserError(_(
                    "This document is protected by a hash. "
                    "Therefore, you cannot edit the following fields: %s.",
                    ', '.join(f['string'] for f in self.fields_get(violated_fields).values())
                ))
            if (
                    move.posted_before
                    and 'journal_id' in vals and move.journal_id.id != vals['journal_id']
                    and not (move.name == '/' or not move.name or ('name' in vals and (vals['name'] == '/' or not vals['name'])))
            ):
                raise UserError(_('You cannot edit the journal of an account move if it has been posted once, unless the name is removed or set to "/". This might create a gap in the sequence.'))
            if (
                    move.name and move.name != '/'
                    and move.sequence_number not in (0, 1)
                    and 'journal_id' in vals and move.journal_id.id != vals['journal_id']
                    and not move.quick_edit_mode
                    and not ('name' in vals and (vals['name'] == '/' or not vals['name']))
            ):
                raise UserError(_('You cannot edit the journal of an account move with a sequence number assigned, unless the name is removed or set to "/". This might create a gap in the sequence.'))

            # You can't change the date or name of a move being inside a locked period.
            if move.state == "posted" and (
                    ('name' in vals and move.name != vals['name'])
                    or ('date' in vals and move.date != vals['date'])
            ):
                move._check_fiscal_lock_dates()
                move.line_ids._check_tax_lock_date()

            # You can't post subtract a move to a locked period.
            if 'state' in vals and move.state == 'posted' and vals['state'] != 'posted':
                move._check_fiscal_lock_dates()
                move.line_ids._check_tax_lock_date()

            # Disallow modifying readonly fields on a posted move
            move_state = vals.get('state', move.state)
            unmodifiable_fields = (
                'invoice_line_ids', 'line_ids', 'invoice_date', 'date', 'partner_id',
                'invoice_payment_term_id', 'currency_id', 'fiscal_position_id', 'invoice_cash_rounding_id')
            readonly_fields = [val for val in vals if val in unmodifiable_fields]
            if not self.env.context.get('skip_readonly_check') and move_state == "posted" and readonly_fields:
                raise UserError(_("You cannot modify the following readonly fields on a posted move: %s", ', '.join(readonly_fields)))

            if move.journal_id.sequence_override_regex and vals.get('name') and vals['name'] != '/' and not re.match(move.journal_id.sequence_override_regex, vals['name']):
                if not self.env.user.has_group('account.group_account_manager'):
                    raise UserError(_('The Journal Entry sequence is not conform to the current format. Only the Accountant can change it.'))
                move.journal_id.sequence_override_regex = False

        if {'sequence_prefix', 'sequence_number', 'journal_id', 'name'} & vals.keys():
            self._set_next_made_sequence_gap(True)

        stolen_moves = self.browse(set(move for move in self._stolen_move(vals)))
        container = {'records': self | stolen_moves}
        with self.env.protecting(self._get_protected_vals(vals, self)), self._check_balanced(container):
            with self._sync_dynamic_lines(container):
                if 'is_manually_modified' not in vals and not self.env.context.get('skip_is_manually_modified'):
                    vals['is_manually_modified'] = True

                res = super(AccountMove, self.with_context(
                    skip_account_move_synchronization=True,
                )).write(vals)

                # Reset the name of draft moves when changing the journal.
                # Protected against holes in the pre-validation checks.
                if 'journal_id' in vals and 'name' not in vals:
                    draft_move = self.filtered(lambda m: not m.posted_before)
                    draft_move.name = False
                    draft_move._compute_name()

                # You can't change the date of a not-locked move to a locked period.
                # You can't post a new journal entry inside a locked period.
                if 'date' in vals or 'state' in vals:
                    posted_move = self.filtered(lambda m: m.state == 'posted')
                    posted_move._check_fiscal_lock_dates()
                    posted_move.line_ids._check_tax_lock_date()

                if vals.get('state') == 'posted':
                    self.flush_recordset()  # Ensure that the name is correctly computed
                    self._hash_moves()

            self._synchronize_business_models(set(vals.keys()))

            # Apply the rounding on the Quick Edit mode only when adding a new line
            for move in self:
                if 'tax_totals' in vals:
                    super(AccountMove, move).write({'tax_totals': vals['tax_totals']})

        if any(field in vals for field in ['journal_id', 'currency_id']):
            self.line_ids._check_constrains_account_id_journal_id()

        return res

    def check_move_sequence_chain(self):
        return self.filtered(lambda move: move.name != '/')._is_end_of_seq_chain()

    def _get_unlink_logger_message(self):
        """ Before unlink, get a log message for audit trail if restricted.
        Logger is added here because in api ondelete, account.move.line is deleted, and we can't get total amount """
        if not self.env.context.get('force_delete'):
            pass

        moves_details = []
        for move in self.filtered(lambda m: m.posted_before and m.company_id.restrictive_audit_trail):
            entry_details = f"{move.name} ({move.id}) amount {move.amount_total} {move.currency_id.name} and partner {move.partner_id.display_name}"
            account_balances_per_account = defaultdict(float)
            for line in move.line_ids:
                account_balances_per_account[line.account_id] += line.balance
            account_details = "\n".join(
                f"- {account.name} ({account.id}) with balance {balance} {move.currency_id.name}"
                for account, balance in account_balances_per_account.items()
            )
            moves_details.append(f"{entry_details}\n{account_details}")

        if moves_details:
            return "\nForce deleted Journal Entries by {user_name} ({user_id})\nEntries\n{moves_details}".format(
                user_name=self.env.user.name,
                user_id=self.env.user.id,
                moves_details="\n".join(moves_details),
            )

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
            self.env.user.has_group('account.group_account_manager')
            or any(self.company_id.mapped('quick_edit_mode'))
            or self.env.context.get('force_delete')
            or self.check_move_sequence_chain()
        ):
            raise UserError(_(
                "You cannot delete this entry, as it has already consumed a sequence number and is not the last one in the chain. "
                "You should probably revert it instead."
            ))

    @api.ondelete(at_uninstall=False)
    def _unlink_account_audit_trail_except_once_post(self):
        if not self.env.context.get('force_delete') and any(
                move.posted_before and move.company_id.restrictive_audit_trail
                for move in self
        ):
            raise UserError(_(
                "To keep the restrictive audit trail, you can not delete journal entries once they have been posted.\n"
                "Instead, you can cancel the journal entry."
            ))

    def unlink(self):
        self._set_next_made_sequence_gap(True)
        self = self.with_context(skip_invoice_sync=True, dynamic_unlink=True)  # no need to sync to delete everything
        logger_message = self._get_unlink_logger_message()
        self.line_ids.remove_move_reconcile()
        self.line_ids.unlink()
        res = super().unlink()
        if logger_message:
            _logger.info(logger_message)
        return res

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
        is_payment = self.origin_payment_id or self.env.context.get('is_payment')

        if not relaxed:
            domain = [('journal_id', '=', self.journal_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]
            if self.journal_id.refund_sequence:
                refund_types = ('out_refund', 'in_refund')
                domain += [('move_type', 'in' if self.move_type in refund_types else 'not in', refund_types)]
            if self.journal_id.payment_sequence:
                domain += [('origin_payment_id', '!=' if is_payment else '=', False)]
            reference_move_name = self.sudo().search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
            if not reference_move_name:
                reference_move_name = self.sudo().search(domain, order='date asc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(reference_move_name)
            date_start, date_end, *_ = self._get_sequence_date_range(sequence_number_reset)
            where_string += """ AND date BETWEEN %(date_start)s AND %(date_end)s"""
            param['date_start'] = date_start
            param['date_end'] = date_end

            # Some regex are catching more sequence formats than we want, so we
            # need to exclude them:
            #
            #                    |                 Regex type                                 |
            # Move Name Format   | Fixed | Yearly | Monthly | Year Range | Year range Monthly |
            # ------------------ | ----- | ------ | ------- | ---------- | ------------------ |
            # Fixed              |   X   |        |         |            |                    |
            # Yearly             |   X   |   X    |         |            |                    |
            # Monthly            |   X   |   X    |    X    |     X      |                    |
            # Year Range         |   X   |   X    |         |     X      |                    |
            # Year range Monthly |   X   |   X    |    X    |     X      |          X         |
            if sequence_number_reset in ('year', 'year_range'):
                param['anti_regex'] = self._make_regex_non_capturing(self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
            elif sequence_number_reset == 'never':
                # Excluding yearly will also exclude "monthly", "year range" and
                # "year range monthly"
                param['anti_regex'] = self._make_regex_non_capturing(self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

            if param.get('anti_regex') and not self.journal_id.sequence_override_regex:
                where_string += " AND sequence_prefix !~ %(anti_regex)s "

        if self.journal_id.refund_sequence:
            if self.move_type in ('out_refund', 'in_refund'):
                where_string += " AND move_type IN ('out_refund', 'in_refund') "
            else:
                where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "
        elif self.journal_id.payment_sequence:
            if is_payment:
                where_string += " AND origin_payment_id IS NOT NULL "
            else:
                where_string += " AND origin_payment_id IS NULL "

        return where_string, param

    def _get_starting_sequence(self):
        # EXTENDS account sequence.mixin
        self.ensure_one()
        move_date = self.date or self.invoice_date or fields.Date.context_today(self)
        year_part = "%04d" % move_date.year
        last_day = int(self.company_id.fiscalyear_last_day)
        last_month = int(self.company_id.fiscalyear_last_month)
        is_staggered_year = last_month != 12 or last_day != 31
        if is_staggered_year:
            max_last_day = calendar.monthrange(move_date.year, last_month)[1]
            last_day = min(last_day, max_last_day)
            if move_date > date(move_date.year, last_month, last_day):
                year_part = "%s-%s" % (move_date.strftime('%y'), (move_date + relativedelta(years=1)).strftime('%y'))
            else:
                year_part = "%s-%s" % ((move_date + relativedelta(years=-1)).strftime('%y'), move_date.strftime('%y'))
        # Arbitrarily use annual sequence for sales documents, but monthly
        # sequence for other documents
        if self.journal_id.type in ['sale', 'bank', 'cash', 'credit']:
            # We reduce short code to 4 characters (0000) in case of staggered
            # year to avoid too long sequences (see Indian GST rule 46(b) for
            # example). Note that it's already the case for monthly sequences.
            starting_sequence = "%s/%s/%s" % (self.journal_id.code, year_part, '0000' if is_staggered_year else '00000')
        else:
            starting_sequence = "%s/%s/%02d/0000" % (self.journal_id.code, year_part, move_date.month)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        if self.journal_id.payment_sequence and self.origin_payment_id or self.env.context.get('is_payment'):
            starting_sequence = "P" + starting_sequence
        return starting_sequence

    def _get_sequence_date_range(self, reset):
        if reset not in ('year_range', 'year_range_month'):
            return super()._get_sequence_date_range(reset)

        fiscalyear_last_day = self.company_id.fiscalyear_last_day
        fiscalyear_last_month = int(self.company_id.fiscalyear_last_month)
        date_start, date_end = date_utils.get_fiscal_year(self.date, day=fiscalyear_last_day, month=fiscalyear_last_month)

        if reset == 'year_range':
            return (date_start, date_end) + (None, None)

        forced_year_range = (date_start.year, date_end.year)
        month_range = date_utils.get_month(self.date)
        fiscalyear_last_month_max_day = calendar.monthrange(self.date.year, fiscalyear_last_month)[1]
        # We need to truncate the month if:
        # - the fiscal year does not end on the last day of the month
        # - and the move date is part of that month
        # The sequence date range will be something like 2020-11-01 to
        # 2020-11-30. But the sequence should be 2019-2020/11/0001 (or
        # 2020-2021/11/0001), not 2020-2020/11/0001.
        if fiscalyear_last_day < fiscalyear_last_month_max_day and fiscalyear_last_month == self.date.month:
            if self.date.day <= fiscalyear_last_day:
                return (month_range[0], month_range[1].replace(day=fiscalyear_last_day)) + forced_year_range
            else:
                return (month_range[0].replace(day=fiscalyear_last_day + 1), month_range[1]) + forced_year_range
        else:
            return month_range + forced_year_range

    # -------------------------------------------------------------------------
    # PAYMENT REFERENCE
    # -------------------------------------------------------------------------

    def _get_invoice_reference_euro_invoice(self):
        """ This computes the reference based on the RF Creditor Reference.
            The data of the reference is the journal short code and the database
            id number of the invoice. For instance, if a journal code is INV and
            an invoice is issued with id 37, the check number is 67 so the
            reference will be 'RF67 INV0 0003 7'.
        """
        self.ensure_one()
        journal_identifier = self.journal_id.code if self.journal_id.code.isascii() else self.journal_id.id
        return format_structured_reference_iso(f'{journal_identifier}{str(self.id).zfill(6)}')

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
        journal_identifier = self.journal_id.code if self.journal_id.code.isascii() else self.journal_id.id
        partner_ref = self.partner_id.ref
        partner_ref_nr = re.sub(r'\D', '', partner_ref or '')[-21:] or str(self.partner_id.id)[-21:]
        partner_ref_nr = f'{journal_identifier}{partner_ref_nr}'[-21:]
        return format_structured_reference_iso(partner_ref_nr)

    def _get_invoice_reference_number_invoice(self):
        """ This computes the reference based on the Number format.
            Return the number of the invoice, defined on the journal sequence.
        """
        ref = self._get_invoice_reference_odoo_invoice() or ''
        return ''.join(char for char in ref if char.isdigit())

    def _get_invoice_reference_number_partner(self):
        """ This computes the reference based on the Number format.
            The data used is the reference set on the partner or its database
            id otherwise. For instance if the reference of the customer is
            'customer 97', the reference will be '97'.
        """
        ref = self._get_invoice_reference_odoo_partner()
        return ''.join(char for char in ref if char.isdigit())

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
            ('date', '>=', date.today() - timedelta(days=365 * 2)),
        ]
        if move_type in self.env['account.move'].get_inbound_types(include_receipts=True):
            domain.append(('account_id.internal_group', '=', 'income'))
        elif move_type in self.env['account.move'].get_outbound_types(include_receipts=True):
            domain.append(('account_id.internal_group', '=', 'expense'))

        query = self.env['account.move.line']._search(domain, bypass_access=True)
        account_code = self.env['account.account']._field_to_sql('account_move_line__account_id', 'code', query)
        rows = self.env.execute_query(SQL("""
            SELECT COUNT(foo.id), foo.account_id, foo.taxes
              FROM (
                         SELECT account_move_line__account_id.id AS account_id,
                                %(account_code)s AS code,
                                account_move_line.id,
                                ARRAY_AGG(tax_rel.account_tax_id) FILTER (WHERE tax_rel.account_tax_id IS NOT NULL) AS taxes
                           FROM %(from_clause)s
                      LEFT JOIN account_move_line_account_tax_rel tax_rel ON account_move_line.id = tax_rel.account_move_line_id
                          WHERE %(where_clause)s
                       GROUP BY account_move_line__account_id.id,
                                %(account_code)s,
                                account_move_line.id
                   ) AS foo
          GROUP BY foo.account_id, foo.taxes
          ORDER BY COUNT(foo.id) DESC, taxes ASC NULLS LAST
             LIMIT 1
            """,
            account_code=account_code,
            from_clause=query.from_clause,
            where_clause=query.where_clause or SQL("TRUE"),
        ))
        return rows[0] if rows else (0, False, False)

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
        remaining_amount = self.quick_edit_total_amount - self.tax_totals['total_amount_currency']

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
        tax_amount_rounding_error = amount_total - totals['total_amount_currency']
        if not float_is_zero(tax_amount_rounding_error, precision_rounding=self.currency_id.rounding):
            for subtotal in totals['subtotals']:
                if _('Untaxed Amount') == subtotal['name']:
                    if subtotal['tax_groups']:
                        subtotal['tax_groups'][0]['tax_amount_currency'] += tax_amount_rounding_error
                    totals['total_amount_currency'] = amount_total
                    self.tax_totals = totals
                    break

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------

    def _get_integrity_hash_fields(self):
        # Use the latest hash version by default, but keep the old one for backward compatibility when generating the integrity report.
        hash_version = self.env.context.get('hash_version', MAX_HASH_VERSION)
        if hash_version == 1:
            return ['date', 'journal_id', 'company_id']
        elif hash_version in (2, 3, 4):
            return ['name', 'date', 'journal_id', 'company_id']
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

    def _get_integrity_hash_fields_and_subfields(self):
        return self._get_integrity_hash_fields() + [f'line_ids.{subfield}' for subfield in self.line_ids._get_integrity_hash_fields()]

    @api.model
    def _get_move_hash_domain(self, common_domain=False, force_hash=False):
        """
        Returns a search domain on model account.move checking whether they should be hashed.
        :param common_domain: a search domain that will be included in the returned domain in any case
        :param force_hash: if True, we'll check all moves posted, independently of journal settings
        """
        domain = Domain(common_domain or Domain.TRUE) & Domain('state', '=', 'posted')
        if force_hash:
            return domain
        return domain & Domain('restrict_mode_hash_table', '=', True)

    @api.model
    def _is_move_restricted(self, move, force_hash=False):
        """
        Returns whether a move should be hashed (depending on journal settings)
        :param move: the account.move we check
        :param force_hash: if True, we'll check all moves posted, independently of journal settings
        """
        return move.filtered_domain(self._get_move_hash_domain(force_hash=force_hash))

    def _hash_moves(self, **kwargs):
        chains_to_hash = self._get_chains_to_hash(**kwargs)
        grant_secure_group_access = False
        for chain in chains_to_hash:
            move_hashes = chain['moves']._calculate_hashes(chain['previous_hash'])
            for move, move_hash in move_hashes.items():
                move.inalterable_hash = move_hash
            # If any secured entries belong to journals without 'hash on post', the user should be granted access rights
            if not chain['journal_restrict_mode']:
                grant_secure_group_access = True
            chain['moves']._message_log_batch(bodies={m.id: self.env._("This journal entry has been secured.") for m in chain['moves']})
        if grant_secure_group_access:
            self.env['res.groups']._activate_group_account_secured()

    def _get_chain_info(self, force_hash=False, include_pre_last_hash=False, early_stop=False):
        """All records in `self` must belong to the same journal and sequence_prefix
        """
        if not self:
            return False
        last_move_in_chain = max(self, key=lambda m: m.sequence_number)
        journal = last_move_in_chain.journal_id
        if not self._is_move_restricted(last_move_in_chain, force_hash=force_hash):
            return False

        common_domain = [
            ('journal_id', '=', journal.id),
            ('sequence_prefix', '=', last_move_in_chain.sequence_prefix),
        ]
        last_move_hashed = self.env['account.move'].search([
            *common_domain,
            ('inalterable_hash', '!=', False),
        ], order='sequence_number desc', limit=1)

        domain = self.env['account.move']._get_move_hash_domain([
            *common_domain,
            ('sequence_number', '<=', last_move_in_chain.sequence_number),
            ('inalterable_hash', '=', False),
        ], force_hash=True)
        if last_move_hashed and not include_pre_last_hash:
            # Hash moves only after the last hashed move, not the ones that may have been posted before the journal was set on restrict mode
            domain &= Domain('sequence_number', '>', last_move_hashed.sequence_number)

        # On the accounting dashboard, we are only interested on whether there are documents to hash or not
        # so we can stop the computation early if we find at least one document to hash
        if early_stop:
            return self.env['account.move'].sudo().search_count(domain, limit=1)
        moves_to_hash = self.env['account.move'].sudo().search(domain, order='sequence_number')
        warnings = set()
        if moves_to_hash:
            # gap warning
            if last_move_hashed:
                first = last_move_hashed.sequence_number
                difference = len(moves_to_hash)
            else:
                first = moves_to_hash[0].sequence_number
                difference = len(moves_to_hash) - 1
            last = moves_to_hash[-1].sequence_number
            if first + difference != last:
                warnings.add('gap')

            # unreconciled warning
            unreconciled = False in moves_to_hash.statement_line_ids.mapped('is_reconciled')
            if unreconciled:
                warnings.add('unreconciled')
        else:
            warnings.add('no_document')
        moves = moves_to_hash.sudo(False)
        return {
            'previous_hash': last_move_hashed.inalterable_hash,
            'last_move_hashed': last_move_hashed,
            'moves': moves,
            'remaining_moves': self - moves,
            'warnings': warnings,
        }

    def _get_chains_to_hash(self, force_hash=False, raise_if_gap=True, raise_if_no_document=True, include_pre_last_hash=False, early_stop=False):
        """
        From a recordset of moves, retrieve the chains of moves that need to be hashed by taking
        into account the last move of each chain of the recordset.
        So if we have INV/1, INV/2, INV/3, INV4 that are not hashed yet in the database
        but self contains INV/2, INV/3, we will return INV/1, INV/2 and INV/3. Not INV/4.
        :param force_hash: if True, we'll check all moves posted, independently of journal settings
        :param raise_if_gap: if True, we'll raise an error if a gap is detected in the sequence
        :param raise_if_no_document: if True, we'll raise an error if no document needs to be hashed
        :param include_pre_last_hash: if True, we'll include the moves not hashed that are previous to the last hashed move
        :param early_stop: if True, we'll stop the computation as soon as we find at least one document to hash
        :return bool when early_stop else a list of dictionaries (each dict generated by `_get_chain_info`)
        """
        res = []
        for journal, journal_moves in self.grouped('journal_id').items():
            for chain_moves in journal_moves.grouped('sequence_prefix').values():
                chain_info = chain_moves._get_chain_info(
                    force_hash=force_hash, include_pre_last_hash=include_pre_last_hash, early_stop=early_stop
                )

                if not chain_info:
                    continue
                if early_stop:
                    return True
                chain_info['journal_restrict_mode'] = journal.restrict_mode_hash_table

                if 'unreconciled' in chain_info['warnings']:
                    raise UserError(_("An error occurred when computing the inalterability. All entries have to be reconciled."))

                if raise_if_no_document and 'no_document' in chain_info['warnings']:
                    raise UserError(_(
                        "This move could not be locked either because "
                        "some move with the same sequence prefix has a higher number. You may need to resequence it."
                    ))
                if raise_if_gap and 'gap' in chain_info['warnings']:
                    raise UserError(_(
                        "An error occurred when computing the inalterability. A gap has been detected in the sequence."
                    ))

                res.append(chain_info)
        if early_stop:
            return False
        return res

    def _calculate_hashes(self, previous_hash):
        """
        :return: dict of move_id: hash
        """
        hash_version = self.env.context.get('hash_version', MAX_HASH_VERSION)

        def _getattrstring(obj, field_name):
            field_value = obj[field_name]
            if obj._fields[field_name].type == 'many2one':
                field_value = field_value.id
            if obj._fields[field_name].type == 'monetary' and hash_version >= 3:
                return float_repr(field_value, obj.currency_id.decimal_places)
            return str(field_value)

        move2hash = {}
        previous_hash = previous_hash or ''

        for move in self:
            if previous_hash and previous_hash.startswith("$"):
                previous_hash = previous_hash.split("$")[2]  # The hash version is not used for the computation of the next hash
            values = {}
            for fname in move._get_integrity_hash_fields():
                values[fname] = _getattrstring(move, fname)

            for line in move.line_ids:
                for fname in line._get_integrity_hash_fields():
                    k = 'line_%d_%s' % (line.id, fname)
                    values[k] = _getattrstring(line, fname)
            current_record = dumps(values, sort_keys=True, ensure_ascii=True, indent=None, separators=(',', ':'))
            hash_string = sha256((previous_hash + current_record).encode('utf-8')).hexdigest()
            move2hash[move] = f"${hash_version}${hash_string}" if hash_version >= 4 else hash_string
            previous_hash = move2hash[move]
        return move2hash

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

    def _extend_with_attachments(self, files_data, new=False):
        existing_lines = self.invoice_line_ids
        res = super()._extend_with_attachments(files_data, new)

        if new_lines := (self.invoice_line_ids - existing_lines):
            new_lines.is_imported = True
            if not existing_lines:
                self._link_bill_origin_to_purchase_orders(timeout=4)

        return res

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

    def _reason_cannot_decode_has_invoice_lines(self):
        """ Helper to get a reason why an invoice cannot be decoded if it has invoice lines. """
        if self.invoice_line_ids:
            return self.env._("The invoice already contains lines.")

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _prepare_tax_lines_for_taxes_computation(self, tax_amls, round_from_tax_lines):
        if round_from_tax_lines:
            return [self._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]
        return []

    def _prepare_invoice_aggregated_taxes(
        self,
        filter_invl_to_apply=None,
        filter_tax_values_to_apply=None,
        grouping_key_generator=None,
        round_from_tax_lines=None,
        postfix_function=None,
    ):
        """ This method is deprecated and will be removed in the next version.
        Use the following pattern instead:

        base_amls = self.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [self._prepare_product_base_line_for_taxes_computation(x) for x in base_amls]
        tax_amls = self.line_ids.filtered('tax_repartition_line_id')
        tax_lines = [self._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id, tax_lines=tax_lines)

        def grouping_function(base_line, tax_data):
            ...

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        if round_from_tax_lines is None:
            round_from_tax_lines = filter_tax_values_to_apply or filter_invl_to_apply

        base_amls = self.line_ids.filtered(lambda x: x.display_type == 'product' and (not filter_invl_to_apply or filter_invl_to_apply(x)))
        base_lines = [self._prepare_product_base_line_for_taxes_computation(x) for x in base_amls]
        tax_amls = self.line_ids.filtered('tax_repartition_line_id')
        tax_lines = self._prepare_tax_lines_for_taxes_computation(tax_amls, round_from_tax_lines)
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        if postfix_function:
            postfix_function(base_lines)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id, tax_lines=tax_lines)

        # Retro-compatibility with previous aggregator.
        results = {
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
            'tax_details_per_record': defaultdict(lambda: {
                'base_amount_currency': 0.0,
                'base_amount': 0.0,
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
            }),
            'base_lines': base_lines,
        }

        def total_grouping_function(base_line, tax_data):
            if tax_data:
                return not filter_tax_values_to_apply or filter_tax_values_to_apply(base_line, tax_data)

        # Report the total amounts.
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, total_grouping_function)
        for base_line, aggregated_values in base_lines_aggregated_values:
            record = base_line['record']
            base_line_results = results['tax_details_per_record'][record]
            base_line_results['base_line'] = base_line
            for grouping_key, values in aggregated_values.items():
                if grouping_key:
                    for key in ('base_amount', 'base_amount_currency', 'tax_amount', 'tax_amount_currency'):
                        base_line_results[key] += values[key]

        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if grouping_key:
                for key in ('base_amount', 'base_amount_currency', 'tax_amount', 'tax_amount_currency'):
                    results[key] += values[key]

        # Same with the custom grouping_key passed as parameter.
        def tax_details_grouping_function(base_line, tax_data):
            if not total_grouping_function(base_line, tax_data):
                return None
            if grouping_key_generator:
                grouping_key = grouping_key_generator(base_line, tax_data)
                assert grouping_key is not None  # None must be kept for inner-grouping.
                return grouping_key
            return tax_data['tax']

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, tax_details_grouping_function)
        for base_line, aggregated_values in base_lines_aggregated_values:
            record = base_line['record']
            base_line_results = results['tax_details_per_record'][record]
            base_line_results['tax_details'] = tax_details = {}
            for grouping_key, values in aggregated_values.items():
                if not grouping_key:
                    continue
                if isinstance(grouping_key, dict):
                    values.update(grouping_key)
                tax_details[grouping_key] = values

        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        results['tax_details'] = tax_details = {}
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue
            if isinstance(grouping_key, dict):
                values.update(grouping_key)
            tax_details[grouping_key] = values

        return results

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

        def inverse_tax_rep(tax_rep):
            tax = tax_rep.tax_id
            index = list(tax.invoice_repartition_line_ids).index(tax_rep)
            return tax.refund_repartition_line_ids[index]

        company = self.company_id
        payment_term_line = self.line_ids.filtered(lambda x: x.display_type == 'payment_term')
        tax_lines = self.line_ids.filtered('tax_repartition_line_id')
        invoice_lines = self.line_ids.filtered(lambda x: x.display_type == 'product')
        payment_term = self.invoice_payment_term_id
        early_pay_discount_computation = payment_term.early_pay_discount_computation
        discount_percentage = payment_term.discount_percentage

        res = {
            'term_lines': defaultdict(lambda: {}),
            'tax_lines': defaultdict(lambda: {}),
            'base_lines': defaultdict(lambda: {}),
        }
        if not discount_percentage:
            return res

        # Get the current tax amounts in the current invoice.
        tax_amounts = {
            inverse_tax_rep(line.tax_repartition_line_id).id: {
                'amount_currency': line.amount_currency,
                'balance': line.balance,
            }
            for line in tax_lines
        }

        base_lines = [
            {
                **self._prepare_product_base_line_for_taxes_computation(line),
                'is_refund': True,
            }
            for line in invoice_lines
        ]
        for base_line in base_lines:
            base_line['tax_ids'] = base_line['tax_ids'].filtered(lambda t: t.amount_type != 'fixed')

            if early_pay_discount_computation == 'included':
                remaining_part_to_consider = (100 - discount_percentage) / 100.0
                base_line['price_unit'] *= remaining_part_to_consider
        AccountTax = self.env['account.tax']
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, self.company_id)

        if self.is_inbound(include_receipts=True):
            cash_discount_account = company.account_journal_early_pay_discount_loss_account_id
        else:
            cash_discount_account = company.account_journal_early_pay_discount_gain_account_id

        bases_details = {}

        term_amount_currency = payment_term_line.amount_currency - payment_term_line.discount_amount_currency
        term_balance = payment_term_line.balance - payment_term_line.discount_balance
        if early_pay_discount_computation == 'included' and invoice_lines.tax_ids:
            # Compute the base amounts.
            resulting_delta_base_details = {}
            resulting_delta_tax_details = {}
            for base_line in base_lines:
                tax_details = base_line['tax_details']
                invoice_line = base_line['record']

                grouping_dict = {
                    'tax_ids': [Command.set(base_line['tax_ids'].ids)],
                    'tax_tag_ids': [Command.set(base_line['tax_tag_ids'].ids)],
                    'partner_id': base_line['partner_id'].id,
                    'currency_id': base_line['currency_id'].id,
                    'account_id': cash_discount_account.id,
                    'analytic_distribution': base_line['analytic_distribution'],
                }
                base_detail = resulting_delta_base_details.setdefault(frozendict(grouping_dict), {
                    'balance': 0.0,
                    'amount_currency': 0.0,
                })

                amount_currency = self.currency_id\
                    .round(self.direction_sign * tax_details['total_excluded_currency'] - invoice_line.amount_currency)
                balance = self.company_currency_id\
                    .round(self.direction_sign * tax_details['total_excluded'] - invoice_line.balance)

                base_detail['balance'] += balance
                base_detail['amount_currency'] += amount_currency

                bases_details[frozendict(grouping_dict)] = base_detail

            # Compute the tax amounts.
            tax_results = AccountTax._prepare_tax_lines(base_lines, self.company_id)
            for tax_line_vals in tax_results['tax_lines_to_add']:
                tax_amount_without_epd = tax_amounts.get(tax_line_vals['tax_repartition_line_id'])
                if tax_amount_without_epd:
                    resulting_delta_tax_details[tax_line_vals['tax_repartition_line_id']] = {
                        **tax_line_vals,
                        'amount_currency': tax_line_vals['amount_currency'] - tax_amount_without_epd['amount_currency'],
                        'balance': tax_line_vals['balance'] - tax_amount_without_epd['balance'],
                    }

            # Multiply the amount by the percentage
            percentage_paid = abs(payment_term_line.amount_residual_currency / self.amount_total)
            for tax_line_vals in resulting_delta_tax_details.values():
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_line_vals['tax_repartition_line_id'])
                tax = tax_rep.tax_id

                grouping_dict = {
                    'account_id': tax_line_vals['account_id'],
                    'partner_id': tax_line_vals['partner_id'],
                    'currency_id': tax_line_vals['currency_id'],
                    'analytic_distribution': tax_line_vals['analytic_distribution'],
                    'tax_repartition_line_id': tax_rep.id,
                    'tax_ids': tax_line_vals['tax_ids'],
                    'tax_tag_ids': tax_line_vals['tax_tag_ids'],
                    'group_tax_id': tax_line_vals['group_tax_id'],
                }

                res['tax_lines'][payment_term_line][frozendict(grouping_dict)] = {
                    'name': _("Early Payment Discount (%s)", tax.name),
                    'amount_currency': payment_term_line.currency_id.round(tax_line_vals['amount_currency'] * percentage_paid),
                    'balance': payment_term_line.company_currency_id.round(tax_line_vals['balance'] * percentage_paid),
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
        if self.env.context.get('name_as_amount_total'):
            currency_amount = self.currency_id.format(self.amount_total)
            if self.state == 'posted':
                return _("%(ref)s (%(currency_amount)s)", ref=(self.ref or self.name), currency_amount=currency_amount)
            else:
                return _("Draft (%(currency_amount)s)", currency_amount=currency_amount)
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
        if self.name and self.name != '/':
            name = f"{name} {self.name}".strip()
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
        return self._get_reconciled_amls().move_id.origin_payment_id

    def _get_reconciled_statement_lines(self):
        """Helper used to retrieve the reconciled statement lines on this journal entry"""
        return self._get_reconciled_amls().move_id.statement_line_id

    def _get_reconciled_invoices(self):
        """Helper used to retrieve the reconciled invoices on this journal entry"""
        return self._get_reconciled_amls().move_id.filtered(lambda move: move.is_invoice(include_receipts=True))

    def _get_all_reconciled_invoice_partials(self):
        self.ensure_one()
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        if not reconciled_lines.ids:
            return {}

        self.env['account.partial.reconcile'].flush_model([
            'credit_amount_currency', 'credit_move_id', 'debit_amount_currency',
            'debit_move_id', 'exchange_move_id',
        ])
        sql = SQL('''
            SELECT
                part.id,
                part.exchange_move_id,
                part.debit_amount_currency AS amount,
                part.credit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.debit_move_id IN %(line_ids)s

            UNION ALL

            SELECT
                part.id,
                part.exchange_move_id,
                part.credit_amount_currency AS amount,
                part.debit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.credit_move_id IN %(line_ids)s
        ''', line_ids=tuple(reconciled_lines.ids))

        partial_values_list = []
        counterpart_line_ids = set()
        exchange_move_ids = set()
        for values in self.env.execute_query_dict(sql):
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
            sql = SQL('''
                SELECT
                    part.id,
                    part.credit_move_id AS counterpart_line_id
                FROM account_partial_reconcile part
                JOIN account_move_line credit_line ON credit_line.id = part.credit_move_id
                WHERE credit_line.move_id IN %(exchange_move_ids)s AND part.debit_move_id IN %(counterpart_line_ids)s

                UNION ALL

                SELECT
                    part.id,
                    part.debit_move_id AS counterpart_line_id
                FROM account_partial_reconcile part
                JOIN account_move_line debit_line ON debit_line.id = part.debit_move_id
                WHERE debit_line.move_id IN %(exchange_move_ids)s AND part.credit_move_id IN %(counterpart_line_ids)s
            ''', exchange_move_ids=tuple(exchange_move_ids), counterpart_line_ids=tuple(counterpart_line_ids))

            for part_id, line_ids in self.env.execute_query(sql):
                counterpart_line_ids.add(line_ids)
                partial_values_list.append({
                    'aml_id': line_ids,
                    'partial_id': part_id,
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
                .sorted(lambda l: l.account_type not in ('asset_receivable', 'liability_payable')) \
                .grouped(lambda l: (l.account_id, l.currency_id))
            for (account, _currency), lines in group.items():
                if (
                    all(not line.reconciled for line in lines) # if it was reconciled due to a previous group
                    and account.reconcile or account.account_type in ('asset_cash', 'liability_credit_card')
                ):
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
        lock_date = self.company_id._get_user_fiscal_lock_date(self.journal_id)
        posted_caba_entry = self.state == 'posted' and (self.tax_cash_basis_rec_id or self.tax_cash_basis_origin_move_id)
        posted_exchange_diff_entry = self.state == 'posted' and self.exchange_diff_partial_ids
        return not self.inalterable_hash and self.date > lock_date and not posted_caba_entry and not posted_exchange_diff_entry

    def _is_protected_by_audit_trail(self):
        return any(move.posted_before and move.company_id.restrictive_audit_trail for move in self)

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

        :param bool soft: if True, future documents are not immediately posted,
            but are set to be auto posted automatically at the set accounting date.
            Nothing will be performed on those documents before the accounting date.
        :returns: the Model<account.move> documents that have been posted
        """
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))

        # Avoid marking is_manually_modified as True when posting an invoice
        self = self.with_context(skip_is_manually_modified=True)  # noqa: PLW0642

        validation_msgs = set()

        for invoice in self.filtered(lambda move: move.is_invoice(include_receipts=True)):
            if (
                invoice.quick_edit_mode
                and invoice.quick_edit_total_amount
                and invoice.currency_id.compare_amounts(invoice.quick_edit_total_amount, invoice.amount_total) != 0
            ):
                validation_msgs.add(_(
                    "The current total is %(current_total)s but the expected total is %(expected_total)s. In order to post the invoice/bill, "
                    "you can adjust its lines or the expected Total (tax inc.).",
                    current_total=formatLang(self.env, invoice.amount_total, currency_obj=invoice.currency_id),
                    expected_total=formatLang(self.env, invoice.quick_edit_total_amount, currency_obj=invoice.currency_id),
                ))
            if invoice.partner_bank_id and not invoice.partner_bank_id.active:
                validation_msgs.add(_(
                    "The recipient bank account linked to this invoice is archived.\n"
                    "So you cannot confirm the invoice."
                ))
            if float_compare(invoice.amount_total, 0.0, precision_rounding=invoice.currency_id.rounding) < 0:
                validation_msgs.add(_(
                    "You cannot validate an invoice with a negative total amount. "
                    "You should create a credit note instead. "
                    "Use the action menu to transform it into a credit note or refund."
                ))

            if not invoice.partner_id:
                if invoice.is_sale_document():
                    validation_msgs.add(_(
                        "The 'Customer' field is required to validate the invoice.\n"
                        "You probably don't want to explain to your auditor that you invoiced an invisible man :)"
                    ))
                elif invoice.is_purchase_document():
                    validation_msgs.add(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

            # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
            # lines are recomputed accordingly.
            if not invoice.invoice_date and invoice.is_invoice(include_receipts=True):
                invoice.invoice_date = fields.Date.context_today(self)

        for move in self:
            if move.state in ['posted', 'cancel']:
                validation_msgs.add(_('The entry %(name)s (id %(id)s) must be in draft.', name=move.name, id=move.id))
            if not move.line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_subsection', 'line_note')):
                validation_msgs.add(_("Even magicians can't post nothing!"))
            if not soft and move.auto_post != 'no' and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                validation_msgs.add(_("This move is configured to be auto-posted on %(date)s", date=date_msg))
            if not move.journal_id.active:
                validation_msgs.add(_(
                    "You cannot post an entry in an archived journal (%(journal)s)",
                    journal=move.journal_id.display_name,
                ))
            if move.display_inactive_currency_warning:
                validation_msgs.add(_(
                    "You cannot validate a document with an inactive currency: %s",
                    move.currency_id.name
                ))

            if move.line_ids.account_id.filtered(lambda account: not account.active) and not self.env.context.get('skip_account_deprecation_check'):
                validation_msgs.add(_("A line of this move is using a archived account, you cannot post it."))

        if validation_msgs:
            msg = "\n".join([line for line in validation_msgs])
            raise UserError(msg)

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
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report, lock_dates=lock_dates)

        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        to_post.line_ids._create_analytic_lines()

        # Trigger copying for recurring invoices
        to_post.filtered(lambda m: m.auto_post not in ('no', 'at_date'))._copy_recurring_entries()

        for invoice in to_post:
            # Fix inconsistencies that may occure if the OCR has been editing the invoice at the same time of a user. We force the
            # partner on the lines to be the same as the one on the move, because that's the only one the user can see/edit.
            wrong_lines = invoice.is_invoice() and invoice.line_ids.filtered(lambda aml:
                aml.partner_id != invoice.commercial_partner_id
                and aml.display_type not in ('line_section', 'line_subsection', 'line_note')
            )
            if wrong_lines:
                wrong_lines.write({'partner_id': invoice.commercial_partner_id.id})

        # reconcile if state is in draft and move has reversal_entry_id set
        draft_reverse_moves = to_post.filtered(lambda move: move.reversed_entry_id and move.reversed_entry_id.state == 'posted')

        # deal with the eventually related draft moves to the ones we want to post
        partials_to_unlink = self.env['account.partial.reconcile']

        for aml in self.line_ids:
            for partials, counterpart_field in [(aml.matched_debit_ids, 'debit_move_id'), (aml.matched_credit_ids, 'credit_move_id')]:
                for partial in partials:
                    counterpart_move =  partial[counterpart_field].move_id
                    if counterpart_move.state == 'posted' or counterpart_move in to_post:
                        if partial.exchange_move_id:
                            to_post |= partial.exchange_move_id
                            # If the draft invoice changed since it was reconciled, in a way that would affect the exchange diff,
                            # any existing reconcilation and draft exchange move would be deleted already (to force the user to
                            # re-do the reconciliation).
                            # This is ensured by the the checks in env['account.move.line'].write():
                            #     see env[account.move.line]._get_lock_date_protected_fields()['reconciliation']

                        if partial._get_draft_caba_move_vals() != partial.draft_caba_move_vals:
                            # draft invoice changed since it was reconciled, the cash basis entry isn't correct anymore
                            # and the user has to re-do the reconciliation. Existing draft cash basis move will be unlinked
                            partials_to_unlink |= partial

                        elif move.tax_cash_basis_created_move_ids:
                            to_post |= move.tax_cash_basis_created_move_ids.filtered(lambda m: m.tax_cash_basis_rec_id == partial)
                        elif counterpart_move.tax_cash_basis_created_move_ids:
                            to_post |= counterpart_move.tax_cash_basis_created_move_ids.filtered(lambda m: m.tax_cash_basis_rec_id == partial)

        if partials_to_unlink:
            partials_to_unlink.unlink()

        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        if not self.env.user.has_group('account.group_partial_purchase_deductibility') and \
                self.filtered(lambda move: move.move_type == 'in_invoice' and move.invoice_line_ids.filtered(lambda l: l.deductible_amount != 100)):
            self.env.user.sudo().group_ids = [Command.link(self.env.ref('account.group_partial_purchase_deductibility').id)]

        # Add the move number to the non_deductible lines for easier auditing
        if non_deductible_lines := self.line_ids.filtered(lambda line: (line.display_type in ('non_deductible_product_total', 'non_deductible_tax'))):
            for line in non_deductible_lines:
                line.name = (
                    _('%s - private part', line.move_id.name)
                    if line.display_type == 'non_deductible_product_total'
                    else _('%s - private part (taxes)', line.move_id.name)
                )

        draft_reverse_moves.reversed_entry_id._reconcile_reversed_moves(draft_reverse_moves, self.env.context.get('move_reverse_cancel', False))
        to_post.line_ids._reconcile_marked()

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

    def _set_next_made_sequence_gap(self, made_gap: bool):
        """Update the field made_sequence_gap on the next moves of the current ones.

        Either:
        - we changed something related to the sequence on the current moves, so we need to set the
          sequence as broken on the next moves before updating (made_gap=True)
        - we are filling a gap, so we need to update the next move to remove the flag (made_gap=False)
        """
        next_moves = self.browse()
        named = self.filtered(lambda m: m.name and m.name != '/')
        for (journal, prefix), moves in named.grouped(lambda move: (move.journal_id, move.sequence_prefix)).items():
            next_moves += self.env['account.move'].sudo().search([
                ('journal_id', '=', journal.id),
                ('sequence_prefix', '=', prefix),
                ('sequence_number', 'in', [move.sequence_number + 1 for move in moves]),
            ])
        next_moves.made_sequence_gap = made_gap

    def _find_and_set_purchase_orders(self, po_references, partner_id, amount_total, from_ocr=False, timeout=10):
        # hook to be used with purchase, so that vendor bills are sync/autocompleted with purchase orders
        self.ensure_one()

    def _link_bill_origin_to_purchase_orders(self, timeout=10):
        for move in self.filtered(lambda m: m.move_type in self.get_purchase_types()):
            references = move.invoice_origin.split() if move.invoice_origin else []
            move._find_and_set_purchase_orders(references, move.partner_id.id, move.amount_total, timeout=timeout)
        return self

    def _autopost_bill(self):
        # Verify if the bill should be autoposted, if so, post it
        self.ensure_one()
        if (
            self.company_id.autopost_bills
            and self.partner_id
            and self.is_purchase_document(include_receipts=True)
            and self.partner_id.autopost_bills == 'always'
            and not self.abnormal_amount_warning
            and not self.restrict_mode_hash_table
        ):
            if self.duplicated_ref_ids:
                self.message_post(body=_("Auto-post was disabled on this invoice because a potential duplicate was detected."))
            else:
                self.action_post()

    def _show_autopost_bills_wizard(self):
        if (
            len(self) != 1
            or self.state != "posted"
            or not self.is_purchase_document(include_receipts=True)
            or self.restrict_mode_hash_table
            or all(not l.is_imported for l in self.line_ids)
            or not self.partner_id
            or self.partner_id.autopost_bills != "ask"
            or not self.company_id.autopost_bills
            or self.is_manually_modified
        ):
            return False
        prev_bills_same_partner = self.search([
            ('id', '!=', self.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', self.get_purchase_types(include_receipts=True)),
        ], order="create_date DESC", limit=10)
        nb_unmodified_bills = 1  # +1 for current bill that hasn't been modified either
        for move in prev_bills_same_partner:
            if move.is_manually_modified:
                break
            nb_unmodified_bills += 1
        if nb_unmodified_bills < 3:
            return False
        wizard = self.env['account.autopost.bills.wizard'].create({
            'partner_id': self.partner_id.id,
            'nb_unmodified_bills': nb_unmodified_bills,
        })
        return {
            'name': _("Autopost Bills"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.autopost.bills.wizard',
            'res_id': wizard.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    # -------------------------------------------------------------------------
    # PUBLIC ACTIONS
    # -------------------------------------------------------------------------

    def open_payments(self):
        return self.matched_payment_ids._get_records_action(name=_("Payments"))

    def open_reconcile_view(self):
        return self.line_ids.open_reconcile_view()

    def action_open_business_doc(self):
        self.ensure_one()
        if self.origin_payment_id:
            name = _("Payment")
            res_model = 'account.payment'
            res_id = self.origin_payment_id.id
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
        self.invoice_line_ids._compute_price_unit()
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
            'views': [(self.env.ref('account.view_move_tree').id, 'list'), (False, 'form')],
        }

    def open_adjusting_entries(self):
        self.ensure_one()
        return self.adjusting_entries_move_ids._get_records_action(name="Adjusting Entries")

    def open_adjusting_entry_origin_moves(self):
        self.ensure_one()
        label = self.adjusting_entry_origin_label if len(self.adjusting_entries_move_ids) == 1 else 'Invoices'
        return self.adjusting_entry_origin_move_ids._get_records_action(name=label)

    def action_switch_move_type(self):
        if any(move.posted_before for move in self):
            raise ValidationError(_("Once a document has been posted once, its type is set in stone and you can't change it anymore."))
        if any(move.move_type == "entry" for move in self):
            raise ValidationError(_("This action isn't available for this document."))

        for move in self:
            in_out, old_move_type = move.move_type.split('_')
            new_move_type = f"{in_out}_{'invoice' if old_move_type == 'refund' else 'refund'}"
            move.name = False
            move.write({
                'move_type': new_move_type,
                'currency_id': move.currency_id.id,
                'fiscal_position_id': move.fiscal_position_id.id,
            })
            if move.amount_total < 0:
                line_ids_commands = []
                for line in move.line_ids:
                    if line.display_type != 'product':
                        continue
                    line_ids_commands.append(Command.update(line.id, {
                        'quantity': -line.quantity,
                        'extra_tax_data': self.env['account.tax']._reverse_quantity_base_line_extra_tax_data(line.extra_tax_data),
                    }))
                move.write({'line_ids': line_ids_commands})

    def get_currency_rate(self, company_id, to_currency_id, date):
        company = self.env['res.company'].browse(company_id)
        to_currency = self.env['res.currency'].browse(to_currency_id)

        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    def refresh_invoice_currency_rate(self):
        for move in self:
            move.invoice_currency_rate = move.expected_currency_rate

    def action_register_payment(self):
        if any(m.state != 'posted' for m in self):
            raise UserError(_("You can only register payment for posted journal entries."))
        return self.action_force_register_payment()

    def action_force_register_payment(self):
        if any(m.move_type == 'entry' for m in self):
            raise UserError(_("You cannot register payments for miscellaneous entries."))
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
        self.env['account.move.send']._check_move_constrains(self)
        return {
            'name': _("Send"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move.send.wizard' if len(self) == 1 else 'account.move.send.batch.wizard',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
        }

    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()

        report_action = self.action_send_and_print()
        report_action['context'].update({'allow_partners_without_mail': True})
        if self.env.is_admin() and not self.env.company.external_report_layout_id and not self.env.context.get('discard_logo_check'):
            report_action = self.env['ir.actions.report']._action_configure_external_report_layout(report_action, "account.action_base_document_layout_configurator")
            report_action['context']['default_from_invoice'] = self.move_type == 'out_invoice'

        return report_action

    def action_invoice_download_pdf(self, target = "download"):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/account/download_invoice_documents/{",".join(map(str, self.ids))}/pdf',
            'target': target,
        }

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('account.account_invoices').report_action(self.id)

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
        # Disabled by default to avoid breaking automated action flow
        if (
            not self.env.context.get('disable_abnormal_invoice_detection', True)
            and self.filtered(lambda m: m.abnormal_amount_warning or m.abnormal_date_warning)
        ):
            wizard = self.env['validate.account.move'].create({
                'move_ids': [Command.set(self.ids)],
            })
            return {
                'name': _("Confirm Entries"),
                'type': 'ir.actions.act_window',
                'res_model': 'validate.account.move',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }
        if self:
            self._post(soft=False)
        if autopost_bills_wizard := self._show_autopost_bills_wizard():
            return autopost_bills_wizard
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
        self.set_moves_checked()

    def check_selected_moves(self):
        self.env['account.move'].browse(self.env.context.get('active_ids', [])).set_moves_checked()

    def set_moves_checked(self, is_checked=True):
        for move in self.filtered(lambda m: m.state == 'posted'):
            move.checked = is_checked

    def button_draft(self):
        if any(move.state not in ('cancel', 'posted') for move in self):
            raise UserError(_("Only posted/cancelled journal entries can be reset to draft."))
        if any(move.need_cancel_request for move in self):
            raise UserError(_("You can't reset to draft those journal entries. You need to request a cancellation instead."))

        self._check_draftable()
        # We remove all the analytics entries for this journal
        self.line_ids.analytic_line_ids.with_context(skip_analytic_sync=True).unlink()
        self.state = 'draft'

        self._detach_attachments()

    def _get_fields_to_detach(self):
        """"
        Returns a list of field names to detach on resetting an invoice to draft. Can be overridden by other modules to
        add more fields.
        """
        return ['invoice_pdf_report_file']

    def _detach_attachments(self):
        """
        Called by button_draft to detach specific attachments for the current journal entries to allow regeneration.
        """
        files_to_detach = self.sudo().env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', self.ids),
            ('res_field', 'in', self._get_fields_to_detach()),
        ])
        if files_to_detach:
            files_to_detach.res_field = False
            today = format_date(self.env, fields.Date.context_today(self))
            for attachment in files_to_detach:
                attachment_name, attachment_extension = os.path.splitext(attachment.name)
                attachment.name = _(
                    '%(attachment_name)s (detached by %(user)s on %(date)s)%(attachment_extension)s',
                    attachment_name=attachment_name,
                    attachment_extension=attachment_extension,
                    user=self.env.user.name,
                    date=today,
                )

    def _check_draftable(self):
        exchange_move_ids = set()
        if self:
            self.env['account.partial.reconcile'].flush_model(['exchange_move_id'])
            sql = SQL(
                """
                    SELECT DISTINCT exchange_move_id
                    FROM account_partial_reconcile
                    WHERE exchange_move_id IN %s
                """,
                tuple(self.ids),
            )
            exchange_move_ids = {id_ for id_, in self.env.execute_query(sql)}

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
            if move.inalterable_hash:
                raise UserError(_('You cannot reset to draft a locked journal entry.'))

    def button_hash(self):
        self._hash_moves(force_hash=True)

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

        self.line_ids.remove_move_reconcile()
        self.payment_ids.state = "canceled"
        self.write({'auto_post': 'no', 'state': 'cancel'})

    def action_toggle_block_payment(self):
        self.ensure_one()
        if self.payment_state == 'blocked':
            self.payment_state = 'not_paid'
            self.env.add_to_compute(self._fields['payment_state'], self)
        else:
            if self.payment_state in ('paid', 'in_payment'):
                raise UserError(_("You can't block a paid invoice."))
            self.payment_state = 'blocked'

    def action_activate_currency(self):
        self.currency_id.filtered(lambda currency: not currency.active).write({'active': True})

    def _get_mail_template(self):
        """
        :return: the correct mail template based on the current move type
        """
        return self.env.ref(
            'account.email_template_edi_credit_note'
            if all(move.move_type == 'out_refund' for move in self)
            else 'account.email_template_edi_invoice'
        )

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(message, model_description, msg_vals=msg_vals)
        self.ensure_one()

        if self.move_type != 'entry':
            local_msg_vals = dict(msg_vals or {})
            partner_ids = local_msg_vals.get('partner_ids', []) if 'partner_ids' in local_msg_vals else message.partner_ids.ids
            self._portal_ensure_token()
            access_link = self._notify_get_action_link('view', **local_msg_vals, access_token=self.access_token)

            # Create a new group for partners that have been manually added as recipients.
            # Those partners should have access to the invoice.
            button_access = {'url': access_link} if access_link else {}
            recipient_group = (
                'additional_intended_recipient',
                lambda pdata: pdata['id'] in partner_ids and pdata['id'] != self.partner_id.id and pdata['type'] != 'user',
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

    def _autopost_draft_entries(self, batch_size=100):
        ''' This method is called from a cron job.
        It is used to post entries such as those created by the module
        account_asset and recurring entries created in _post().
        '''
        domain = [
            ('state', '=', 'draft'),
            ('date', '<=', fields.Date.context_today(self)),
            ('auto_post', '!=', 'no'),
        ]
        moves = self.search(domain, limit=batch_size)
        remaining = len(moves) if len(moves) < batch_size else self.search_count(domain)
        self.env['ir.cron']._commit_progress(remaining=remaining)

        try:  # try posting in batch
            moves._post()
            self.env['ir.cron']._commit_progress(len(moves))
            return
        except UserError:  # if at least one move cannot be posted, handle moves one by one
            self.env.cr.rollback()

        for move in moves:
            try:
                move = move.try_lock_for_update().filtered_domain(domain)
                if not move:
                    continue
                move._post()
                self.env['ir.cron']._commit_progress(1)
            except UserError as e:
                self.env.cr.rollback()
                msg = _('The move could not be posted for the following reason: %(error_message)s', error_message=e)
                move.message_post(body=msg, message_type='comment')
                self.env['ir.cron']._commit_progress()

    @api.model
    def _cron_account_move_send(self, job_count=10):
        """ Process invoices generation and sending asynchronously.
        :param job_count: maximum number of jobs to process if specified.
        """
        def get_account_notification(moves, is_success: bool):
            _ = self.env._
            return [
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

        domain = [('sending_data', '!=', False)]
        to_process = self.search(domain, limit=job_count).try_lock_for_update()
        if not to_process:
            return

        # Collect moves by res.partner that executed the Send & Print wizard, must be done before the _process
        # that modify sending_data.
        moves_by_partner = to_process.grouped(lambda m: m.sending_data['author_partner_id'])

        self.env['account.move.send']._generate_and_send_invoices(
            to_process,
            from_cron=True,
        )

        for partner_id, partner_moves in moves_by_partner.items():
            partner = self.env['res.partner'].browse(partner_id)
            partner_moves_error = partner_moves.filtered(lambda m: m.sending_data and m.sending_data.get('error'))
            if partner_moves_error:
                partner._bus_send(*get_account_notification(partner_moves_error, False))
            partner_moves_success = partner_moves - partner_moves_error
            if partner_moves_success:
                partner._bus_send(*get_account_notification(partner_moves_success, True))
            partner_moves_error.sending_data = False

        self.env['ir.cron']._commit_progress(len(to_process), remaining=self.search_count(domain))

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------
    def _get_available_action_reports(self, is_invoice_report=True):
        domain = [('model', '=', 'account.move')]

        if is_invoice_report:
            domain += [('is_invoice_report', '=', 'True')]

        model_reports = self.env['ir.actions.report'].search(domain)

        available_reports = model_reports.filtered(
            lambda model_template: len(self.filtered_domain(ast.literal_eval(model_template.domain or '[]'))) == len(self)
        )

        return available_reports

    def _is_action_report_available(self, action_report, is_invoice_report=True):
        assert len(action_report) == 1

        self.ensure_one()

        if available_report := action_report.filtered(lambda available_report: not (is_invoice_report^available_report.is_invoice_report)):
            return bool(self.filtered_domain(ast.literal_eval(available_report.domain or '[]')))

        return False

    @api.model
    def _get_suitable_journal_ids(self, move_type, company=False):
        """Return the suitable journals for the given move type and company (current company if False)."""
        journal_type = self._get_invoice_filter_type_domain(move_type) or 'general'
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(company or self.env.company),
            ('type', '=', journal_type),
        ])

    @api.model
    def _get_invoice_filter_type_domain(self, move_type):
        if self.is_sale_document(include_receipts=True, move_type=move_type):
            return 'sale'
        elif self.is_purchase_document(include_receipts=True, move_type=move_type):
            return 'purchase'
        else:
            return False

    @api.model
    def get_invoice_types(self, include_receipts=False):
        return self.get_sale_types(include_receipts) + self.get_purchase_types(include_receipts)

    def is_invoice(self, include_receipts=False):
        return self.is_sale_document(include_receipts) or self.is_purchase_document(include_receipts)

    def is_entry(self):
        return self.move_type == 'entry'

    def is_receipt(self):
        return self.move_type in ['out_receipt', 'in_receipt']

    @api.model
    def get_sale_types(self, include_receipts=False):
        return ['out_invoice', 'out_refund'] + (include_receipts and ['out_receipt'] or [])

    def is_sale_document(self, include_receipts=False, move_type=False):
        return (move_type or self.move_type) in self.get_sale_types(include_receipts)

    @api.model
    def get_purchase_types(self, include_receipts=False):
        return ['in_invoice', 'in_refund'] + (include_receipts and ['in_receipt'] or [])

    def is_purchase_document(self, include_receipts=False, move_type=False):
        return (move_type or self.move_type) in self.get_purchase_types(include_receipts)

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

    def _get_installments_data(self):
        self.ensure_one()
        term_lines = self.line_ids.filtered(lambda l: l.display_type == 'payment_term')
        return term_lines._get_installments_data()

    def _get_invoice_next_payment_values(self, custom_amount=None):
        self.ensure_one()
        term_lines = self.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        if not term_lines:
            return {}
        installments = term_lines._get_installments_data()
        not_reconciled_installments = [x for x in installments if not x['reconciled']]
        overdue_installments = [x for x in not_reconciled_installments if x['type'] == 'overdue']
        # Early payment discounts can only have one installment at most
        epd_installment = next((installment for installment in installments if installment['type'] == 'early_payment_discount'), {})
        show_installments = len(installments) > 1
        additional_info = {}

        if show_installments and overdue_installments:
            installment_state = 'overdue'
            amount_due = self.amount_residual
            next_amount_to_pay = sum(x['amount_residual_currency_unsigned'] for x in overdue_installments)
            next_payment_reference = f"{self.name}-{overdue_installments[0]['number']}"
            next_due_date = overdue_installments[0]['date_maturity']
        elif show_installments and not_reconciled_installments:
            installment_state = 'next'
            amount_due = self.amount_residual
            next_amount_to_pay = not_reconciled_installments[0]['amount_residual_currency_unsigned']
            next_payment_reference = f"{self.name}-{not_reconciled_installments[0]['number']}"
            next_due_date = not_reconciled_installments[0]['date_maturity']
        elif epd_installment:
            installment_state = 'epd'
            amount_due = epd_installment['amount_residual_currency_unsigned']
            next_amount_to_pay = self.amount_residual
            next_payment_reference = self.name
            next_due_date = epd_installment['date_maturity']
            discount_date = epd_installment['line'].discount_date or fields.Date.context_today(self)
            discount_amount_currency = epd_installment['discount_amount_currency']
            days_left = max(0, (discount_date - fields.Date.context_today(self)).days)  # should never be lower than 0 since epd is valid
            if days_left > 0:
                discount_msg = _(
                    "Discount of %(amount)s if paid within %(days)s days",
                    amount=self.currency_id.format(discount_amount_currency),
                    days=days_left,
                )
            else:
                discount_msg = _(
                    "Discount of %(amount)s if paid today",
                    amount=self.currency_id.format(discount_amount_currency),
                )

            additional_info.update({
                'epd_discount_amount_currency': discount_amount_currency,
                'epd_discount_amount': epd_installment['discount_amount'],
                'discount_date': fields.Date.to_string(discount_date),
                'epd_days_left': days_left,
                'epd_line': epd_installment['line'],
                'epd_discount_msg': discount_msg,
            })
        else:
            installment_state = None
            amount_due = self.amount_residual
            next_amount_to_pay = self.amount_residual
            next_payment_reference = self.name
            next_due_date = self.invoice_date_due

        if custom_amount is not None:
            is_custom_amount_same_as_next_amount = self.currency_id.is_zero(custom_amount - next_amount_to_pay)
            is_custom_amount_same_as_epd_discounted_amount = installment_state == 'epd' and self.currency_id.is_zero(custom_amount - amount_due)
            if not is_custom_amount_same_as_next_amount and not is_custom_amount_same_as_epd_discounted_amount:
                installment_state = 'next'
                next_amount_to_pay = custom_amount
                next_payment_reference = self.name
                next_due_date = installments[0]['date_maturity']

        return {
            'payment_state': self.payment_state,
            'installment_state': installment_state,
            'next_amount_to_pay': next_amount_to_pay,
            'next_payment_reference': next_payment_reference,
            'amount_paid': self.amount_total - self.amount_residual,
            'amount_due': amount_due,
            'next_due_date': next_due_date,
            'due_date': self.invoice_date_due,
            'not_reconciled_installments': not_reconciled_installments,
            'is_last_installment': len(not_reconciled_installments) == 1,
            **additional_info,
        }

    def _get_invoice_portal_extra_values(self, custom_amount=None):
        self.ensure_one()
        return {
            'invoice': self,
            'currency': self.currency_id,
            **self._get_invoice_next_payment_values(custom_amount=custom_amount),
        }

    def _get_accounting_date(self, invoice_date, has_tax, lock_dates=None):
        """Get correct accounting date for previous periods, taking tax lock date and affected journal into account.
        When registering an invoice in the past, we still want the sequence to be increasing.
        We then take the last day of the period, depending on the sequence format.

        If there is a tax lock date and there are taxes involved, we register the invoice at the
        last date of the first open period.
        :param invoice_date (datetime.date): The invoice date
        :param has_tax (bool): Iff any taxes are involved in the lines of the invoice
        :param lock_dates: Like result from `_get_violated_lock_dates`;
                           Can be used to avoid recomputing them in case they are already known.
        :rtype: datetime.date
        """
        self.ensure_one()
        lock_dates = lock_dates or self._get_violated_lock_dates(invoice_date, has_tax)
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
            if not highest_name or number_reset in ('month', 'year_range_month'):
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
        self.ensure_one()
        return self.company_id._get_violated_lock_dates(invoice_date, has_tax, self.journal_id)

    def _get_lock_date_message(self, invoice_date, has_tax):
        """Get a message describing the latest lock date affecting the specified date.
        :param invoice_date: The date to be checked
        :param has_tax: If any taxes are involved in the lines of the invoice
        :return: a message describing the latest lock date affecting this move and the date it will be
                 accounted on if posted, or False if no lock dates affect this move.
        """
        lock_dates = self._get_violated_lock_dates(invoice_date, has_tax)
        if lock_dates:
            invoice_date = self._get_accounting_date(invoice_date, has_tax, lock_dates=lock_dates)
            tax_lock_date_message = _(
                "The date is being set prior to: %(lock_date_info)s. "
                "The Journal Entry will be accounted on %(invoice_date)s upon posting.",
                lock_date_info=self.env['res.company']._format_lock_dates(lock_dates),
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

    def _generate_portal_payment_qr(self):
        # This method is designed to prevent traceback.
        # Scenario: A traceback occurs when `account.payment` is not installed, and the user attempts to
        # preview or print the invoice.
        self.ensure_one()
        return None

    def _get_portal_payment_link(self):
        # This method is designed to prevent traceback.
        # Scenario: A traceback occurs when `account.payment` is not installed, and the user attempts to
        # preview or print the invoice.
        self.ensure_one()
        return None

    def _generate_and_send(self, force_synchronous=True, allow_fallback_pdf=True, **custom_settings):
        """ Generate the pdf and electronic format(s) for the current invoices and send them given default settings
        (on partner or company) or given provided custom_settings.
        :param force_synchronous: whether to process (as)synchronously (! only relevant for batch sending (multiple invoices))
        :param allow_fallback_pdf:  In case of error when generating the documents for invoices, generate a
                                    proforma PDF report instead.
        :param custom_settings: custom settings to create the wizard (! only relevant for single sending (one invoice))
        (Since default settings are use for batch sending.
        If you are looking for something more flexible, directly call env[account.move.send]._generate_and_send_invoices method.)
        """
        if not self:
            return
        if len(self) == 1:
            wizard = self.env['account.move.send.wizard'].with_context(
                active_model='account.move',
                active_ids=self.ids,
            ).create(custom_settings)
            wizard.action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
        else:
            wizard = self.env['account.move.send.batch.wizard'].with_context(
                active_model='account.move',
                active_ids=self.ids,
            ).create({})
            wizard.action_send_and_print(force_synchronous=force_synchronous)
        return wizard

    def _get_invoice_pdf_proforma(self):
        """ Generate the Proforma of the invoice.
        :return dict: the Proforma's data such as
        {'filename': 'INV_2024_0001_proforma.pdf', 'filetype': 'pdf', 'content': ...}
        """
        self.ensure_one()
        filename = self._get_invoice_proforma_pdf_report_filename()
        content, report_type = self.env['ir.actions.report']._pre_render_qweb_pdf('account.account_invoices', self.ids, data={'proforma': True})
        content_by_id = self.env['ir.actions.report']._get_splitted_report('account.account_invoices', content, report_type)
        return {
            'filename': filename,
            'filetype': 'pdf',
            'content': content_by_id[self.id],
        }

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        """ Retrieve the invoice legal document of type filetype.
        :param filetype: the type of legal document to retrieve. Example: 'pdf'.
        :param bool allow_fallback: if True, returns a Proforma if the PDF invoice doesn't exist.
        :return dict: the invoice PDF data such as
        {'filename': 'INV_2024_0001.pdf', 'filetype': 'pdf', 'content':...}
        To extend to add more supported filetypes.
        """
        self.ensure_one()
        if filetype == 'pdf':
            if invoice_pdf := self.invoice_pdf_report_id:
                return {
                    'filename': invoice_pdf.name,
                    'filetype': invoice_pdf.mimetype,
                    'content': invoice_pdf.raw,
                }
            elif allow_fallback:
                return self._get_invoice_pdf_proforma()

    def _get_invoice_legal_documents_all(self, allow_fallback=False):
        """ Retrieve the invoice legal attachments: PDF, XML, ...
        :param bool allow_fallback: if True, returns a Proforma if the PDF invoice doesn't exist.
        :return list: a list of the attachments data such as
        [{'filename': 'INV_2024_0001.pdf', 'filetype': 'pdf', 'content': ...}, ...]
        """
        self.ensure_one()
        if self.invoice_pdf_report_id:
            attachments = self.env['account.move.send']._get_invoice_extra_attachments(self)
            return [
                {
                    'filename': attachment.name,
                    'filetype': attachment.mimetype,
                    'content': attachment.raw,
                }
                for attachment in attachments
            ]
        elif allow_fallback:
            return [self._get_invoice_pdf_proforma()]

    def _get_invoice_report_filename(self, extension='pdf'):
        """ Get the filename of the generated invoice report with extension file. """
        self.ensure_one()
        return f"{self.name.replace('/', '_')}.{extension}"

    def _get_invoice_proforma_pdf_report_filename(self):
        """ Get the filename of the generated proforma PDF invoice report. """
        self.ensure_one()
        return f"{self._get_move_display_name().replace(' ', '_').replace('/', '_')}_proforma.pdf"

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

    def _get_available_invoice_template_pdf_report_ids(self):
        """
        Helper to get available invoice template pdf reports
        """
        moves = self

        for move_type in ['out_invoice', 'out_refund', 'out_receipt']:
            moves += self.new({'move_type': move_type})

        available_reports = moves._get_available_action_reports()

        if not available_reports:
            raise UserError(_("There is no template that applies to invoices."))

        return available_reports

    def _is_user_able_to_review(self):
        # If only account is installed, we don't check user access rights.
        return True

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

        If the value linked to the key is the same as the target, yield `True`.
        Check for the key both in the record's context and in the recursion stack.

        :param container: deprecated, not used anymore
        :param key: The context key to apply to the recordsets.
        :param default: the default value of the context key, if it isn't defined
                        yet in the context
        :param target: the value of the context key meaning that we shouldn't
                       recurse
        :return: True iff we should just exit the context manager
        """

        stack = self.env.cr.cache.setdefault('account_disable_recursion_stack', StackMap())
        try:
            current_val = stack[key]
        except KeyError:
            current_val = self.env.context.get(key, default)

        disabled = current_val == target
        stack.pushmap({key: target})
        try:
            yield disabled
        finally:
            stack.popmap()

    # ------------------------------------------------------------
    # MAIL.THREAD
    # ------------------------------------------------------------

    def _mailing_get_default_domain(self, mailing):
        return ['&', ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]

    @api.model
    def _routing_check_route(self, message, message_dict, route, raise_exception=True):
        if route[0] == 'account.move' and len(message_dict['attachments']) < 1:
            # Don't create the move if no attachment.
            body = self.env['ir.qweb']._render('account.email_template_mail_gateway_failed', {
                'company_email': self.env.company.email,
                'company_name': self.env.company.name,
            })
            self._routing_create_bounce_email(
                message_dict['from'], body, message,
                references=f'{message_dict["message_id"]} {generate_tracking_message_id("loop-detection-bounce-email")}')
            return ()
        return super()._routing_check_route(message, message_dict, route, raise_exception=raise_exception)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # EXTENDS mail mail.thread
        custom_values = custom_values or {}
        # Add custom behavior when receiving a new invoice through the mail's gateway.
        if custom_values.get('move_type', 'entry') not in ('out_invoice', 'in_invoice', 'entry'):
            return super().message_new(msg_dict, custom_values=custom_values)

        self = self.with_context(skip_is_manually_modified=True)  # noqa: PLW0642

        company = self.env['res.company'].browse(custom_values['company_id']) if custom_values.get('company_id') else self.env.company

        def is_internal_partner(partner):
            # Helper to know if the partner is an internal one.
            return (
                    company.partner_id in (partner | partner.parent_id)
                    or (partner.user_ids and all(user._is_internal() for user in partner.user_ids))
            )

        def is_right_company(partner):
            if company:
                return partner.company_id.id in [False, company.id]
            return True

        # Search for partner that sent the mail.
        from_mail_addresses = email_split(msg_dict.get('from', ''))
        partners = self._partner_find_from_emails_single(
            from_mail_addresses, filter_found=lambda p: is_right_company(p) or not p.partner_share, no_create=True,
        )
        # if we are in the case when an internal user forwarded the mail manually
        # search for partners in mail's body
        if partners and is_internal_partner(partners[0]):
            # Search for partners in the mail's body.
            body_mail_addresses = set(email_re.findall(msg_dict.get('body')))
            partners = self._partner_find_from_emails_single(
                body_mail_addresses, filter_found=lambda p: is_right_company(p) or p.partner_share, no_create=True,
            ) if body_mail_addresses else self.env['res.partner']

        # Little hack: Inject the mail's subject in the body.
        if msg_dict.get('subject') and msg_dict.get('body'):
            msg_dict['body'] = Markup('<div><div><h3>%s</h3></div>%s</div>') % (msg_dict['subject'], msg_dict['body'])

        # Create the invoice.
        values = {
            'name': '/',  # we have to give the name otherwise it will be set to the mail's subject
            'invoice_source_email': from_mail_addresses[0],
            'partner_id': partners[0].id if partners else False,
        }
        move_ctx = self.with_context(from_alias=True, default_move_type=custom_values.get('move_type', 'entry'), default_journal_id=custom_values.get('journal_id'))
        move = super(AccountMove, move_ctx).message_new(msg_dict, custom_values=values)
        move._compute_name()  # because the name is given, we need to recompute in case it is the first invoice of the journal

        move.journal_id._notify_einvoices_received(move)

        return move

    def _message_post_after_hook(self, new_message, message_values):
        """ This method processes the attachments of a new mail.message. It handles the 3 following situations:
            (1) receiving an e-mail from a mail alias. In that case, we potentially want to split the attachments into several invoices.
            (2) receiving an e-mail / posting a message on an existing invoice via the webclient:
                (2)(a): If the poster is an internal user, we enhance the invoice with the attachments.
                (2)(b): Otherwise, we don't do any further processing.
            (3) posting a message on an invoice in application code. In that case, don't do anything.

            Furthermore, in cases (1) and (2), we decide for each attachment whether to add it as an attachment on the invoice,
            based on its mimetype.
        """
        # EXTENDS mail mail.thread
        attachments = new_message.attachment_ids

        if not attachments or new_message.message_type not in {'email', 'comment'} or self.env.context.get('disable_attachment_import'):
            # No attachments, or the message was created in application code, so don't do anything.
            return super()._message_post_after_hook(new_message, message_values)

        files_data = self._to_files_data(attachments)

        # Extract embedded files. Note that `_unwrap_attachments` may create ir.attachment records - for example
        # see l10n_{es,it}_edi, so to retrieve those attachments you should use the `_from_files_data` method.
        files_data.extend(self._unwrap_attachments(files_data))

        if self.env.context.get('from_alias'):
            # This is a newly-created invoice from a mail alias.
            # So dispatch the attachments into groups, and create a new invoice for each group beyond the first.
            file_data_groups = self._group_files_data_into_groups_of_mixed_types(files_data)

            invoices = self
            if len(file_data_groups) > 1:
                create_vals = (len(file_data_groups) - 1) * self.copy_data()
                invoices |= self.with_context(skip_is_manually_modified=True).create(create_vals)

            for invoice, file_data_group in zip(invoices, file_data_groups):
                attachment_records = self._from_files_data(file_data_group)
                invoice._fix_attachments_on_record(attachment_records)

                if invoice == self:
                    new_message.attachment_ids = [Command.set(attachment_records.ids)]
                    message_values['attachment_ids'] = [Command.link(attachment.id) for attachment in attachment_records]
                    res = super()._message_post_after_hook(new_message, message_values)
                else:
                    sub_new_message = new_message.copy({
                        'res_id': invoice.id,
                        'attachment_ids': [Command.set(attachment_records.ids)],
                    })
                    sub_message_values = {
                        **message_values,
                        'res_id': invoice.id,
                        'attachment_ids': [Command.link(attachment.id) for attachment in attachment_records],
                    }
                    super(AccountMove, invoice)._message_post_after_hook(sub_new_message, sub_message_values)

            for invoice, file_data_group in zip(invoices, file_data_groups):
                invoice._extend_with_attachments(file_data_group, new=True)

            return res

        else:
            # This is an existing invoice on which a message was posted either by e-mail or via the webclient.
            attachment_records = self._from_files_data(files_data)
            self._fix_attachments_on_record(attachment_records)

            # Only trigger decoding if the message was sent by an active internal user (note OdooBot is always inactive).
            if self.env.user.active and self.env.user._is_internal():
                self._extend_with_attachments(files_data)

            new_message.attachment_ids = [Command.set(attachment_records.ids)]
            message_values['attachment_ids'] = [Command.link(attachment.id) for attachment in attachment_records]
            return super()._message_post_after_hook(new_message, message_values)

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
            if self.origin_payment_id and 'state' in init_values:
                self.origin_payment_id._message_track(['state'], {self.origin_payment_id.id: init_values})
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
                                                   force_email_company=False, force_email_lang=False,
                                                   force_record_name=False):
        # EXTENDS mail mail.thread
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals=msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang,
            force_record_name=force_record_name,
        )
        record = render_context['record']
        subtitles = [f"{record.name} - {record.partner_id.name}" if record.partner_id.name else record.name]
        if self.is_invoice(include_receipts=True):
            # Only show the amount in emails for non-miscellaneous moves. It might confuse recipients otherwise.
            if self.invoice_date_due and self.payment_state not in ('in_payment', 'paid'):
                subtitles.append(_(
                    '%(amount)s due\N{NO-BREAK SPACE}%(date)s',
                    amount=format_amount(self.env, self.amount_total, self.currency_id, lang_code=render_context.get('lang')),
                    date=format_date(self.env, self.invoice_date_due, lang_code=render_context.get('lang')),
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

    def get_extra_print_items(self):
        """ Helper to dynamically add items in the 'Print' menu of list and form of account.move.
        """
        # TO OVERRIDE
        return []

    @staticmethod
    def _can_commit():
        """ Helper to know if we can commit the current transaction or not.

        :returns: True if commit is acceptable, False otherwise.
        """
        return not modules.module.current_test

    @api.model
    def get_import_templates(self):
        move_type = self.env.context.get('default_move_type')
        match move_type:
            case 'entry':
                return [{
                    'label': _('Import Template for Misc. Operations'),
                    'template': '/account/static/xls/misc_operations_import_template.xlsx',
                }]
            case 'out_invoice':
                return [{
                    'label': _('Import Template for Invoices'),
                    'template': '/account/static/xls/customer_invoices_credit_notes_import_template.xlsx',
                }]
            case 'out_refund':
                return [{
                    'label': _('Import Template for Credit Notes'),
                    'template': '/account/static/xls/customer_invoices_credit_notes_import_template.xlsx',
                }]
            case 'in_invoice':
                return [{
                    'label': _('Import Template for Bills'),
                    'template': '/account/static/xls/vendor_bills_refunds_import_template.xlsx',
                }]
            case 'in_refund':
                return [{
                    'label': _('Import Template for Refunds'),
                    'template': '/account/static/xls/vendor_bills_refunds_import_template.xlsx',
                }]
            case _:
                return []
