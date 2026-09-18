import ast
import logging
import re
import sys
import uuid
from collections import defaultdict
from contextlib import ExitStack, contextmanager, nullcontext
from datetime import date, timedelta
from textwrap import shorten

from markupsafe import Markup

from odoo import _, api, fields, models, modules
from odoo.db.errors import PG_RETRY_EXCEPTIONS
from odoo.db.schema import column_exists, create_column
from odoo.exceptions import AccessError, RedirectWarning, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    SQL,
    TransactionMemo,
    date_utils,
    float_compare,
    format_date,
    format_list,
    formatLang,
    frozendict,
    get_lang,
    groupby,
)
from odoo.tools.date_utils import time_unit_selection
from odoo.tools.mail import is_html_empty
from odoo.tools.misc import StackMap
from odoo.tools.safe_eval import safe_eval

from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES

_logger = logging.getLogger(__name__)
DEFAULT_JOURNALS = TransactionMemo(
    "account.move.default_journals", invalidated_by=("account.journal",)
)
INVOICE_TEMPLATE_REPORTS = TransactionMemo(
    "account.move.invoice_template_reports", invalidated_by=("ir.actions.report",)
)

_debug = DebugLog(__name__)


MAX_HASH_VERSION = 4

DISABLE_RECURSION_STACK_CACHE_KEY = "account_disable_recursion_stack"

PAYMENT_STATE_SELECTION = [
    ("not_paid", "Not Paid"),
    ("in_payment", "In Payment"),
    ("paid", "Paid"),
    ("partial", "Partially Paid"),
    ("reversed", "Reversed"),
    ("blocked", "Blocked"),
    ("invoicing_legacy", "Invoicing App Legacy"),
]

TYPE_REVERSE_MAP = {
    "entry": "entry",
    "out_invoice": "out_refund",
    "out_refund": "out_invoice",
    "in_invoice": "in_refund",
    "in_refund": "in_invoice",
    "out_receipt": "out_refund",
    "in_receipt": "in_refund",
}

RECEIVABLE_PAYABLE_TYPES = ("asset_receivable", "liability_payable")

EMPTY = object()
BYPASS_LOCK_CHECK = object()


_SQL_DUPLICATE_OUT_MOVES = """
move.move_type in ('out_invoice', 'out_refund')
AND (
   move.amount_total = duplicate_move.amount_total
   AND move.amount_total != 0.0
   AND move.invoice_date = duplicate_move.invoice_date
)
"""

_SQL_DUPLICATE_IN_MOVES = """
move.move_type in ('in_invoice', 'in_refund')
AND duplicate_move.move_type in ('in_invoice', 'in_refund')
AND (
   -- case 1: same ref and (no date or same year)
     (
         move.ref = duplicate_move.ref
         AND (
             move.invoice_date IS NULL
             OR
             duplicate_move.invoice_date IS NULL
             OR
             date_part('year', move.invoice_date) = date_part('year', duplicate_move.invoice_date)
         )
     )
     -- case 2: different refs, same partner, amount and date
     OR (
            move.commercial_partner_id = duplicate_move.commercial_partner_id
            AND move.amount_total = duplicate_move.amount_total
            AND move.amount_total != 0.0
            AND move.invoice_date = duplicate_move.invoice_date
   )
)
"""

_SQL_DUPLICATE_MOVES = """
SELECT move.id AS move_id,
       array_agg(duplicate_move.id) AS duplicate_ids
  FROM %(move_table_and_alias)s
  JOIN account_move AS duplicate_move
    ON move.company_id = duplicate_move.company_id
   AND move.id != duplicate_move.id
   AND duplicate_move.state IN %(matching_states)s
   AND move.move_type = duplicate_move.move_type
   AND move.currency_id = duplicate_move.currency_id
   AND (
           move.commercial_partner_id = duplicate_move.commercial_partner_id
           OR (move.commercial_partner_id IS NULL AND duplicate_move.state = 'draft')
       )
   AND (%(move_type_sql_condition)s)
 WHERE move.id IN %(moves)s
 GROUP BY move.id
"""


_SQL_SEQUENCE_NEIGHBOURS = """
SELECT ARRAY(
                SELECT other.id
                  FROM account_move other
                 WHERE other.journal_id = move.journal_id
                   AND other.sequence_prefix = move.sequence_prefix
                   AND other.sequence_number < move.sequence_number
              ORDER BY other.sequence_number DESC
                 LIMIT 2
       ),
       move.id,
       ARRAY(
                SELECT other.id
                  FROM account_move other
                 WHERE other.journal_id = move.journal_id
                   AND other.sequence_prefix = move.sequence_prefix
                   AND other.sequence_number > move.sequence_number
              ORDER BY other.sequence_number ASC
                 LIMIT 2
       )
  FROM account_move move
 WHERE move.id = ANY(%s)
"""


_SQL_ABNORMAL_INVOICE_STATS = """
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
              SELECT DISTINCT ON (id)
                     id, last_invoice_date, date_diff_mean, date_diff_deviation, amount_mean, amount_deviation
                FROM stats
               WHERE row_number BETWEEN 10 AND 30
            ORDER BY id, row_number DESC
"""


_SQL_PAYMENT_RECONCILIATION = """
                    SELECT
                        source_line.id AS source_line_id,
                        source_line.move_id AS source_move_id,
                        account.account_type AS source_line_account_type,
                        ARRAY_AGG(counterpart_move.move_type) AS counterpart_move_types,
                        COALESCE(BOOL_AND(COALESCE(pay.is_bank_matched, FALSE))
                            FILTER (WHERE pay.id IS NOT NULL), TRUE) AS all_payments_matched,
                        BOOL_OR(COALESCE(BOOL(pay.id), FALSE)) as has_payment,
                        BOOL_OR(COALESCE(BOOL(counterpart_move.statement_line_id), FALSE)) as has_st_line
                    FROM account_partial_reconcile part
                    JOIN account_move_line source_line ON source_line.id = part.%s
                    JOIN account_account account ON account.id = source_line.account_id
                    JOIN account_move_line counterpart_line ON counterpart_line.id = part.%s
                    JOIN account_move counterpart_move ON counterpart_move.id = counterpart_line.move_id
                    LEFT JOIN account_payment pay ON pay.move_id = counterpart_move.id
                    WHERE source_line.move_id = ANY(%s) AND counterpart_line.move_id != source_line.move_id
                    GROUP BY source_line.id, source_line.move_id, account.account_type
"""


_SQL_PAYMENTS_PER_INVOICE = """
SELECT invoice_id,
       ARRAY_AGG(DISTINCT payment_id) AS payment_ids
  FROM (
        SELECT counterpart_line.move_id AS invoice_id,
               payment.id AS payment_id
          FROM account_partial_reconcile part
          JOIN account_move_line line ON line.id = part.debit_move_id
          JOIN account_move_line counterpart_line ON counterpart_line.id = part.credit_move_id
          JOIN account_payment payment ON payment.move_id = line.move_id
          JOIN account_account account ON account.id = line.account_id
         WHERE account.account_type IN ('asset_receivable', 'liability_payable')
           AND counterpart_line.move_id = ANY(%(invoice_ids)s)
           AND counterpart_line.id != line.id

        UNION ALL

        SELECT counterpart_line.move_id AS invoice_id,
               payment.id AS payment_id
          FROM account_partial_reconcile part
          JOIN account_move_line line ON line.id = part.credit_move_id
          JOIN account_move_line counterpart_line ON counterpart_line.id = part.debit_move_id
          JOIN account_payment payment ON payment.move_id = line.move_id
          JOIN account_account account ON account.id = line.account_id
         WHERE account.account_type IN ('asset_receivable', 'liability_payable')
           AND counterpart_line.move_id = ANY(%(invoice_ids)s)
           AND counterpart_line.id != line.id
       ) links
 GROUP BY invoice_id
"""


_SQL_RECONCILED_PARTIALS = """
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
"""

_SQL_EXCHANGE_MOVE_PARTIALS = """
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
"""


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = [
        "mixin.portal",
        "mixin.mail.thread.main.attachment",
        "mixin.mail.activity",
        "mixin.sequence",
        "mixin.product.catalog",
        "mixin.account.document.import",
        "mixin.default.read.fields",
        "mixin.recurrence.rule",
    ]
    _description = "Journal Entry"
    _order = "date desc, name desc, invoice_date desc, id desc"
    _mail_post_access = "read"
    _check_company_auto = True
    _sequence_index = "journal_id"
    _rec_names_search = ["name", "partner_id.name", "ref"]
    _mailing_enabled = True
    _operation_checkpoints = {"action_post": "_post_check_business_rules"}

    @property
    def _sequence_monthly_regex(self):
        return (
            self.journal_id.sequence_override_regex or super()._sequence_monthly_regex
        )

    @property
    def _sequence_yearly_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_yearly_regex

    @property
    def _sequence_year_range_regex(self):
        return (
            self.journal_id.sequence_override_regex
            or super()._sequence_year_range_regex
        )

    @property
    def _sequence_fixed_regex(self):
        return self.journal_id.sequence_override_regex or super()._sequence_fixed_regex

    @property
    def _sequence_year_range_monthly_regex(self):
        return (
            self.journal_id.sequence_override_regex
            or super()._sequence_year_range_monthly_regex
        )

    name = fields.Char(
        string="Number",
        compute="_compute_name",
        inverse="_inverse_name",
        store=True,
        index="trigram",
        copy=False,
        readonly=False,
        tracking=True,
    )
    name_placeholder = fields.Char(compute="_compute_name_placeholder")
    ref = fields.Char(
        string="Reference",
        index="trigram",
        copy=False,
        tracking=True,
    )
    date = fields.Date(
        compute="_compute_date",
        precompute=True,
        store=True,
        index=True,
        copy=False,
        readonly=False,
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        copy=False,
        readonly=True,
        required=True,
        tracking=True,
    )
    move_type = fields.Selection(
        selection=[
            ("entry", "Journal Entry"),
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Credit Note"),
            ("in_invoice", "Vendor Bill"),
            ("in_refund", "Vendor Credit Note"),
            ("out_receipt", "Sales Receipt"),
            ("in_receipt", "Purchase Receipt"),
        ],
        string="Type",
        default="entry",
        change_default=True,
        index=True,
        readonly=True,
        required=True,
        tracking=True,
    )
    is_storno = fields.Boolean(compute="_compute_is_storno")
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        inverse="_inverse_journal_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="journal_id_domain",
        check_company=True,
    )
    journal_group_id = fields.Many2one(
        comodel_name="account.journal.group",
        string="Ledger",
        search="_search_journal_group_id",
        store=False,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        inverse="_inverse_company_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
    )
    line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="move_id",
        string="Journal Items",
        copy=True,
    )

    exchange_diff_partial_ids = fields.One2many(
        comodel_name="account.partial.reconcile",
        inverse_name="exchange_move_id",
        string="Related reconciliation",
    )

    origin_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment",
        compute="_compute_origin_payment_id",
        search="_search_origin_payment_id",
        compute_sudo=True,
    )
    matched_payment_ids = fields.Many2many(
        comodel_name="account.payment",
        relation="account_move__account_payment",
        column1="invoice_id",
        column2="payment_id",
        string="Matched Payments",
        copy=False,
    )
    reconciled_payment_ids = fields.Many2many(
        comodel_name="account.payment",
        string="Reconciled Payments",
        compute="_compute_reconciled_payment_ids",
        search="_search_reconciled_payment_ids",
        help="Payments that have been reconciled with this invoice.",
    )
    payment_count = fields.Count(
        count_of="reconciled_payment_ids",
        compute_sudo=True,
    )

    statement_line_id = fields.Many2one(
        comodel_name="account.bank.statement.line",
        index="btree_not_null",
        copy=False,
        check_company=True,
    )
    statement_id = fields.Many2one(related="statement_line_id.statement_id")

    adjusting_entry_origin_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="adjusting_entries__account_move",
        column1="move_id",
        column2="adjusting_entry_move_id",
        string="Adjusting Entry Origin Moves",
    )
    adjusting_entry_origin_label = fields.Char(
        compute="_compute_adjusting_entry_origin_label"
    )
    adjusting_entry_origin_moves_count = fields.Count(
        count_of="adjusting_entry_origin_move_ids"
    )
    adjusting_entries_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="adjusting_entries__account_move",
        column1="adjusting_entry_move_id",
        column2="move_id",
        string="Created Adjusting Entries",
    )
    adjusting_entries_count = fields.Count(count_of="adjusting_entries_move_ids")

    tax_cash_basis_rec_id = fields.Many2one(
        comodel_name="account.partial.reconcile",
        string="Tax Cash Basis Entry of",
        index="btree_not_null",
    )
    tax_cash_basis_origin_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Cash Basis Origin",
        index="btree_not_null",
        readonly=True,
        help="The journal entry from which this tax cash basis journal entry has been created.",
    )
    tax_cash_basis_created_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="tax_cash_basis_origin_move_id",
        string="Cash Basis Entries",
        help="The cash basis entries created from the taxes on this entry, when reconciling its lines.",
    )

    always_tax_exigible = fields.Boolean(
        compute="_compute_always_tax_exigible",
        store=True,
        readonly=False,
    )

    auto_post = fields.Selection(
        selection=[
            ("no", "No"),
            ("at_date", "At Date"),
            ("recurring", "Recurring"),
        ],
        string="Auto-post",
        default="no",
        copy=False,
        required=True,
        help="Specify whether this entry is posted automatically on its accounting date, and any similar recurring invoices.",
    )
    # The cadence is `mixin.recurrence.rule`'s. `auto_post` used to answer three
    # questions at once -- whether the entry posts itself, whether it repeats,
    # and how often -- with `monthly`, `quarterly` and `yearly` standing in for
    # intervals of 1, 3 and 12 months that `_apply_delta_recurring_entries`
    # then decoded from a table of its own.
    repeat_unit = fields.Selection(
        selection=time_unit_selection("month", "year"),
        default="month",
    )
    repeat_until = fields.Date(
        string="Auto-post until",
        compute="_compute_repeat_until",
        store=True,
        copy=False,
        readonly=False,
        help="This recurring move will be posted up to and including this date.",
    )
    auto_post_origin_id = fields.Many2one(
        comodel_name="account.move",
        string="First recurring entry",
        index="btree_not_null",
        copy=False,
        readonly=True,
    )
    hide_post_button = fields.Boolean(
        compute="_compute_hide_post_button",
        readonly=True,
    )
    checked = fields.Boolean(
        string="Reviewed",
        compute="_compute_checked",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
    )
    posted_before = fields.Boolean(copy=False)
    suitable_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        compute="_compute_suitable_journal_ids",
    )
    journal_id_domain = fields.Binary(
        compute="_compute_journal_id_domain",
        exportable=False,
        help="Dynamic domain limiting journal selection to the journals suitable for "
        "this move type that the user is allowed to access.",
    )
    highest_name = fields.Char(compute="_compute_highest_name")
    made_sequence_gap = fields.Boolean()
    show_name_warning = fields.Boolean(store=False)
    type_name = fields.Char(compute="_compute_type_name")
    country_code = fields.Char(
        related="company_id.account_fiscal_country_id.code",
        depends=["company_id"],
        readonly=True,
    )
    account_fiscal_country_group_codes = fields.Json(
        related="company_id.account_fiscal_country_group_codes"
    )
    company_price_include = fields.Selection(
        related="company_id.account_price_include",
        readonly=True,
    )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Attachments",
        domain=[("res_model", "=", "account.move")],
    )
    audit_trail_message_ids = fields.One2many(
        comodel_name="mail.message",
        inverse_name="res_id",
        string="Audit Trail Messages",
        domain=[
            ("model", "=", "account.move"),
            ("message_type", "=", "notification"),
        ],
    )
    no_followup = fields.Boolean(
        string="No Follow-Up",
        compute="_compute_no_followup",
        inverse="_inverse_no_followup",
        readonly=False,
        help="Exclude this journal entry from follow-up reports.",
    )

    restrict_mode_hash_table = fields.Boolean(
        related="journal_id.restrict_mode_hash_table"
    )
    secure_sequence_number = fields.Integer(
        string="Inalterability No Gap Sequence #",
        index=True,
        copy=False,
        readonly=True,
    )
    inalterable_hash = fields.Char(
        string="Inalterability Hash",
        index="btree_not_null",
        copy=False,
        readonly=True,
    )
    secured = fields.Boolean(
        compute="_compute_secured",
        search="_search_secured",
        help="The entry is secured with an inalterable hash.",
    )

    invoice_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="move_id",
        string="Invoice lines",
        copy=False,
        domain=[
            (
                "display_type",
                "in",
                ("product", *NON_ACCOUNTABLE_DISPLAY_TYPES),
            )
        ],
    )

    invoice_date = fields.Date(
        string="Invoice/Bill Date",
        index=True,
        copy=False,
    )
    invoice_date_due = fields.Date(
        string="Due Date",
        compute="_compute_invoice_date_due",
        store=True,
        index=True,
        copy=False,
        readonly=False,
    )
    delivery_date = fields.Date(
        compute="_compute_delivery_date",
        inverse="_inverse_delivery_date",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
    )
    show_delivery_date = fields.Boolean(compute="_compute_show_delivery_date")
    taxable_supply_date = fields.Date(
        compute="_compute_taxable_supply_date",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
    )
    show_taxable_supply_date = fields.Boolean(
        compute="_compute_show_taxable_supply_date"
    )
    taxable_supply_date_placeholder = fields.Char(
        compute="_compute_taxable_supply_date_placeholder"
    )
    invoice_payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Payment Terms",
        compute="_compute_invoice_payment_term_id",
        inverse="_inverse_invoice_payment_term_id",
        precompute=True,
        store=True,
        readonly=False,
        check_company=True,
    )
    needed_terms = fields.Binary(
        compute="_compute_payment_terms",
        exportable=False,
    )
    needed_terms_dirty = fields.Boolean(compute="_compute_payment_terms")
    tax_calculation_rounding_method = fields.Selection(
        related="company_id.tax_calculation_rounding_method",
        string="Tax calculation rounding method",
        readonly=True,
    )
    show_journal = fields.Boolean(compute="_compute_show_journal")
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        inverse="_inverse_partner_id",
        change_default=True,
        index=True,
        readonly=False,
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Commercial Entity",
        compute="_compute_commercial_partner_id",
        store=True,
        readonly=True,
        ondelete="restrict",
        check_company=True,
    )
    partner_shipping_id = fields.Many2one(
        comodel_name="res.partner",
        string="Delivery Address",
        compute="_compute_partner_shipping_id",
        precompute=True,
        store=True,
        readonly=False,
        check_company=True,
        help="The delivery address will be used in the computation of the fiscal position.",
    )
    allow_external_delivery_address = fields.Boolean(
        default=False,
        tracking=True,
        help="Allow selecting a delivery address that does not belong to the "
        "customer's company (e.g. drop-shipping). When disabled, the delivery "
        "address is limited to the customer's own contacts.",
    )
    partner_shipping_domain = fields.Binary(
        compute="_compute_partner_shipping_domain",
        help="Dynamic domain limiting delivery address selection.",
    )
    partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Recipient Bank",
        compute="_compute_partner_bank_id",
        store=True,
        index="btree_not_null",
        readonly=False,
        ondelete="restrict",
        check_company=True,
        tracking=True,
        help="Bank Account Number to which the invoice will be paid. "
        "A Company bank account if this is a Customer Invoice or Vendor Credit Note, "
        "otherwise a Partner bank account number.",
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        compute="_compute_fiscal_position_id",
        precompute=True,
        store=True,
        readonly=False,
        ondelete="restrict",
        check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular "
        "customers or sales orders/invoices. The default value comes from the customer.",
    )

    payment_reference = fields.Char(
        compute="_compute_payment_reference",
        inverse="_inverse_payment_reference",
        store=True,
        index="trigram",
        copy=False,
        readonly=False,
        tracking=True,
        help="The payment reference to set on journal items.",
    )
    display_qr_code = fields.Boolean(
        string="Display QR-code",
        compute="_compute_display_qr_code",
    )
    display_link_qr_code = fields.Boolean(
        string="Display Link QR-code",
        compute="_compute_display_link_qr_code",
    )
    qr_code_method = fields.Selection(
        selection=lambda self: self.env[
            "res.partner.bank"
        ].get_available_qr_methods_in_sequence(),
        string="Payment QR-code",
        copy=False,
        help="Type of QR-code to be generated for the payment of this invoice, "
        "when printing it. If left blank, the first available and usable method "
        "will be used.",
    )

    invoice_outstanding_credits_debits_widget = fields.Binary(
        compute="_compute_invoice_outstanding_credits_debits_widget",
        exportable=False,
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    invoice_has_outstanding = fields.Boolean(
        compute="_compute_invoice_has_outstanding",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    invoice_payments_widget = fields.Binary(
        compute="_compute_invoice_payments_widget",
        exportable=False,
        groups="account.group_account_invoice,account.group_account_readonly",
    )

    preferred_payment_channel_id = fields.Many2one(
        comodel_name="account.payment.channel",
        string="Preferred Payment Method Line",
        compute="_compute_preferred_payment_channel_id",
        store=True,
        readonly=False,
    )

    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        inverse="_inverse_currency_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        tracking=True,
    )
    expected_currency_rate = fields.Float(
        digits=0,
        compute="_compute_expected_currency_rate",
    )
    invoice_currency_rate = fields.Float(
        string="Currency Rate",
        digits=0,
        compute="_compute_invoice_currency_rate",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="Currency rate from company currency to document currency.",
    )

    direction_sign = fields.Integer(
        compute="_compute_direction_sign",
        help="Multiplicator depending on the document type, to convert a price into a balance",
    )
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        compute="_compute_amounts",
        store=True,
        readonly=True,
        tracking=True,
    )
    amount_tax = fields.Monetary(
        string="Tax",
        compute="_compute_amounts",
        store=True,
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        inverse="_inverse_amount_total",
        store=True,
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string="Amount Due",
        compute="_compute_amounts",
        store=True,
    )
    amount_untaxed_signed = fields.Monetary(
        string="Untaxed Amount Signed",
        currency_field="company_currency_id",
        compute="_compute_amounts",
        store=True,
        readonly=True,
    )
    amount_untaxed_in_currency_signed = fields.Monetary(
        string="Untaxed Amount Signed Currency",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
        readonly=True,
    )
    amount_tax_signed = fields.Monetary(
        string="Tax Signed",
        currency_field="company_currency_id",
        compute="_compute_amounts",
        store=True,
        readonly=True,
    )
    amount_total_signed = fields.Monetary(
        string="Total Signed",
        currency_field="company_currency_id",
        compute="_compute_amounts",
        store=True,
        readonly=True,
    )
    amount_total_in_currency_signed = fields.Monetary(
        string="Total in Currency Signed",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
        readonly=True,
    )
    amount_residual_signed = fields.Monetary(
        string="Amount Due Signed",
        currency_field="company_currency_id",
        compute="_compute_amounts",
        store=True,
    )
    tax_totals = fields.Binary(
        string="Invoice Totals",
        compute="_compute_tax_totals",
        inverse="_inverse_tax_totals",
        exportable=False,
        help="Edit Tax amounts if you encounter rounding issues.",
    )
    payment_state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION,
        string="Payment Status",
        compute="_compute_payment_state",
        store=True,
        copy=False,
        readonly=True,
        tracking=True,
    )
    display_state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION
        + [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("sent", "Sent"),
            ("cancel", "Cancelled"),
        ],
        compute="_compute_display_state",
        copy=False,
        value_sql="_state_field_sql",
    )
    amount_total_words = fields.Char(
        string="Amount total in words",
        compute="_compute_amount_total_words",
    )

    reversed_entry_id = fields.Many2one(
        comodel_name="account.move",
        string="Reversal of",
        index="btree_not_null",
        copy=False,
        readonly=True,
        check_company=True,
    )
    reversal_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="reversed_entry_id",
    )

    invoice_vendor_bill_id = fields.Many2one(
        comodel_name="account.move",
        string="Vendor Bill",
        store=False,
        check_company=True,
        help="Auto-complete from a previous bill or refund.",
    )
    invoice_source_email = fields.Char(
        string="Source Email",
        tracking=True,
    )
    invoice_partner_display_name = fields.Char(
        compute="_compute_invoice_partner_display_name",
        store=True,
    )
    is_manually_modified = fields.Boolean()

    quick_edit_mode = fields.Boolean(compute="_compute_quick_edit_mode")
    quick_edit_total_amount = fields.Monetary(
        string="Total (Tax inc.)",
        help="Use this field to encode the total amount of the invoice.\n"
        "Odoo will automatically create one invoice line with default values to match it.",
    )
    quick_encoding_vals = fields.Json(
        compute="_compute_quick_encoding_vals",
        exportable=False,
    )

    narration = fields.Html(
        string="Terms and Conditions",
        compute="_compute_narration",
        store=True,
        readonly=False,
    )
    is_move_sent = fields.Boolean(
        copy=False,
        readonly=True,
        help="It indicates that the invoice/payment has been sent or the PDF has been generated.",
    )
    is_being_sent = fields.Boolean(
        compute="_compute_is_being_sent",
        help="Is the move being sent asynchronously",
    )

    move_sent_values = fields.Selection(
        selection=[
            ("sent", "Sent"),
            ("not_sent", "Not Sent"),
        ],
        string="Sent",
        compute="_compute_move_sent_values",
        search="_search_move_sent_values",
        value_sql="_state_field_sql",
    )
    invoice_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        compute="_compute_invoice_user_id",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
    )
    user_id = fields.Many2one(
        related="invoice_user_id",
        string="User",
    )
    invoice_origin = fields.Char(
        string="Origin",
        copy=False,
        readonly=True,
        tracking=True,
        help="The document(s) that generated the invoice.",
    )
    invoice_incoterm_id = fields.Many2one(
        comodel_name="account.incoterms",
        string="Incoterm",
        compute="_compute_invoice_incoterm_id",
        store=True,
        readonly=False,
        help="International Commercial Terms are a series of predefined commercial "
        "terms used in international transactions.",
    )
    incoterm_location = fields.Char(
        compute="_compute_incoterm_location",
        store=True,
        readonly=False,
    )
    invoice_cash_rounding_id = fields.Many2one(
        comodel_name="account.cash.rounding",
        string="Cash Rounding Method",
        help="Defines the smallest coinage of the currency that can be used to pay by cash.",
    )
    sending_data = fields.Json(copy=False)
    invoice_pdf_report_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="PDF Attachment",
        compute=lambda self: self._compute_linked_attachment_id(
            "invoice_pdf_report_id", "invoice_pdf_report_file"
        ),
        depends=["invoice_pdf_report_file"],
    )
    invoice_pdf_report_file = fields.Binary(
        string="PDF File",
        attachment=True,
        copy=False,
    )
    invoice_incoterm_placeholder = fields.Char(
        compute="_compute_invoice_incoterm_placeholder"
    )

    invoice_filter_type_domain = fields.Char(
        compute="_compute_invoice_filter_type_domain"
    )
    bank_partner_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_bank_partner_id",
        help="Technical field to get the domain on the bank",
    )
    tax_lock_date_message = fields.Char(compute="_compute_tax_lock_date_message")
    display_inactive_currency_warning = fields.Boolean(
        compute="_compute_display_inactive_currency_warning"
    )
    tax_country_id = fields.Many2one(
        comodel_name="res.country",
        compute="_compute_tax_country_id",
    )
    tax_country_code = fields.Char(compute="_compute_tax_country_code")
    has_reconciled_entries = fields.Boolean(compute="_compute_has_reconciled_entries")
    show_reset_to_draft_button = fields.Boolean(
        compute="_compute_show_reset_to_draft_button"
    )
    partner_credit_warning = fields.Text(
        compute="_compute_partner_credit_warning",
        groups="account.group_account_invoice,account.group_account_readonly",
    )
    duplicated_ref_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_duplicated_ref_ids",
    )
    is_draft_duplicated_ref_ids = fields.Boolean(compute="_compute_duplicates")
    is_exact_move_duplicate = fields.Boolean(compute="_compute_duplicates")
    need_cancel_request = fields.Boolean(compute="_compute_need_cancel_request")

    show_update_fpos = fields.Boolean(
        string="Has Fiscal Position Changed",
        store=False,
    )

    payment_term_details = fields.Binary(
        compute="_compute_payment_term_details",
        exportable=False,
    )
    show_payment_term_details = fields.Boolean(compute="_compute_show_details")
    show_discount_details = fields.Boolean(compute="_compute_show_details")

    abnormal_amount_warning = fields.Text(compute="_compute_abnormal_warnings")
    abnormal_date_warning = fields.Text(compute="_compute_abnormal_warnings")
    alerts = fields.Json(compute="_compute_alerts")

    taxes_legal_notes = fields.Html(compute="_compute_taxes_legal_notes")

    next_payment_date = fields.Date(
        compute="_compute_next_payment_date",
        search="_search_next_payment_date",
    )

    show_send_button = fields.Boolean(compute="_compute_show_send_button")
    highlight_send_button = fields.Boolean(compute="_compute_highlight_send_button")
    is_sale_installed = fields.Boolean(compute="_compute_is_sale_installed")

    _checked_idx = models.Index("(journal_id) WHERE (checked IS NOT TRUE)")
    _payment_idx = models.Index("(journal_id, state, payment_state, move_type, date)")
    _unique_name = models.UniqueIndex(
        "(name, journal_id) WHERE (state = 'posted' AND name != '/')",
        "Another entry with the same name already exists.",
    )
    _journal_id_company_id_idx = models.Index("(journal_id, company_id, date)")
    _made_gaps = models.Index(
        "(journal_id, company_id, date, sequence_prefix) WHERE (made_sequence_gap IS TRUE)"
    )
    _duplicate_bills_idx = models.Index(
        "(ref) WHERE (move_type IN ('in_invoice', 'in_refund'))"
    )

    @_debug.perf.timed
    def _auto_init(self):
        _debug.lifecycle("_auto_init", records=self)
        super()._auto_init()
        if not column_exists(
            self.env.cr, "account_move", "preferred_payment_channel_id"
        ):
            create_column(
                self.env.cr, "account_move", "preferred_payment_channel_id", "int4"
            )

    @api.depends("move_type", "partner_id")
    @api.depends_context("uid")
    @_debug.perf.timed
    def _compute_invoice_user_id(self):
        env_user = self.env.user
        default_user = (
            env_user
            if not (env_user._is_superuser() or env_user._is_public())
            else self.env["res.users"]
        )
        for move in self:
            if move.is_invoice(include_receipts=True):
                move.invoice_user_id = (
                    move.invoice_user_id
                    or (
                        move.is_sale_document(include_receipts=True)
                        and (
                            move.partner_id.user_id
                            or move.commercial_partner_id.user_id
                        )
                    )
                    or default_user
                )
            else:
                move.invoice_user_id = False

    @api.depends("sending_data")
    def _compute_is_being_sent(self):
        for move in self:
            move.is_being_sent = bool(move.sending_data)

    @api.depends("is_move_sent")
    def _compute_move_sent_values(self):
        for move in self:
            move.move_sent_values = "sent" if move.is_move_sent else "not_sent"

    @_debug.perf.timed
    def _search_move_sent_values(self, operator, value):
        if operator != "in" or value - {"sent", "not_sent"}:
            return NotImplemented
        return [("is_move_sent", "in", [elem == "sent" for elem in value])]

    def _compute_payment_reference(self):
        for move in self.filtered(
            lambda m: (
                m.state == "posted"
                and m.move_type == "out_invoice"
                and not m.payment_reference
            )
        ):
            move.payment_reference = move._get_invoice_computed_reference()
        self._inverse_payment_reference()

    def _get_accounting_date_source(self):
        self.check_singleton()
        return self.invoice_date or self.date

    @api.depends("invoice_date", "company_id", "move_type", "taxable_supply_date")
    def _compute_date(self):
        for move in self:
            accounting_date = move._get_accounting_date_source()
            if not accounting_date or not move.is_invoice(include_receipts=True):
                if not move.date:
                    move.date = fields.Date.context_today(self)
                continue
            if not move.is_sale_document(include_receipts=True):
                accounting_date = move._get_accounting_date(
                    accounting_date, move._affect_tax_report()
                )
            if accounting_date and accounting_date != move.date:
                move.date = accounting_date
                self.env.add_to_compute(move.line_ids._fields["date"], move.line_ids)
                self.env.add_to_compute(self._fields["name"], move)

    @api.depends("auto_post", "repeat_type")
    def _compute_repeat_until(self):
        # Cleared unless the series both recurs and says it ends, so that
        # `_copy_recurring_entries` can read the date alone as the cut-off
        # rather than having to agree with `repeat_type` about it.
        for record in self:
            if record.auto_post != "recurring" or record.repeat_type != "until":
                record.repeat_until = False

    @api.depends("state", "date", "auto_post")
    def _compute_hide_post_button(self):
        for record in self:
            record.hide_post_button = record.state != "draft" or (
                record.auto_post != "no"
                and record.date
                and record.date > fields.Date.context_today(record)
            )

    @api.depends("journal_id")
    def _compute_company_id(self):
        for move in self:
            if move.journal_id.company_id not in move.company_id.parent_ids:
                move.company_id = (
                    move.journal_id.company_id or self.env.company
                )._get_accessible_branches()[:1]

    @api.depends("payment_ids")
    def _compute_origin_payment_id(self):
        for move in self:
            move.origin_payment_id = move.payment_ids[:1]

    @_debug.perf.timed
    def _search_origin_payment_id(self, operator, value):
        return [("payment_ids", operator, value)]

    @api.depends("move_type", "origin_payment_id", "statement_line_id")
    def _compute_journal_id(self):
        # the default journal is one search per move; the moves of a batch
        # that share a company, a kind and a currency share the answer
        defaults = {}
        for move in self.filtered(
            lambda r: r.journal_id.type not in r._get_valid_journal_types()
        ):
            key = move._get_default_journal_key()
            if key not in defaults:
                defaults[key] = move._search_default_journal()
            move.journal_id = defaults[key]

    def _get_default_journal_key(self):
        currency_id = None
        if self.env.cache.contains(self, self._fields["currency_id"]):
            currency_id = self.currency_id.id or self.env.context.get(
                "default_currency_id"
            )
        return (
            self.statement_line_ids.statement_id.journal_id.id,
            self.company_id.id,
            tuple(self._get_valid_journal_types()),
            currency_id,
        )

    def _get_valid_journal_types(self):
        if self.is_sale_document(include_receipts=True):
            return ["sale"]
        elif self.is_purchase_document(include_receipts=True):
            return ["purchase"]
        elif (
            self.origin_payment_id
            or self.statement_line_id
            or self.env.context.get("is_payment")
            or self.env.context.get("is_statement_line")
        ):
            return ["bank", "cash", "credit"]
        return ["general"]

    @_debug.perf.timed
    def _search_default_journal(self):
        if self.statement_line_ids.statement_id.journal_id:
            return self.statement_line_ids.statement_id.journal_id[:1]

        journal_types = self._get_valid_journal_types()
        company = self.company_id or self.env.company
        domain = [
            *self.env["account.journal"]._check_company_domain(company),
            ("type", "in", journal_types),
        ]

        currency_id = None
        if self.env.cache.contains(self, self._fields["currency_id"]):
            currency_id = self.currency_id.id or self.env.context.get(
                "default_currency_id"
            )
            if currency_id == company.currency_id.id:
                currency_id = None
        memo = DEFAULT_JOURNALS(self.env)
        key = (self.env.uid, self.env.su, Domain(domain), currency_id)
        if key in memo:
            journal = self.env["account.journal"].browse(memo[key])
        else:
            journal = None
            if currency_id:
                currency_domain = domain + [("currency_id", "=", currency_id)]
                journal = self.env["account.journal"].search(currency_domain, limit=1)
            if not journal:
                journal = self.env["account.journal"].search(domain, limit=1)
            memo[key] = journal.id
        _debug.logic(
            "_search_default_journal",
            types=journal_types,
            company=company,
            journal=journal,
        )

        if not journal:
            error_msg = self.env["account.journal"]._prepare_no_journal_error_msg(
                company.display_name, journal_types
            )
            raise UserError(error_msg)

        return journal

    @api.depends("move_type", "company_id")
    def _compute_is_storno(self):
        for move in self:
            is_refund = move.move_type in ("out_refund", "in_refund")
            move.is_storno = is_refund and move.company_id.account_storno

    @api.depends("company_id", "move_type")
    def _compute_suitable_journal_ids(self):
        for (move_type, company), moves in self.grouped(
            lambda m: (m.move_type, m.company_id)
        ).items():
            moves.suitable_journal_ids = self._get_suitable_journal_ids(
                move_type, company
            )

    @api.depends_context("uid")
    @api.depends("suitable_journal_ids")
    def _compute_journal_id_domain(self):
        selectable = self.env["account.journal"]._get_domain_selectable()
        for move in self:
            move.journal_id_domain = [
                ("id", "in", move.suitable_journal_ids.ids),
                *selectable,
            ]

    @api.depends(
        "posted_before", "state", "journal_id", "date", "move_type", "origin_payment_id"
    )
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date or date.min, m.ref or "", m._origin.id))

        for move in self:
            if move.state == "cancel":
                continue

            move_has_name = move.name and move.name != "/"
            if not move.posted_before and not move._sequence_matches_date():
                _debug.logic("_compute_name_sequence_no_longer_matches", move=move)
                move.name = False
                continue
            if move.date and not move_has_name and move.state != "draft":
                move._set_next_sequence()

        self._inverse_name()

    @api.depends(
        "date",
        "journal_id",
        "move_type",
        "name",
        "posted_before",
        "sequence_number",
        "sequence_prefix",
        "state",
    )
    @_debug.perf.timed
    def _compute_name_placeholder(self):
        for move in self:
            if (
                (not move.name or move.name == "/")
                and move.date
                and not move._get_last_sequence()
            ):
                sequence_format_string, sequence_format_values = (
                    move._get_next_sequence_format()
                )
                sequence_format_values["seq"] += 1
                move.name_placeholder = sequence_format_string.format(
                    **sequence_format_values
                )
            else:
                move.name_placeholder = False

    @api.depends("journal_id", "date")
    def _compute_highest_name(self):
        for record in self:
            record.highest_name = record._get_last_sequence()

    @api.depends_context("lang")
    @api.depends("move_type")
    def _compute_type_name(self):
        type_name_mapping = dict(
            self._fields["move_type"]._description_selection(self.env),
            out_invoice=_("Invoice"),
            out_refund=_("Credit Note"),
        )

        for record in self:
            record.type_name = type_name_mapping[record.move_type]

    @api.depends("inalterable_hash")
    def _compute_secured(self):
        for move in self:
            move.secured = bool(move.inalterable_hash)

    @_debug.perf.timed
    def _search_secured(self, operator, value):
        if operator != "in" or set(value) != {True}:
            return NotImplemented
        return [("inalterable_hash", "!=", False)]

    @api.depends("line_ids.account_id.account_type")
    def _compute_always_tax_exigible(self):
        for record in self.with_context(prefetch_fields=False):
            record.always_tax_exigible = (
                not record.is_invoice(True)
                and not record._collect_tax_cash_basis_values()
            )

    @api.depends("partner_id")
    def _compute_commercial_partner_id(self):
        for move in self:
            move.commercial_partner_id = move.partner_id.commercial_partner_id

    @api.depends("partner_id")
    def _compute_partner_shipping_id(self):
        invoices = self.filtered(lambda move: move.is_invoice(include_receipts=True))
        addresses = invoices.partner_id._address_get_multi(["delivery"])
        for move in self:
            if move in invoices and move.partner_id:
                move.partner_shipping_id = addresses[move.partner_id.id]["delivery"]
            else:
                move.partner_shipping_id = False

    @api.depends(
        "commercial_partner_id", "company_id", "allow_external_delivery_address"
    )
    def _compute_partner_shipping_domain(self):
        for move in self:
            company_ids = [False, move.company_id.id] if move.company_id else [False]
            company_term = ("company_id", "in", company_ids)
            if move.allow_external_delivery_address or not move.commercial_partner_id:
                move.partner_shipping_domain = [company_term]
            else:
                move.partner_shipping_domain = [
                    ("id", "child_of", move.commercial_partner_id.id),
                    company_term,
                ]

    @api.depends("partner_id", "partner_shipping_id", "company_id", "move_type")
    @_debug.perf.timed
    def _compute_fiscal_position_id(self):
        for move in self:
            receipt_fiscal_position = {
                "in_receipt": move.company_id.account_purchase_receipt_fiscal_position_id,
            }.get(move.move_type)
            if receipt_fiscal_position:
                move.fiscal_position_id = receipt_fiscal_position
                continue
            delivery_partner = self.env["res.partner"].browse(
                move.partner_shipping_id.id
                or move.partner_id.address_get(["delivery"])["delivery"]
            )
            move.fiscal_position_id = (
                self.env["account.fiscal.position"]
                .with_company(move.company_id)
                ._get_fiscal_position(move.partner_id, delivery=delivery_partner)
            )

    @api.depends("bank_partner_id", "currency_id", "preferred_payment_channel_id")
    @_debug.perf.timed
    def _compute_partner_bank_id(self):
        def _bank_selection_key(bank):
            if bank.currency_id == move.currency_id or not bank.currency_id:
                currency_priority = 0
            else:
                currency_priority = 1
            return (currency_priority, not bank.allow_out_payment)

        for move in self:
            if (
                move.is_inbound()
                and (
                    payment_method := (
                        move.preferred_payment_channel_id
                        or move.bank_partner_id.property_inbound_payment_channel_id
                    )
                )
                and payment_method.journal_id
            ):
                move.partner_bank_id = payment_method.journal_id.bank_account_id
                _debug.logic(
                    "partner_bank_payment_channel",
                    move=move,
                    partner_bank_id=move.partner_bank_id,
                    payment_method=payment_method,
                )
                continue

            move.partner_bank_id = move.bank_partner_id.bank_ids.filtered_domain(
                [
                    *self.env["res.partner.bank"]._check_company_domain(
                        move.company_id
                    ),
                    ("active", "=", True),
                ]
            ).sorted(key=_bank_selection_key)[:1]
            _debug.logic(
                "partner_bank_bank_partner",
                move=move,
                partner_bank_id=move.partner_bank_id,
                bank_partner_id=move.bank_partner_id,
                bank_ids_count=len(move.bank_partner_id.bank_ids),
            )

    @api.depends("partner_id", "move_type", "company_id")
    def _compute_invoice_payment_term_id(self):
        for move in self:
            move = move.with_company(move.company_id)
            if move.is_sale_document(include_receipts=True):
                move.invoice_payment_term_id = (
                    move.partner_id.property_payment_term_id
                    or move.invoice_payment_term_id
                )
            elif move.is_purchase_document(include_receipts=True):
                move.invoice_payment_term_id = (
                    move.partner_id.property_supplier_payment_term_id
                    or move.invoice_payment_term_id
                )
            else:
                move.invoice_payment_term_id = False

    @api.depends("needed_terms")
    @_debug.perf.timed
    def _compute_invoice_date_due(self):
        today = fields.Date.context_today(self)
        for move in self:
            move.invoice_date_due = (
                (
                    move.needed_terms
                    and max(
                        (
                            k["date_maturity"]
                            for k in move.needed_terms
                            if k and k["date_maturity"]
                        ),
                        default=False,
                    )
                )
                or move.invoice_date_due
                or today
            )

    def _compute_delivery_date(self):
        pass

    @api.depends("delivery_date", "move_type")
    def _compute_show_delivery_date(self):
        for move in self:
            move.show_delivery_date = move.delivery_date and move.is_sale_document()

    def _compute_taxable_supply_date(self):
        pass

    def _compute_show_taxable_supply_date(self):
        for move in self:
            move.show_taxable_supply_date = False

    def _compute_taxable_supply_date_placeholder(self):
        for move in self:
            move.taxable_supply_date_placeholder = ""

    @api.depends("journal_id", "statement_line_id")
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
        self.check_singleton()
        if self.is_invoice(include_receipts=True):
            return self.invoice_date or fields.Date.context_today(self)
        return self.date or fields.Date.context_today(self)

    def _get_expected_currency_rate_at(self, date):
        self.check_singleton()
        return self.env["res.currency"]._get_conversion_rate(
            from_currency=self.company_currency_id,
            to_currency=self.currency_id,
            company=self.company_id,
            date=date,
        )

    @api.depends(
        "currency_id",
        "company_currency_id",
        "company_id",
        "invoice_date",
        "date",
        "taxable_supply_date",
    )
    def _compute_expected_currency_rate(self):
        for move in self:
            if move.currency_id:
                move.expected_currency_rate = move._get_expected_currency_rate_at(
                    move._get_invoice_currency_rate_date()
                )
            else:
                move.expected_currency_rate = 1

    # The invoice's own rate inputs, not expected_currency_rate: on an
    # editable compute the dependencies say when a rate set by hand is
    # discarded, and expected_currency_rate also follows `date` and, in
    # l10n_hu_edi, `delivery_date` -- a post that fills the delivery date
    # would reset the rate the user typed.
    @api.depends(
        "currency_id",
        "company_currency_id",
        "company_id",
        "invoice_date",
        "taxable_supply_date",
    )
    def _compute_invoice_currency_rate(self):
        self._update_invoice_currency_rate()

    def _update_invoice_currency_rate(self):
        for move in self:
            move.invoice_currency_rate = move.expected_currency_rate

    @api.depends("move_type")
    def _compute_direction_sign(self):
        for invoice in self:
            if invoice.move_type == "entry" or invoice.is_outbound():
                invoice.direction_sign = 1
            else:
                invoice.direction_sign = -1

    @api.depends(
        "line_ids.balance",
        "line_ids.currency_id",
        "line_ids.amount_currency",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "line_ids.payment_id.state",
        "line_ids.full_reconcile_id",
        "line_ids.display_type",
        "line_ids.tax_repartition_line_id",
        "state",
    )
    @_debug.perf.timed
    def _compute_amounts(self):
        self.line_ids.fetch(
            [
                "debit",
                "balance",
                "amount_currency",
                "amount_residual",
                "amount_residual_currency",
                "display_type",
                "tax_repartition_line_id",
            ]
        )
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            is_invoice = move.is_invoice(True)
            for line in move.line_ids:
                if is_invoice:
                    if line.display_type in ("tax", "non_deductible_tax") or (
                        line.display_type == "rounding" and line.tax_repartition_line_id
                    ):
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in (
                        "product",
                        "rounding",
                        "non_deductible_product",
                        "non_deductible_product_total",
                    ):
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == "payment_term":
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                elif line.debit:
                    total += line.balance
                    total_currency += line.amount_currency

            _debug.logic(
                "amounts_summed",
                move=move,
                is_invoice=is_invoice,
                total_currency=total_currency,
                tax_currency=total_tax_currency,
                residual_currency=total_residual_currency,
            )
            sign = move.direction_sign
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_untaxed_in_currency_signed = -total_untaxed_currency
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = (
                abs(total) if move.move_type == "entry" else -total
            )
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = (
                abs(total_currency) if move.move_type == "entry" else -total_currency
            )

    def _get_payment_state_currency(self):
        return (
            self.currency_id
            or self.company_id.currency_id
            or self.env.company.currency_id
        )

    def _prepare_payment_state_reconciliation_data(self, stored_ids):
        if not stored_ids:
            return {}
        self.env["account.partial.reconcile"].flush_model()
        self.env["account.payment"].flush_model(["is_bank_matched"])

        queries = [
            SQL(
                _SQL_PAYMENT_RECONCILIATION,
                SQL.identifier(source_field),
                SQL.identifier(counterpart_field),
                stored_ids,
            )
            for source_field, counterpart_field in (
                ("debit_move_id", "credit_move_id"),
                ("credit_move_id", "debit_move_id"),
            )
        ]
        payment_data = defaultdict(list)
        for row in self.env.execute_query_dict(SQL(" UNION ALL ").join(queries)):
            payment_data[row["source_move_id"]].append(row)
        _debug.perf.count(
            "payment_reconciliation_rows_fetched",
            rows=self.env.cr.rowcount,
            moves=len(payment_data),
        )
        return payment_data

    def _get_reversed_payment_state(self, invoice, reconciliation_vals):
        reverse_move_types = set()
        for x in reconciliation_vals:
            reverse_move_types.update(x["counterpart_move_types"])

        in_reverse = invoice.move_type in ("in_invoice", "in_receipt") and (
            reverse_move_types in ({"in_refund"}, {"in_refund", "entry"})
        )
        out_reverse = invoice.move_type in (
            "out_invoice",
            "out_receipt",
        ) and (reverse_move_types in ({"out_refund"}, {"out_refund", "entry"}))
        misc_reverse = invoice.move_type in (
            "entry",
            "out_refund",
            "in_refund",
        ) and reverse_move_types == {"entry"}
        return "reversed" if in_reverse or out_reverse or misc_reverse else "paid"

    def _get_invoice_payment_state(self, invoice, reconciliation_vals):
        currency = invoice._get_payment_state_currency()
        if currency.is_zero(invoice.amount_residual):
            if any(x["has_payment"] or x["has_st_line"] for x in reconciliation_vals):
                if all(x["all_payments_matched"] for x in reconciliation_vals):
                    _debug.logic("payment_state_all_matched", move=invoice)
                    return "paid"
                return invoice._get_invoice_in_payment_state()
            _debug.logic(
                "payment_state_reversal_candidate",
                move=invoice,
                partials=len(reconciliation_vals),
            )
            return self._get_reversed_payment_state(invoice, reconciliation_vals)
        if invoice.state == "posted" and invoice.matched_payment_ids.filtered(
            lambda p: not p.move_id and p.state == "in_process"
        ):
            _debug.logic("payment_state_unbooked_in_process", move=invoice)
            return invoice._get_invoice_in_payment_state()
        if reconciliation_vals:
            return "partial"
        if invoice.state == "posted" and invoice.matched_payment_ids.filtered(
            lambda p: not p.move_id and p.state == "paid"
        ):
            _debug.logic("payment_state_unbooked_paid", move=invoice)
            return invoice._get_invoice_in_payment_state()
        return "not_paid"

    @api.depends(
        "amount_residual",
        "move_type",
        "state",
        "company_id",
        "reconciled_payment_ids.state",
        "matched_payment_ids.state",
        "line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_bank_matched",
        "line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_bank_matched",
    )
    @_debug.perf.timed
    def _compute_payment_state(self):
        def _invoice_qualifies(move):
            currency = move._get_payment_state_currency()
            return move.is_invoice(True) and (
                move.state == "posted"
                or (move.state == "draft" and not currency.is_zero(move.amount_total))
            )

        groups = self.grouped(
            lambda move: (
                "legacy"
                if move.payment_state == "invoicing_legacy"
                else "blocked"
                if move.payment_state == "blocked"
                else "invoices"
                if _invoice_qualifies(move)
                else "unpaid"
            )
        )
        groups.get("unpaid", self.browse()).payment_state = "not_paid"
        invoices = groups.get("invoices", self.browse())
        if _debug.logic.enabled:
            _debug.logic(
                "_compute_payment_state_groups",
                group_sizes={k: len(v) for k, v in groups.items()},
            )

        payment_data = self._prepare_payment_state_reconciliation_data(
            list(invoices.ids)
        )
        for invoice in invoices:
            reconciliation_vals = [
                row
                for row in payment_data.get(invoice.id, [])
                if row["source_line_account_type"] in RECEIVABLE_PAYABLE_TYPES
            ]
            invoice.payment_state = self._get_invoice_payment_state(
                invoice, reconciliation_vals
            )
            _debug.logic(
                "_compute_payment_state",
                move=invoice,
                payment_state=invoice.payment_state,
                residual=invoice.amount_residual,
                partials=len(reconciliation_vals),
                state=invoice.state,
            )

    @api.depends("payment_state", "state", "is_move_sent")
    def _compute_display_state(self):
        for move in self:
            if move.state == "posted":
                if move.payment_state in ("partial", "in_payment", "paid", "reversed"):
                    move.display_state = move.payment_state
                elif move.is_move_sent:
                    move.display_state = "sent"
            elif move.state == "draft":
                if move.payment_state in ("partial", "in_payment", "paid"):
                    move.display_state = move.payment_state

            if not move.display_state:
                move.display_state = move.state

    def _state_field_sql(self, field, alias: str, query=None) -> SQL:
        fname = field.name
        _debug.logic("state_field_to_sql", field=fname, alias=alias)
        is_move_sent = self._field_to_sql(alias, "is_move_sent", query)
        if fname == "move_sent_values":
            return SQL("CASE WHEN %s THEN 'sent' ELSE 'not_sent' END", is_move_sent)
        state = self._field_to_sql(alias, "state", query)
        payment_state = self._field_to_sql(alias, "payment_state", query)
        return SQL(
            "CASE "
            "WHEN %(state)s = 'draft' "
            "     AND %(payment_state)s IN ('partial', 'in_payment', 'paid') "
            "    THEN %(payment_state)s "
            "WHEN %(state)s = 'draft' THEN 'draft' "
            "WHEN %(state)s = 'posted' "
            "     AND %(payment_state)s IN ('partial', 'in_payment', 'paid', 'reversed') "
            "    THEN %(payment_state)s "
            "WHEN %(state)s = 'posted' AND %(is_move_sent)s THEN 'sent' "
            "WHEN %(state)s = 'posted' THEN 'posted' "
            "ELSE %(state)s "
            "END",
            state=state,
            payment_state=payment_state,
            is_move_sent=is_move_sent,
        )

    @api.depends_context("lang")
    @api.depends("adjusting_entry_origin_move_ids")
    def _compute_adjusting_entry_origin_label(self):
        for move in self:
            if len(move.adjusting_entry_origin_move_ids) == 1:
                move.adjusting_entry_origin_label = dict(
                    self._fields["move_type"].selection
                )[move.adjusting_entry_origin_move_ids.move_type]
            else:
                move.adjusting_entry_origin_label = False

    @_debug.perf.timed
    def _get_payment_term_base_amounts(self, invoice, sign):
        if invoice.id == invoice._origin.id:
            _debug.logic("term_base_from_stored_amounts", move=invoice)
            return {
                "tax_amount_currency": invoice.amount_tax * sign,
                "tax_amount": invoice.amount_tax_signed,
                "untaxed_amount_currency": invoice.amount_untaxed * sign,
                "untaxed_amount": invoice.amount_untaxed_signed,
            }
        AccountTax = self.env["account.tax"]
        amounts = {
            "tax_amount_currency": 0.0,
            "tax_amount": 0.0,
            "untaxed_amount_currency": 0.0,
            "untaxed_amount": 0.0,
        }
        base_lines, _tax_lines = invoice._get_rounded_base_and_tax_lines(
            round_from_tax_lines=False
        )
        AccountTax._add_accounting_data_in_base_lines_tax_details(
            base_lines,
            invoice.company_id,
            include_caba_tags=invoice.always_tax_exigible,
        )
        tax_results = AccountTax._prepare_tax_lines(base_lines, invoice.company_id)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "term_base_recomputed_from_lines",
                move=invoice,
                base_lines=len(base_lines),
                tax_lines=len(tax_results["tax_lines_to_add"]),
            )
        for _base_line, to_update in tax_results["base_lines_to_update"]:
            amounts["untaxed_amount_currency"] -= to_update["amount_currency"]
            amounts["untaxed_amount"] -= to_update["balance"]
        for tax_line_vals in tax_results["tax_lines_to_add"]:
            amounts["tax_amount_currency"] -= tax_line_vals["amount_currency"]
            amounts["tax_amount"] -= tax_line_vals["balance"]
        return amounts

    @_debug.perf.timed
    def _update_needed_terms_from_payment_term(self, invoice, sign):
        invoice_payment_terms = invoice.invoice_payment_term_id._get_terms(
            date_ref=invoice.invoice_date
            or invoice.date
            or fields.Date.context_today(invoice),
            currency=invoice.currency_id,
            company=invoice.company_id,
            cash_rounding=invoice.invoice_cash_rounding_id,
            sign=sign,
            **self._get_payment_term_base_amounts(invoice, sign),
        )
        _debug.pipeline(
            "payment_terms_computed",
            move=invoice,
            term=invoice.invoice_payment_term_id,
            term_lines=len(invoice_payment_terms["line_ids"]),
            discount_date=invoice_payment_terms.get("discount_date"),
        )
        for term_line in invoice_payment_terms["line_ids"]:
            key = frozendict(
                {
                    "move_id": invoice.id,
                    "date_maturity": fields.Date.to_date(term_line.get("date")),
                    "discount_date": invoice_payment_terms.get("discount_date"),
                }
            )
            values = {
                "balance": term_line["company_amount"],
                "amount_currency": term_line["foreign_amount"],
                "discount_date": invoice_payment_terms.get("discount_date"),
                "discount_balance": invoice_payment_terms.get("discount_balance")
                or 0.0,
                "discount_amount_currency": invoice_payment_terms.get(
                    "discount_amount_currency"
                )
                or 0.0,
            }
            if key not in invoice.needed_terms:
                invoice.needed_terms[key] = values
            else:
                invoice.needed_terms[key]["balance"] += values["balance"]
                invoice.needed_terms[key]["amount_currency"] += values[
                    "amount_currency"
                ]

    def _update_needed_terms_from_due_date(self, invoice):
        invoice.needed_terms[
            frozendict(
                {
                    "move_id": invoice.id,
                    "date_maturity": fields.Date.to_date(invoice.invoice_date_due),
                    "discount_date": False,
                }
            )
        ] = {
            "balance": invoice.amount_total_signed,
            "amount_currency": invoice.amount_total_in_currency_signed,
            "discount_date": False,
            "discount_balance": 0.0,
            "discount_amount_currency": 0.0,
        }

    @api.depends(
        "invoice_payment_term_id",
        "invoice_date",
        "currency_id",
        "amount_total_in_currency_signed",
        "invoice_date_due",
    )
    def _compute_payment_terms(self):
        for invoice in self.with_context(bin_size=False):
            invoice.needed_terms = {}
            invoice.needed_terms_dirty = True
            sign = 1 if invoice.is_inbound(include_receipts=True) else -1
            if not (invoice.is_invoice(True) and invoice.invoice_line_ids):
                continue
            if invoice.invoice_payment_term_id:
                self._update_needed_terms_from_payment_term(invoice, sign)
            else:
                self._update_needed_terms_from_due_date(invoice)

    @api.depends("suitable_journal_ids")
    def _compute_show_journal(self):
        for move in self:
            move.show_journal = len(move.suitable_journal_ids) > 1 or (
                move.journal_id and move.journal_id not in move.suitable_journal_ids
            )

    def _get_outstanding_lines(self, key, group_account_ids):
        company_id, partner_id, is_inbound = key
        company = self.env["res.company"].browse(company_id)
        return self.env["account.move.line"].search(
            [
                ("account_id", "in", list(group_account_ids)),
                ("parent_state", "=", "posted"),
                *self.env["account.move.line"]._check_company_domain(company),
                ("partner_id", "=", partner_id),
                ("reconciled", "=", False),
                ("balance", "<" if is_inbound else ">", 0.0),
                "|",
                ("amount_residual", "!=", 0.0),
                ("amount_residual_currency", "!=", 0.0),
            ]
        )

    def _get_outstanding_lines_per_group(self, groups):
        return {
            key: self._get_outstanding_lines(key, group_account_ids)
            for key, group_account_ids in groups.items()
        }

    @_debug.perf.timed
    def _get_outstanding_widget_content(self, move, lines, account_id_set):
        content = []
        for line in lines:
            if line.account_id.id not in account_id_set:
                continue
            if line.currency_id == move.currency_id:
                amount = abs(line.amount_residual_currency)
            else:
                amount = line.company_currency_id._convert(
                    abs(line.amount_residual),
                    move.currency_id,
                    move.company_id,
                    line.date,
                )

            if move.currency_id.is_zero(amount):
                continue

            content.append(
                {
                    "journal_name": line.ref or line.move_id.name,
                    "amount": amount,
                    "currency_id": move.currency_id.id,
                    "id": line.id,
                    "move_id": line.move_id.id,
                    "date": fields.Date.to_string(line.date),
                    "account_payment_id": line.payment_id.id,
                    "move_ref": line.ref or "",
                }
            )
        _debug.logic(
            "outstanding_lines_filtered",
            move=move,
            lines=len(lines),
            kept=len(content),
        )
        return content

    @_debug.perf.timed
    def _compute_invoice_outstanding_credits_debits_widget(self):
        self.invoice_outstanding_credits_debits_widget = False

        candidates = {}
        groups = defaultdict(set)
        for move in self:
            if (
                move.state not in {"draft", "posted"}
                or move.payment_state not in ("not_paid", "partial")
                or not move.is_invoice(include_receipts=True)
            ):
                continue

            pay_term_account_ids = move._get_receivable_payable_lines().account_id.ids
            if not pay_term_account_ids:
                continue

            candidates[move] = set(pay_term_account_ids)
            key = (move.company_id.id, move.commercial_partner_id.id, move.is_inbound())
            groups[key].update(pay_term_account_ids)

        if not candidates:
            return

        lines_per_group = self._get_outstanding_lines_per_group(groups)
        if _debug.logic.enabled:
            _debug.logic(
                "outstanding_widget_lines",
                candidates_count=len(candidates),
                groups_count=len(groups),
                group={k: len(v) for k, v in lines_per_group.items()},
            )

        for move, account_id_set in candidates.items():
            key = (move.company_id.id, move.commercial_partner_id.id, move.is_inbound())
            content = self._get_outstanding_widget_content(
                move, lines_per_group[key], account_id_set
            )
            _debug.logic("outstanding_widget", move=move, content_count=len(content))
            if content:
                move.invoice_outstanding_credits_debits_widget = {
                    "outstanding": True,
                    "content": content,
                    "move_id": move.id,
                    "title": _("Outstanding credits")
                    if move.is_inbound()
                    else _("Outstanding debits"),
                }

    @api.depends("invoice_outstanding_credits_debits_widget")
    def _compute_invoice_has_outstanding(self):
        for move in self:
            move.invoice_has_outstanding = bool(
                move.invoice_outstanding_credits_debits_widget
            )

    @api.depends("partner_id", "company_id", "move_type")
    def _compute_preferred_payment_channel_id(self):
        for move in self:
            partner = move.partner_id.with_company(move.company_id)
            if move.is_sale_document():
                move.preferred_payment_channel_id = (
                    partner.property_inbound_payment_channel_id
                )
            else:
                move.preferred_payment_channel_id = (
                    partner.property_outbound_payment_channel_id
                )

    @api.depends("move_type", "line_ids.amount_residual")
    @_debug.perf.timed
    def _compute_invoice_payments_widget(self):
        for move in self:
            payments_widget_vals = {
                "title": _("Less Payment"),
                "outstanding": False,
                "content": [],
            }

            if move.state in {"draft", "posted"} and move.is_invoice(
                include_receipts=True
            ):
                reconciled_vals = []
                reconciled_partials = move.sudo()._get_all_reconciled_invoice_partials()
                for reconciled_partial in reconciled_partials:
                    counterpart_line = reconciled_partial["aml"]
                    if counterpart_line.move_id.ref:
                        reconciliation_ref = "%s (%s)" % (
                            counterpart_line.move_id.name,
                            counterpart_line.move_id.ref,
                        )
                    else:
                        reconciliation_ref = counterpart_line.move_id.name
                    if (
                        counterpart_line.amount_currency
                        and counterpart_line.currency_id
                        != counterpart_line.company_id.currency_id
                    ):
                        foreign_currency = counterpart_line.currency_id
                    else:
                        foreign_currency = False

                    reconciled_vals.append(
                        {
                            "name": counterpart_line.name,
                            "journal_name": counterpart_line.journal_id.name,
                            "company_name": counterpart_line.journal_id.company_id.name
                            if counterpart_line.journal_id.company_id != move.company_id
                            else False,
                            "amount": reconciled_partial["amount"],
                            "currency_id": move.company_id.currency_id.id
                            if reconciled_partial["is_exchange"]
                            else reconciled_partial["currency"].id,
                            "date": counterpart_line.date,
                            "partial_id": reconciled_partial["partial_id"],
                            "account_payment_id": counterpart_line.payment_id.id,
                            "payment_method_name": counterpart_line.payment_id.payment_channel_id.name,
                            "move_id": counterpart_line.move_id.id,
                            "is_refund": counterpart_line.move_id.move_type
                            in ["in_refund", "out_refund"],
                            "ref": reconciliation_ref,
                            "is_exchange": reconciled_partial["is_exchange"],
                            "amount_company_currency": formatLang(
                                self.env,
                                abs(counterpart_line.balance),
                                currency_obj=counterpart_line.company_id.currency_id,
                            ),
                            "amount_foreign_currency": foreign_currency
                            and formatLang(
                                self.env,
                                abs(counterpart_line.amount_currency),
                                currency_obj=foreign_currency,
                            ),
                        }
                    )
                payments_widget_vals["content"] = reconciled_vals
                _debug.logic(
                    "payments_widget_partials",
                    move=move,
                    partials=len(reconciled_partials),
                )

            if payments_widget_vals["content"]:
                move.invoice_payments_widget = payments_widget_vals
            else:
                move.invoice_payments_widget = False

    def _get_product_base_line_currency_rate(self, product_line):
        if self.is_invoice(include_receipts=True):
            return self.invoice_currency_rate
        return (
            abs(product_line.amount_currency / product_line.balance)
            if product_line.balance
            else 0.0
        )

    @_debug.perf.timed
    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        self.check_singleton()
        is_invoice = self.is_invoice(include_receipts=True)
        sign = self.direction_sign if is_invoice else 1

        kwargs = {
            "price_unit": product_line.price_unit
            if is_invoice
            else product_line.amount_currency,
            "quantity": product_line.quantity if is_invoice else 1.0,
            "discount": product_line.discount if is_invoice else 0.0,
            "rate": self._get_product_base_line_currency_rate(product_line),
            "sign": sign,
            "special_mode": False if is_invoice else "total_excluded",
            "name": product_line.name,
        }

        computation_key = (product_line.extra_tax_data or {}).get("computation_key", "")
        if computation_key.startswith("global_discount"):
            _debug.logic("global_discount_line_detected", move=self, line=product_line)
            kwargs["special_type"] = "global_discount"
        elif computation_key.startswith("down_payment"):
            _debug.logic("down_payment_line_detected", move=self, line=product_line)
            kwargs["special_type"] = "down_payment"

        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            product_line, **kwargs
        )

    def _is_refund(self):
        return self.move_type in ("out_refund", "in_refund")

    @_debug.perf.timed
    def _prepare_special_base_line_for_taxes_computation(self, line, special_type):
        self.check_singleton()
        sign = self.direction_sign
        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            line,
            price_unit=sign * line.amount_currency,
            quantity=1.0,
            sign=sign,
            special_mode="total_excluded",
            special_type=special_type,
            is_refund=self._is_refund(),
            rate=self.invoice_currency_rate,
        )

    @_debug.perf.timed
    def _prepare_epd_base_line_for_taxes_computation(self, epd_line):
        return self._prepare_special_base_line_for_taxes_computation(
            epd_line, "early_payment"
        )

    @_debug.perf.timed
    def _prepare_epd_base_lines_for_taxes_computation_from_product_lines(
        self, product_amls
    ):
        self.check_singleton()
        aggregated_results = self._sync_dynamic_line_needed_values(
            product_amls.mapped("epd_needed")
        )
        sign = self.direction_sign
        rate = self.invoice_currency_rate
        epd_lines = []
        for grouping_key, values in aggregated_results.items():
            all_values = {**grouping_key, **values}
            epd_lines.append(
                self.env["account.tax"]._prepare_base_line_for_taxes_computation(
                    all_values,
                    id=grouping_key,
                    tax_ids=self.env["account.tax"].browse(all_values["tax_ids"][0][2]),
                    price_unit=sign * values["amount_currency"],
                    quantity=1.0,
                    currency_id=self.currency_id,
                    sign=1,
                    special_mode="total_excluded",
                    special_type="early_payment",
                    partner_id=self.commercial_partner_id,
                    account_id=self.env["account.account"].browse(
                        all_values["account_id"]
                    ),
                    is_refund=self._is_refund(),
                    rate=rate,
                )
            )
        _debug.pipeline(
            "epd_base_lines_prepared",
            move=self,
            product_lines=len(product_amls),
            groups=len(aggregated_results),
            epd_lines=len(epd_lines),
        )
        return epd_lines

    @_debug.perf.timed
    def _prepare_cash_rounding_base_line_for_taxes_computation(
        self, cash_rounding_line
    ):
        return self._prepare_special_base_line_for_taxes_computation(
            cash_rounding_line, "cash_rounding"
        )

    @_debug.perf.timed
    def _prepare_tax_line_for_taxes_computation(self, tax_line):
        self.check_singleton()
        return self.env["account.tax"]._prepare_tax_line_for_taxes_computation(
            tax_line,
            sign=self.direction_sign,
        )

    @_debug.perf.timed
    def _prepare_non_deductible_base_line_for_taxes_computation(
        self, non_deductible_line
    ):
        return self._prepare_special_base_line_for_taxes_computation(
            non_deductible_line, "non_deductible"
        )

    @_debug.perf.timed
    def _prepare_non_deductible_base_lines_for_taxes_computation_from_product_lines(
        self, product_amls
    ):
        self.check_singleton()
        non_deductible_product_lines = product_amls.filtered(
            lambda line: (
                line.display_type == "product"
                and float_compare(line.deductible_amount, 100, precision_digits=2) != 0
            )
        )
        _debug.logic(
            "non_deductible_product_lines_found",
            move=self,
            product_lines=len(product_amls),
            non_deductible=len(non_deductible_product_lines),
        )
        if not non_deductible_product_lines:
            return []

        sign = self.direction_sign
        rate = self.invoice_currency_rate

        non_deductible_lines_base_total_currency = 0.0
        non_deductible_lines = []
        for line in non_deductible_product_lines:
            percentage = 1 - line.deductible_amount / 100
            non_deductible_subtotal = line.currency_id.round(
                line.price_subtotal * percentage
            )
            non_deductible_base_currency = (
                line.company_currency_id.round(sign * non_deductible_subtotal / rate)
                if rate
                else 0.0
            )
            non_deductible_lines_base_total_currency += non_deductible_base_currency

            non_deductible_lines += [
                self.env["account.tax"]._prepare_base_line_for_taxes_computation(
                    None,
                    price_unit=-non_deductible_base_currency,
                    quantity=1.0,
                    sign=1,
                    special_mode="total_excluded",
                    special_type="non_deductible",
                    tax_ids=line.tax_ids.filtered(
                        lambda tax: tax.amount_type != "fixed"
                    ),
                    currency_id=self.currency_id,
                )
            ]
        non_deductible_lines += [
            self.env["account.tax"]._prepare_base_line_for_taxes_computation(
                None,
                price_unit=non_deductible_lines_base_total_currency,
                quantity=1.0,
                sign=1,
                special_mode="total_excluded",
                special_type=False,
                currency_id=self.currency_id,
            )
        ]
        _debug.pipeline(
            "non_deductible_base_lines_prepared",
            move=self,
            lines=len(non_deductible_lines),
            base_total_currency=non_deductible_lines_base_total_currency,
        )
        return non_deductible_lines

    @_debug.perf.timed
    def _get_rounded_base_and_tax_lines(
        self, round_from_tax_lines=True, reapply_currency_rate=False
    ):
        self.check_singleton()
        AccountTax = self.env["account.tax"]
        is_invoice = self.is_invoice(include_receipts=True)

        _debug.logic(
            "rounded_lines_source",
            move=self,
            stored=bool(self.id),
            is_invoice=is_invoice,
            round_from_tax_lines=round_from_tax_lines,
            reapply_currency_rate=reapply_currency_rate,
        )
        if self.id or not is_invoice:
            base_amls = self.line_ids.filtered(
                lambda line: line.display_type == "product"
            )
        else:
            base_amls = self.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
            )
        base_lines = [
            self._prepare_product_base_line_for_taxes_computation(line)
            for line in base_amls
        ]

        tax_lines = []
        if self.id:
            epd_amls = self.line_ids.filtered(lambda line: line.display_type == "epd")
            base_lines += [
                self._prepare_epd_base_line_for_taxes_computation(line)
                for line in epd_amls
            ]
            cash_rounding_amls = self.line_ids.filtered(
                lambda line: (
                    line.display_type == "rounding" and not line.tax_repartition_line_id
                )
            )
            base_lines += [
                self._prepare_cash_rounding_base_line_for_taxes_computation(line)
                for line in cash_rounding_amls
            ]
            non_deductible_base_lines = self.line_ids.filtered(
                lambda line: (
                    line.display_type
                    in ("non_deductible_product", "non_deductible_product_total")
                )
            )
            base_lines += [
                self._prepare_non_deductible_base_line_for_taxes_computation(line)
                for line in non_deductible_base_lines
            ]
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            tax_amls = self.line_ids.filtered("tax_repartition_line_id")
            tax_lines = [
                self._prepare_tax_line_for_taxes_computation(tax_line)
                for tax_line in tax_amls
            ]
            if reapply_currency_rate and (rate := self.invoice_currency_rate):
                for tax_line in tax_lines:
                    tax_line["balance"] = self.company_currency_id.round(
                        tax_line["amount_currency"] / rate
                    )
            AccountTax._round_base_lines_tax_details(
                base_lines,
                self.company_id,
                tax_lines=tax_lines if round_from_tax_lines else [],
            )
        else:
            base_lines += (
                self._prepare_epd_base_lines_for_taxes_computation_from_product_lines(
                    base_amls
                )
            )
            base_lines += self._prepare_non_deductible_base_lines_for_taxes_computation_from_product_lines(
                base_amls
            )
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        _debug.pipeline(
            "base_and_tax_lines_rounded",
            move=self,
            base_lines=len(base_lines),
            tax_lines=len(tax_lines),
        )
        return base_lines, tax_lines

    @api.depends_context("lang")
    @api.depends(
        "invoice_line_ids.currency_rate",
        "invoice_line_ids.tax_base_amount",
        "invoice_line_ids.tax_line_id",
        "invoice_line_ids.price_total",
        "invoice_line_ids.price_subtotal",
        "invoice_payment_term_id",
        "invoice_cash_rounding_id",
        "partner_id",
        "currency_id",
        "company_id",
    )
    @_debug.perf.timed
    def _compute_tax_totals(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
                move.tax_totals = self.env["account.tax"]._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=move.currency_id,
                    company=move.company_id,
                    cash_rounding=move.invoice_cash_rounding_id,
                )
                move.tax_totals["display_in_company_currency"] = (
                    move.company_id.display_invoice_tax_company_currency
                    and move.company_currency_id != move.currency_id
                    and move.tax_totals["has_tax_groups"]
                    and move.is_sale_document(include_receipts=True)
                )
            else:
                move.tax_totals = None

    @api.depends(
        "show_payment_term_details",
        "line_ids.display_type",
        "line_ids.date_maturity",
        "line_ids.amount_currency",
    )
    @api.depends_context("lang")
    def _compute_payment_term_details(self):
        for invoice in self:
            invoice.payment_term_details = False
            if invoice.show_payment_term_details:
                sign = 1 if invoice.is_inbound(include_receipts=True) else -1
                payment_term_details = [
                    {
                        "date": format_date(self.env, line.date_maturity),
                        "amount": sign * line.amount_currency,
                    }
                    for line in invoice.line_ids.filtered(
                        lambda l: l.display_type == "payment_term"
                    ).sorted("date_maturity")
                ]
                invoice.payment_term_details = payment_term_details

    @api.depends("move_type", "payment_state", "invoice_payment_term_id")
    @_debug.perf.timed
    def _compute_show_details(self):
        for invoice in self:
            if (
                invoice.move_type in self._early_payment_discount_move_types()
                and invoice.payment_state in ("not_paid", "partial")
            ):
                payment_term_lines = invoice.line_ids.filtered(
                    lambda l: l.display_type == "payment_term"
                )
                invoice.show_discount_details = (
                    invoice.invoice_payment_term_id.early_discount
                )
                invoice.show_payment_term_details = (
                    len(payment_term_lines) > 1 or invoice.show_discount_details
                )
            else:
                invoice.show_discount_details = False
                invoice.show_payment_term_details = False

    def _is_cancel_request_required(self):
        self.check_singleton()
        return False

    @api.depends("country_code")
    def _compute_need_cancel_request(self):
        for move in self:
            move.need_cancel_request = move._is_cancel_request_required()

    @api.depends("partner_id", "invoice_source_email", "partner_id.display_name")
    @api.depends_context("uid")
    def _compute_invoice_partner_display_name(self):
        for move in self:
            vendor_display_name = move.partner_id.display_name
            if not vendor_display_name:
                if move.invoice_source_email:
                    vendor_display_name = _(
                        "@From: %(email)s", email=move.invoice_source_email
                    )
                else:
                    vendor_display_name = _(
                        "#Created by: %s",
                        move.sudo().create_uid.name or self.env.user.name,
                    )
            move.invoice_partner_display_name = vendor_display_name

    @api.depends("move_type")
    def _compute_invoice_filter_type_domain(self):
        for move in self:
            move.invoice_filter_type_domain = self._get_domain_invoice_filter_type(
                move.move_type
            )

    @api.depends("commercial_partner_id", "company_id", "move_type")
    def _compute_bank_partner_id(self):
        for move in self:
            if move.is_inbound():
                move.bank_partner_id = move.company_id.partner_id
            else:
                move.bank_partner_id = move.commercial_partner_id

    @api.depends(
        "date",
        "line_ids.debit",
        "line_ids.credit",
        "line_ids.tax_line_id",
        "line_ids.tax_ids",
        "line_ids.tax_tag_ids",
    )
    def _compute_tax_lock_date_message(self):
        for move in self:
            accounting_date = move.date or fields.Date.context_today(move)
            affects_tax_report = move._affect_tax_report()
            move.tax_lock_date_message = move._get_lock_date_message(
                accounting_date, affects_tax_report
            )

    @api.depends("currency_id", "state")
    def _compute_display_inactive_currency_warning(self):
        for move in self.with_context(active_test=False):
            move.display_inactive_currency_warning = (
                move.state == "draft"
                and move.currency_id
                and not move.currency_id.active
            )

    @api.depends(
        "company_id.account_fiscal_country_id",
        "fiscal_position_id",
        "fiscal_position_id.country_id",
        "fiscal_position_id.foreign_vat",
    )
    def _compute_tax_country_id(self):
        self._update_tax_country_id()

    def _update_tax_country_id(self):
        self.fetch(["fiscal_position_id", "company_id"])
        records = self.with_context(skip_is_manually_modified=True)
        for (fiscal_position, company), record_group in groupby(
            records, key=lambda r: (r.fiscal_position_id, r.company_id)
        ):
            records.browse(
                [record.id for record in record_group]
            ).tax_country_id = fiscal_position._get_tax_country(company)

    @api.depends("tax_country_id")
    def _compute_tax_country_code(self):
        for record in self:
            record.tax_country_code = record.tax_country_id.code

    @api.depends(
        "line_ids.reconciled",
        "line_ids.matched_debit_ids",
        "line_ids.matched_credit_ids",
    )
    def _compute_has_reconciled_entries(self):
        for move in self:
            move.has_reconciled_entries = len(move.line_ids._reconciled_lines()) > 1

    @api.depends("restrict_mode_hash_table", "state", "inalterable_hash")
    def _compute_show_reset_to_draft_button(self):
        for move in self:
            move.show_reset_to_draft_button = (
                not self._is_move_restricted(move)
                and not move.inalterable_hash
                and (
                    move.state == "cancel"
                    or (move.state == "posted" and not move.need_cancel_request)
                )
            )

    def _compute_access_url(self):
        super()._compute_access_url()
        for move in self.filtered(lambda move: move.is_invoice()):
            move.access_url = "/my/invoices/%s" % (move.id)

    @api.depends(
        "move_type",
        "partner_id",
        "partner_id.lang",
        "company_id",
        "company_id.partner_id.lang",
        "company_id.terms_type",
        "company_id.invoice_terms",
    )
    @_debug.perf.timed
    def _compute_narration(self):
        use_invoice_terms = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("account.use_invoice_terms")
        )
        invoice_to_update_terms = self.filtered(
            lambda m: use_invoice_terms and m.is_sale_document(include_receipts=True)
        )
        for move in invoice_to_update_terms:
            lang = move.partner_id.lang or move.company_id.partner_id.lang
            if move.company_id.terms_type != "html":
                narration = (
                    move.company_id.with_context(lang=lang).invoice_terms
                    if not is_html_empty(move.company_id.invoice_terms)
                    else ""
                )
            else:
                baseurl = move.company_id.get_base_url() + "/terms"
                context = {"lang": lang}
                narration = _("Terms & Conditions: %s", baseurl)
                del context
            move.narration = narration or False

    def _get_partner_credit_warning_exclude_amount(self):
        self.check_singleton()
        return 0

    @api.depends(
        "company_id", "partner_id", "tax_totals", "currency_id", "state", "move_type"
    )
    @_debug.perf.timed
    def _compute_partner_credit_warning(self):
        for move in self:
            move = move.with_company(move.company_id)
            move.partner_credit_warning = ""
            show_warning = (
                move.state == "draft"
                and move.move_type == "out_invoice"
                and move.company_id.account_use_credit_limit
            )
            if show_warning:
                total_field = (
                    "total_amount_currency"
                    if move.currency_id == move.company_currency_id
                    else "total_amount"
                )
                current_amount = move.tax_totals[total_field]
                move.partner_credit_warning = self._prepare_credit_warning_message(
                    move,
                    current_amount=current_amount,
                    exclude_amount=move._get_partner_credit_warning_exclude_amount(),
                )

    @_debug.perf.timed
    def _prepare_credit_warning_message(
        self, record, current_amount=0.0, exclude_amount=0.0
    ):
        partner_id = record.partner_id.commercial_partner_id
        credit_to_invoice = partner_id.credit_to_invoice - exclude_amount
        total_credit = partner_id.credit + credit_to_invoice + current_amount
        if _debug.logic.enabled:
            _debug.logic(
                "credit_limit_checked",
                partner=partner_id,
                credit_limit=partner_id.credit_limit,
                total_credit=total_credit,
                credit_to_invoice=credit_to_invoice,
                current_amount=current_amount,
            )
        if not partner_id.credit_limit or total_credit <= partner_id.credit_limit:
            return ""
        msg = _(
            "%(partner_name)s has reached its credit limit of: %(credit_limit)s",
            partner_name=partner_id.name,
            credit_limit=formatLang(
                self.env,
                partner_id.credit_limit,
                currency_obj=record.company_id.currency_id,
            ),
        )
        total_credit_formatted = formatLang(
            self.env, total_credit, currency_obj=record.company_id.currency_id
        )
        if credit_to_invoice > 0 and current_amount > 0:
            return (
                msg
                + "\n"
                + _(
                    "Total amount due (including sales orders and this document): %(total_credit)s",
                    total_credit=total_credit_formatted,
                )
            )
        elif credit_to_invoice > 0:
            return (
                msg
                + "\n"
                + _(
                    "Total amount due (including sales orders): %(total_credit)s",
                    total_credit=total_credit_formatted,
                )
            )
        elif current_amount > 0:
            return (
                msg
                + "\n"
                + _(
                    "Total amount due (including this document): %(total_credit)s",
                    total_credit=total_credit_formatted,
                )
            )
        else:
            return (
                msg
                + "\n"
                + _(
                    "Total amount due: %(total_credit)s",
                    total_credit=total_credit_formatted,
                )
            )

    @api.depends("journal_id.type", "company_id")
    def _compute_quick_edit_mode(self):
        for move in self:
            quick_edit_mode = move.company_id.quick_edit_mode
            if move.journal_id.type == "sale":
                move.quick_edit_mode = quick_edit_mode in (
                    "out_invoices",
                    "out_and_in_invoices",
                )
            elif move.journal_id.type == "purchase":
                move.quick_edit_mode = quick_edit_mode in (
                    "in_invoices",
                    "out_and_in_invoices",
                )
            else:
                move.quick_edit_mode = False

    @api.depends(
        "quick_edit_total_amount", "invoice_line_ids.price_total", "tax_totals"
    )
    def _compute_quick_encoding_vals(self):
        for move in self:
            move.quick_encoding_vals = move._get_quick_edit_suggestions()

    @api.depends(
        "ref", "move_type", "partner_id", "invoice_date", "tax_totals", "currency_id"
    )
    def _compute_duplicated_ref_ids(self):
        move_to_duplicate_move = self._get_duplicate_reference()
        for move in self:
            move.duplicated_ref_ids = move_to_duplicate_move.get(
                move._origin,
                move_to_duplicate_move.get(move, self.browse()),
            )

    def _get_duplicate_reference_move_table(self, moves, used_fields, synthetic_ids):
        if all(move.id for move in moves):
            return SQL("account_move AS move")
        all_values = []
        for move in moves:
            values = {
                field_name: move._fields[field_name].convert_to_write(
                    move[field_name], move
                )
                or None
                for field_name in used_fields
            }
            values["id"] = synthetic_ids[move]
            values["amount_total"] = move.tax_totals.get("total_amount_currency", 0)
            casted_values = SQL(", ").join(
                SQL(
                    "%s::%s",
                    value,
                    SQL.identifier(move._fields[field_name].column_type[0]),
                )
                for field_name, value in values.items()
            )
            all_values.append(SQL("(%s)", casted_values))
        column_names = SQL(", ").join(
            SQL.identifier(field_name) for field_name in used_fields + ("id",)
        )
        return SQL("(VALUES %s) AS move(%s)", SQL(", ").join(all_values), column_names)

    def _get_duplicate_reference_conditions(self, moves):
        to_query = []
        out_moves = moves.filtered(
            lambda m: m.move_type in ("out_invoice", "out_refund")
        )
        if out_moves:
            to_query.append((out_moves, SQL(_SQL_DUPLICATE_OUT_MOVES)))
        in_moves = moves.filtered(lambda m: m.move_type in ("in_invoice", "in_refund"))
        if in_moves:
            to_query.append((in_moves, SQL(_SQL_DUPLICATE_IN_MOVES)))
        return to_query

    def _get_duplicate_reference_rows(
        self, moves, move_table_and_alias, matching_states, synthetic_ids
    ):
        result = []
        for (
            subset_moves,
            move_type_sql_condition,
        ) in self._get_duplicate_reference_conditions(moves):
            result.extend(
                self.env.execute_query(
                    SQL(
                        _SQL_DUPLICATE_MOVES,
                        matching_states=tuple(matching_states),
                        moves=tuple(synthetic_ids[move] for move in subset_moves),
                        move_table_and_alias=move_table_and_alias,
                        move_type_sql_condition=move_type_sql_condition,
                    )
                )
            )
        return result

    @_debug.perf.timed
    def _get_duplicate_reference(self, matching_states=("draft", "posted")):
        moves = self.filtered(
            lambda m: m.is_sale_document() or m.is_purchase_document()
        )

        if not moves:
            return {}

        used_fields = (
            "company_id",
            "partner_id",
            "commercial_partner_id",
            "ref",
            "move_type",
            "invoice_date",
            "state",
            "amount_total",
            "currency_id",
        )

        self.flush_model(used_fields)

        synthetic_id_by_move = {
            move: move._origin.id or -(index + 1) for index, move in enumerate(moves)
        }
        result = self._get_duplicate_reference_rows(
            moves,
            self._get_duplicate_reference_move_table(
                moves, used_fields, synthetic_id_by_move
            ),
            matching_states,
            synthetic_id_by_move,
        )
        move_by_synthetic_id = {
            synthetic_id: move for move, synthetic_id in synthetic_id_by_move.items()
        }
        readable_ids = set(
            self.browse(
                {
                    duplicate_id
                    for _move_id, duplicate_ids in result
                    for duplicate_id in duplicate_ids
                }
            )
            ._filtered_access("read")
            .ids
        )
        if _debug.logic.enabled and result:
            _debug.logic(
                "_get_duplicate_reference",
                states=matching_states,
                duplicates={m: d[:8] for m, d in result},
                readable_count=len(readable_ids),
            )
        return {
            (
                self.browse(move_id) if move_id > 0 else move_by_synthetic_id[move_id]
            ): self.browse(
                duplicate_id
                for duplicate_id in duplicate_ids
                if duplicate_id in readable_ids
            )
            for move_id, duplicate_ids in result
        }

    @api.depends("duplicated_ref_ids")
    @_debug.perf.timed
    def _compute_duplicates(self):
        for move in self:
            move.is_draft_duplicated_ref_ids = any(
                duplicate_move.state == "draft"
                for duplicate_move in move.duplicated_ref_ids
            )
            move.is_exact_move_duplicate = move.is_purchase_document() and any(
                move.ref
                and move.ref == dup.ref
                and move.move_type == dup.move_type
                and move.commercial_partner_id == dup.commercial_partner_id
                and move.invoice_date == dup.invoice_date
                and move.currency_id.compare_amounts(
                    move.amount_total, dup.amount_total
                )
                == 0
                for dup in move.duplicated_ref_ids
            )

    @api.depends("company_id.qr_code", "move_type")
    def _compute_display_qr_code(self):
        for move in self:
            move.display_qr_code = (
                move.move_type
                in ("out_invoice", "out_receipt", "in_invoice", "in_receipt")
                and move.company_id.qr_code
            )

    @api.depends("company_id.link_qr_code", "move_type")
    def _compute_display_link_qr_code(self):
        for move in self:
            move.display_link_qr_code = (
                move.move_type
                in ("out_invoice", "out_receipt", "in_invoice", "in_receipt")
                and move.company_id.link_qr_code
            )

    @api.depends("amount_total", "currency_id")
    def _compute_amount_total_words(self):
        for move in self:
            move.amount_total_words = move.currency_id.amount_to_text(
                move.amount_total
            ).replace(",", "")

    @api.depends("company_id", "move_type")
    def _compute_invoice_incoterm_id(self):
        for move in self:
            if move.move_type.startswith("out_"):
                move.invoice_incoterm_id = move.company_id.incoterm_id

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "in", self.ids),
                ("res_field", "=", binary_field),
            ],
            order="id",
        )
        move_vals = {att.res_id: att for att in attachments}
        for move in self:
            move[attachment_field] = move_vals.get(move._origin.id, False)

    def _compute_incoterm_location(self):
        pass

    @api.depends("company_id.incoterm_id")
    def _compute_invoice_incoterm_placeholder(self):
        for move in self:
            move.invoice_incoterm_placeholder = (
                move.company_id.incoterm_id.display_name
                if move.company_id.incoterm_id
                else _("Define a default in the settings")
            )

    def _is_abnormal_detection_enabled(self):
        return not self.env.context.get("disable_abnormal_invoice_detection")

    def _is_abnormal_confirmation_requested(self):
        return not self.env.context.get("disable_abnormal_invoice_detection", True)

    def _get_abnormal_invoice_stats(self, draft_invoices, today):
        draft_invoices.flush_recordset(
            [
                "invoice_date",
                "date",
                "amount_total",
                "partner_id",
                "move_type",
                "company_id",
                "currency_id",
            ]
        )
        self.env.cr.execute(
            _SQL_ABNORMAL_INVOICE_STATS,
            {
                "today": today,
                "move_ids": draft_invoices.ids,
            },
        )
        return {invoice: vals for invoice, *vals in self.env.cr.fetchall()}

    def _get_abnormal_date_warning(self, move, invoice_date, stats):
        last_invoice_date, date_diff_mean, date_diff_deviation = stats
        if date_diff_mean > 25:
            date_diff_deviation += 1
        wiggle_room_date = 2 * date_diff_deviation
        return (
            not move.partner_id.ignore_abnormal_invoice_date
            and (invoice_date - last_invoice_date).days
            < int(date_diff_mean - wiggle_room_date)
        ) and _(
            "The billing frequency for %(partner_name)s appears unusual. Based on your historical data, "
            "the expected next invoice date is not before %(expected_date)s (every %(mean)s (± %(wiggle)s) days).\n"
            "Please verify if this date is accurate.",
            partner_name=move.partner_id.display_name,
            expected_date=format_date(
                self.env,
                fields.Date.add(
                    last_invoice_date, days=int(date_diff_mean - wiggle_room_date)
                ),
            ),
            mean=int(date_diff_mean),
            wiggle=int(wiggle_room_date),
        )

    def _get_abnormal_amount_warning(self, move, amount_mean, amount_deviation):
        wiggle_room_amount = 2 * amount_deviation
        return (
            not move.partner_id.ignore_abnormal_invoice_amount
            and not (
                amount_mean - wiggle_room_amount
                <= move.amount_total
                <= amount_mean + wiggle_room_amount
            )
        ) and _(
            "The amount for %(partner_name)s appears unusual. Based on your historical data, the expected amount is %(mean)s (± %(wiggle)s).\n"
            "Please verify if this amount is accurate.",
            partner_name=move.partner_id.display_name,
            mean=move.currency_id.format(amount_mean),
            wiggle=move.currency_id.format(wiggle_room_amount),
        )

    @api.depends(
        "partner_id",
        "invoice_date",
        "date",
        "amount_total",
        "currency_id",
        "state",
        "move_type",
        "partner_id.ignore_abnormal_invoice_date",
        "partner_id.ignore_abnormal_invoice_amount",
    )
    @api.depends_context("lang")
    @_debug.perf.timed
    def _compute_abnormal_warnings(self):
        if not self._is_abnormal_detection_enabled():
            draft_invoices = self.browse()
        else:
            draft_invoices = self.filtered(
                lambda m: (
                    m.id
                    and m.is_purchase_document()
                    and m.state == "draft"
                    and m.amount_total
                    and not (
                        m.partner_id.ignore_abnormal_invoice_date
                        and m.partner_id.ignore_abnormal_invoice_amount
                    )
                )
            )
        other_moves = self - draft_invoices
        other_moves.abnormal_amount_warning = False
        other_moves.abnormal_date_warning = False
        if not draft_invoices:
            return
        today = fields.Date.context_today(self)
        result = self._get_abnormal_invoice_stats(draft_invoices, today)
        for move in draft_invoices:
            invoice_date = move._get_accounting_date_source() or today
            (
                last_invoice_date,
                date_diff_mean,
                date_diff_deviation,
                amount_mean,
                amount_deviation,
            ) = result.get(
                move._origin.id, (invoice_date, 0, 10000000000, 0, 10000000000)
            )
            move.abnormal_date_warning = self._get_abnormal_date_warning(
                move,
                invoice_date,
                (last_invoice_date, date_diff_mean, date_diff_deviation),
            )
            move.abnormal_amount_warning = self._get_abnormal_amount_warning(
                move, amount_mean, amount_deviation
            )
            _debug.logic(
                "abnormal",
                move=move,
                date=bool(move.abnormal_date_warning),
                amount=bool(move.abnormal_amount_warning),
                last=last_invoice_date,
                mean_days=date_diff_mean,
                date_diff_deviation=date_diff_deviation,
                mean_amount=amount_mean,
                amount_deviation=amount_deviation,
                total=move.amount_total,
            )

    @api.depends(
        "state",
        "date",
        "invoice_line_ids",
        "invoice_line_ids.price_total",
        "tax_lock_date_message",
        "auto_post",
        "repeat_until",
        "repeat_interval",
        "repeat_unit",
        "is_being_sent",
        "partner_credit_warning",
        "abnormal_amount_warning",
        "abnormal_date_warning",
    )
    @api.depends_context("uid")
    def _compute_alerts(self):
        for move in self:
            move.alerts = move._get_alerts()

    @api.depends("line_ids.tax_ids")
    def _compute_taxes_legal_notes(self):
        for move in self:
            move.taxes_legal_notes = "".join(
                tax.invoice_legal_notes
                for tax in move.line_ids.tax_ids
                if not is_html_empty(tax.invoice_legal_notes)
            )

    @api.depends("line_ids.payment_date", "line_ids.reconciled")
    def _compute_next_payment_date(self):
        for move in self:
            move.next_payment_date = min(
                [
                    line.payment_date
                    for line in move.line_ids.filtered(
                        lambda l: l.payment_date and not l.reconciled
                    )
                ],
                default=False,
            )

    @api.depends("move_type", "state")
    def _compute_show_send_button(self):
        for move in self:
            move.show_send_button = move.is_sale_document() and move.state == "posted"

    @api.depends("is_being_sent", "invoice_pdf_report_id")
    def _compute_highlight_send_button(self):
        for move in self:
            move.highlight_send_button = (
                not move.is_being_sent and not move.invoice_pdf_report_id
            )

    def _compute_is_sale_installed(self):
        self.is_sale_installed = (
            "sale" in self.env["ir.module.module"]._get_installed_module_ids()
        )

    @api.depends(
        "line_ids.matched_debit_ids",
        "line_ids.matched_credit_ids",
        "matched_payment_ids",
        "matched_payment_ids.state",
    )
    @_debug.perf.timed
    def _compute_reconciled_payment_ids(self):
        self.env["account.payment"].flush_model(fnames=["move_id"])
        self.flush_model(fnames=["move_type"])
        self.env["account.move.line"].flush_model(fnames=["move_id", "account_id"])
        self.env["account.partial.reconcile"].flush_model(
            fnames=["debit_move_id", "credit_move_id"]
        )
        self.env["account.account"].flush_model(fnames=["account_type"])

        invoice_payment_links = (
            dict(
                self.env.execute_query(
                    SQL(_SQL_PAYMENTS_PER_INVOICE, invoice_ids=list(self.ids))
                )
            )
            if self.ids
            else {}
        )
        readable_payment_ids = set(
            self.env["account.payment"]
            .browse(
                {
                    payment_id
                    for payment_ids in invoice_payment_links.values()
                    for payment_id in payment_ids
                }
            )
            ._filtered_access("read")
            .ids
        )
        _debug.pipeline(
            "reconciled_payments_fetched",
            moves=self,
            linked_invoices=len(invoice_payment_links),
            readable_payments=len(readable_payment_ids),
        )
        for move in self:
            move.reconciled_payment_ids = (
                self.env["account.payment"].browse(
                    payment_id
                    for payment_id in invoice_payment_links.get(move.id, ())
                    if payment_id in readable_payment_ids
                )
                | move.matched_payment_ids
            )

    @_debug.perf.timed
    def _search_next_payment_date(self, operator, value):
        if operator not in ("in", "<", "<="):
            return NotImplemented
        return [
            (
                "line_ids",
                "any",
                [("reconciled", "=", False), ("payment_date", operator, value)],
            )
        ]

    @api.depends("state", "journal_id.type")
    def _compute_checked(self):
        for move in self:
            move.checked = move.state == "posted" and (
                move.journal_id.type == "general" or move._is_user_able_to_review()
            )

    @api.depends("line_ids.no_followup")
    def _compute_no_followup(self):
        for move in self:
            if move.is_invoice():
                lines = move._get_receivable_payable_lines()
                move.no_followup = all(lines.mapped("no_followup")) if lines else True
            else:
                move.no_followup = True

    def _inverse_no_followup(self):
        for move in self:
            if move.is_invoice():
                move._get_receivable_payable_lines().no_followup = move.no_followup

    @_debug.perf.timed
    def _get_alerts(self):
        self.check_singleton()
        alerts = {}
        has_account_group = self.env.user.has_groups(
            "account.group_account_readonly,account.group_account_invoice"
        )

        if self.state == "draft":
            if has_account_group and self.tax_lock_date_message:
                alerts["account_tax_lock_date"] = {
                    "level": "warning",
                    "message": self.tax_lock_date_message,
                }
            if self.auto_post == "at_date":
                alerts["account_auto_post_at_date"] = {
                    "level": "info",
                    "message": _(
                        "This move is configured to be posted automatically at the accounting date: %s.",
                        self.date,
                    ),
                }
            if self.auto_post == "recurring":
                unit_labels = dict(
                    self._fields["repeat_unit"]._description_selection(self.env)
                )
                message = _(
                    "Recurring auto-posting enabled, every %(interval)s"
                    " %(unit)s. Next accounting date: %(move_date)s.",
                    interval=self.repeat_interval,
                    unit=unit_labels[self.repeat_unit].lower(),
                    move_date=self.date,
                )
                if self.repeat_until:
                    message += " "
                    message += _(
                        "The recurrence will end on %s (included).",
                        self.repeat_until,
                    )
                alerts["account_auto_post_on_period"] = {
                    "level": "info",
                    "message": message,
                }
            if (
                self.is_purchase_document(include_receipts=True)
                and (
                    zero_lines := self.invoice_line_ids.filtered(
                        lambda line: line._is_empty_line()
                    )
                )
                and len(zero_lines) >= 2
            ):
                alerts["account_remove_empty_lines"] = {
                    "level": "info",
                    "message": _("We've noticed some empty lines on your invoice."),
                    "action_text": _("Remove empty lines"),
                    "action_call": ("account.move.line", "unlink", zero_lines.ids),
                }

        if self.is_being_sent:
            alerts["account_is_being_sent"] = {
                "level": "info",
                "message": _("This invoice is being sent in the background."),
            }
        if has_account_group and self.partner_credit_warning:
            alerts["account_partner_credit_warning"] = {
                "level": "warning",
                "message": self.partner_credit_warning,
            }
        if self.abnormal_amount_warning:
            alerts["account_abnormal_amount_warning"] = {
                "level": "warning",
                "message": self.abnormal_amount_warning,
            }
        if self.abnormal_date_warning:
            alerts["account_abnormal_date_warning"] = {
                "level": "warning",
                "message": self.abnormal_date_warning,
            }

        if _debug.logic.enabled:
            _debug.logic(
                "alerts_raised",
                move=self,
                state=self.state,
                alerts=",".join(sorted(alerts)),
            )
        return alerts

    @_debug.perf.timed
    def _search_journal_group_id(self, operator, value):
        positive_operator = {
            "!=": "=",
            "not in": "in",
            "not like": "like",
            "not ilike": "ilike",
            "not =like": "=like",
            "not =ilike": "=ilike",
        }.get(operator)
        search_operator = positive_operator or operator
        field = "name" if "like" in search_operator else "id"
        journal_groups = self.env["account.journal.group"].search(
            [(field, search_operator, value)]
        )
        membership = Domain.OR(
            [
                Domain("journal_id", "not in", group.excluded_journal_ids.ids)
                & Domain("journal_id.company_id", "=?", group.company_id.id)
                for group in journal_groups
            ]
        )
        return ~membership if positive_operator else membership

    @_debug.perf.timed
    def _search_reconciled_payment_ids(self, operator, value):
        if operator not in ("in", "="):
            return NotImplemented
        invoice_ids = (
            self.env["account.payment"].browse(value).reconciled_invoice_ids.ids
        )
        return Domain.OR(
            [
                Domain("id", "in", invoice_ids),
                Domain("matched_payment_ids", "in", value),
            ]
        )

    def _inverse_delivery_date(self):
        pass

    @_debug.perf.timed
    def _inverse_tax_totals(self):
        with self._disable_recursion("skip_invoice_sync") as disabled:
            if disabled:
                _debug.logic(
                    "tax_totals_inverse_skipped", moves=self, reason="recursion"
                )
                return
        with self._sync_dynamic_line(
            existing_key_fname="term_key",
            needed_vals_fname="needed_terms",
            needed_dirty_fname="needed_terms_dirty",
            line_type="payment_term",
            container={"records": self},
        ):
            for move in self:
                if not move.is_invoice(include_receipts=True):
                    continue
                invoice_totals = move.tax_totals

                for subtotal in invoice_totals["subtotals"]:
                    for tax_group in subtotal["tax_groups"]:
                        tax_lines = move.line_ids.filtered(
                            lambda line, tax_group=tax_group: (
                                line.tax_group_id.id == tax_group["id"]
                            )
                        )

                        if tax_lines:
                            first_tax_line = tax_lines[0]
                            tax_group_old_amount = sum(
                                tax_lines.mapped("amount_currency")
                            )
                            sign = -1 if move.is_inbound() else 1
                            delta_amount = (
                                tax_group_old_amount
                                - tax_group.get(
                                    "non_deductible_tax_amount_currency", 0.0
                                )
                            ) * sign - tax_group["tax_amount_currency"]

                            if not move.currency_id.is_zero(delta_amount):
                                _debug.logic(
                                    "tax_group_amount_adjusted",
                                    move=move,
                                    line=first_tax_line,
                                    tax_group=tax_group["id"],
                                    delta_amount=delta_amount,
                                )
                                first_tax_line.amount_currency -= delta_amount * sign
            self.env.add_to_compute(self._fields["amount_total"], self)

    @_debug.perf.timed
    def _inverse_amount_total(self):
        for move in self:
            if len(move.line_ids) != 2 or move.is_invoice(include_receipts=True):
                continue

            amount_currency = abs(move.amount_total)
            balance = move.currency_id._convert(
                amount_currency,
                move.company_currency_id,
                move.company_id,
                move.invoice_date or move.date,
            )

            to_write = [
                Command.update(
                    line.id,
                    {
                        "debit": (line.balance > 0.0 and balance) or 0.0,
                        "credit": (line.balance < 0.0 and balance) or 0.0,
                        "amount_currency": (line.balance > 0.0 and amount_currency)
                        or -amount_currency,
                    },
                )
                for line in move.line_ids
                if not move.company_currency_id.is_zero(balance - abs(line.balance))
            ]

            move.write({"line_ids": to_write})

    @api.onchange("partner_id")
    def _inverse_partner_id(self):
        for invoice in self:
            if invoice.is_invoice(True):
                for line in invoice.line_ids | invoice.invoice_line_ids:
                    if line.partner_id != invoice.commercial_partner_id:
                        line.partner_id = invoice.commercial_partner_id
                        line._inverse_partner_id()

    @api.onchange("company_id")
    @_debug.perf.timed
    def _inverse_company_id(self):
        for move in self:
            if not move.company_id:
                raise ValidationError(
                    _(
                        "We can't leave this document without any company. Please select a company for this document."
                    )
                )
        self._conditional_add_to_compute(
            "journal_id",
            lambda m: (
                not m.journal_id.filtered_domain(
                    self.env["account.journal"]._check_company_domain(m.company_id)
                )
            ),
        )

    @api.onchange("currency_id")
    def _inverse_currency_id(self):
        (self.line_ids | self.invoice_line_ids)._conditional_add_to_compute(
            "currency_id",
            lambda l: (
                l.move_id.is_invoice(True) and l.move_id.currency_id != l.currency_id
            ),
        )

    @api.onchange("journal_id")
    def _inverse_journal_id(self):
        self._conditional_add_to_compute(
            "company_id",
            lambda m: not m.company_id or m.company_id != m.journal_id.company_id,
        )
        self._conditional_add_to_compute(
            "currency_id",
            lambda m: (
                not m.currency_id
                or (
                    m.journal_id.currency_id
                    and m.currency_id != m.journal_id.currency_id
                )
            ),
        )

    @api.onchange("payment_reference")
    def _inverse_payment_reference(self):
        self.line_ids._conditional_add_to_compute(
            "name", lambda line: line.display_type == "payment_term"
        )

    @api.onchange("invoice_payment_term_id")
    def _inverse_invoice_payment_term_id(self):
        self.line_ids._conditional_add_to_compute(
            "name", lambda l: l.display_type == "payment_term"
        )

    def _inverse_name(self):
        self._conditional_add_to_compute(
            "payment_reference", lambda move: move.name and move.name != "/"
        )
        self._update_sequence_made_gap()

    def _get_computed_payment_reference_moves(self):
        computed_ref_moves = self.browse()
        for move in self:
            if move.move_type != "out_invoice" or not move.payment_reference:
                continue
            try:
                computed_reference = move._get_invoice_computed_reference()
            except UserError:
                continue
            if move.payment_reference == computed_reference:
                computed_ref_moves |= move
        return computed_ref_moves

    @api.onchange("date")
    def _onchange_date(self):
        if not self.is_invoice(True):
            self.line_ids._inverse_amount_currency()

    @api.onchange("invoice_vendor_bill_id")
    def _onchange_invoice_vendor_bill(self):
        if self.invoice_vendor_bill_id:
            for line in self.invoice_vendor_bill_id.invoice_line_ids:
                copied_vals = line.copy_data()[0]
                self.invoice_line_ids += self.env["account.move.line"].new(copied_vals)

            self.currency_id = self.invoice_vendor_bill_id.currency_id
            self.fiscal_position_id = self.invoice_vendor_bill_id.fiscal_position_id

            self.invoice_vendor_bill_id = False

    @api.onchange("fiscal_position_id")
    def _onchange_fpos_id_show_update_fpos(self):
        self.show_update_fpos = (
            self.line_ids and self._origin.fiscal_position_id != self.fiscal_position_id
        )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        company = (
            self.journal_id.company_id or self.env.company
        )._get_accessible_branches()[:1] or self.env.company
        self = self.with_company(company)
        company = company.with_company(company)
        _debug.logic("partner_onchange_company", move=self, company=company)

        if self.partner_id:
            rec_account = (
                self.partner_id.property_account_receivable_id
                or company.partner_id.property_account_receivable_id
            )
            pay_account = (
                self.partner_id.property_account_payable_id
                or company.partner_id.property_account_payable_id
            )
            if not rec_account and not pay_account:
                _debug.logic(
                    "partner_accounts_missing",
                    move=self,
                    partner=self.partner_id,
                    company=company,
                )
                action = self.env.ref("account.action_account_config")
                msg = _(
                    "Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration."
                )
                raise RedirectWarning(
                    msg, action.id, _("Go to the configuration panel")
                )

    @api.onchange("name", "highest_name")
    @_debug.perf.timed
    def _onchange_name_warning(self):
        if (
            self.name
            and self.name != "/"
            and self.name <= (self.highest_name or "")
            and not self.quick_edit_mode
        ):
            self.show_name_warning = True
        else:
            self.show_name_warning = False
        if _debug.logic.enabled:
            _debug.logic(
                "name_warning_decided",
                move=self,
                show_name_warning=self.show_name_warning,
            )

        origin_name = self._origin.name
        if not origin_name or origin_name == "/":
            origin_name = self.highest_name
        if (
            self.name
            and self.name != "/"
            and origin_name
            and origin_name != "/"
            and self.date == self._origin.date
            and self.journal_id == self._origin.journal_id
        ):
            new_format, new_format_values = self._get_sequence_format_param(self.name)
            origin_format, origin_format_values = self._get_sequence_format_param(
                origin_name
            )

            if new_format != origin_format or dict(
                new_format_values, year=0, month=0, seq=0
            ) != dict(origin_format_values, year=0, month=0, seq=0):
                changed = _(
                    "It was previously '%(previous)s' and it is now '%(current)s'.",
                    previous=origin_name,
                    current=self.name,
                )
                reset = self._deduce_sequence_number_reset(self.name)
                _debug.logic(
                    "sequence_format_changed",
                    move=self,
                    new_format=new_format,
                    origin_format=origin_format,
                    reset=reset,
                )
                if reset == "month":
                    detected = _(
                        "The sequence will restart at 1 at the start of every month.\n"
                        "The year detected here is '%(year)s' and the month is '%(month)s'.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                elif reset == "year":
                    detected = _(
                        "The sequence will restart at 1 at the start of every year.\n"
                        "The year detected here is '%(year)s'.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                elif reset == "year_range":
                    detected = _(
                        "The sequence will restart at 1 at the start of every financial year.\n"
                        "The financial start year detected here is '%(year)s'.\n"
                        "The financial end year detected here is '%(year_end)s'.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                elif reset == "year_range_month":
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
                new_format_values["formatted_seq"] = "{seq:0{seq_length}d}".format(
                    **new_format_values
                )
                detected %= new_format_values
                return {
                    "warning": {
                        "title": _("The sequence format has changed."),
                        "message": "%s\n\n%s" % (changed, detected),
                    }
                }
        return None

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        if not self.quick_edit_mode:
            self.name = False
            self.env.add_to_compute(self._fields["name"], self)

    @api.onchange("invoice_cash_rounding_id")
    def _onchange_invoice_cash_rounding_id(self):
        for move in self:
            if (
                move.invoice_cash_rounding_id.strategy == "add_invoice_line"
                and not move.invoice_cash_rounding_id.profit_account_id
            ):
                return {
                    "warning": {
                        "title": _(
                            "Warning for Cash Rounding Method: %s",
                            move.invoice_cash_rounding_id.name,
                        ),
                        "message": _(
                            "You must specify the Profit Account (company dependent)"
                        ),
                    }
                }
        return None

    @contextmanager
    def _check_balanced(self, container):
        with self._disable_recursion(
            "check_move_validity", default=True, target=False
        ) as disabled:
            yield  # noqa: RUF075 - deliberate: on exception the transaction aborts and rolls back, so a balance check skipped here would only have judged writes that are not being kept
            if disabled:
                return

        if unbalanced_moves := self._get_unbalanced_moves(container):
            _debug.logic(
                "_check_balanced_unbalanced_rows", unbalanced_moves=unbalanced_moves[:8]
            )
            if len(unbalanced_moves) == 1:
                raise UserError(_("The entry is not balanced."))

            error_msg = _("The following entries are unbalanced:\n\n")
            names = self.browse(row[0] for row in unbalanced_moves).mapped("name")
            error_msg += "".join(f"  - {name}\n" for name in names)

            raise UserError(error_msg)

    def _get_unbalanced_moves(self, container):
        moves = container["records"].filtered(lambda move: move.line_ids)
        if not moves:
            return None

        self.env["account.move.line"].flush_model(
            ["debit", "credit", "balance", "currency_id", "move_id"]
        )
        self.flush_model(["company_id"])
        return self.env.execute_query(
            SQL(
                """
            SELECT line.move_id,
                   ROUND(SUM(line.debit), currency.decimal_places) debit,
                   ROUND(SUM(line.credit), currency.decimal_places) credit
              FROM account_move_line line
              JOIN account_move move ON move.id = line.move_id
              JOIN res_company company ON company.id = move.company_id
              JOIN res_currency currency ON currency.id = company.currency_id
             WHERE line.move_id = ANY(%s)
          GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.balance), currency.decimal_places) != 0
        """,
                list(moves.ids),
            )
        )

    @_debug.perf.timed
    def _check_fiscal_lock_dates(self):
        if self.env.context.get("bypass_lock_check") is BYPASS_LOCK_CHECK:
            _debug.logic("fiscal_lock_check_bypassed", moves=self)
            return None
        for move in self:
            journal = move.journal_id
            violated_lock_dates = move.company_id._get_lock_date_violations(
                move.date,
                fiscalyear=True,
                sale=journal and journal.type == "sale",
                purchase=journal and journal.type == "purchase",
                tax=False,
                hard=True,
            )
            if violated_lock_dates:
                _debug.logic(
                    "fiscal_lock_date_violated",
                    move=move,
                    journal=journal,
                    violations=violated_lock_dates,
                )
                message = _(
                    "You cannot add/modify entries prior to and inclusive of: %(lock_date_info)s.",
                    lock_date_info=self.env["res.company"]._format_lock_dates(
                        violated_lock_dates
                    ),
                )
                raise UserError(message)
        return True

    @api.constrains("auto_post", "invoice_date")
    def _require_bill_date_for_autopost(self):
        for record in self:
            if (
                record.auto_post != "no"
                and record.is_purchase_document()
                and not record.invoice_date
            ):
                raise ValidationError(
                    _(
                        "For this entry to be automatically posted, it required a bill date."
                    )
                )

    @api.constrains("journal_id", "move_type")
    @_debug.perf.timed
    def _check_journal_move_type(self):
        for move in self:
            if (
                move.is_purchase_document(include_receipts=True)
                and move.journal_id.type != "purchase"
            ):
                _debug.logic(
                    "purchase_journal_mismatch", move=move, journal=move.journal_id
                )
                raise ValidationError(
                    _("Cannot create a purchase document in a non purchase journal")
                )
            if (
                move.is_sale_document(include_receipts=True)
                and move.journal_id.type != "sale"
            ):
                _debug.logic(
                    "sale_journal_mismatch", move=move, journal=move.journal_id
                )
                raise ValidationError(
                    _("Cannot create a sale document in a non sale journal")
                )

    @_debug.perf.timed
    def _prepare_epd_needed_per_line(self):
        self.check_singleton()
        AccountTax = self.env["account.tax"]
        company = self.company_id or self.env.company
        currency = self.currency_id or company.currency_id
        discount_percentage = self.invoice_payment_term_id.discount_percentage
        percentage_name = f"{discount_percentage}%"
        percentage = discount_percentage / 100
        sign = self.direction_sign

        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(
            AccountTax._aggregate_base_lines_tax_details(
                self._prepare_discountable_base_lines_for_epd(company),
                self.env["account.move.line"]._get_epd_grouping_function(),
            )
        )

        result_per_invoice_line = {}
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue
            key_line = frozendict(
                {"move_id": self.id, **grouping_key, "display_type": "epd"}
            )
            key_counterpart = frozendict(
                {
                    "move_id": self.id,
                    "account_id": grouping_key["account_id"],
                    "display_type": "epd",
                }
            )
            aggregated_base_lines = [
                base_line for base_line, _taxes_data in values["base_line_x_taxes_data"]
            ]
            for base_line in aggregated_base_lines:
                result_per_invoice_line[base_line["_invoice_line"]] = {
                    key_line: {
                        "name": _("Early Payment Discount (%s)", percentage_name),
                        "amount_currency": 0.0,
                        "balance": 0.0,
                    },
                    key_counterpart: {
                        "name": _("Early Payment Discount (%s)", percentage_name),
                        "amount_currency": 0.0,
                        "balance": 0.0,
                        "tax_ids": [Command.clear()],
                    },
                }

            self._spread_epd_over_base_lines(
                result_per_invoice_line,
                aggregated_base_lines,
                key_line,
                key_counterpart,
                {
                    "amount_currency": (
                        currency.decimal_places,
                        currency.round(
                            sign * values["total_excluded_currency"] * percentage
                        ),
                    ),
                    "balance": (
                        company.currency_id.decimal_places,
                        company.currency_id.round(
                            sign * values["total_excluded"] * percentage
                        ),
                    ),
                },
            )

        _debug.pipeline(
            "epd_needed_prepared",
            move=self,
            discount_percentage=discount_percentage,
            groups=len(values_per_grouping_key),
            invoice_lines=len(result_per_invoice_line),
        )
        return result_per_invoice_line

    @_debug.perf.timed
    def _prepare_discountable_base_lines_for_epd(self, company):
        AccountTax = self.env["account.tax"]
        base_lines = [
            self._prepare_product_base_line_for_taxes_computation(line)
            for line in self.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
            )
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, company)
        AccountTax._round_base_lines_tax_details(base_lines, company)
        for base_line in base_lines:
            base_line["_invoice_line"] = base_line["record"]
        return AccountTax._prepare_discountable_base_lines(base_lines, company)

    def _spread_epd_over_base_lines(
        self, result_per_invoice_line, base_lines, key_line, key_counterpart, deltas
    ):
        target_factors = [
            {
                "factor": base_line["tax_details"]["raw_total_excluded_currency"],
                "base_line": base_line,
            }
            for base_line in base_lines
        ]
        for fname, (precision, delta) in deltas.items():
            amounts = self.env["account.tax"]._distribute_delta_amount_smoothly(
                precision_digits=precision,
                delta_amount=delta,
                target_factors=target_factors,
            )
            for target_factor, amount in zip(target_factors, amounts, strict=True):
                epd_needed = result_per_invoice_line[
                    target_factor["base_line"]["_invoice_line"]
                ]
                epd_needed[key_line][fname] -= amount
                epd_needed[key_counterpart][fname] += amount

    @api.constrains("journal_id")
    @_debug.perf.timed
    def _check_journal_is_selectable(self):
        selectable_domain = self.env["account.journal"]._get_domain_selectable()
        if not selectable_domain:
            return
        journals = self.journal_id
        selectable = journals.filtered_domain(selectable_domain)
        forbidden = journals - selectable
        if forbidden:
            raise ValidationError(
                _(
                    "You are not allowed to use the journal %(journals)s.",
                    journals=", ".join(forbidden.mapped("display_name")),
                )
            )

    @api.constrains("line_ids", "fiscal_position_id", "company_id")
    @_debug.perf.timed
    def _check_taxes_country(self):
        self._update_tax_country_id()
        for record in self:
            amls = record.line_ids
            impacted_countries = amls.tax_ids.country_id | amls.tax_line_id.country_id
            if impacted_countries and impacted_countries != record.tax_country_id:
                if (
                    record.fiscal_position_id
                    and impacted_countries != record.fiscal_position_id.country_id
                ):
                    _debug.logic(
                        "tax_country_fpos_incompatible",
                        move=record,
                        countries=impacted_countries,
                    )
                    raise ValidationError(
                        _(
                            "This entry contains taxes that are not compatible with your fiscal position. Check the country set in fiscal position and in your tax configuration."
                        )
                    )
                _debug.logic(
                    "tax_country_incompatible",
                    move=record,
                    countries=impacted_countries,
                )
                raise ValidationError(
                    _(
                        "This entry contains one or more taxes that are incompatible with your fiscal country. Check company fiscal country in the settings and tax country in taxes configuration."
                    )
                )

    @api.constrains("invoice_currency_rate")
    @_debug.perf.timed
    def _check_invoice_currency_rate(self):
        for move in self:
            if (
                move.currency_id
                and move.company_id
                and move.currency_id != move.company_id.currency_id
                and move.is_invoice(include_receipts=True)
                and move.invoice_currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    def _is_eligible_for_early_payment_discount(self, currency, reference_date):
        self.check_singleton()
        payment_terms = self.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        eligible = (
            self.currency_id == currency
            and self.move_type in self._early_payment_discount_move_types()
            and self.invoice_payment_term_id.early_discount
            and (
                not reference_date
                or not self.invoice_date
                or (
                    (existing_discount_date := payment_terms[:1].discount_date)
                    and reference_date <= existing_discount_date
                )
            )
            and not (
                payment_terms.sudo().matched_debit_ids
                + payment_terms.sudo().matched_credit_ids
            )
        )
        _debug.logic(
            "early_payment_discount",
            move=self,
            eligible=bool(eligible),
            currency=currency,
            ref=reference_date,
            discount_date=payment_terms[:1].discount_date,
        )
        return eligible

    def _early_payment_discount_move_types(self):
        return ("out_invoice", "out_receipt", "in_invoice", "in_receipt")

    def _get_early_payment_discount_details(self):
        self.check_singleton()
        line = self.line_ids.filtered(lambda line: line.display_type == "payment_term")[
            :1
        ]
        sign = 1 if self.is_inbound(include_receipts=True) else -1
        return {
            "amount_due": sign * line.discount_amount_currency,
            "date": format_date(self.env, line.discount_date),
        }

    @_debug.perf.timed
    def _sync_business_models(self, changed_fields):
        if self.env.context.get("skip_account_move_synchronization"):
            return

        self_sudo = self.sudo()
        if _debug.pipeline.enabled and self_sudo.statement_line_id:
            _debug.pipeline(
                "syncing_statement_lines",
                move=self,
                statement_lines=self_sudo.statement_line_id,
                fields=sorted(changed_fields),
            )
        self_sudo.statement_line_id._sync_from_moves(changed_fields)

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        default = dict(default or {})
        vals_list = super().copy_data(default)
        default_date = fields.Date.to_date(default.get("date"))
        for move, vals in zip(self, vals_list, strict=True):
            if move.is_invoice(include_receipts=True):
                vals["line_ids"] = [
                    (command, _id, line_vals)
                    for command, _id, line_vals in vals["line_ids"]
                    if command == Command.CREATE
                ]
            elif move.move_type == "entry":
                if "partner_id" not in vals or not self.env.context.get(
                    "move_reverse_cancel", False
                ):
                    vals["partner_id"] = False
            user_fiscal_lock_date = move.company_id._get_user_fiscal_lock_date(
                move.journal_id
            )
            if (default_date or move.date) <= user_fiscal_lock_date:
                _debug.logic(
                    "copy_date_moved_past_lock",
                    move=move,
                    lock_date=user_fiscal_lock_date,
                )
                vals["date"] = user_fiscal_lock_date + timedelta(days=1)
            if not move.journal_id.active and "journal_id" in vals:
                _debug.logic(
                    "copy_archived_journal_dropped", move=move, journal=move.journal_id
                )
                del vals["journal_id"]
        return vals_list

    @_debug.perf.timed
    def copy(self, default=None):
        _debug.lifecycle("copy", records=self)
        default = dict(default or {})
        new_moves = super().copy(default)
        bodies = {}
        for old_move, new_move in zip(self, new_moves, strict=True):
            message_origin = (
                ""
                if not new_move.auto_post_origin_id
                else (
                    Markup("<br/>")
                    + _(
                        "This recurring entry originated from %s",
                        new_move.auto_post_origin_id._get_html_link(),
                    )
                )
            )
            message_content = old_move._get_copy_message_content(default)
            bodies[new_move.id] = message_content + message_origin
        new_moves._message_log_batch(bodies=bodies)
        return new_moves

    def _get_copy_message_content(self, default):
        return (
            _("This entry has been reversed from %s", self._get_html_link())
            if default.get("reversed_entry_id")
            else _("This entry has been duplicated from %s", self._get_html_link())
        )

    @_debug.perf.timed
    def _normalize_vals(self, vals):
        if not (vals.get("invoice_line_ids") and vals.get("line_ids")):
            return vals
        vals = dict(vals)
        update_vals = {
            line_id: line_vals[0]
            for command, line_id, *line_vals in vals["invoice_line_ids"]
            if command == Command.UPDATE
        }
        merged_line_ids = []
        for command, line_id, *line_vals in vals["line_ids"]:
            if command == Command.UPDATE and line_id in update_vals:
                line_vals = [{**line_vals[0], **update_vals.pop(line_id)}]
            merged_line_ids.append((command, line_id, *line_vals))
        for line_id, extra in update_vals.items():
            merged_line_ids.append(Command.update(line_id, extra))
        seen_id_commands = {
            (command, line_id)
            for command, line_id, *_rest in merged_line_ids
            if command != Command.CREATE and line_id
        }
        for command, line_id, *line_vals in vals["invoice_line_ids"]:
            if command in (Command.SET, Command.CLEAR):
                raise UserError(
                    _(
                        "The lines of this entry cannot be replaced wholesale while "
                        "individual journal items are also being modified in the same "
                        "operation. Save the line changes first, then replace them."
                    )
                )
            if command == Command.UPDATE:
                continue
            if line_id and (command, line_id) in seen_id_commands:
                continue
            merged_line_ids.append((command, line_id, *line_vals))
        _debug.pipeline(
            "invoice_line_commands_merged",
            invoice_line_commands=len(vals["invoice_line_ids"]),
            merged_commands=len(merged_line_ids),
        )
        vals["line_ids"] = merged_line_ids
        del vals["invoice_line_ids"]
        return vals

    def _stolen_move(self, vals):
        line_ids = []
        for command in vals.get("line_ids", ()):
            if command[0] == Command.LINK:
                line_ids.append(command[1])
            elif command[0] == Command.SET:
                line_ids.extend(command[2])
        return self.env["account.move.line"].browse(line_ids).move_id.ids

    def _get_field_protections(self, vals, records):
        protected = set()
        for fname in vals:
            field = records._fields[fname]
            if field.inverse or (field.compute and not field.readonly):
                protected.update(self.pool.field_computed.get(field, [field]))
        return [(protected, rec) for rec in records] if protected else []

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        if any(vals.get("state") == "posted" for vals in vals_list):
            raise UserError(
                _(
                    "You cannot create a move already in the posted state. Please create a draft move and post it after."
                )
            )
        container = {"records": self}
        with self._check_balanced(container):
            with ExitStack() as exit_stack, self._sync_dynamic_lines(container):
                vals_list = [self._normalize_vals(vals) for vals in vals_list]
                stolen_moves = self.browse(
                    {move for vals in vals_list for move in self._stolen_move(vals)}
                )
                if _debug.logic.enabled and stolen_moves:
                    _debug.logic("create_stolen_moves", stolen_moves=stolen_moves)
                moves = super().create(vals_list)
                if _debug.pipeline.enabled:
                    _debug.pipeline(
                        "created",
                        move=moves,
                        types=sorted({v.get("move_type", "entry") for v in vals_list}),
                    )
                exit_stack.enter_context(
                    self.env.protecting(
                        [
                            protected
                            for vals, move in zip(vals_list, moves, strict=True)
                            for protected in self._get_field_protections(vals, move)
                        ]
                    )
                )
                container["records"] = moves | stolen_moves
            for move, vals in zip(moves, vals_list, strict=True):
                if "tax_totals" in vals:
                    move.tax_totals = vals["tax_totals"]
            super(AccountMove, moves).write({"is_manually_modified": False})
        return moves

    _UNMODIFIABLE_WHEN_POSTED = frozenset(
        (
            "invoice_line_ids",
            "line_ids",
            "invoice_date",
            "date",
            "partner_id",
            "invoice_payment_term_id",
            "currency_id",
            "fiscal_position_id",
            "invoice_cash_rounding_id",
        )
    )

    @_debug.perf.timed
    def _check_write_journal_change(self, move, vals):
        if (
            move.posted_before
            and "journal_id" in vals
            and move.journal_id.id != vals["journal_id"]
            and not (
                move.name == "/"
                or not move.name
                or ("name" in vals and (vals["name"] == "/" or not vals["name"]))
            )
        ):
            _debug.logic(
                "journal_change_blocked_posted",
                move=move,
                journal_id=vals.get("journal_id"),
            )
            raise UserError(
                _(
                    'You cannot edit the journal of an account move if it has been posted once, unless the name is removed or set to "/". This might create a gap in the sequence.'
                )
            )
        if (
            move.name
            and move.name != "/"
            and move.sequence_number not in (0, 1)
            and "journal_id" in vals
            and move.journal_id.id != vals["journal_id"]
            and not move.quick_edit_mode
            and not ("name" in vals and (vals["name"] == "/" or not vals["name"]))
        ):
            _debug.logic(
                "journal_change_blocked_sequenced",
                move=move,
                journal_id=vals.get("journal_id"),
            )
            raise UserError(
                _(
                    'You cannot edit the journal of an account move with a sequence number assigned, unless the name is removed or set to "/". This might create a gap in the sequence.'
                )
            )

    @_debug.perf.timed
    def _check_write_review_rights(self, move, vals):
        if vals.get("checked") and not move._is_user_able_to_review():
            raise AccessError(
                _("You don't have the access rights to perform this action.")
            )
        if (
            vals.get("state") == "draft"
            and move.checked
            and not move._is_user_able_to_review()
        ):
            raise ValidationError(
                _("Validated entries can only be changed by your accountant.")
            )

    @_debug.perf.timed
    def _check_write_sequence_override(self, move, vals):
        if (
            move.journal_id.sequence_override_regex
            and vals.get("name")
            and vals["name"] != "/"
            and not re.match(move.journal_id.sequence_override_regex, vals["name"])
        ):
            if not self.env.user.has_group("account.group_account_manager"):
                raise UserError(
                    _(
                        "The Journal Entry sequence is not conform to the current format. Only the Accountant can change it."
                    )
                )
            move.journal_id.sequence_override_regex = False

    @_debug.perf.timed
    def _check_write_allowed(self, vals):
        vals_keys = set(vals)
        hashed_fnames = set(self._get_fields_integrity_hash()) | {"inalterable_hash"}
        skip_readonly_check = self.env.context.get("skip_readonly_check")
        readonly_fields = [
            fname for fname in vals if fname in self._UNMODIFIABLE_WHEN_POSTED
        ]
        _debug.logic(
            "write_allowed_scope",
            moves=self,
            fields=len(vals_keys),
            readonly_fields=len(readonly_fields),
            skip_readonly_check=bool(skip_readonly_check),
        )
        for move in self:
            self._check_write_review_rights(move, vals)

            violated_fields = vals_keys & hashed_fnames
            if move.inalterable_hash and violated_fields:
                _debug.logic(
                    "hashed_field_write_refused",
                    move=move,
                    fields=len(violated_fields),
                )
                raise UserError(
                    _(
                        "This document is protected by a hash. "
                        "Therefore, you cannot edit the following fields: %s.",
                        ", ".join(
                            f["string"]
                            for f in self.fields_get(violated_fields).values()
                        ),
                    )
                )
            self._check_write_journal_change(move, vals)

            if move.state == "posted" and (
                ("name" in vals and move.name != vals["name"])
                or ("date" in vals and move.date != vals["date"])
            ):
                _debug.logic("lock_dates_checked_on_rename", move=move)
                move._check_fiscal_lock_dates()
                move.line_ids._check_tax_lock_date()

            if "state" in vals and move.state == "posted" and vals["state"] != "posted":
                _debug.logic("lock_dates_checked_on_unpost", move=move)
                move._check_fiscal_lock_dates()
                move.line_ids._check_tax_lock_date()

            move_state = vals.get("state", move.state)
            if not skip_readonly_check and move_state == "posted" and readonly_fields:
                raise UserError(
                    _(
                        "You cannot modify the following readonly fields on a posted move: %s",
                        ", ".join(
                            f["string"]
                            for f in self.fields_get(readonly_fields).values()
                        ),
                    )
                )

            self._check_write_sequence_override(move, vals)

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if not vals:
            return True
        vals = self._normalize_vals(vals)

        self._check_write_allowed(vals)

        if _debug.lifecycle.enabled and "state" in vals:
            _debug.lifecycle(
                "state_change",
                move=self,
                state=set(self.mapped("state")),
                state_to=vals["state"],
            )
        if {"sequence_prefix", "sequence_number", "journal_id", "name"} & vals.keys():
            if _debug.logic.enabled:
                _debug.logic(
                    "write_sequence_affecting_keys",
                    fields=sorted(
                        vals.keys()
                        & {"sequence_prefix", "sequence_number", "journal_id", "name"}
                    ),
                    records=self,
                )
            self._update_sequence_made_gap(invalidate_current=True)

        renumbered_moves = (
            self.filtered(
                lambda move: move.name != vals["name"]
            )._get_computed_payment_reference_moves()
            if "name" in vals and "payment_reference" not in vals
            else self.browse()
        )

        stolen_moves = self.browse(set(self._stolen_move(vals)))
        container = {"records": self | stolen_moves}
        with (
            self.env.protecting(self._get_field_protections(vals, self)),
            self._check_balanced(container),
        ):
            with self._sync_dynamic_lines(container):
                if "is_manually_modified" not in vals and not self.env.context.get(
                    "skip_is_manually_modified"
                ):
                    vals = dict(vals, is_manually_modified=True)

                res = super(
                    AccountMove,
                    self.with_context(
                        skip_account_move_synchronization=True,
                    ),
                ).write(vals)

                if "journal_id" in vals and "name" not in vals:
                    draft_move = self.filtered(lambda m: not m.posted_before)
                    _debug.logic(
                        "write_journal_changed_name_reset", draft_move=draft_move
                    )
                    draft_move.name = False
                    self.env.add_to_compute(self._fields["name"], draft_move)

                if renumbered_moves:
                    _debug.logic(
                        "write_payment_reference_reset_renumbered",
                        renumbered_moves=renumbered_moves,
                    )
                    renumbered_moves.payment_reference = False

                if "date" in vals or "state" in vals:
                    posted_move = self.filtered(lambda m: m.state == "posted")
                    posted_move._check_fiscal_lock_dates()
                    posted_move.line_ids._check_tax_lock_date()

                if vals.get("state") == "posted":
                    self.flush_recordset()
                    with _debug.perf("write_hash_moves", cr=self.env.cr, records=self):
                        self._hash_moves()

            self._sync_business_models(set(vals.keys()))

            if "tax_totals" in vals:
                super().write({"tax_totals": vals["tax_totals"]})

        if any(field in vals for field in ["journal_id", "currency_id"]):
            self.line_ids._check_account_is_usable()

        return res

    def check_move_sequence_chain(self):
        return self.filtered(lambda move: move.name != "/")._is_end_of_seq_chain()

    def _get_unlink_logger_message(self):
        moves_details = []
        for move in self.filtered(
            lambda m: m.posted_before and m.company_id.restrictive_audit_trail
        ):
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
        return None

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_forbid_parts_of_chain(self):
        _debug.lifecycle("_unlink_forbid_parts_of_chain", records=self)
        if self.env.user.has_group(
            "account.group_account_manager"
        ) or self.env.context.get("force_delete"):
            _debug.logic("chain_unlink_check_bypassed", moves=self)
            return
        protected_moves = self.filtered(
            lambda move: not move.company_id.quick_edit_mode
        )
        if not protected_moves.check_move_sequence_chain():
            _debug.logic(
                "chain_unlink_blocked", moves=self, protected_moves=protected_moves
            )
            raise UserError(
                _(
                    "You cannot delete this entry, as it has already consumed a sequence number and is not the last one in the chain. "
                    "You should probably revert it instead."
                )
            )

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_forbid_hashed(self):
        _debug.lifecycle("_unlink_forbid_hashed", records=self)
        if not self.env.context.get("force_delete") and any(
            self.mapped("inalterable_hash")
        ):
            raise UserError(
                _(
                    "You cannot delete a journal entry that has been secured with "
                    "an inalterability hash."
                )
            )

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_account_audit_trail_except_once_post(self):
        _debug.lifecycle("_unlink_account_audit_trail_except_once_post", records=self)
        if not self.env.context.get("force_delete") and any(
            move.posted_before and move.company_id.restrictive_audit_trail
            for move in self
        ):
            raise UserError(
                _(
                    "To keep the restrictive audit trail, you can not delete journal entries once they have been posted.\n"
                    "Instead, you can cancel the journal entry."
                )
            )

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        with self.env.cr.savepoint():
            self._update_sequence_made_gap(invalidate_current=True)
            moves = self.with_context(skip_invoice_sync=True, dynamic_unlink=True)
            logger_message = moves._get_unlink_logger_message()
            moves.line_ids.remove_move_reconcile()
            moves.line_ids.unlink()
            res = super(AccountMove, moves).unlink()
        if logger_message:
            _logger.info(logger_message)
        return res

    @api.depends(
        "partner_id", "date", "state", "move_type", "name", "ref", "amount_total"
    )
    @api.depends_context("input_full_display_name", "name_as_amount_total")
    def _compute_display_name(self):
        for move in self:
            move.display_name = move._get_move_display_name(show_ref=True)

    @_debug.perf.timed
    def onchange(self, values, field_names, fields_spec):
        if _debug.logic.enabled:
            _debug.logic(
                "onchange_lines_pane",
                line_ids="line_ids" in field_names,
                invoice_line_ids="invoice_line_ids" in field_names,
            )
        if "line_ids" in field_names:
            values = {
                key: val for key, val in values.items() if key != "invoice_line_ids"
            }
            fields_spec = {
                key: val
                for key, val in fields_spec.items()
                if key != "invoice_line_ids"
            }
        elif "invoice_line_ids" in field_names:
            values = {key: val for key, val in values.items() if key != "line_ids"}
            fields_spec = {
                key: val for key, val in fields_spec.items() if key != "line_ids"
            }
            invoice_line_ids = values.get("invoice_line_ids")
            for invoice_line_idx, invoice_line in enumerate(invoice_line_ids):
                if (
                    len(invoice_line) == 3
                    and invoice_line[0] == 1
                    and isinstance(invoice_line[2], dict)
                    and "product_id" in invoice_line[2]
                    and "price_unit" in invoice_line[2]
                ):
                    if isinstance(invoice_line, tuple):
                        invoice_line_ids[invoice_line_idx] = invoice_line = list(
                            invoice_line
                        )
                    invoice_line[2] = dict(
                        sorted(
                            invoice_line[2].items(),
                            key=lambda item: item[0] != "product_id",
                        )
                    )
        return super().onchange(values, field_names, fields_spec)

    @_debug.perf.timed
    def _collect_tax_cash_basis_values(self):
        self.check_singleton()

        values = {
            "move": self,
            "to_process_lines": [],
            "total_balance": 0.0,
            "total_residual": 0.0,
            "total_amount_currency": 0.0,
            "total_residual_currency": 0.0,
        }

        currencies = set()
        has_term_lines = False
        for line in self.line_ids:
            if line.account_type in RECEIVABLE_PAYABLE_TYPES:
                sign = 1 if line.balance > 0.0 else -1

                currencies.add(line.currency_id)
                has_term_lines = True
                values["total_balance"] += sign * line.balance
                values["total_residual"] += sign * line.amount_residual
                values["total_amount_currency"] += sign * line.amount_currency
                values["total_residual_currency"] += (
                    sign * line.amount_residual_currency
                )
            elif line.tax_line_id.tax_exigibility == "on_payment":
                values["to_process_lines"].append(("tax", line))
                currencies.add(line.currency_id)
            elif "on_payment" in line.tax_ids.flatten_taxes_hierarchy().mapped(
                "tax_exigibility"
            ):
                values["to_process_lines"].append(("base", line))
                currencies.add(line.currency_id)

        _debug.logic(
            "caba_lines_collected",
            move=self,
            to_process_lines=len(values["to_process_lines"]),
            has_term_lines=has_term_lines,
            currencies=len(currencies),
        )
        if not values["to_process_lines"] or not has_term_lines:
            return None

        if len(currencies) == 1:
            values["currency"] = next(iter(currencies))
        else:
            return None

        values["is_fully_paid"] = self.company_id.currency_id.is_zero(
            values["total_residual"]
        ) or values["currency"].is_zero(values["total_residual_currency"])

        _debug.logic(
            "caba_fully_paid_decided",
            move=self,
            is_fully_paid=values["is_fully_paid"],
        )
        return values

    @_debug.perf.timed
    def _prepare_tax_lines_for_taxes_computation(self, tax_amls, round_from_tax_lines):
        if round_from_tax_lines:
            return [self._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]
        return []

    _AGGREGATED_TAX_AMOUNT_KEYS = (
        "base_amount",
        "base_amount_currency",
        "tax_amount",
        "tax_amount_currency",
    )

    @_debug.perf.timed
    def _prepare_aggregated_taxes_base_lines(
        self,
        filter_invl_to_apply=None,
        round_from_tax_lines=None,
        postfix_function=None,
    ):
        self.check_singleton()
        AccountTax = self.env["account.tax"]
        base_amls = self.line_ids.filtered(
            lambda x: (
                x.display_type == "product"
                and (not filter_invl_to_apply or filter_invl_to_apply(x))
            )
        )
        base_lines = [
            self._prepare_product_base_line_for_taxes_computation(x) for x in base_amls
        ]
        tax_amls = self.line_ids.filtered("tax_repartition_line_id")
        tax_lines = self._prepare_tax_lines_for_taxes_computation(
            tax_amls, round_from_tax_lines
        )
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        if postfix_function:
            postfix_function(base_lines)
        AccountTax._round_base_lines_tax_details(
            base_lines, self.company_id, tax_lines=tax_lines
        )
        return base_lines

    def _accumulate_aggregated_tax_totals(self, results, base_lines, grouping_function):
        AccountTax = self.env["account.tax"]
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(
            base_lines, grouping_function
        )
        for base_line, aggregated_values in base_lines_aggregated_values:
            base_line_results = results["tax_details_per_record"][base_line["record"]]
            base_line_results["base_line"] = base_line
            for grouping_key, values in aggregated_values.items():
                if grouping_key:
                    for key in self._AGGREGATED_TAX_AMOUNT_KEYS:
                        base_line_results[key] += values[key]

        for grouping_key, values in AccountTax._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        ).items():
            if grouping_key:
                for key in self._AGGREGATED_TAX_AMOUNT_KEYS:
                    results[key] += values[key]
        _debug.pipeline(
            "tax_totals_accumulated",
            base_lines=len(base_lines),
            aggregated=len(base_lines_aggregated_values),
        )
        return base_lines_aggregated_values

    def _accumulate_aggregated_tax_details(
        self, results, base_lines, grouping_function
    ):
        AccountTax = self.env["account.tax"]
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(
            base_lines, grouping_function
        )
        for base_line, aggregated_values in base_lines_aggregated_values:
            base_line_results = results["tax_details_per_record"][base_line["record"]]
            base_line_results["tax_details"] = self._index_by_grouping_key(
                aggregated_values
            )
        results["tax_details"] = self._index_by_grouping_key(
            AccountTax._aggregate_base_lines_aggregated_values(
                base_lines_aggregated_values
            )
        )

    def _index_by_grouping_key(self, values_per_grouping_key):
        tax_details = {}
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue
            if isinstance(grouping_key, dict):
                values.update(grouping_key)
            tax_details[grouping_key] = values
        return tax_details

    @_debug.perf.timed
    def _prepare_invoice_aggregated_taxes(
        self,
        filter_invl_to_apply=None,
        filter_tax_values_to_apply=None,
        grouping_key_generator=None,
        round_from_tax_lines=None,
        postfix_function=None,
    ):
        self.check_singleton()
        if round_from_tax_lines is None:
            round_from_tax_lines = bool(
                filter_tax_values_to_apply or filter_invl_to_apply
            )
        base_lines = self._prepare_aggregated_taxes_base_lines(
            filter_invl_to_apply=filter_invl_to_apply,
            round_from_tax_lines=round_from_tax_lines,
            postfix_function=postfix_function,
        )

        results = {
            "base_amount_currency": 0.0,
            "base_amount": 0.0,
            "tax_amount_currency": 0.0,
            "tax_amount": 0.0,
            "tax_details_per_record": defaultdict(
                lambda: {
                    "base_amount_currency": 0.0,
                    "base_amount": 0.0,
                    "tax_amount_currency": 0.0,
                    "tax_amount": 0.0,
                }
            ),
            "base_lines": base_lines,
        }

        def total_grouping_function(base_line, tax_data):
            if tax_data:
                return not filter_tax_values_to_apply or filter_tax_values_to_apply(
                    base_line, tax_data
                )
            return None

        def tax_details_grouping_function(base_line, tax_data):
            if not total_grouping_function(base_line, tax_data):
                return None
            if grouping_key_generator:
                grouping_key = grouping_key_generator(base_line, tax_data)
                assert grouping_key is not None
                return grouping_key
            return tax_data["tax"]

        self._accumulate_aggregated_tax_totals(
            results, base_lines, total_grouping_function
        )
        self._accumulate_aggregated_tax_details(
            results, base_lines, tax_details_grouping_function
        )
        _debug.pipeline(
            "aggregated_taxes_prepared",
            move=self,
            round_from_tax_lines=round_from_tax_lines,
            custom_grouping=bool(grouping_key_generator),
            base_lines=len(base_lines),
            records=len(results["tax_details_per_record"]),
            tax_details=len(results["tax_details"]),
        )
        return results

    def _get_early_payment_discount_tax_deltas(self, base_lines, tax_amounts):
        self.check_singleton()
        tax_results = self.env["account.tax"]._prepare_tax_lines(
            base_lines, self.company_id
        )
        tax_deltas_per_repartition_line = {}
        for tax_line_vals in tax_results["tax_lines_to_add"]:
            tax_amount_without_epd = tax_amounts.get(
                tax_line_vals["tax_repartition_line_id"]
            )
            if tax_amount_without_epd:
                tax_deltas_per_repartition_line[
                    tax_line_vals["tax_repartition_line_id"]
                ] = {
                    **tax_line_vals,
                    "amount_currency": tax_line_vals["amount_currency"]
                    - tax_amount_without_epd["amount_currency"],
                    "balance": tax_line_vals["balance"]
                    - tax_amount_without_epd["balance"],
                }
        return tax_deltas_per_repartition_line

    def _get_early_payment_discount_bases_details(
        self, base_lines, cash_discount_account, epd_analytic_distribution
    ):
        bases_details = {}
        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            invoice_line = base_line["record"]
            grouping_dict = frozendict(
                {
                    "tax_ids": [Command.set(base_line["tax_ids"].ids)],
                    "tax_tag_ids": [Command.set(base_line["tax_tag_ids"].ids)],
                    "partner_id": base_line["partner_id"].id,
                    "currency_id": base_line["currency_id"].id,
                    "account_id": cash_discount_account.id,
                    "analytic_distribution": base_line["analytic_distribution"]
                    or epd_analytic_distribution,
                }
            )
            base_detail = bases_details.setdefault(
                grouping_dict, {"balance": 0.0, "amount_currency": 0.0}
            )
            base_detail["amount_currency"] += self.currency_id.round(
                self.direction_sign * tax_details["total_excluded_currency"]
                - invoice_line.amount_currency
            )
            base_detail["balance"] += self.company_currency_id.round(
                self.direction_sign * tax_details["total_excluded"]
                - invoice_line.balance
            )
        return bases_details

    @_debug.perf.timed
    def _prepare_early_payment_discount_tax_line_vals(
        self, base_lines, tax_amounts, payment_term_line, percentage_paid
    ):
        tax_deltas_per_repartition_line = self._get_early_payment_discount_tax_deltas(
            base_lines, tax_amounts
        )
        tax_line_vals_list = {}
        for tax_line_vals in tax_deltas_per_repartition_line.values():
            tax_rep = self.env["account.tax.repartition.line"].browse(
                tax_line_vals["tax_repartition_line_id"]
            )
            grouping_dict = frozendict(
                {
                    "account_id": tax_line_vals["account_id"],
                    "partner_id": tax_line_vals["partner_id"],
                    "currency_id": tax_line_vals["currency_id"],
                    "analytic_distribution": tax_line_vals["analytic_distribution"],
                    "tax_repartition_line_id": tax_rep.id,
                    "tax_ids": tax_line_vals["tax_ids"],
                    "tax_tag_ids": tax_line_vals["tax_tag_ids"],
                    "group_tax_id": tax_line_vals["group_tax_id"],
                }
            )
            tax_line_vals_list[grouping_dict] = {
                "name": _("Early Payment Discount (%s)", tax_rep.tax_id.name),
                "amount_currency": payment_term_line.currency_id.round(
                    tax_line_vals["amount_currency"] * percentage_paid
                ),
                "balance": payment_term_line.company_currency_id.round(
                    tax_line_vals["balance"] * percentage_paid
                ),
            }
        _debug.pipeline(
            "epd_tax_lines_prepared",
            move=self,
            line=payment_term_line,
            tax_deltas=len(tax_deltas_per_repartition_line),
            tax_lines=len(tax_line_vals_list),
            percentage_paid=percentage_paid,
        )
        return tax_line_vals_list

    @_debug.perf.timed
    def _prepare_included_early_payment_discount_line_vals(
        self,
        base_lines,
        tax_amounts,
        payment_term_line,
        cash_discount_account,
        epd_analytic_distribution,
        term_amount_currency,
        term_balance,
    ):
        self.check_singleton()
        bases_details = self._get_early_payment_discount_bases_details(
            base_lines, cash_discount_account, epd_analytic_distribution
        )
        percentage_paid = (
            abs(payment_term_line.amount_residual_currency / self.amount_total)
            if self.amount_total
            else 0.0
        )
        tax_line_vals_list = self._prepare_early_payment_discount_tax_line_vals(
            base_lines, tax_amounts, payment_term_line, percentage_paid
        )

        base_line_vals = {
            grouping_dict: {
                "name": _("Early Payment Discount"),
                "amount_currency": payment_term_line.currency_id.round(
                    base_detail["amount_currency"] * percentage_paid
                ),
                "balance": payment_term_line.company_currency_id.round(
                    base_detail["balance"] * percentage_paid
                ),
            }
            for grouping_dict, base_detail in bases_details.items()
        }

        biggest_base_line = max(
            base_line_vals.values(), key=lambda x: abs(x["amount_currency"])
        )
        biggest_base_line["amount_currency"] += (
            term_amount_currency
            - sum(x["amount_currency"] for x in base_line_vals.values())
            - sum(x["amount_currency"] for x in tax_line_vals_list.values())
        )
        biggest_base_line["balance"] += (
            term_balance
            - sum(x["balance"] for x in base_line_vals.values())
            - sum(x["balance"] for x in tax_line_vals_list.values())
        )
        _debug.pipeline(
            "epd_included_lines_prepared",
            move=self,
            line=payment_term_line,
            base_lines=len(base_line_vals),
            tax_lines=len(tax_line_vals_list),
            percentage_paid=percentage_paid,
        )
        return {"base_lines": base_line_vals, "tax_lines": tax_line_vals_list}

    def _get_inverse_tax_repartition_line(self, tax_rep):
        tax = tax_rep.tax_id
        source, target = (
            tax.invoice_repartition_line_ids,
            tax.refund_repartition_line_ids,
        )
        if tax_rep.document_type == "refund":
            source, target = target, source
        try:
            return target[list(source).index(tax_rep)]
        except ValueError, IndexError:
            _debug.logic(
                "inverse_repartition_line_missing",
                tax=tax,
                tax_rep=tax_rep,
                document_type=tax_rep.document_type,
            )
            raise UserError(
                _(
                    "The invoice and credit note distribution of tax %(tax)s"
                    " must contain the same number of lines to compute the"
                    " early payment discount.",
                    tax=tax.display_name,
                )
            ) from None

    def _get_early_payment_discount_base_lines(self, invoice_lines, payment_term):
        base_lines = [
            {
                **self._prepare_product_base_line_for_taxes_computation(line),
                "is_refund": True,
            }
            for line in invoice_lines
        ]
        for base_line in base_lines:
            base_line["tax_ids"] = base_line["tax_ids"].filtered(
                lambda t: t.amount_type != "fixed"
            )

            if payment_term.early_pay_discount_computation == "included":
                remaining_part_to_consider = (
                    100 - payment_term.discount_percentage
                ) / 100.0
                base_line["price_unit"] *= remaining_part_to_consider
        AccountTax = self.env["account.tax"]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(
            base_lines, self.company_id
        )
        return base_lines

    def _get_early_payment_discount_account_and_distribution(self):
        company = self.company_id
        if self.is_inbound(include_receipts=True):
            cash_discount_account = (
                company.account_journal_early_pay_discount_loss_account_id
            )
        else:
            cash_discount_account = (
                company.account_journal_early_pay_discount_gain_account_id
            )

        epd_analytic_distribution = self.env[
            "account.analytic.distribution.model"
        ]._get_distribution(
            {
                "account_prefix": cash_discount_account.code,
                "company_id": self.company_id.id,
                "partner_id": self.commercial_partner_id.id,
                "partner_tag_id": self.partner_id.tag_ids.ids,
            }
        )
        return cash_discount_account, epd_analytic_distribution

    @_debug.perf.timed
    def _get_invoice_counterpart_amls_for_early_payment_discount_per_payment_term_line(
        self,
    ):
        self.check_singleton()

        payment_term_line = self.line_ids.filtered(
            lambda x: x.display_type == "payment_term"
        )
        tax_lines = self.line_ids.filtered("tax_repartition_line_id")
        invoice_lines = self.line_ids.filtered(lambda x: x.display_type == "product")
        payment_term = self.invoice_payment_term_id
        early_pay_discount_computation = payment_term.early_pay_discount_computation

        res = {
            "term_lines": defaultdict(dict),
            "tax_lines": defaultdict(dict),
            "base_lines": defaultdict(dict),
        }
        if not (payment_term.early_discount and payment_term.discount_percentage):
            _debug.logic(
                "epd_counterpart_skipped", move=self, reason="no_early_discount"
            )
            return res

        payment_term_line.check_singleton()

        tax_amounts = defaultdict(lambda: {"amount_currency": 0.0, "balance": 0.0})
        for line in tax_lines:
            tax_rep_id = self._get_inverse_tax_repartition_line(
                line.tax_repartition_line_id
            ).id
            tax_amounts[tax_rep_id]["amount_currency"] += line.amount_currency
            tax_amounts[tax_rep_id]["balance"] += line.balance

        base_lines = self._get_early_payment_discount_base_lines(
            invoice_lines, payment_term
        )
        cash_discount_account, epd_analytic_distribution = (
            self._get_early_payment_discount_account_and_distribution()
        )

        term_amount_currency = (
            payment_term_line.amount_currency
            - payment_term_line.discount_amount_currency
        )
        term_balance = payment_term_line.balance - payment_term_line.discount_balance
        _debug.logic(
            "epd_computation_chosen",
            move=self,
            line=payment_term_line,
            term=payment_term,
            computation=early_pay_discount_computation,
            tax_amounts=len(tax_amounts),
            base_lines=len(base_lines),
        )
        if early_pay_discount_computation == "included" and invoice_lines.tax_ids:
            discount_lines = self._prepare_included_early_payment_discount_line_vals(
                base_lines=base_lines,
                tax_amounts=tax_amounts,
                payment_term_line=payment_term_line,
                cash_discount_account=cash_discount_account,
                epd_analytic_distribution=epd_analytic_distribution,
                term_amount_currency=term_amount_currency,
                term_balance=term_balance,
            )
            res["base_lines"][payment_term_line].update(discount_lines["base_lines"])
            res["tax_lines"][payment_term_line].update(discount_lines["tax_lines"])
        else:
            grouping_dict = {"account_id": cash_discount_account.id}

            res["term_lines"][payment_term_line][frozendict(grouping_dict)] = {
                "name": _("Early Payment Discount"),
                "partner_id": payment_term_line.partner_id.id,
                "currency_id": payment_term_line.currency_id.id,
                "amount_currency": term_amount_currency,
                "balance": term_balance,
                "analytic_distribution": epd_analytic_distribution,
            }

        return res

    @api.model
    @_debug.perf.timed
    def _get_invoice_counterpart_amls_for_early_payment_discount(
        self, aml_values_list, open_balance
    ):
        res = {
            "base_lines": {},
            "tax_lines": {},
            "term_lines": {},
            "exchange_lines": {},
        }
        if not aml_values_list:
            return {key: [] for key in res}

        res_per_invoice = {}
        reference_aml = aml_values_list[-1]["aml"]
        for aml_values in aml_values_list:
            aml = aml_values["aml"]
            invoice = aml.move_id

            if invoice not in res_per_invoice:
                res_per_invoice[invoice] = (
                    invoice._get_invoice_counterpart_amls_for_early_payment_discount_per_payment_term_line()
                )

            for key in ("base_lines", "tax_lines", "term_lines"):
                for grouping_dict, vals in res_per_invoice[invoice][key][aml].items():
                    line_vals = res[key].setdefault(
                        grouping_dict,
                        {
                            **vals,
                            "amount_currency": 0.0,
                            "balance": 0.0,
                        },
                    )
                    line_vals["amount_currency"] += vals["amount_currency"]
                    line_vals["balance"] += vals["balance"]

                    open_balance -= vals["balance"]

        exchange_diff_sign = reference_aml.company_currency_id.compare_amounts(
            open_balance, 0.0
        )
        _debug.pipeline(
            "epd_counterparts_aggregated",
            amls=len(aml_values_list),
            invoices=len(res_per_invoice),
            base_lines=len(res["base_lines"]),
            tax_lines=len(res["tax_lines"]),
            term_lines=len(res["term_lines"]),
            open_balance=open_balance,
            exchange_diff_sign=exchange_diff_sign,
        )
        if exchange_diff_sign != 0:
            if exchange_diff_sign > 0:
                exchange_line_account = (
                    reference_aml.company_id.expense_currency_exchange_account_id
                )
            else:
                exchange_line_account = (
                    reference_aml.company_id.income_currency_exchange_account_id
                )

            grouping_dict = {
                "account_id": exchange_line_account.id,
                "currency_id": reference_aml.currency_id.id,
                "partner_id": reference_aml.partner_id.id,
            }
            line_vals = res["exchange_lines"].setdefault(
                frozendict(grouping_dict),
                {
                    **grouping_dict,
                    "name": _("Early Payment Discount (Exchange Difference)"),
                    "amount_currency": 0.0,
                    "balance": 0.0,
                },
            )
            line_vals["balance"] += open_balance

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
        return any(
            line._affect_tax_report()
            for line in (self.line_ids | self.invoice_line_ids)
        )

    @_debug.perf.timed
    def _get_move_display_name(self, show_ref=False):
        self.check_singleton()
        if self.env.context.get("name_as_amount_total"):
            _debug.logic("display_name_as_amount_total", move=self)
            currency_amount = self.currency_id.format(self.amount_total)
            if self.is_sale_document(include_receipts=True) and self.state == "posted":
                ref = f" - {self.ref}" if self.ref else ""
                return _(
                    "%(name)s%(ref)s at %(currency_amount)s",
                    name=(self.name),
                    ref=ref,
                    currency_amount=currency_amount,
                )
            label = (
                (self.ref or self.name or "")
                if self.is_purchase_document(include_receipts=True)
                else (self.name or "")
            )
            if label:
                if self.state == "draft":
                    return _(
                        "%(label)s at %(currency_amount)s (Draft)",
                        label=label,
                        currency_amount=currency_amount,
                    )
                return _(
                    "%(label)s at %(currency_amount)s",
                    label=label,
                    currency_amount=currency_amount,
                )
            return _("Draft (%(currency_amount)s)", currency_amount=currency_amount)
        name = ""
        if self.state == "draft":
            name += {
                "out_invoice": _("Draft Invoice"),
                "out_refund": _("Draft Credit Note"),
                "in_invoice": _("Draft Bill"),
                "in_refund": _("Draft Vendor Credit Note"),
                "out_receipt": _("Draft Sales Receipt"),
                "in_receipt": _("Draft Purchase Receipt"),
                "entry": _("Draft Entry"),
            }[self.move_type]
        if self.name and self.name != "/":
            name = f"{name} {self.name}".strip()
            if self.env.context.get("input_full_display_name"):
                if self.partner_id:
                    name += f", {self.partner_id.name}"
                if self.date:
                    name += f", {format_date(self.env, self.date)}"
        return name + (
            f" ({shorten(self.ref, width=50)})" if show_ref and self.ref else ""
        )

    def _get_receivable_payable_lines(self):
        return self.line_ids.filtered(
            lambda line: line.account_type in RECEIVABLE_PAYABLE_TYPES
        )

    def _get_reconciled_amls(self):
        reconciled_lines = self._get_receivable_payable_lines()
        return reconciled_lines.mapped(
            "matched_debit_ids.debit_move_id"
        ) | reconciled_lines.mapped("matched_credit_ids.credit_move_id")

    def _get_reconciled_payments(self):
        return self._get_reconciled_amls().move_id.origin_payment_id

    def _get_reconciled_statement_lines(self):
        return self._get_reconciled_amls().move_id.statement_line_id

    def _get_reconciled_invoices(self):
        return self._get_reconciled_amls().move_id.filtered(
            lambda move: move.is_invoice(include_receipts=True)
        )

    def _add_exchange_move_partials(
        self, partial_values_list, counterpart_line_ids, exchange_move_ids
    ):
        self.env["account.move.line"].flush_model(["move_id"])
        rows = self.env.execute_query(
            SQL(
                _SQL_EXCHANGE_MOVE_PARTIALS,
                exchange_move_ids=tuple(exchange_move_ids),
                counterpart_line_ids=tuple(counterpart_line_ids),
            )
        )
        _debug.perf.count("exchange_move_partials_fetched", rows=len(rows))
        for part_id, line_ids in rows:
            counterpart_line_ids.add(line_ids)
            partial_values_list.append(
                {
                    "aml_id": line_ids,
                    "partial_id": part_id,
                    "currency": self.company_id.currency_id,
                }
            )

    @_debug.perf.timed
    def _get_all_reconciled_invoice_partials(self):
        self.check_singleton()
        reconciled_lines = self._get_receivable_payable_lines()
        if not reconciled_lines.ids:
            _debug.logic(
                "reconciled_partials_skipped", move=self, reason="no_term_lines"
            )
            return []

        self.env["account.partial.reconcile"].flush_model(
            [
                "credit_amount_currency",
                "credit_move_id",
                "debit_amount_currency",
                "debit_move_id",
                "exchange_move_id",
            ]
        )
        sql = SQL(_SQL_RECONCILED_PARTIALS, line_ids=tuple(reconciled_lines.ids))

        partial_values_list = []
        counterpart_line_ids = set()
        exchange_move_ids = set()
        for values in self.env.execute_query_dict(sql):
            partial_values_list.append(
                {
                    "aml_id": values["counterpart_line_id"],
                    "partial_id": values["id"],
                    "amount": values["amount"],
                    "currency": self.currency_id,
                }
            )
            counterpart_line_ids.add(values["counterpart_line_id"])
            if values["exchange_move_id"]:
                exchange_move_ids.add(values["exchange_move_id"])

        _debug.pipeline(
            "reconciled_partials_fetched",
            move=self,
            term_lines=len(reconciled_lines),
            partials=len(partial_values_list),
            exchange_moves=len(exchange_move_ids),
        )
        if exchange_move_ids:
            self._add_exchange_move_partials(
                partial_values_list, counterpart_line_ids, exchange_move_ids
            )

        counterpart_lines = {
            x.id: x for x in self.env["account.move.line"].browse(counterpart_line_ids)
        }
        for partial_values in partial_values_list:
            partial_values["aml"] = counterpart_lines[partial_values["aml_id"]]
            partial_values["is_exchange"] = (
                partial_values["aml"].move_id.id in exchange_move_ids
            )
            if partial_values["is_exchange"]:
                partial_values["amount"] = abs(partial_values["aml"].balance)

        return partial_values_list

    def _get_reconciled_invoices_partials(self):
        self.check_singleton()
        pay_term_lines = self._get_receivable_payable_lines()
        invoice_partials = []
        exchange_diff_moves = []

        for partial in pay_term_lines.matched_debit_ids:
            invoice_partials.append(
                (partial, partial.credit_amount_currency, partial.debit_move_id)
            )
            if partial.exchange_move_id:
                exchange_diff_moves.append(partial.exchange_move_id.id)
        for partial in pay_term_lines.matched_credit_ids:
            invoice_partials.append(
                (partial, partial.debit_amount_currency, partial.credit_move_id)
            )
            if partial.exchange_move_id:
                exchange_diff_moves.append(partial.exchange_move_id.id)
        _debug.pipeline(
            "invoice_partials_collected",
            move=self,
            partials=len(invoice_partials),
            exchange_moves=len(exchange_diff_moves),
        )
        return invoice_partials, exchange_diff_moves

    @_debug.perf.timed
    def _reconcile_reversed_moves(self, reverse_moves, move_reverse_cancel):
        _debug.pipeline(
            "reversed_moves_reconciling",
            moves=self,
            reverse_moves=reverse_moves,
            cancel=move_reverse_cancel,
        )
        for reverse_move in reverse_moves:
            move = reverse_move.reversed_entry_id
            if move not in self:
                continue
            group = (
                (move.line_ids + reverse_move.line_ids)
                .filtered(lambda l: not l.reconciled)
                .sorted(lambda l: l.account_type not in RECEIVABLE_PAYABLE_TYPES)
                .grouped(lambda l: (l.account_id, l.currency_id))
            )
            for (account, _currency), lines in group.items():
                if (
                    all(not line.reconciled for line in lines) and account.reconcile
                ) or account.account_type in ("asset_cash", "liability_credit_card"):
                    _debug.logic(
                        "reversal_lines_reconciled",
                        move=move,
                        reverse_move=reverse_move,
                        account=account,
                        lines=lines,
                    )
                    lines.with_context(
                        move_reverse_cancel=move_reverse_cancel
                    ).reconcile()
        return reverse_moves

    @_debug.perf.timed
    def _reverse_moves(self, default_values_list=None, cancel=False):
        _debug.lifecycle("_reverse_moves", records=self)
        if not default_values_list:
            default_values_list = [{} for _move in self]

        if cancel:
            lines = self.mapped("line_ids")
            if lines:
                _debug.pipeline(
                    "reverse_cancel_unreconciling", move=self, lines_count=len(lines)
                )
                lines.remove_move_reconcile()

        reverse_moves = self.browse()
        for move, default_values in zip(self, default_values_list, strict=True):
            default_values = {
                **default_values,
                "move_type": TYPE_REVERSE_MAP[move.move_type],
                "reversed_entry_id": move.id,
                "partner_id": move.partner_id.id,
            }
            reverse_moves += move.with_context(
                move_reverse_cancel=cancel,
                include_business_fields=True,
                skip_invoice_sync=move.move_type == "entry",
            ).copy(default_values)

        reverse_moves.with_context(skip_invoice_sync=cancel).write(
            {
                "line_ids": [
                    Command.update(
                        line.id,
                        {
                            "balance": -line.balance,
                            "amount_currency": -line.amount_currency,
                            **(
                                {"is_storno": not line.is_storno}
                                if line.company_id.account_storno
                                else {}
                            ),
                        },
                    )
                    for line in reverse_moves.line_ids
                    if line.move_id.move_type == "entry" or line.display_type == "cogs"
                ]
            }
        )

        _debug.pipeline(
            "reversed", move=self, reverse_moves=reverse_moves, cancel=cancel
        )
        if cancel:
            reverse_moves.with_context(move_reverse_cancel=cancel)._post(soft=False)

        return reverse_moves

    def _can_be_unlinked(self):
        self.check_singleton()
        if self.inalterable_hash:
            _debug.logic("unlink_refused_hashed", move=self)
            return False
        if self.state != "posted":
            return True
        lock_date = self.company_id._get_user_fiscal_lock_date(self.journal_id)
        posted_caba_entry = (
            self.tax_cash_basis_rec_id or self.tax_cash_basis_origin_move_id
        )
        posted_exchange_diff_entry = self.exchange_diff_partial_ids
        _debug.logic(
            "posted_unlink_inputs",
            move=self,
            lock_date=lock_date,
            caba_entry=bool(posted_caba_entry),
            exchange_diff_entry=bool(posted_exchange_diff_entry),
        )
        return (
            self.date > lock_date
            and not posted_caba_entry
            and not posted_exchange_diff_entry
        )

    def _is_protected_by_audit_trail(self):
        return any(
            move.posted_before and move.company_id.restrictive_audit_trail
            for move in self
        )

    @_debug.perf.timed
    def _unlink_or_reverse(self):
        _debug.lifecycle("_unlink_or_reverse", records=self)
        if not self:
            return None
        to_unlink = self.browse()
        to_cancel = self.browse()
        to_reverse = self.browse()
        for move in self:
            if not move._can_be_unlinked():
                to_reverse += move
            elif move._is_protected_by_audit_trail():
                to_cancel += move
            else:
                to_unlink += move
        _debug.logic(
            "_unlink_or_reverse", unlink=to_unlink, cancel=to_cancel, reverse=to_reverse
        )
        to_unlink.filtered(lambda m: m.state in ("posted", "cancel")).action_draft()
        to_unlink.filtered(lambda m: m.state == "draft").unlink()
        to_cancel.filtered(lambda m: m.state != "cancel").action_cancel()
        return to_reverse._reverse_moves(cancel=True)

    def _reveal_partial_deductibility_group(self):
        if self.env.user.has_group("account.group_partial_purchase_deductibility"):
            _debug.logic("partial_deductibility_group_already_held", moves=self)
            return
        has_partial_deductibility = self.filtered(
            lambda move: (
                move.move_type == "in_invoice"
                and move.invoice_line_ids.filtered(
                    lambda line: (
                        float_compare(line.deductible_amount, 100, precision_digits=2)
                        != 0
                    )
                )
            )
        )
        if has_partial_deductibility:
            _debug.logic(
                "partial_deductibility_group_granted",
                moves=has_partial_deductibility,
            )
            self.env.user.sudo().group_ids = [
                Command.link(
                    self.env.ref("account.group_partial_purchase_deductibility").id
                )
            ]

    @_debug.perf.timed
    def _post_check_access(self):
        _debug.lifecycle("_post_check_access", records=self)
        if not self.env.su and not self.env.user.has_group(
            "account.group_account_invoice"
        ):
            raise AccessError(_("You don't have the access rights to post an invoice."))

    def _post_check_business_rules(self):
        return

    @_debug.perf.timed
    def _check_post_partner_bank(self, invoice, validation_msgs):
        if invoice.partner_bank_id and not invoice.partner_bank_id.active:
            _debug.logic(
                "partner_bank_archived", move=invoice, bank=invoice.partner_bank_id
            )
            validation_msgs.add(
                _(
                    "The recipient bank account linked to this invoice is archived.\n"
                    "So you cannot confirm the invoice."
                )
            )
        if (
            invoice.partner_bank_id
            and invoice.is_inbound()
            and not invoice.partner_bank_id.allow_out_payment
        ):
            _debug.logic(
                "partner_bank_untrusted",
                move=invoice,
                bank=invoice.partner_bank_id,
                su=self.env.su,
            )
            if self.env.su or self.env.user.has_groups(
                "base.group_public,base.group_portal"
            ):
                _debug.logic("partner_bank_cleared", move=invoice)
                invoice.partner_bank_id = False
            elif invoice.partner_bank_id._can_user_trust():
                raise RedirectWarning(
                    _(
                        "The company bank account (%(account_number)s) linked to this invoice is not trusted. "
                        "Go to the Bank Settings, double-check that it is yours or correct the number, and click on Send Money to trust it.",
                        account_number=invoice.partner_bank_id.display_name,
                    ),
                    invoice.partner_bank_id._get_records_action(),
                    _("Bank settings"),
                )
            else:
                raise UserError(
                    _(
                        "The bank account of your company is not trusted. Please ask an admin or someone with approval rights to check it."
                    )
                )

    @_debug.perf.timed
    def _check_post_invoice_date(self, invoice, validation_msgs):
        if invoice.invoice_date:
            return
        if invoice.is_sale_document(include_receipts=True):
            expected_rate = invoice._get_expected_currency_rate_at(
                invoice.create_date.date()
            )
            is_manual_rate = (
                float_compare(
                    invoice.invoice_currency_rate,
                    expected_rate,
                    precision_digits=6,
                )
                != 0
            )
            _debug.logic(
                "invoice_date_defaulted", move=invoice, manual_rate=is_manual_rate
            )
            with (
                self.env.protecting([self._fields["invoice_currency_rate"]], invoice)
                if is_manual_rate
                else nullcontext()
            ):
                invoice.invoice_date = fields.Date.context_today(self)
        elif invoice.is_purchase_document(include_receipts=True):
            _debug.logic("bill_date_missing", move=invoice)
            validation_msgs.add(
                _("The Bill/Refund date is required to validate this document.")
            )

    @_debug.perf.timed
    def _check_post_invoices(self, validation_msgs):
        for invoice in self.filtered(
            lambda move: move.is_invoice(include_receipts=True)
        ):
            if (
                invoice.quick_edit_mode
                and invoice.quick_edit_total_amount
                and invoice.currency_id.compare_amounts(
                    invoice.quick_edit_total_amount, invoice.amount_total
                )
                != 0
            ):
                _debug.logic(
                    "post_refused_quick_edit_total",
                    move=invoice,
                    expected_total=invoice.quick_edit_total_amount,
                    amount_total=invoice.amount_total,
                )
                validation_msgs.add(
                    _(
                        "The current total is %(current_total)s but the expected total is %(expected_total)s. In order to post the invoice/bill, "
                        "you can adjust its lines or the expected Total (tax inc.).",
                        current_total=formatLang(
                            self.env,
                            invoice.amount_total,
                            currency_obj=invoice.currency_id,
                        ),
                        expected_total=formatLang(
                            self.env,
                            invoice.quick_edit_total_amount,
                            currency_obj=invoice.currency_id,
                        ),
                    )
                )
            self._check_post_partner_bank(invoice, validation_msgs)
            if (
                float_compare(
                    invoice.amount_total,
                    0.0,
                    precision_rounding=invoice.currency_id.rounding,
                )
                < 0
            ):
                _debug.logic(
                    "post_refused_negative_total",
                    move=invoice,
                    amount_total=invoice.amount_total,
                )
                validation_msgs.add(
                    _(
                        "You cannot validate an invoice with a negative total amount. "
                        "You should create a credit note instead. "
                        "Use the action menu to transform it into a credit note or refund."
                    )
                )

            if not invoice.partner_id:
                _debug.logic("post_refused_missing_partner", move=invoice)
                if invoice.is_sale_document():
                    validation_msgs.add(
                        _(
                            "The 'Customer' field is required to validate the invoice.\n"
                            "You probably don't want to explain to your auditor that you invoiced an invisible man :)"
                        )
                    )
                elif invoice.is_purchase_document():
                    validation_msgs.add(
                        _(
                            "The field 'Vendor' is required, please complete it to validate the Vendor Bill."
                        )
                    )

            self._check_post_invoice_date(invoice, validation_msgs)

    @_debug.perf.timed
    def _check_post_moves(self, validation_msgs, posting_now=True):
        for move in self:
            if move.state in ["posted", "cancel"]:
                _debug.logic("post_refused_not_draft", move=move, state=move.state)
                validation_msgs.add(
                    _(
                        "The entry %(name)s (id %(id)s) must be in draft.",
                        name=move.name,
                        id=move.id,
                    )
                )
            if not move.line_ids.filtered(
                lambda line: line.display_type not in NON_ACCOUNTABLE_DISPLAY_TYPES
            ):
                _debug.logic("post_refused_no_accountable_lines", move=move)
                validation_msgs.add(_("Even magicians can't post nothing!"))
            if (
                posting_now
                and move.auto_post != "no"
                and move.date > fields.Date.context_today(self)
            ):
                _debug.logic(
                    "post_refused_future_auto_post",
                    move=move,
                    auto_post=move.auto_post,
                    date=move.date,
                )
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                validation_msgs.add(
                    _(
                        "This move is configured to be auto-posted on %(date)s",
                        date=date_msg,
                    )
                )
            if not move.journal_id.active:
                validation_msgs.add(
                    _(
                        "You cannot post an entry in an archived journal (%(journal)s)",
                        journal=move.journal_id.display_name,
                    )
                )
            if move.display_inactive_currency_warning:
                validation_msgs.add(
                    _(
                        "You cannot validate a document with an inactive currency: %s",
                        move.currency_id.name,
                    )
                )

            if move.line_ids.account_id.filtered(
                lambda account: not account.active
            ) and not self.env.context.get("skip_account_deprecation_check"):
                validation_msgs.add(
                    _(
                        "A line of this move is using a archived account, you cannot post it."
                    )
                )

            move_company_and_parents = move.company_id.sudo().parent_ids
            mismatched_accounts = move.line_ids.mapped("account_id").filtered(
                lambda account, move_company_and_parents=move_company_and_parents: (
                    not move_company_and_parents & account.sudo().company_ids
                )
            )
            if mismatched_accounts:
                _debug.logic(
                    "post_refused_foreign_company_accounts",
                    move=move,
                    accounts=mismatched_accounts,
                )
                validation_msgs.add(
                    self.env._(
                        "The entry is using accounts (%(accounts_codes_names)s) from a different company.",
                        accounts_codes_names=format_list(
                            self.env, mismatched_accounts.mapped("display_name")
                        ),
                    )
                )

    @_debug.perf.timed
    def _check_before_post(self, posting_now=True):
        _debug.lifecycle("_check_before_post", records=self)
        validation_msgs = set()

        self._check_post_invoices(validation_msgs)

        self.line_ids._check_account_is_usable()
        self._check_post_moves(validation_msgs, posting_now)

        if validation_msgs:
            _debug.logic(
                "_check_before_post",
                refused=self,
                validation_msgs_count=len(validation_msgs),
            )
            msg = "\n".join(sorted(validation_msgs))
            raise UserError(msg)

        if inactive_analytic_ids := (
            self.line_ids.sudo()
            .with_context(active_test=False)
            .distribution_analytic_account_ids.filtered(lambda a: not a.active)
        ):
            raise UserError(
                _(
                    "You cannot post an entry with an archived analytic account: %s",
                    ", ".join(inactive_analytic_ids.mapped("name")),
                )
            )

    @_debug.perf.timed
    def _post_get_draft_reverse_moves(self):
        _debug.lifecycle("_post_get_draft_reverse_moves", records=self)
        return self.filtered(
            lambda move: (
                move.reversed_entry_id and move.reversed_entry_id.state == "posted"
            )
        )

    @_debug.perf.timed
    def _post_prepare_reconciliation(self):
        _debug.lifecycle("_post_prepare_reconciliation", records=self)
        side_move_ids = set()
        partial_ids_to_unlink = set()
        reachable_ids = set(self.ids)
        collected_per_move = {}

        for aml in self.line_ids:
            for partials, counterpart_field in [
                (aml.matched_debit_ids, "debit_move_id"),
                (aml.matched_credit_ids, "credit_move_id"),
            ]:
                for partial in partials:
                    counterpart_move = partial[counterpart_field].move_id
                    if (
                        counterpart_move.state == "posted"
                        or counterpart_move.id in reachable_ids
                    ):
                        side_move_ids.update(partial.exchange_move_id.ids)
                        reachable_ids.update(partial.exchange_move_id.ids)

                        if partial._has_outdated_draft_caba_move_vals(
                            collected_per_move
                        ):
                            partial_ids_to_unlink.add(partial.id)
                            continue

                        caba_source = (
                            aml.move_id
                            if aml.move_id.tax_cash_basis_created_move_ids
                            else counterpart_move
                        )
                        caba_moves = (
                            caba_source.tax_cash_basis_created_move_ids.filtered(
                                lambda m, partial=partial: (
                                    m.tax_cash_basis_rec_id == partial
                                )
                            )
                        )
                        side_move_ids.update(caba_moves.ids)
                        reachable_ids.update(caba_moves.ids)

        _debug.pipeline(
            "post_side_moves_collected",
            moves=self,
            side_moves=len(side_move_ids),
            outdated_caba_partials=len(partial_ids_to_unlink),
        )
        if partial_ids_to_unlink:
            self.env["account.partial.reconcile"].browse(partial_ids_to_unlink).unlink()

        return self.browse(side_move_ids) - self

    @_debug.perf.timed
    def _post_update_partner_ranks(self):
        _debug.lifecycle("_post_update_partner_ranks", records=self)
        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for invoice in self:
            if invoice.is_sale_document():
                customer_count[invoice.partner_id] += 1
            elif invoice.is_purchase_document():
                supplier_count[invoice.partner_id] += 1
            elif invoice.move_type == "entry":
                sale_amls = invoice.line_ids.filtered(
                    lambda line: (
                        line.partner_id
                        and line.account_id.account_type == "asset_receivable"
                    )
                )
                for partner in sale_amls.mapped("partner_id"):
                    customer_count[partner] += 1
                purchase_amls = invoice.line_ids.filtered(
                    lambda line: (
                        line.partner_id
                        and line.account_id.account_type == "liability_payable"
                    )
                )
                for partner in purchase_amls.mapped("partner_id"):
                    supplier_count[partner] += 1
        _debug.pipeline(
            "partner_ranks_counted",
            moves=self,
            customers=len(customer_count),
            suppliers=len(supplier_count),
        )
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank(
                "customer_rank", count
            )
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank(
                "supplier_rank", count
            )

    @_debug.perf.timed
    def _post_defer_future_moves(self):
        _debug.lifecycle("_post_defer_future_moves", records=self)
        future_moves = self.filtered(
            lambda move: move.date > fields.Date.context_today(self)
        )
        if not future_moves:
            return self
        _debug.logic(
            "_post_defer_future_moves_deferring_auto_post_date",
            future_moves=future_moves,
        )
        future_moves._check_before_post(posting_now=False)
        future_moves.filtered(lambda move: move.auto_post == "no").auto_post = "at_date"
        future_moves._message_log_batch(
            bodies={
                move.id: _(
                    "This move will be posted at the accounting date: %(date)s",
                    date=format_date(self.env, move.date),
                )
                for move in future_moves
            }
        )
        return self - future_moves

    @_debug.perf.timed
    def _post_update_accounting_dates(self):
        _debug.lifecycle("_post_update_accounting_dates", records=self)
        move_ids_per_accounting_date = defaultdict(list)
        for move in self:
            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move_ids_per_accounting_date[
                    move._get_accounting_date(
                        move._get_accounting_date_source(),
                        affects_tax_report,
                        lock_dates=lock_dates,
                    )
                ].append(move.id)
        for accounting_date, move_ids in move_ids_per_accounting_date.items():
            _debug.logic(
                "_post_update_accounting_dates_lock_date_violated_moving",
                move_ids=move_ids[:8],
                accounting_date=accounting_date,
            )
            self.browse(move_ids).date = accounting_date

    @_debug.perf.timed
    def _post_update_line_partners(self):
        _debug.lifecycle("_post_update_line_partners", records=self)
        wrong_line_ids_per_partner = defaultdict(list)
        for invoice in self.filtered(lambda move: move.is_invoice()):
            wrong_lines = invoice.line_ids.filtered(
                lambda aml, invoice=invoice: (
                    aml.partner_id != invoice.commercial_partner_id
                    and aml.display_type not in NON_ACCOUNTABLE_DISPLAY_TYPES
                )
            )
            if wrong_lines:
                wrong_line_ids_per_partner[invoice.commercial_partner_id.id].extend(
                    wrong_lines.ids
                )
        for partner_id, wrong_line_ids in wrong_line_ids_per_partner.items():
            self.env["account.move.line"].browse(wrong_line_ids).write(
                {"partner_id": partner_id}
            )

    @_debug.perf.timed
    def _post_update_non_deductible_names(self):
        _debug.lifecycle("_post_update_non_deductible_names", records=self)
        non_deductible_lines = self.line_ids.filtered(
            lambda line: (
                line.display_type
                in ("non_deductible_product_total", "non_deductible_tax")
            )
        )
        if not non_deductible_lines:
            return
        line_ids_per_name = defaultdict(list)
        for line in non_deductible_lines:
            line_ids_per_name[
                _("%s - private part", line.move_id.name)
                if line.display_type == "non_deductible_product_total"
                else _("%s - private part (taxes)", line.move_id.name)
            ].append(line.id)
        for name, line_ids in line_ids_per_name.items():
            self.env["account.move.line"].browse(line_ids).name = name

    @_debug.perf.timed
    def _post(self, soft=True):
        _debug.lifecycle("_post", records=self)
        self._post_check_access()

        moves = self.with_context(skip_is_manually_modified=True)
        to_post = moves._post_defer_future_moves() if soft else moves
        _debug.pipeline("_post_posting", move=self, soft=soft, to_post=to_post)

        return to_post._post_entries() if to_post else to_post

    @_debug.perf.timed
    def _post_entries(self):
        _debug.lifecycle("_post_entries", records=self)
        self._check_before_post()

        self._post_update_accounting_dates()
        self.line_ids._create_analytic_lines()

        if not self.env.context.get("skip_recurring_copy"):
            self.filtered(
                lambda m: m.auto_post == "recurring"
            )._copy_recurring_entries()

        self._post_update_line_partners()

        draft_reverse_moves = self._post_get_draft_reverse_moves()
        side_moves = self._post_prepare_reconciliation()
        _debug.pipeline(
            "_post_entries",
            move=self,
            draft_reverse=draft_reverse_moves,
            side=side_moves,
        )

        (self | side_moves).write({"state": "posted", "posted_before": True})
        self._reveal_partial_deductibility_group()
        self._post_update_non_deductible_names()

        draft_reverse_moves.reversed_entry_id._reconcile_reversed_moves(
            draft_reverse_moves, self.env.context.get("move_reverse_cancel", False)
        )
        (self | side_moves).line_ids._reconcile_marked()
        self._post_update_partner_ranks()

        zero_invoices = self.filtered(
            lambda m: (
                m.is_invoice(include_receipts=True)
                and m.currency_id.is_zero(m.amount_total)
            )
        )
        if _debug.logic.enabled and zero_invoices:
            _debug.logic(
                "_post_entries_zero_total_invoices_treated", zero_invoices=zero_invoices
            )
        zero_invoices._invoice_paid_hook()

        return self

    @_debug.perf.timed
    def _has_sequence_gap_around(self, previous, current, next_move):
        return (
            current.name
            and current.name != "/"
            and (
                (
                    previous
                    and previous.name
                    and previous.name != "/"
                    and (current.sequence_number != previous.sequence_number + 1)
                )
                or (
                    next_move
                    and current.state != "posted"
                    and previous.state == "posted"
                )
            )
        )

    def _is_sequence_computed_with_mixin(self, move, sequence_mixin_cache):
        if not move.name or move.name == "/":
            return False
        try:
            format_string, format_values = move._get_sequence_format_param(move.name)
        except ValidationError:
            return False
        format_values.pop("seq")
        cache_key = (
            format_string.format(**format_values, seq=0),
            self._sequence_index and move[self._sequence_index],
        )
        return sequence_mixin_cache.get(cache_key) is not None

    def _get_sequence_gap_neighbours(self):
        self.flush_model(["name", "sequence_prefix", "sequence_number", "journal_id"])
        made_gap_data = self.env.execute_query(SQL(_SQL_SEQUENCE_NEIGHBOURS, self.ids))
        _debug.perf.count("sequence_neighbours_fetched", rows=len(made_gap_data))
        all_ids = tuple(
            {
                id_
                for row in made_gap_data
                for ids in row
                for id_ in (ids if isinstance(ids, list) else [ids])
            }
        )
        return made_gap_data, all_ids

    @_debug.perf.timed
    def _update_sequence_made_gap(self, invalidate_current=False):
        if not self:
            return

        sequence_mixin_cache = self._get_sequence_cache()
        made_gap_data, all_ids = self._get_sequence_gap_neighbours()

        def browse(ids=()):
            return self.sudo().browse(ids).with_prefetch(all_ids)

        def is_computed_with_mixin(move):
            return self._is_sequence_computed_with_mixin(move, sequence_mixin_cache)

        _debug.pipeline(
            "sequence_gap_neighbours_fetched",
            moves=self,
            rows=len(made_gap_data),
            invalidate_current=invalidate_current,
        )
        gap_flags_changed = 0  # debuglog
        for previous_ids, current_id, next_ids in made_gap_data:
            move_p1, move_p2 = (
                browse(previous_ids)
                if len(previous_ids) == 2
                else (browse(previous_ids), browse())
            )
            move_n1, move_n2 = (
                browse(next_ids) if len(next_ids) == 2 else (browse(next_ids), browse())
            )
            current_move = browse(current_id)

            current_made_gap = bool(
                (
                    not is_computed_with_mixin(current_move)
                    or current_move.state != "posted"
                )
                and self._has_sequence_gap_around(move_p1, current_move, move_n1)
            )
            if current_move.made_sequence_gap != current_made_gap:
                gap_flags_changed += 1  # debuglog
                current_move.made_sequence_gap = current_made_gap

            if move_n1:
                n1_made_gap = bool(
                    invalidate_current
                    or self._has_sequence_gap_around(
                        self.browse() if invalidate_current else current_move,
                        move_n1,
                        move_n2,
                    )
                )
                if move_n1.made_sequence_gap != n1_made_gap:
                    gap_flags_changed += 1  # debuglog
                    move_n1.made_sequence_gap = n1_made_gap

            if move_p1 and (
                not is_computed_with_mixin(current_move)
                or current_move.state != "posted"
            ):
                p1_made_gap = bool(
                    self._has_sequence_gap_around(
                        move_p2,
                        move_p1,
                        self.browse() if invalidate_current else current_move,
                    )
                )
                if move_p1.made_sequence_gap != p1_made_gap:
                    gap_flags_changed += 1  # debuglog
                    move_p1.made_sequence_gap = p1_made_gap

        _debug.logic(
            "sequence_gap_flags_updated", moves=self, changed=gap_flags_changed
        )
        self.journal_id.invalidate_recordset(["has_sequence_holes"])

    def _find_and_set_purchase_orders(
        self, po_references, partner_id, amount_total, from_ocr=False, timeout=10
    ):
        self.check_singleton()

    def _link_bill_origin_to_purchase_orders(self, timeout=10):
        for move in self.filtered(lambda m: m.move_type in self.get_purchase_types()):
            references = re.findall(r"[^,\s]+", move.invoice_origin or "")
            move._find_and_set_purchase_orders(
                references, move.partner_id.id, move.amount_total, timeout=timeout
            )
        return self

    def _autopost_bill(self):
        self.check_singleton()
        eligible = bool(
            self.company_id.autopost_bills
            and self.partner_id
            and self.is_purchase_document(include_receipts=True)
            and self.partner_id.autopost_bills == "always"
            and not self.abnormal_amount_warning
            and not self.restrict_mode_hash_table
        )
        _debug.logic(
            "_autopost_bill",
            move=self,
            eligible=eligible,
            partner_setting=self.partner_id.autopost_bills,
            duplicates=bool(self.duplicated_ref_ids),
        )
        if eligible:
            if self.duplicated_ref_ids:
                self.message_post(
                    body=_(
                        "Auto-post was disabled on this invoice because a potential duplicate was detected."
                    )
                )
            else:
                self.action_post()

    @_debug.perf.timed
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
            _debug.logic("autopost_wizard_skipped", moves=self, reason="not_eligible")
            return False
        prev_bills_same_partner = self.search(
            [
                ("id", "!=", self.id),
                ("partner_id", "=", self.partner_id.id),
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("move_type", "in", self.get_purchase_types(include_receipts=True)),
            ],
            order="create_date DESC",
            limit=10,
        )
        nb_unmodified_bills = 1
        for move in prev_bills_same_partner:
            if move.is_manually_modified:
                break
            nb_unmodified_bills += 1
        _debug.logic(
            "autopost_unmodified_bills_counted",
            move=self,
            previous_bills=len(prev_bills_same_partner),
            nb_unmodified_bills=nb_unmodified_bills,
        )
        if nb_unmodified_bills < 3:
            return False
        wizard = self.env["account.autopost.bills.wizard"].create(
            {
                "partner_id": self.partner_id.id,
                "nb_unmodified_bills": nb_unmodified_bills,
            }
        )
        return {
            "name": _("Autopost Bills"),
            "type": "ir.actions.act_window",
            "res_model": "account.autopost.bills.wizard",
            "res_id": wizard.id,
            "views": [(False, "form")],
            "target": "new",
        }

    @_debug.perf.timed
    def open_payments(self):
        _debug.lifecycle("open_payments", records=self)
        payments = self.reconciled_payment_ids
        return payments._get_records_action(name=_("Payments"))

    @_debug.perf.timed
    def open_reconcile_view(self):
        _debug.lifecycle("open_reconcile_view", records=self)
        return self.line_ids.open_reconcile_view()

    @_debug.perf.timed
    def action_view_business_doc(self):
        _debug.lifecycle("action_view_business_doc", records=self)
        self.check_singleton()
        if self.origin_payment_id:
            name = _("Payment")
            res_model = "account.payment"
            res_id = self.origin_payment_id.id
        elif self.statement_line_id:
            name = _("Bank Transaction")
            res_model = "account.bank.statement.line"
            res_id = self.statement_line_id.id
        else:
            name = _("Journal Entry")
            res_model = "account.move"
            res_id = self.id

        _debug.logic("business_doc_resolved", move=self, res_model=res_model)
        return {
            "name": name,
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_model": res_model,
            "res_id": res_id,
            "target": "current",
        }

    @_debug.perf.timed
    def action_update_fpos_values(self):
        _debug.lifecycle("action_update_fpos_values", records=self)
        if any(move.state != "draft" for move in self):
            _debug.logic("fpos_update_refused", moves=self, reason="not_draft")
            raise UserError(
                _("The fiscal position values can only be updated on draft entries.")
            )
        container = {"records": self}
        with self._check_balanced(container), self._sync_dynamic_lines(container):
            lines_to_recompute = self.env["account.move.line"]
            for line in self.invoice_line_ids:
                if line.display_type in ("line_section", "line_note"):
                    continue
                if not line.price_unit:
                    lines_to_recompute |= line
                    continue
                new_taxes = line._get_computed_taxes()
                if line.tax_ids.filtered("price_include") != new_taxes.filtered(
                    "price_include"
                ):
                    line.price_unit = (
                        line.product_id._get_tax_included_unit_price_from_price(
                            line.price_unit,
                            line.tax_ids,
                            fiscal_position=line.move_id.fiscal_position_id,
                            product_taxes_after_fp=new_taxes,
                        )
                    )
            _debug.pipeline(
                "fpos_lines_queued_for_recompute",
                moves=self,
                zero_price_lines=len(lines_to_recompute),
            )
            self.env.add_to_compute(
                lines_to_recompute._fields["price_unit"], lines_to_recompute
            )
            self.env.add_to_compute(
                self.invoice_line_ids._fields["tax_ids"], self.invoice_line_ids
            )
            self.env.add_to_compute(self.line_ids._fields["account_id"], self.line_ids)

    @_debug.perf.timed
    def open_created_caba_entries(self):
        _debug.lifecycle("open_created_caba_entries", records=self)
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cash Basis Entries"),
            "res_model": "account.move",
            "view_mode": "form",
            "domain": [("id", "in", self.tax_cash_basis_created_move_ids.ids)],
            "views": [
                (self.env.ref("account.view_move_tree").id, "list"),
                (False, "form"),
            ],
        }

    @_debug.perf.timed
    def open_adjusting_entries(self):
        _debug.lifecycle("open_adjusting_entries", records=self)
        self.check_singleton()
        return self.adjusting_entries_move_ids._get_records_action(
            name="Adjusting Entries"
        )

    @_debug.perf.timed
    def open_adjusting_entry_origin_moves(self):
        _debug.lifecycle("open_adjusting_entry_origin_moves", records=self)
        self.check_singleton()
        label = (
            self.adjusting_entry_origin_label
            if len(self.adjusting_entries_move_ids) == 1
            else "Invoices"
        )
        return self.adjusting_entry_origin_move_ids._get_records_action(name=label)

    @_debug.perf.timed
    def action_switch_move_type(self):
        _debug.lifecycle("action_switch_move_type", records=self)
        if any((move.posted_before and move.name) for move in self):
            raise ValidationError(
                _(
                    "You cannot switch the type of a document with an existing sequence number."
                )
            )
        if any(move.move_type == "entry" for move in self):
            raise ValidationError(_("This action isn't available for this document."))

        for move in self:
            in_out, old_move_type = move.move_type.split("_")
            new_move_type = (
                f"{in_out}_{'invoice' if old_move_type == 'refund' else 'refund'}"
            )
            _debug.logic("move_type_switched", move=move, new_move_type=new_move_type)
            move.name = False
            move.write(
                {
                    "move_type": new_move_type,
                    "currency_id": move.currency_id.id,
                    "fiscal_position_id": move.fiscal_position_id.id,
                }
            )
            if move.amount_total < 0:
                line_ids_commands = []
                for line in move.line_ids:
                    if line.display_type != "product":
                        continue
                    line_ids_commands.append(
                        Command.update(
                            line.id,
                            {
                                "quantity": -line.quantity,
                                "extra_tax_data": self.env[
                                    "account.tax"
                                ]._reverse_quantity_base_line_extra_tax_data(
                                    line.extra_tax_data
                                ),
                            },
                        )
                    )
                _debug.logic(
                    "switched_quantities_negated",
                    move=move,
                    lines=len(line_ids_commands),
                )
                move.write({"line_ids": line_ids_commands})

    def get_currency_rate(self, company_id, to_currency_id, date):
        self.check_access("read")
        company = self.env["res.company"].browse(company_id)
        company.check_access("read")
        to_currency = self.env["res.currency"].browse(to_currency_id)
        to_currency.check_access("read")

        return self.env["res.currency"]._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    def refresh_invoice_currency_rate(self):
        self._update_invoice_currency_rate()

    @_debug.perf.timed
    def action_register_payment(self):
        _debug.lifecycle("action_register_payment", records=self)
        if any(m.state != "posted" for m in self):
            raise UserError(
                _("You can only register payment for posted journal entries.")
            )
        return self.action_force_register_payment()

    @_debug.perf.timed
    def action_force_register_payment(self):
        _debug.lifecycle("action_force_register_payment", records=self)
        if any(m.move_type == "entry" for m in self):
            raise UserError(
                _("You cannot register payments for miscellaneous entries.")
            )
        if blocked := self.filtered(lambda m: m.payment_state == "blocked"):
            raise UserError(
                _(
                    "You cannot register payments for blocked invoices: "
                    "%(invoices)s.\nUnblock them first.",
                    invoices=", ".join(blocked.mapped("display_name")),
                )
            )
        return self.line_ids.action_register_payment()

    @_debug.perf.timed
    def action_duplicate(self):
        _debug.lifecycle("action_duplicate", records=self)
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_move_journal_line"
        )
        action["context"] = dict(self.env.context)
        action["context"]["view_no_maturity"] = False
        action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
        action["res_id"] = self.copy().id
        return action

    @_debug.perf.timed
    def action_send_and_print(self):
        _debug.lifecycle("action_send_and_print", records=self)
        self.env["mixin.account.move.send"]._check_move_constraints(self)
        return {
            "name": _("Send"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "account.move.send.wizard"
            if len(self) == 1
            else "account.move.send.batch.wizard",
            "target": "new",
            "context": {
                "active_model": "account.move",
                "active_ids": self.ids,
            },
        }

    @_debug.perf.timed
    def action_invoice_sent(self):
        _debug.lifecycle("action_invoice_sent", records=self)
        self.check_singleton()
        report_action = self.action_send_and_print()
        report_action["context"].update({"allow_partners_without_mail": True})
        return self._get_action_with_base_document_layout_configurator(report_action)

    @_debug.perf.timed
    def action_invoice_download_pdf(self, target="download"):
        _debug.lifecycle("action_invoice_download_pdf", records=self)
        return {
            "type": "ir.actions.act_url",
            "url": f"/account/download_invoice_documents/{','.join(map(str, self.ids))}/pdf",
            "target": target,
        }

    @_debug.perf.timed
    def action_move_download_all(self):
        _debug.lifecycle("action_move_download_all", records=self)
        return {
            "type": "ir.actions.act_url",
            "url": f"/account/download_move_attachments/{','.join(str(move_id) for move_id in self.ids)}",
            "target": "download",
        }

    def preview_invoice(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": self.get_portal_url(),
        }

    @_debug.perf.timed
    def action_reverse(self):
        _debug.lifecycle("action_reverse", records=self)
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_view_account_move_reversal"
        )

        if self.is_invoice():
            action["name"] = _("Credit Note")

        return action

    def _get_confirm_entries_action(self, view_id=None):
        wizard = self.env["validate.account.move"].create(
            {
                "move_ids": [Command.set(self.ids)],
            }
        )
        action = {
            "name": _("Confirm Entries"),
            "type": "ir.actions.act_window",
            "res_model": "validate.account.move",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
        if view_id:
            action["view_id"] = view_id
        return action

    @_debug.perf.timed
    def _post_needing_confirmation(self, need_confirmation, view_id=None):
        _debug.lifecycle("_post_needing_confirmation", records=self)
        to_post = self - need_confirmation
        if to_post:
            to_post._post_check_business_rules()
            to_post._post(soft=False)
        if need_confirmation:
            return need_confirmation._get_confirm_entries_action(view_id=view_id)
        if autopost_bills_wizard := to_post._show_autopost_bills_wizard():
            return autopost_bills_wizard
        return False

    @_debug.perf.timed
    def action_post(self):
        _debug.lifecycle("action_post", records=self)
        need_confirmation = (
            self.filtered(
                lambda m: m.abnormal_amount_warning or m.abnormal_date_warning
            )
            if self._is_abnormal_confirmation_requested()
            else self.browse()
        )
        if _debug.logic.enabled and need_confirmation:
            _debug.logic(
                "action_post_abnormal_warnings_need_confirmation",
                need_confirmation=need_confirmation,
            )
        return self._post_needing_confirmation(need_confirmation)

    def _filtered_requiring_confirmation(self):
        return self.filtered(
            lambda move: (
                (move.date or move.invoice_date) > fields.Date.context_today(self)
                or move.restrict_mode_hash_table
            ),
        )

    @_debug.perf.timed
    def action_post_moves_with_confirmation(self):
        _debug.lifecycle("action_post_moves_with_confirmation", records=self)
        draft_moves = self.filtered(lambda m: m.state == "draft" and m.line_ids)
        if not draft_moves:
            raise UserError(_("There are no journal items in the draft state to post."))

        return draft_moves._post_needing_confirmation(
            draft_moves._filtered_requiring_confirmation(),
            view_id=self.env.ref("account.validate_account_move_view").id,
        )

    @_debug.perf.timed
    def js_add_outstanding_line(self, line_id):
        _debug.lifecycle("js_add_outstanding_line", records=self)
        self.check_singleton()
        counterpart_line = self.env["account.move.line"].browse(line_id).exists()
        if (
            not counterpart_line
            or counterpart_line.company_id != self.company_id
            or counterpart_line.parent_state != "posted"
            or counterpart_line.reconciled
        ):
            raise UserError(
                _("This line cannot be reconciled with this invoice anymore.")
            )
        lines = counterpart_line
        lines += self.line_ids.filtered(
            lambda line: (
                line.account_id == counterpart_line.account_id and not line.reconciled
            )
        )
        _debug.pipeline(
            "widget_reconciling_outstanding_line",
            move=self,
            counterpart_line=counterpart_line,
            lines=lines - counterpart_line,
        )
        return lines.reconcile()

    @_debug.perf.timed
    def js_remove_outstanding_partial(self, partial_id):
        _debug.lifecycle("js_remove_outstanding_partial", records=self)
        self.check_singleton()
        partial = self.env["account.partial.reconcile"].browse(partial_id).exists()
        if not (partial.debit_move_id + partial.credit_move_id) & self.line_ids:
            raise UserError(
                _("This partial reconciliation does not concern this document.")
            )
        return partial.unlink()

    @_debug.perf.timed
    def button_set_checked(self):
        _debug.lifecycle("button_set_checked", records=self)
        self.set_moves_checked()

    def check_selected_moves(self):
        self.browse(self.env.context.get("active_ids", [])).set_moves_checked()

    def set_moves_checked(self, is_checked=True):
        self.filtered(lambda m: m.state == "posted").checked = is_checked

    @_debug.perf.timed
    def action_draft(self):
        _debug.lifecycle("action_draft", records=self)
        if any(move.state not in ("cancel", "posted") for move in self):
            raise UserError(
                _("Only posted/cancelled journal entries can be reset to draft.")
            )
        if any(move.need_cancel_request for move in self):
            raise UserError(
                _(
                    "You can't reset to draft those journal entries. You need to request a cancellation instead."
                )
            )

        self._check_draftable()
        self._unlink_next_draft_auto_post_moves()
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "action_draft_dropping_analytic_lines",
                move=self,
                states=set(self.mapped("state")),
                analytic_line_count=len(self.line_ids.analytic_line_ids),
            )
        self.line_ids.analytic_line_ids.with_context(skip_analytic_sync=True).unlink()
        self.state = "draft"
        self.sending_data = False

        self._detach_attachments()

    @_debug.perf.timed
    def _unlink_next_draft_auto_post_moves(self):
        _debug.lifecycle("_unlink_next_draft_auto_post_moves", records=self)
        recurring_moves = self.filtered(
            lambda move: move.id and move.auto_post_origin_id.id
        )
        if not recurring_moves:
            _debug.logic("next_draft_unlink_skipped", moves=self, reason="no_recurring")
            return
        self.flush_model(["date", "auto_post_origin_id"])
        next_draft_move_ids = [
            move_id
            for [move_id] in self.env.execute_query(
                SQL(
                    """
                       SELECT next_move.id
                         FROM account_move AS current_move
                         JOIN LATERAL (
                                  SELECT move.id, move.state
                                    FROM account_move AS move
                                   WHERE move.auto_post_origin_id = current_move.auto_post_origin_id
                                     AND move.date > current_move.date
                                ORDER BY move.date, move.id
                                   LIMIT 1
                              ) AS next_move ON TRUE
                        WHERE current_move.id = ANY(%(ids)s)
                          AND next_move.state = 'draft'
                    """,
                    ids=list(recurring_moves.ids),
                )
            )
        ]
        _debug.pipeline(
            "next_draft_auto_post_moves_found",
            recurring_moves=recurring_moves,
            next_drafts=len(next_draft_move_ids),
        )
        self.browse(next_draft_move_ids).unlink()

    def _get_fields_to_detach(self):
        return ["invoice_pdf_report_file"]

    def _is_attachment_detach_required(self):
        return self.is_sale_document()

    def _detach_attachments(self):
        moves = self.filtered(lambda move: move._is_attachment_detach_required())
        files_to_detach = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("res_model", "=", "account.move"),
                    ("res_id", "in", moves.ids),
                    ("res_field", "in", self._get_fields_to_detach()),
                ]
            )
        )
        if files_to_detach:
            files_to_detach.res_field = False
            today = format_date(self.env, fields.Date.context_today(self))
            for attachment in files_to_detach:
                stem, _dot, extension = attachment.name.rpartition(".")
                attachment_name, attachment_extension = (
                    (stem, f".{extension}") if stem else (attachment.name, "")
                )
                attachment.name = _(
                    "%(attachment_name)s (detached by %(user)s on %(date)s)%(attachment_extension)s",
                    attachment_name=attachment_name,
                    attachment_extension=attachment_extension,
                    user=self.env.user.name,
                    date=today,
                )

    @_debug.perf.timed
    def _check_draftable(self):
        exchange_move_ids = set()
        if self:
            self.env["account.partial.reconcile"].flush_model(["exchange_move_id"])
            sql = SQL(
                """
                    SELECT DISTINCT exchange_move_id
                    FROM account_partial_reconcile
                    WHERE exchange_move_id = ANY(%s)
                """,
                list(self.ids),
            )
            exchange_move_ids = {id_ for (id_,) in self.env.execute_query(sql)}
            _debug.perf.count("exchange_moves_fetched", rows=len(exchange_move_ids))

        for move in self:
            if move.id in exchange_move_ids:
                _debug.logic("draft_blocked_exchange_move", move=move)
                raise UserError(
                    _("You cannot reset to draft an exchange difference journal entry.")
                )
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                _debug.logic("draft_blocked_cash_basis", move=move)
                raise UserError(
                    _("You cannot reset to draft a tax cash basis journal entry.")
                )
            if move.inalterable_hash:
                _debug.logic("draft_blocked_hashed", move=move)
                raise UserError(_("You cannot reset to draft a locked journal entry."))

    @_debug.perf.timed
    def button_hash(self):
        _debug.lifecycle("button_hash", records=self)
        self._hash_moves(force_hash=True)

    @_debug.perf.timed
    def button_request_cancel(self):
        _debug.lifecycle("button_request_cancel", records=self)
        self.check_singleton()
        if not self.need_cancel_request:
            raise UserError(
                _(
                    "You can only request a cancellation for invoice sent to the government."
                )
            )

    @_debug.perf.timed
    def action_cancel(self):
        _debug.lifecycle("action_cancel", records=self)
        moves_to_reset_draft = self.filtered(lambda x: x.state == "posted")
        if moves_to_reset_draft:
            moves_to_reset_draft.action_draft()

        if any(move.state != "draft" for move in self):
            raise UserError(_("Only draft journal entries can be cancelled."))

        self.line_ids.remove_move_reconcile()
        self.payment_ids.state = "canceled"
        self.write({"auto_post": "no", "state": "cancel"})

    @_debug.perf.timed
    def action_toggle_block_payment(self):
        _debug.lifecycle("action_toggle_block_payment", records=self)
        self.check_singleton()
        if self.payment_state == "blocked":
            self.payment_state = "not_paid"
            self.env.add_to_compute(self._fields["payment_state"], self)
        else:
            if self.payment_state in ("paid", "in_payment"):
                raise UserError(_("You can't block a paid invoice."))
            self.payment_state = "blocked"

    @_debug.perf.timed
    def action_activate_currency(self):
        _debug.lifecycle("action_activate_currency", records=self)
        self.currency_id.filtered(lambda currency: not currency.active).write(
            {"active": True}
        )

    @_debug.perf.timed
    def action_remove_duplicates(self):
        _debug.lifecycle("action_remove_duplicates", records=self)
        for move in self:
            move.duplicated_ref_ids.unlink()

    _SELF_BILLING_MAIL_TEMPLATES = {
        "in_invoice": "account.email_template_edi_self_billing_invoice",
        "in_refund": "account.email_template_edi_self_billing_credit_note",
    }

    def _get_mail_template(self):
        move_types = set(self.mapped("move_type"))
        if len(move_types) == 1:
            move_type = move_types.pop()
            if move_type == "out_refund":
                return self.env.ref("account.email_template_edi_credit_note")
            if move_type in self._SELF_BILLING_MAIL_TEMPLATES and all(
                move.journal_id.is_self_billing for move in self
            ):
                return self.env.ref(self._SELF_BILLING_MAIL_TEMPLATES[move_type])
        return self.env.ref("account.email_template_edi_invoice")

    @_debug.perf.timed
    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        self.check_singleton()

        if self.move_type != "entry":
            local_msg_vals = dict(msg_vals or {})
            partner_ids = (
                local_msg_vals.get("partner_ids", [])
                if "partner_ids" in local_msg_vals
                else message.partner_ids.ids
            )
            self._portal_get_or_create_token()
            access_link = self._notify_get_action_link(
                "view", **local_msg_vals, access_token=self.access_token
            )

            button_access = {"url": access_link} if access_link else {}
            recipient_group = (
                "additional_intended_recipient",
                lambda pdata: (
                    pdata["id"] in partner_ids
                    and pdata["id"] != self.partner_id.id
                    and pdata["type"] != "user"
                ),
                {
                    "has_button_access": True,
                    "button_access": button_access,
                },
            )
            _debug.logic(
                "intended_recipient_group_added",
                move=self,
                partners=len(partner_ids),
                has_access_link=bool(access_link),
            )
            groups.insert(0, recipient_group)

        return groups

    @_debug.perf.timed
    def _get_report_base_filename(self):
        return self._get_move_display_name()

    @_debug.perf.timed
    def _autopost_draft_entries(self, batch_size=100):
        domain = [
            ("state", "=", "draft"),
            ("date", "<=", fields.Date.context_today(self)),
            ("auto_post", "!=", "no"),
        ]
        moves = self.search(domain, limit=batch_size).try_lock_for_update()
        remaining = len(moves) if len(moves) < batch_size else self.search_count(domain)
        self.env["ir.cron"]._commit_progress(remaining=remaining)
        _debug.lifecycle("cron_autopost_batch", moves=moves, remaining=remaining)

        try:
            moves._post_check_business_rules()
            moves._post()
            self.env["ir.cron"]._commit_progress(len(moves))
            return
        except PG_RETRY_EXCEPTIONS:
            raise
        except Exception:
            _debug.logic(
                "cron_autopost_batch_failed_one_by_one",
                error=repr(sys.exc_info()[1]),
            )
            self.env.cr.rollback()

        for move in moves:
            try:
                move = move.try_lock_for_update().filtered_domain(domain)
                if not move:
                    self.env["ir.cron"]._commit_progress(1)
                    continue
                move._post_check_business_rules()
                move._post()
                self.env["ir.cron"]._commit_progress(1)
            except PG_RETRY_EXCEPTIONS:
                raise
            except (UserError, ValidationError) as e:
                self.env.cr.rollback()
                msg = _(
                    "The move could not be posted for the following reason: %(error_message)s",
                    error_message=e,
                )
                move.message_post(body=msg, message_type="comment")
                self.env["ir.cron"]._commit_progress(1)
            except Exception:
                self.env.cr.rollback()
                _logger.warning(
                    "Auto-post cron: skipping move %s this run after an "
                    "unexpected error; it will be retried.",
                    move.id,
                    exc_info=True,
                )
                self.env["ir.cron"]._commit_progress(1)

    @api.model
    @_debug.perf.timed
    def _cron_account_move_send(self, job_count=10):
        _debug.lifecycle("_cron_account_move_send", records=self)
        domain = [
            ("sending_data", "!=", False),
            ("state", "=", "posted"),
        ]
        to_process = self.search(
            domain,
            order="date asc, invoice_date asc, sequence_number asc, id asc",
            limit=job_count,
        )
        to_process = to_process.try_lock_for_update()
        if not to_process:
            return

        _debug.pipeline("cron_send_processing", to_process=to_process)
        self.env["mixin.account.move.send"]._generate_and_send_invoices(
            to_process,
            from_cron=True,
        )
        self.env["ir.cron"]._commit_progress(
            len(to_process), remaining=self.search_count(domain)
        )

    def _get_available_action_reports(self, is_invoice_report=True):
        domain = [("model", "=", "account.move")]

        if is_invoice_report:
            domain += [("is_invoice_report", "=", True)]

        model_reports = self.env["ir.actions.report"].search(domain)

        return model_reports.filtered(
            lambda model_template: (
                len(
                    self.filtered_domain(
                        ast.literal_eval(model_template.domain or "[]")
                    )
                )
                == len(self)
            )
        )

    def _is_action_report_available(self, action_report, is_invoice_report=True):
        assert len(action_report) == 1

        self.check_singleton()

        if available_report := action_report.filtered(
            lambda available_report: (
                not (is_invoice_report ^ available_report.is_invoice_report)
            )
        ):
            return bool(
                self.filtered_domain(ast.literal_eval(available_report.domain or "[]"))
            )

        return False

    @api.model
    def _get_suitable_journal_ids(self, move_type, company=False):
        journal_type = self._get_domain_invoice_filter_type(move_type) or "general"
        return self.env["account.journal"].search(
            [
                *self.env["account.journal"]._check_company_domain(
                    company or self.env.company
                ),
                ("type", "=", journal_type),
            ]
        )

    @api.model
    def _get_domain_invoice_filter_type(self, move_type):
        if self.is_sale_document(include_receipts=True, move_type=move_type):
            return "sale"
        elif self.is_purchase_document(include_receipts=True, move_type=move_type):
            return "purchase"
        else:
            return False

    @api.model
    def get_invoice_types(self, include_receipts=False):
        return self.get_sale_types(include_receipts) + self.get_purchase_types(
            include_receipts
        )

    def is_invoice(self, include_receipts=False):
        return self.is_sale_document(include_receipts) or self.is_purchase_document(
            include_receipts
        )

    def is_entry(self):
        return self.move_type == "entry"

    @api.model
    def get_sale_types(self, include_receipts=False):
        return ["out_invoice", "out_refund"] + (
            (include_receipts and ["out_receipt"]) or []
        )

    def is_sale_document(self, include_receipts=False, move_type=False):
        return (move_type or self.move_type) in self.get_sale_types(include_receipts)

    @api.model
    def get_purchase_types(self, include_receipts=False):
        return ["in_invoice", "in_refund"] + (
            (include_receipts and ["in_receipt"]) or []
        )

    def is_purchase_document(self, include_receipts=False, move_type=False):
        return (move_type or self.move_type) in self.get_purchase_types(
            include_receipts
        )

    @api.model
    def get_inbound_types(self, include_receipts=True):
        return ["out_invoice", "in_refund"] + (
            (include_receipts and ["out_receipt"]) or []
        )

    def is_inbound(self, include_receipts=True):
        return self.move_type in self.get_inbound_types(include_receipts)

    @api.model
    def get_outbound_types(self, include_receipts=True):
        return ["in_invoice", "out_refund"] + (
            (include_receipts and ["in_receipt"]) or []
        )

    def is_outbound(self, include_receipts=True):
        return self.move_type in self.get_outbound_types(include_receipts)

    def _get_action_with_base_document_layout_configurator(self, report_action):
        if (
            self.env.is_admin()
            and not self.env.company.external_report_layout_id
            and not self.env.context.get("discard_logo_check")
        ):
            report_action = self.env[
                "ir.actions.report"
            ]._prepare_layout_configurator_action(
                report_action,
                "account.action_base_document_layout_configurator",
            )
            report_action["context"]["default_from_invoice"] = (
                self.move_type == "out_invoice"
            )
        return report_action

    def _prepare_installments_data(self):
        self.check_singleton()
        term_lines = self.line_ids.filtered(lambda l: l.display_type == "payment_term")
        return term_lines._prepare_installments_data()

    def _prepare_early_payment_discount_installment_values(self, epd_installment):
        discount_date = epd_installment[
            "line"
        ].discount_date or fields.Date.context_today(self)
        discount_amount_currency = epd_installment["discount_amount_currency"]
        days_left = max(0, (discount_date - fields.Date.context_today(self)).days)
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
        return {
            "epd_discount_amount_currency": discount_amount_currency,
            "epd_discount_amount": epd_installment["discount_amount"],
            "discount_date": fields.Date.to_string(discount_date),
            "epd_days_left": days_left,
            "epd_line": epd_installment["line"],
            "epd_discount_msg": discount_msg,
        }

    @_debug.perf.timed
    def _prepare_next_installment_values(self, installments):
        not_reconciled = [x for x in installments if not x["reconciled"]]
        overdue = [x for x in not_reconciled if x["type"] == "overdue"]
        epd_installment = next(
            (
                installment
                for installment in installments
                if installment["type"] == "early_payment_discount"
            ),
            {},
        )
        show_installments = len(installments) > 1

        _debug.logic(
            "installments_classified",
            move=self,
            installments=len(installments),
            not_reconciled=len(not_reconciled),
            overdue=len(overdue),
            has_epd=bool(epd_installment),
        )
        if show_installments and overdue:
            return {
                "installment_state": "overdue",
                "amount_due": self.amount_residual,
                "next_amount_to_pay": sum(
                    x["amount_residual_currency_unsigned"] for x in overdue
                ),
                "next_payment_reference": f"{self.name}-{overdue[0]['number']}",
                "next_due_date": overdue[0]["date_maturity"],
                "additional_info": {},
            }
        if show_installments and not_reconciled:
            return {
                "installment_state": "next",
                "amount_due": self.amount_residual,
                "next_amount_to_pay": not_reconciled[0][
                    "amount_residual_currency_unsigned"
                ],
                "next_payment_reference": f"{self.name}-{not_reconciled[0]['number']}",
                "next_due_date": not_reconciled[0]["date_maturity"],
                "additional_info": {},
            }
        if epd_installment:
            return {
                "installment_state": "epd",
                "amount_due": epd_installment["amount_residual_currency_unsigned"],
                "next_amount_to_pay": self.amount_residual,
                "next_payment_reference": self.name,
                "next_due_date": epd_installment["date_maturity"],
                "additional_info": self._prepare_early_payment_discount_installment_values(
                    epd_installment
                ),
            }
        return {
            "installment_state": None,
            "amount_due": self.amount_residual,
            "next_amount_to_pay": self.amount_residual,
            "next_payment_reference": self.name,
            "next_due_date": self.invoice_date_due,
            "additional_info": {},
        }

    @_debug.perf.timed
    def _prepare_invoice_next_payment_values(self, custom_amount=None):
        self.check_singleton()
        term_lines = self.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        if not term_lines:
            _debug.logic("next_payment_skipped", move=self, reason="no_term_lines")
            return {}
        installments = term_lines._prepare_installments_data()
        not_reconciled_installments = [x for x in installments if not x["reconciled"]]
        next_values = self._prepare_next_installment_values(installments)

        if custom_amount is not None:
            is_custom_amount_same_as_next_amount = self.currency_id.is_zero(
                custom_amount - next_values["next_amount_to_pay"]
            )
            is_custom_amount_same_as_epd_discounted_amount = next_values[
                "installment_state"
            ] == "epd" and self.currency_id.is_zero(
                custom_amount - next_values["amount_due"]
            )
            if (
                not is_custom_amount_same_as_next_amount
                and not is_custom_amount_same_as_epd_discounted_amount
            ):
                _debug.logic(
                    "custom_amount_overrides_next",
                    move=self,
                    previous_state=next_values["installment_state"],
                )
                next_values |= {
                    "installment_state": "next",
                    "next_amount_to_pay": custom_amount,
                    "next_payment_reference": self.name,
                    "next_due_date": installments[0]["date_maturity"],
                }

        additional_info = next_values.pop("additional_info")
        return {
            "payment_state": self.payment_state,
            **next_values,
            "amount_paid": self.amount_total - self.amount_residual,
            "due_date": self.invoice_date_due,
            "not_reconciled_installments": not_reconciled_installments,
            "is_last_installment": len(not_reconciled_installments) == 1,
            **additional_info,
        }

    def _prepare_invoice_portal_extra_values(self, custom_amount=None):
        self.check_singleton()
        return {
            "invoice": self,
            "currency": self.currency_id,
            **self._prepare_invoice_next_payment_values(custom_amount=custom_amount),
        }

    def _get_accounting_date(self, invoice_date, has_tax, lock_dates=None):
        self.check_singleton()
        lock_dates = lock_dates or self._get_violated_lock_dates(invoice_date, has_tax)
        today = fields.Date.context_today(self)
        highest_name = self.highest_name or self._get_last_sequence(relaxed=True)
        number_reset = self._deduce_sequence_number_reset(highest_name)
        _debug.logic(
            "accounting_date_inputs",
            move=self,
            invoice_date=invoice_date,
            lock_dates=lock_dates,
            number_reset=number_reset,
            highest_name=highest_name,
        )
        if lock_dates:
            invoice_date = lock_dates[-1][0] + timedelta(days=1)
        if self.is_sale_document(include_receipts=True):
            if lock_dates:
                if not highest_name or number_reset in ("month", "year_range_month"):
                    return min(today, date_utils.get_month(invoice_date)[1])
                elif number_reset == "year":
                    return min(today, date_utils.end_of(invoice_date, "year"))
        elif not highest_name or number_reset in ("month", "year_range_month"):
            if (today.year, today.month) > (invoice_date.year, invoice_date.month):
                return date_utils.get_month(invoice_date)[1]
            else:
                return max(invoice_date, today)
        elif number_reset == "year":
            if today.year > invoice_date.year:
                return date(invoice_date.year, 12, 31)
            else:
                return max(invoice_date, today)
        return invoice_date

    def _get_violated_lock_dates(self, invoice_date, has_tax):
        self.check_singleton()
        return self.company_id._get_violated_lock_dates(
            invoice_date, has_tax, self.journal_id
        )

    def _get_lock_date_message(self, invoice_date, has_tax):
        lock_dates = self._get_violated_lock_dates(invoice_date, has_tax)
        if lock_dates:
            invoice_date = self._get_accounting_date(
                invoice_date, has_tax, lock_dates=lock_dates
            )
            return _(
                "The date is being set prior to: %(lock_date_info)s. "
                "The Journal Entry will be accounted on %(invoice_date)s upon posting.",
                lock_date_info=self.env["res.company"]._format_lock_dates(lock_dates),
                invoice_date=format_date(self.env, invoice_date),
            )
        return False

    @api.model
    @_debug.perf.timed
    def _move_dict_to_preview_vals(self, move_vals, currency_id=None):
        preview_vals = {
            "group_name": "%s, %s"
            % (
                format_date(self.env, move_vals["date"]) or _("[Not set]"),
                move_vals["ref"],
            ),
            "items_vals": [
                (command, line_id, dict(line_vals))
                for command, line_id, line_vals in move_vals["line_ids"]
            ],
        }
        for line in preview_vals["items_vals"]:
            if "partner_id" in line[2]:
                line[2]["partner_id"] = (
                    self.env["res.partner"]
                    .browse(line[2]["partner_id"])
                    .sudo()
                    .display_name
                )
            line[2]["account_id"] = self.env["account.account"].browse(
                line[2]["account_id"]
            ).display_name or _("Destination Account")
            line[2]["debit"] = (
                currency_id
                and formatLang(self.env, line[2]["debit"], currency_obj=currency_id)
            ) or line[2]["debit"]
            line[2]["credit"] = (
                currency_id
                and formatLang(self.env, line[2]["credit"], currency_obj=currency_id)
            ) or line[2]["credit"]
        _debug.pipeline(
            "preview_items_built",
            items=len(preview_vals["items_vals"]),
            formatted=bool(currency_id),
        )
        return preview_vals

    def _get_qr_code_method(self):
        self.check_singleton()
        if self.qr_code_method:
            error_msg = self.partner_bank_id._get_error_messages_for_qr(
                self.qr_code_method, self.partner_id, self.currency_id
            )
            if error_msg:
                _debug.logic(
                    "qr_method_rejected", move=self, method=self.qr_code_method
                )
                raise UserError(error_msg)
            return self.qr_code_method
        for candidate_method, _candidate_name in self.env[
            "res.partner.bank"
        ].get_available_qr_methods_in_sequence():
            if not self.partner_bank_id._get_error_messages_for_qr(
                candidate_method, self.partner_id, self.currency_id
            ):
                _debug.logic(
                    "qr_method_auto_selected", move=self, method=candidate_method
                )
                return candidate_method
        _debug.logic("qr_method_none_available", move=self)
        return False

    def _update_qr_code_method(self, qr_code_method):
        self.check_singleton()
        if qr_code_method == self.qr_code_method or not self.has_access("write"):
            return
        self.qr_code_method = qr_code_method

    @_debug.perf.timed
    def _generate_qr_code(self, silent_errors=False):
        self.check_singleton()

        if not self.display_qr_code:
            _debug.logic("qr_code_skipped", move=self, reason="not_displayed")
            return None

        qr_code_method = self._get_qr_code_method()
        if not qr_code_method:
            _debug.logic("qr_code_no_method", move=self)
            return None

        unstruct_ref = self.payment_reference or self.name
        rslt = self.partner_bank_id.prepare_qr_code_base64(
            self.amount_residual,
            unstruct_ref,
            self.payment_reference,
            self.currency_id,
            self.partner_id,
            qr_code_method,
            silent_errors=silent_errors,
        )

        self._update_qr_code_method(qr_code_method)

        return rslt

    @_debug.perf.timed
    def _generate_portal_payment_qr(self):
        self.check_singleton()

    def _get_portal_payment_link(self):
        self.check_singleton()

    @_debug.perf.timed
    def _generate_and_send(
        self, force_synchronous=True, allow_fallback_pdf=True, **custom_settings
    ):
        if not self:
            return None
        _debug.logic(
            "send_wizard_chosen",
            moves=self,
            batch=len(self) != 1,
            force_synchronous=force_synchronous,
        )
        if len(self) == 1:
            wizard = (
                self.env["account.move.send.wizard"]
                .with_context(
                    active_model="account.move",
                    active_ids=self.ids,
                )
                .create(custom_settings)
            )
            wizard.action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
        else:
            wizard = (
                self.env["account.move.send.batch.wizard"]
                .with_context(
                    active_model="account.move",
                    active_ids=self.ids,
                )
                .create({})
            )
            wizard.action_send_and_print(force_synchronous=force_synchronous)
        return wizard

    def _get_invoice_pdf_proforma(self):
        self.check_singleton()
        filename = self._get_invoice_proforma_pdf_report_filename()
        content, report_type = self.env["ir.actions.report"]._pre_render_qweb_pdf(
            "account.account_invoices", self.ids, data={"proforma": True}
        )
        content_by_id = self.env["ir.actions.report"]._get_splitted_report(
            "account.account_invoices", content, report_type
        )
        return {
            "filename": filename,
            "filetype": "pdf",
            "content": content_by_id[self.id],
        }

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        self.check_singleton()
        if filetype == "pdf":
            if invoice_pdf := self.invoice_pdf_report_id:
                return {
                    "filename": invoice_pdf.name,
                    "filetype": invoice_pdf.mimetype,
                    "content": invoice_pdf.raw,
                }
            elif allow_fallback:
                return self._get_invoice_pdf_proforma()
        return None

    def _get_invoice_legal_documents_all(self, allow_fallback=False):
        self.check_singleton()
        if self.invoice_pdf_report_id:
            attachments = self.env[
                "mixin.account.move.send"
            ]._get_invoice_extra_attachments(self)
            _debug.logic(
                "legal_documents_from_attachments", move=self, attachments=attachments
            )
            return [
                {
                    "filename": attachment.name,
                    "filetype": attachment.mimetype,
                    "content": attachment.raw,
                }
                for attachment in attachments
            ]
        elif allow_fallback:
            _debug.logic("legal_documents_proforma_fallback", move=self)
            return [self._get_invoice_pdf_proforma()]
        return None

    @_debug.perf.timed
    def _get_report_filename(self, file_name, extension):
        self.check_singleton()
        stem = file_name or self._get_move_display_name()
        return f"{stem.replace('/', '_')}.{extension}"

    def _get_invoice_report_filename(self, extension="pdf", report=None):
        self.check_singleton()
        if not report:
            report = self.partner_id.invoice_template_pdf_report_id or self.env.ref(
                "account.account_invoices"
            )
        if report.print_report_name and isinstance(report.print_report_name, str):
            file_name = safe_eval(report.print_report_name, {"object": self})
        else:
            file_name = self.name
        return self._get_report_filename(file_name, extension)

    def _get_invoice_mail_template_dynamic_report_filename(
        self, report, extension="pdf"
    ):
        self.check_singleton()
        if not report.print_report_name:
            return False
        file_name = safe_eval(report.print_report_name, {"object": self})
        return self._get_report_filename(file_name, extension)

    def _get_invoice_proforma_pdf_report_filename(self):
        self.check_singleton()
        stem = self._get_move_display_name().replace(" ", "_")
        return self._get_report_filename(f"{stem}_proforma", "pdf")

    def _get_discount_allocation_account(self):
        if (
            self.is_sale_document(include_receipts=True)
            and self.company_id.account_discount_expense_allocation_id
        ):
            return self.company_id.account_discount_expense_allocation_id
        if (
            self.is_purchase_document(include_receipts=True)
            and self.company_id.account_discount_income_allocation_id
        ):
            return self.company_id.account_discount_income_allocation_id
        return None

    def _get_available_invoice_template_pdf_report_ids(self):
        # asked once per partner created and once per journal read, and
        # answered from the report configuration alone for a model-level
        # call: memoized per transaction until a report changes
        if self:
            return self._available_invoice_template_pdf_report_ids()
        per_env = INVOICE_TEMPLATE_REPORTS(self.env)
        key = (self.env.company.id, self.env.uid, self.env.su)
        if key not in per_env:
            per_env[key] = self._available_invoice_template_pdf_report_ids().ids
        return self.env["ir.actions.report"].browse(per_env[key])

    def _available_invoice_template_pdf_report_ids(self):
        moves = self

        for move_type in ["out_invoice", "out_refund", "out_receipt"]:
            moves += self.new({"move_type": move_type})

        available_reports = moves._get_available_action_reports()

        if not available_reports:
            raise UserError(_("There is no template that applies to invoices."))

        return available_reports

    def _is_user_able_to_review(self):
        return True

    @api.model
    def _field_will_change(self, record, vals, field_name):
        if field_name not in vals:
            return False
        field = record._fields[field_name]
        if field.type == "many2one":
            return record[field_name].id != vals[field_name]
        if field.type == "many2many":
            current_ids = set(record[field_name].ids)
            after_write_ids = set(
                record.new({field_name: vals[field_name]})[field_name].ids
            )
            return current_ids != after_write_ids
        if field.type == "one2many":
            return True
        if field.type == "monetary" and record[field.get_currency_field(record)]:
            return not record[field.get_currency_field(record)].is_zero(
                record[field_name] - vals[field_name]
            )
        if field.type == "float":
            record_value = field.convert_to_cache(record[field_name], record)
            to_write_value = field.convert_to_cache(vals[field_name], record)
            return record_value != to_write_value
        return record[field_name] != vals[field_name]

    @api.model
    def _cleanup_write_orm_values(self, record, vals):
        cleaned_vals = dict(vals)
        for field_name in vals:
            if not self._field_will_change(record, vals, field_name):
                del cleaned_vals[field_name]
        return cleaned_vals

    @contextmanager
    def _disable_recursion(self, key, default=None, target=True):
        stack = self.env.cr.cache.setdefault(
            DISABLE_RECURSION_STACK_CACHE_KEY, StackMap()
        )
        try:
            current_val = stack[key]
        except KeyError:
            current_val = self.env.context.get(key, default)

        disabled = current_val == target
        stack.push_map({key: target})
        try:
            yield disabled
        finally:
            stack.pop_map()

    def _conditional_add_to_compute(self, fname, condition):
        field = self._fields[fname]
        to_reset = self.filtered(
            lambda move: (
                condition(move)
                and not self.env.is_protected(field, move._origin)
                and (move._origin or not move[fname])
            )
        )
        to_reset.invalidate_recordset([fname])
        self.env.add_to_compute(field, to_reset)

    def _action_invoice_ready_to_be_sent(self):
        pass

    def _is_ready_to_be_sent(self):
        self.check_singleton()
        return True

    def _can_force_cancel(self):
        self.check_singleton()
        return False

    @contextmanager
    def _send_only_when_ready(self):
        moves_not_ready = self.filtered(lambda x: not x._is_ready_to_be_sent())

        try:
            yield
        finally:
            moves_now_ready = moves_not_ready.filtered(
                lambda x: x._is_ready_to_be_sent()
            )
            if moves_now_ready:
                moves_now_ready._action_invoice_ready_to_be_sent()

    def _invoice_paid_hook(self):
        pass

    @_debug.perf.timed
    def _get_lines_onchange_currency(self):
        return self.line_ids

    @api.model
    def _get_invoice_in_payment_state(self):
        return "paid"

    @api.model
    def _has_full_accounting(self):
        return self._get_invoice_in_payment_state() == "in_payment"

    def _get_name_invoice_report(self):
        self.check_singleton()
        return "account.report_invoice_document"

    def _is_downpayment(self):
        return False

    def _refunds_origin_required(self):
        return False

    def _set_reversed_entry(self, credit_notes):
        for credit_note in credit_notes:
            if credit_note.move_type != "out_refund":
                continue

            credit_note_sale_lines = credit_note.invoice_line_ids.sale_line_ids
            original_invoice = self.filtered(
                lambda inv, sale_lines=credit_note_sale_lines: (
                    inv.move_type == "out_invoice"
                    and sale_lines
                    and set(sale_lines.ids)
                    <= set(inv.invoice_line_ids.sale_line_ids.ids)
                )
            )
            if (
                len(original_invoice) == 1
                and original_invoice._refunds_origin_required()
            ):
                _debug.logic(
                    "reversed_entry_from_sale_lines",
                    move=credit_note,
                    reversed_entry=original_invoice,
                )
                credit_note.reversed_entry_id = original_invoice.id

    @api.model
    def get_invoice_localisation_fields_required_to_invoice(self, country_id):
        return []

    def get_extra_print_items(self):
        if moves_to_export := self.filtered(lambda m: m._has_move_zip_export_docs()):
            return [
                {
                    "key": "download_all",
                    "description": _("Export ZIP"),
                    **moves_to_export.action_move_download_all(),
                },
            ]
        return []

    def _has_move_zip_export_docs(self):
        self.check_singleton()
        if self.state != "posted":
            return False
        if self.is_purchase_document(include_receipts=True):
            return bool(self.message_main_attachment_id)
        return bool(self.invoice_pdf_report_id)

    def _get_move_zip_export_docs(self):
        self.check_singleton()

        if self.state != "posted":
            _debug.logic("zip_export_skipped", move=self, reason="not_posted")
            return []

        if self.is_purchase_document(include_receipts=True):
            attachment = self.message_main_attachment_id.sudo()
            _debug.logic(
                "zip_export_purchase_attachment", move=self, attachment=attachment
            )
            return (
                [
                    {
                        "filename": attachment.name,
                        "filetype": attachment.mimetype,
                        "content": attachment.raw,
                    }
                ]
                if attachment
                else []
            )

        return self._get_invoice_legal_documents_all()

    def _get_move_lines_to_report(self):
        def show_line(line):
            ancestors = line.parent_id | line.parent_id.parent_id
            return line.display_type == "line_section" or not (
                any(ancestors.mapped("collapse_composition"))
                or any(ancestors.mapped("collapse_prices"))
            )

        return self.invoice_line_ids.filtered(show_line).sorted("sequence")

    @staticmethod
    def _can_commit():
        return not modules.module.current_test

    _IMPORT_TEMPLATES = {
        "entry": (
            lambda: _("Import Template for Misc. Operations"),
            "misc_operations_import_template",
        ),
        "out_invoice": (
            lambda: _("Import Template for Invoices"),
            "customer_invoices_credit_notes_import_template",
        ),
        "out_refund": (
            lambda: _("Import Template for Credit Notes"),
            "customer_invoices_credit_notes_import_template",
        ),
        "in_invoice": (
            lambda: _("Import Template for Bills"),
            "vendor_bills_refunds_import_template",
        ),
        "in_refund": (
            lambda: _("Import Template for Refunds"),
            "vendor_bills_refunds_import_template",
        ),
    }

    @api.model
    def get_import_templates(self):
        label, stem = self._IMPORT_TEMPLATES.get(
            self.env.context.get("default_move_type"), (None, None)
        )
        if not stem:
            return []
        return [{"label": label(), "template": f"/account/static/xls/{stem}.xlsx"}]

    def _get_database_scoped_uuid(self):
        self.check_singleton()
        dbuuid = self.env["ir.config_parameter"].sudo().get_param("database.uuid")
        return str(uuid.uuid5(namespace=uuid.UUID(dbuuid), name=str(self.id)))
