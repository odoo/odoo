import logging
import re
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    SQL,
    OrderedSet,
    Query,
    float_compare,
    frozendict,
    groupby,
)

from odoo.addons.account.models.account_move import MAX_HASH_VERSION
from odoo.addons.account.tools.display_types import (
    NON_ACCOUNTABLE_DISPLAY_TYPES,
)
from odoo.addons.account.tools.reconciliation import (
    pick_reconciliation_currency,
    prepare_partial_amounts,
)
from odoo.addons.web.controllers.utils import clean_action

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)

_NON_ACCOUNTABLE_SQL_TUPLE = "({})".format(
    ", ".join(f"'{display_type}'" for display_type in NON_ACCOUNTABLE_DISPLAY_TYPES)
)


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["mixin.analytic", "mixin.default.read.fields"]
    _description = "Journal Item"
    _order = "date desc, move_name desc, id"
    _check_company_auto = True
    _rec_names_search = ["name", "move_id", "product_id"]

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
        check_company=True,
        bypass_search_access=True,
    )
    journal_id = fields.Many2one(  # noqa: E8529  partial index (journal_id) WHERE amount_residual < 0: the open-items scan
        related="move_id.journal_id",
        precompute=True,
        store=True,
        index=True,
        copy=False,
    )

    journal_group_id = fields.Many2one(
        comodel_name="account.journal.group",
        string="Ledger",
        search="_search_journal_group_id",
        store=False,
    )

    company_id = fields.Many2one(  # noqa: E8529  measured: a 2 M-line ledger aggregates 3-4x slower filtering company and state through account_move
        related="move_id.company_id",
        precompute=True,
        store=True,
        index=True,
        readonly=True,
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    move_name = fields.Char(  # noqa: E8529  composite index (date, move_name, id): the ledger's sort key
        related="move_id.name",
        string="Number",
        store=True,
        index="btree",
    )
    parent_state = fields.Selection(  # noqa: E8529  measured: a 2 M-line ledger aggregates 3-4x slower filtering state through account_move (88 -> 326 ms, 250 -> 679 ms)
        related="move_id.state",
        store=True,
    )
    date = fields.Date(  # noqa: E8529  composite indexes (account_id, date) and (date, move_name, id)
        related="move_id.date",
        store=True,
        copy=False,
        aggregator="min",
    )
    invoice_date = fields.Date(
        related="move_id.invoice_date",
        copy=False,
        aggregator="min",
    )
    ref = fields.Char(  # noqa: E8529  composite index (partner_id, ref): payment matching
        related="move_id.ref",
        store=True,
        index="trigram",
        copy=False,
    )
    is_storno = fields.Boolean(
        string="Company Storno Accounting",
        compute="_compute_is_storno",
        precompute=True,
        store=True,
        readonly=False,
        help="Utility field to express whether the journal item is subject to storno accounting",
    )
    sequence = fields.Integer(
        compute="_compute_sequence",
        precompute=True,
        store=True,
        readonly=False,
    )
    move_type = fields.Selection(
        related="move_id.move_type",
    )

    account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_account_id",
        inverse="_inverse_account_id",
        precompute=True,
        store=True,
        index=False,
        readonly=False,
        domain="[('account_type', '!=', 'off_balance')]",
        ondelete="restrict",
        check_company=True,
        bypass_search_access=True,
        tracking=True,
    )
    account_name = fields.Char(related="account_id.name")
    account_code = fields.Char(related="account_id.code")
    account_lookup_id = fields.Many2one(
        comodel_name="account.account",
        search="_search_account_lookup_id",
        store=False,
    )
    name = fields.Char(
        string="Label",
        compute="_compute_name",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
    )
    translated_product_name = fields.Text(compute="_compute_translated_product_name")
    debit = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_debit_credit",
        inverse="_inverse_debit",
        precompute=True,
        store=True,
    )
    credit = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_debit_credit",
        inverse="_inverse_credit",
        precompute=True,
        store=True,
    )
    balance = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_balance",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
    )
    cumulated_balance = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_cumulated_balance",
        exportable=False,
        help="Cumulated balance depending on the domain and the order chosen in the view.",
    )
    currency_rate = fields.Float(
        compute="_compute_currency_rate",
        help="Currency rate from company currency to document currency.",
    )
    amount_currency = fields.Monetary(
        string="Amount in Currency",
        compute="_compute_amount_currency",
        inverse="_inverse_amount_currency",
        precompute=True,
        store=True,
        readonly=False,
        help="The amount expressed in an optional other currency if it is a multi-currency entry.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    is_same_currency = fields.Boolean(compute="_compute_is_same_currency")
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_partner_id",
        inverse="_inverse_partner_id",
        precompute=True,
        store=True,
        readonly=False,
        ondelete="restrict",
    )
    is_imported = fields.Boolean()

    reconcile_model_id = fields.Many2one(
        comodel_name="account.reconcile.model",
        string="Reconciliation Model",
        copy=False,
        readonly=True,
        check_company=True,
    )
    payment_id = fields.Many2one(  # noqa: E8529  move_id.origin_payment_id is a non-stored compute over account_payment.move_id: no column to join
        comodel_name="account.payment",
        related="move_id.origin_payment_id",
        string="Originator Payment",
        store=True,
        index="btree_not_null",
        bypass_search_access=True,
        help="The payment that created this entry",
    )
    statement_line_id = fields.Many2one(
        comodel_name="account.bank.statement.line",
        related="move_id.statement_line_id",
        string="Originator Statement Line",
        bypass_search_access=True,
        help="The statement line that created this entry",
    )
    statement_id = fields.Many2one(
        related="statement_line_id.statement_id",
        copy=False,
        bypass_search_access=True,
        help="The bank statement used for bank reconciliation",
    )
    commercial_partner_country = fields.Many2one(
        related="move_id.commercial_partner_id.country_id",
        string="Commercial Partner Country",
    )

    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes",
        compute="_compute_tax_ids",
        precompute=True,
        store=True,
        readonly=False,
        context={"active_test": False, "hide_original_tax_ids": True},
        check_company=True,
        tracking=True,
    )
    group_tax_id = fields.Many2one(
        comodel_name="account.tax",
        string="Originator Group of Taxes",
        index="btree_not_null",
        check_company=True,
    )
    tax_line_id = fields.Many2one(
        comodel_name="account.tax",
        related="tax_repartition_line_id.tax_id",
        string="Originator Tax",
        help="Indicates that this journal item is a tax line",
    )
    tax_group_id = fields.Many2one(
        related="tax_line_id.tax_group_id",
        string="Originator tax group",
    )
    tax_base_amount = fields.Monetary(
        string="Base Amount",
        currency_field="company_currency_id",
        readonly=True,
    )
    tax_repartition_line_id = fields.Many2one(
        comodel_name="account.tax.repartition.line",
        string="Originator Tax Distribution Line",
        readonly=True,
        ondelete="restrict",
        check_company=True,
        help="Tax distribution line that caused the creation of this move line, if any",
    )
    tax_tag_ids = fields.Many2many(
        comodel_name="account.account.tag",
        string="Tags",
        context={"active_test": False},
        ondelete="restrict",
        tracking=True,
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.",
    )
    extra_tax_data = fields.Json()

    amount_residual = fields.Monetary(
        string="Residual Amount",
        currency_field="company_currency_id",
        compute="_compute_reconciliation",
        store=True,
        help="The residual amount on a journal item expressed in the company currency.",
    )
    amount_residual_currency = fields.Monetary(
        string="Residual Amount in Currency",
        compute="_compute_reconciliation",
        store=True,
        help="The residual amount on a journal item expressed in its currency (possibly not the "
        "company currency).",
    )
    reconciled = fields.Boolean(
        compute="_compute_reconciliation",
        store=True,
    )
    full_reconcile_id = fields.Many2one(
        comodel_name="account.full.reconcile",
        string="Matching",
        index="btree_not_null",
        copy=False,
        readonly=True,
    )
    matched_debit_ids = fields.One2many(
        comodel_name="account.partial.reconcile",
        inverse_name="credit_move_id",
        string="Matched Debits",
        readonly=True,
        help="Debit journal items that are matched with this journal item.",
    )
    matched_credit_ids = fields.One2many(
        comodel_name="account.partial.reconcile",
        inverse_name="debit_move_id",
        string="Matched Credits",
        readonly=True,
        help="Credit journal items that are matched with this journal item.",
    )
    reconciled_lines_ids = fields.Many2many(
        comodel_name="account.move.line",
        compute="_compute_reconciled_lines_ids",
        inverse="_inverse_reconciled_lines_ids",
    )
    reconciled_lines_excluding_exchange_diff_ids = fields.Many2many(
        comodel_name="account.move.line",
        compute="_compute_reconciled_lines_excluding_exchange_diff_ids",
        exportable=False,
    )

    matching_number = fields.Char(
        string="Matching #",
        index="btree",
        copy=False,
        help="Matching number for this line, 'P' if it is only partially reconcile, or the name of "
        "the full reconcile if it exists.",
    )
    is_account_reconcile = fields.Boolean(
        related="account_id.reconcile",
        string="Account Reconcile",
    )

    account_type = fields.Selection(
        related="account_id.account_type",
        string="Internal Type",
    )
    account_internal_group = fields.Selection(related="account_id.internal_group")
    account_root_id = fields.Many2one(
        related="account_id.root_id",
        string="Account Root",
        depends_context="company",
    )
    product_category_id = fields.Many2one(related="product_id.product_tmpl_id.categ_id")

    display_type = fields.Selection(
        selection=[
            ("product", "Product"),
            ("cogs", "Cost of Goods Sold"),
            ("tax", "Tax"),
            ("discount", "Discount"),
            ("rounding", "Rounding"),
            ("payment_term", "Payment Term"),
            ("line_section", "Section"),
            ("line_subsection", "Subsection"),
            ("line_note", "Note"),
            ("epd", "Early Payment Discount"),
            ("non_deductible_product_total", "Non Deductible Products Total"),
            ("non_deductible_product", "Non Deductible Products"),
            ("non_deductible_tax", "Non Deductible Tax"),
            ("balancing", "Automatic Balancing Line"),
        ],
        compute="_compute_display_type",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    collapse_composition = fields.Boolean(
        string="Hide Composition",
        help="If checked, the lines below this section will not be displayed in reports and portal.",
    )
    collapse_prices = fields.Boolean(
        string="Hide Prices",
        help="If checked, the prices of the lines below this section will not be displayed in reports and portal.",
    )
    parent_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Parent Section Line",
        compute="_compute_parent_id",
        compute_sudo=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        inverse="_inverse_product_id",
        index=True,
        ondelete="restrict",
        check_company=True,
    )
    allowed_uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        compute="_compute_allowed_uom_ids",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_product_uom_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('id', 'in', allowed_uom_ids)]",
        ondelete="restrict",
    )
    quantity = fields.Float(
        digits="Product Unit",
        compute="_compute_quantity",
        precompute=True,
        store=True,
        readonly=False,
        help="The optional quantity expressed by this line, eg: number of product sold. "
        "The quantity is not a legal requirement but is very useful for some reports.",
    )
    date_maturity = fields.Date(
        string="Due Date",
        index=True,
        tracking=True,
        help="This field is used for payable and receivable journal entries. "
        "You can put the limit date for the payment of this line.",
    )

    price_unit = fields.Float(
        string="Unit Price",
        min_display_digits="Product Price",
        compute="_compute_price_unit",
        precompute=True,
        store=True,
        readonly=False,
    )
    price_subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    price_total = fields.Monetary(
        string="Total",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        default=0.0,
    )
    tax_calculation_rounding_method = fields.Selection(
        related="company_id.tax_calculation_rounding_method",
        string="Tax calculation rounding method",
        readonly=True,
    )
    deductible_amount = fields.Float(
        string="Deductibility",
        default=100,
    )

    term_key = fields.Binary(
        compute="_compute_term_key",
        exportable=False,
    )
    epd_key = fields.Binary(
        compute="_compute_epd_key",
        exportable=False,
    )
    epd_needed = fields.Binary(
        compute="_compute_epd",
        exportable=False,
    )
    epd_dirty = fields.Boolean(
        compute="_compute_epd",
        exportable=False,
    )
    discount_allocation_key = fields.Binary(
        compute="_compute_discount_allocation_key",
        exportable=False,
    )
    discount_allocation_needed = fields.Binary(
        compute="_compute_discount_allocation",
        exportable=False,
    )
    discount_allocation_dirty = fields.Boolean(
        compute="_compute_discount_allocation",
        exportable=False,
    )

    analytic_line_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="move_line_id",
        string="Analytic lines",
    )
    analytic_distribution = fields.Json(inverse="_inverse_analytic_distribution")
    has_invalid_analytics = fields.Boolean(compute="_compute_has_invalid_analytics")

    discount_date = fields.Date(
        store=True,
        readonly=True,
        help="Last date at which the discounted amount must be paid in order for the Early Payment Discount to be granted",
    )
    discount_amount_currency = fields.Monetary(
        string="Discount amount in Currency",
        currency_field="currency_id",
        store=True,
    )
    discount_balance = fields.Monetary(
        currency_field="company_currency_id",
        store=True,
    )

    payment_date = fields.Date(
        string="Next Payment Date",
        compute="_compute_payment_date",
        search="_search_payment_date",
    )

    is_refund = fields.Boolean(compute="_compute_is_refund")

    no_followup = fields.Boolean(
        string="No Follow-Up",
        compute="_compute_no_followup",
        inverse="_inverse_no_followup",
        store=True,
        readonly=False,
        help="Exclude this journal item from follow-up reports.",
    )

    _check_credit_debit = models.Constraint(
        f"CHECK(display_type IN {_NON_ACCOUNTABLE_SQL_TUPLE} OR credit * debit=0)",
        "Wrong credit or debit value in accounting entry!",
    )
    _check_amount_currency_balance_sign = models.Constraint(
        f"""CHECK(
            display_type IN {_NON_ACCOUNTABLE_SQL_TUPLE}
            OR (balance <= 0 AND amount_currency <= 0)
            OR (balance >= 0 AND amount_currency >= 0)
        )""",
        "The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited. If the currency is the same as the one from the company, this amount must strictly be equal to the balance.",
    )
    _check_accountable_required_fields = models.Constraint(
        f"CHECK(display_type IN {_NON_ACCOUNTABLE_SQL_TUPLE} OR account_id IS NOT NULL)",
        "Missing required account on accountable line.",
    )
    _check_non_accountable_fields_null = models.Constraint(
        f"CHECK(display_type NOT IN {_NON_ACCOUNTABLE_SQL_TUPLE} OR (amount_currency = 0 AND debit = 0 AND credit = 0 AND account_id IS NULL))",
        "Forbidden balance or account on non-accountable line",
    )

    _partner_id_ref_idx = models.Index("(partner_id, ref)")
    _date_name_id_idx = models.Index("(date desc, move_name desc, id)")
    _unreconciled_index = models.Index(
        "(account_id, partner_id) WHERE reconciled IS NOT TRUE"
    )
    _journal_id_neg_amnt_residual_idx = models.Index(
        "(journal_id) WHERE amount_residual < 0"
    )
    _account_id_date_idx = models.Index("(account_id, date)")

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if (
            res["views"].get("list")
            and self.env["ir.ui.view"].sudo().browse(res["views"]["list"]["id"]).name
            == "account.move.line.payment.list"
        ):
            if toolbar := res["views"]["list"].get("toolbar"):
                toolbar["action"] = []
        return res

    @api.depends("move_id")
    @_debug.perf.timed
    def _compute_display_type(self):
        for line in self.filtered(lambda l: not l.display_type):
            account_set = self.env.cache.contains(line, line._fields["account_id"])
            tax_set = self.env.cache.contains(line, line._fields["tax_line_id"])
            line.display_type = (
                (
                    "tax"
                    if tax_set and line.tax_line_id
                    else "payment_term"
                    if account_set
                    and line.account_id.account_type
                    in ["asset_receivable", "liability_payable"]
                    else "product"
                )
                if line.move_id.is_invoice()
                else "product"
            )

    def _compute_partner_id(self):
        for line in self:
            line.partner_id = line.move_id.partner_id.commercial_partner_id

    @api.depends("move_id.currency_id", "display_type", "company_id")
    def _compute_currency_id(self):
        for line in self:
            if line.display_type == "cogs":
                line.currency_id = line.company_currency_id
            elif line.move_id.is_invoice(include_receipts=True):
                line.currency_id = line.move_id.currency_id
            else:
                line.currency_id = line.currency_id or line.company_id.currency_id

    @api.depends(
        "product_id",
        "move_id.ref",
        "move_id.payment_reference",
        "move_id.partner_id",
    )
    @_debug.perf.timed
    def _compute_name(self):
        def get_name(line):
            values = []
            if line.move_id.partner_id.lang:
                product = line.product_id.with_context(
                    lang=line.move_id.partner_id.lang
                )
            elif line.partner_id.lang:
                product = line.product_id.with_context(lang=line.partner_id.lang)
            else:
                product = line.product_id
            if not product:
                return False

            if line.journal_id.type == "sale":
                values.append(product.display_name)
                if product.description_sale:
                    values.append(product.description_sale)
            elif line.journal_id.type == "purchase":
                values.append(product.display_name)
                if product.description_purchase:
                    values.append(product.description_purchase)
            return "\n".join(values) if values else False

        term_by_move = (
            (self.move_id.line_ids | self)
            .filtered(lambda l: l.display_type == "payment_term")
            .sorted(lambda l: l.date_maturity or date.max)
            .grouped("move_id")
        )
        position_in_move = {
            (move, line_id): position
            for move, term_lines in term_by_move.items()
            for position, line_id in enumerate(term_lines._ids)
        }
        if _debug.logic.enabled:
            _debug.logic(
                "name_compute_scope",
                lines=self,
                term_moves=len(term_by_move),
                hashed_skipped=self.filtered(lambda l: l.move_id.inalterable_hash),
            )
        for line in self.filtered(lambda l: not l.move_id.inalterable_hash):
            if line.display_type == "payment_term":
                term_lines = term_by_move.get(
                    line.move_id, self.env["account.move.line"]
                )
                n_terms = len(line.move_id.invoice_payment_term_id.line_ids)
                if (
                    line.move_id.payment_reference
                    and line.move_id.ref
                    and line.move_id.payment_reference != line.move_id.ref
                ):
                    name = f"{line.move_id.ref} - {line.move_id.payment_reference}"
                elif line.move_id.payment_reference:
                    name = line.move_id.payment_reference
                elif (
                    line.move_id.move_type in ["in_invoice", "in_refund"]
                    and line.move_id.ref
                ):
                    name = line.move_id.ref
                else:
                    name = False

                if n_terms > 1:
                    index = position_in_move.get(
                        (line.move_id, line.id), len(term_lines)
                    )
                    name = _(
                        "%(name)s installment #%(number)s",
                        name=name or "",
                        number=index + 1,
                    ).lstrip()
                if name:
                    line.name = name
            if (
                not line.product_id
                or line.display_type in NON_ACCOUNTABLE_DISPLAY_TYPES
            ):
                continue

            if (
                not line.name
                or line._origin.name == get_name(line._origin)
                or line.product_id != line._origin.product_id
            ):
                line.name = get_name(line)

    @api.depends("product_id", "partner_id", "partner_id.lang")
    def _compute_translated_product_name(self):
        for line in self:
            line.translated_product_name = line.product_id.with_context(
                lang=line.partner_id.lang,
            ).display_name

    def _compute_account_id(self):
        self._update_account_id_on_term_lines()
        self._update_account_id_on_product_lines()
        self._update_account_id_fallback()

    @_debug.perf.timed
    def _update_account_id_on_term_lines(self):
        term_lines = self.filtered(lambda line: line.display_type == "payment_term")
        if not term_lines:
            _debug.logic("term_accounts_skipped", lines=self, reason="no_term_lines")
            return
        default_account_ids = term_lines._get_term_default_accounts()
        for line in term_lines:
            move = line.move_id
            is_receivable = move.is_sale_document(include_receipts=True)
            account_type = "asset_receivable" if is_receivable else "liability_payable"
            property_fname = (
                "property_account_receivable_id"
                if is_receivable
                else "property_account_payable_id"
            )
            scoped_move = move.with_company(move.company_id)
            account_id = (
                default_account_ids.get(("account.move", move.id, None))
                or scoped_move.commercial_partner_id[property_fname].id
                or scoped_move.company_id.partner_id[property_fname].id
                or default_account_ids.get(
                    ("res.company", move.company_id.id, account_type)
                )
            )
            if move.fiscal_position_id:
                account_id = move.fiscal_position_id.map_account(
                    self.env["account.account"].browse(account_id)
                )
            line.account_id = account_id
        _debug.pipeline(
            "term_accounts_assigned",
            lines=term_lines,
            defaults=len(default_account_ids),
        )

    @_debug.perf.timed
    def _get_term_default_accounts(self):
        moves = self.move_id
        result = {}
        # the most recent payment-term line of each move, current lines excluded
        previous_lines = self.env["account.move.line"].search(
            [
                ("move_id", "in", moves.ids),
                ("display_type", "=", "payment_term"),
                ("id", "not in", self.ids),
            ],
            order="move_id, id desc",
        )
        for line in previous_lines:
            result.setdefault(
                ("account.move", line.move_id.id, None), line.account_id.id
            )
        # the lowest active receivable / payable account of each company
        accounts = (
            self.env["account.account"]
            .sudo()
            .search(
                [
                    ("company_ids", "in", moves.company_id.ids),
                    ("account_type", "in", ("asset_receivable", "liability_payable")),
                    ("active", "=", True),
                ],
                order="id",
            )
        )
        wanted = set(moves.company_id.ids)
        for account in accounts:
            for company in account.company_ids:
                if company.id in wanted:
                    result.setdefault(
                        ("res.company", company.id, account.account_type), account.id
                    )
        _debug.perf.count(
            "term_default_accounts_fetched", moves=moves, rows=len(result)
        )
        return result

    @_debug.perf.timed
    def _update_account_id_on_product_lines(self):
        product_lines = self.filtered(
            lambda line: (
                line.display_type == "product" and line.move_id.is_invoice(True)
            )
        )
        accounts_per_key = {}
        partner_account_per_key = {}
        for line in product_lines:
            if line.product_id:
                template = line.product_id.product_tmpl_id
                key = (
                    line.company_id.id,
                    template.id,
                    line.move_id.fiscal_position_id.id,
                )
                if key not in accounts_per_key:
                    accounts_per_key[key] = line.with_company(
                        line.company_id
                    ).product_id.product_tmpl_id._get_product_accounts(
                        fiscal_pos=line.move_id.fiscal_position_id
                    )
                accounts = accounts_per_key[key]
                if line.move_id.is_sale_document(include_receipts=True):
                    line.account_id = accounts["income"] or line.account_id
                elif line.move_id.is_purchase_document(include_receipts=True):
                    line.account_id = accounts["expense"] or line.account_id
            elif line.partner_id:
                key = (line.company_id.id, line.partner_id.id, line.move_id.move_type)
                if key not in partner_account_per_key:
                    partner_account_per_key[key] = self.env[
                        "account.account"
                    ]._get_most_frequent_account_for_partner(
                        company_id=key[0], partner_id=key[1], move_type=key[2]
                    )
                if partner_account_per_key[key]:
                    line.account_id = partner_account_per_key[key]
        _debug.pipeline(
            "product_line_accounts_resolved",
            lines=product_lines,
            product_keys=len(accounts_per_key),
            partner_keys=len(partner_account_per_key),
        )
        if _debug.logic.enabled and partner_account_per_key:
            _debug.logic(
                "partner_frequent_account_used",
                keys=len(partner_account_per_key),
                hits=sum(1 for account in partner_account_per_key.values() if account),
            )

    def _update_account_id_fallback(self):
        for line in self:
            non_accountable = line.display_type in NON_ACCOUNTABLE_DISPLAY_TYPES
            if line.account_id or non_accountable:
                continue
            previous_two_accounts = line.move_id.line_ids.filtered(
                lambda l, dtype=line.display_type: (
                    l.account_id and l.display_type == dtype
                )
            )[-2:].account_id
            if len(previous_two_accounts) == 1 and len(line.move_id.line_ids) > 2:
                line.account_id = previous_two_accounts
                source = "previous lines"  # debuglog
            else:
                line.account_id = line.move_id.journal_id.default_account_id
                source = "journal default"  # debuglog
            _debug.logic(
                "fallback_account",
                move=line.move_id,
                line=line,
                account_id=line.account_id,
                source=source,
            )

    @api.model
    @_debug.perf.timed
    def _search_account_lookup_id(self, operator, value):
        if operator in ("in", "not in", "any", "not any") and not isinstance(
            value, (tuple, list, OrderedSet)
        ):
            if operator in ("any", "not any"):
                operator = {"any": "in", "not any": "not in"}[operator]

            if isinstance(value, (Query, SQL)):
                query_value = value.select() if isinstance(value, Query) else value
                value = [row[0] for row in self.env.execute_query(query_value)]
                _debug.perf.count("account_lookup_ids_fetched", rows=len(value))
            else:
                value = (
                    self.env["account.account"].sudo()._search(value).get_result_ids()
                )
                _debug.logic("account_lookup_domain_searched", operator=operator)

        return [("account_id", operator, value)]

    @api.depends("move_id.is_storno", "move_id.move_type", "price_unit", "quantity")
    def _compute_is_storno(self):
        for line in self:
            if not line.company_id.account_storno:
                continue
            line.is_storno = (
                line.is_storno or line.move_id.is_storno
            ) and line.move_type not in ("in_invoice", "out_invoice")

            if (
                not line.move_id.is_storno
                and line in line.move_id.invoice_line_ids
                and line.quantity * line.price_unit
            ):
                line.is_storno = line.quantity * line.price_unit < 0

    @api.depends("move_id")
    def _compute_balance(self):
        for line in self:
            if line.display_type in NON_ACCOUNTABLE_DISPLAY_TYPES:
                line.balance = False
            elif not line.move_id.is_invoice(include_receipts=True):
                other_lines = line.move_id.line_ids - line
                line.balance = -sum(other_lines.mapped("balance"))
            else:
                line.balance = 0

    @api.depends("balance")
    def _compute_debit_credit(self):
        for line in self:
            if not line.is_storno:
                line.debit = max(0.0, line.balance)
                line.credit = -line.balance if line.balance < 0.0 else 0.0
            else:
                line.debit = min(0.0, line.balance)
                line.credit = -line.balance if line.balance > 0.0 else 0.0

    @api.depends(
        "currency_id",
        "company_id",
        "move_id.invoice_currency_rate",
        "move_id.date",
        "move_id.invoice_date",
    )
    def _compute_currency_rate(self):
        for line in self:
            if line.move_id.is_invoice(include_receipts=True):
                line.currency_rate = line.move_id.invoice_currency_rate or 1.0
            elif line.currency_id:
                line.currency_rate = self.env["res.currency"]._get_conversion_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.invoice_date
                    or line.move_id.date
                    or fields.Date.context_today(line),
                )
            else:
                line.currency_rate = 1

    @api.depends("currency_id", "company_currency_id")
    def _compute_is_same_currency(self):
        for record in self:
            record.is_same_currency = record.currency_id == record.company_currency_id

    @api.depends("currency_rate", "balance")
    def _compute_amount_currency(self):
        for line in self:
            if line.amount_currency is False:
                line.amount_currency = line.currency_id.round(
                    line.balance * line.currency_rate
                )
            if (
                line.currency_id == line.company_id.currency_id
                and not line.move_id.is_invoice(True)
            ):
                line.amount_currency = line.balance

    @api.depends_context(
        "order_cumulated_balance",
        "domain_cumulated_balance",
        "allowed_company_ids",
        "uid",
    )
    @_debug.perf.timed
    def _compute_cumulated_balance(self):
        if not self.env.context.get("order_cumulated_balance"):
            _debug.logic("cumulated_balance_skipped", lines=self, reason="no_order")
            self.cumulated_balance = 0
            return

        query = self._search(self.env.context.get("domain_cumulated_balance") or [])
        sql_order = self._order_to_sql(
            self.env.context.get("order_cumulated_balance"), query, reverse=True
        )
        subquery = query.subselect(
            SQL.identifier(query.table, "id"),
            SQL(
                "SUM(%s) OVER (ORDER BY %s ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)",
                SQL.identifier(query.table, "balance"),
                sql_order,
            ),
        )
        result = dict(
            self.env.execute_query(
                SQL(
                    "SELECT * FROM (%(subquery)s) AS aml WHERE id = ANY(%(ids)s)",
                    subquery=subquery,
                    ids=self.ids,
                ),
            )
        )
        _debug.perf.count("cumulated_balance_rows_fetched", rows=len(result))
        for record in self:
            record.cumulated_balance = result.get(record.id, 0)

    @api.depends(
        "debit",
        "credit",
        "amount_currency",
        "account_id",
        "currency_id",
        "company_id",
        "matched_debit_ids",
        "matched_credit_ids",
    )
    @_debug.perf.timed
    def _compute_reconciliation(self):
        need_residual_lines = self.filtered(
            lambda x: (
                x.account_id.reconcile
                or x.account_id.account_type in ("asset_cash", "liability_credit_card")
            )
        )
        stored_lines = need_residual_lines._origin
        _debug.logic(
            "residual_scope",
            lines=self,
            need_residual=need_residual_lines,
            stored=stored_lines,
        )

        if stored_lines:
            Partial = self.env["account.partial.reconcile"]
            amounts_map = {}
            # one row per (line, side); the currency amount is rounded to the side's
            # currency, which every partial of a line shares with the line itself
            debit_groups = Partial._read_group(
                [("debit_move_id", "in", stored_lines.ids)],
                ["debit_move_id", "debit_currency_id"],
                ["amount:sum", "debit_amount_currency:sum"],
            )
            credit_groups = Partial._read_group(
                [("credit_move_id", "in", stored_lines.ids)],
                ["credit_move_id", "credit_currency_id"],
                ["amount:sum", "credit_amount_currency:sum"],
            )
            for side, groups in (("debit", debit_groups), ("credit", credit_groups)):
                for line, currency, amount, amount_currency in groups:
                    amount_currency = amount_currency or 0.0
                    amounts_map[line.id, side] = (
                        amount or 0.0,
                        currency.round(amount_currency)
                        if currency
                        else amount_currency,
                    )
            _debug.perf.count("partial_sums_fetched", rows=len(amounts_map))
        else:
            amounts_map = {}

        for line in self - need_residual_lines:
            line.amount_residual = 0.0
            line.amount_residual_currency = 0.0
            line.reconciled = False

        for line in need_residual_lines:
            comp_curr = line.company_currency_id or self.env.company.currency_id
            foreign_curr = line.currency_id or comp_curr

            debit_amount, debit_amount_currency = amounts_map.get(
                (line._origin.id, "debit"), (0.0, 0.0)
            )
            credit_amount, credit_amount_currency = amounts_map.get(
                (line._origin.id, "credit"), (0.0, 0.0)
            )

            line.amount_residual = comp_curr.round(
                line.balance - debit_amount + credit_amount
            )
            line.amount_residual_currency = foreign_curr.round(
                line.amount_currency - debit_amount_currency + credit_amount_currency
            )
            line.reconciled = comp_curr.is_zero(
                line.amount_residual
            ) and foreign_curr.is_zero(line.amount_residual_currency)
        if _debug.logic.enabled and need_residual_lines:
            _debug.logic(
                "residual_computed",
                lines=need_residual_lines,
                reconciled=need_residual_lines.filtered("reconciled"),
            )

    @api.depends("product_id", "product_id.uom_id", "product_id.uom_ids")
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = line.product_id.uom_id | line.product_id.uom_ids

    @api.depends("product_id")
    @_debug.perf.timed
    def _compute_product_uom_id(self):
        for line in self.filtered(lambda l: l.parent_state == "draft"):
            if line.move_id.is_purchase_document():
                sellers = line.product_id.seller_ids._filtered_for_company_and_product(
                    line.company_id, line.product_id, False
                )
                product_uom = line.product_id.uom_id
                line.product_uom_id = (
                    next(
                        (
                            seller.product_uom_id
                            for seller in sellers
                            if seller.product_uom_id
                            and product_uom
                            and seller.product_uom_id._has_common_reference(product_uom)
                        ),
                        product_uom,
                    )
                    or product_uom
                )
            else:
                line.product_uom_id = line.product_id.uom_id

    @api.depends("display_type")
    def _compute_quantity(self):
        for line in self:
            if line.display_type == "product":
                line.quantity = line.quantity or 1
            else:
                line.quantity = False

    @api.depends("display_type")
    def _compute_sequence(self):
        seq_map = {
            "tax": 10000,
            "rounding": 11000,
            "payment_term": 12000,
        }
        for line in self:
            line.sequence = seq_map.get(line.display_type, 100)

    @api.depends(
        "quantity",
        "discount",
        "price_unit",
        "amount_currency",
        "tax_ids",
        "currency_id",
    )
    @_debug.perf.timed
    def _compute_totals(self):
        AccountTax = self.env["account.tax"]
        for line in self:
            if (
                line.display_type
                not in (
                    "product",
                    "cogs",
                    "non_deductible_product",
                    "non_deductible_product_total",
                )
                or not line.move_id
            ):
                line.price_total = line.price_subtotal = False
                continue

            company = line.company_id or self.env.company
            base_line = line.move_id._prepare_product_base_line_for_taxes_computation(
                line
            )
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            line.price_subtotal = base_line["tax_details"]["total_excluded_currency"]
            line.price_total = base_line["tax_details"]["total_included_currency"]

    @api.depends("product_id", "product_uom_id")
    @_debug.perf.timed
    def _compute_price_unit(self):
        for line in self:
            if (
                not line.product_id
                or line.display_type in NON_ACCOUNTABLE_DISPLAY_TYPES
                or line.is_imported
            ):
                continue
            if line.move_id.is_sale_document(include_receipts=True):
                document_type = "sale"
            elif line.move_id.is_purchase_document(include_receipts=True):
                document_type = "purchase"
            else:
                document_type = "other"
            line.price_unit = line.product_id._get_tax_included_unit_price(
                line.move_id.company_id,
                line.move_id.currency_id,
                line.move_id.date,
                document_type,
                fiscal_position=line.move_id.fiscal_position_id,
                product_uom_id=line.product_uom_id,
            )

    @api.depends("product_id", "product_uom_id")
    def _compute_tax_ids(self):
        for line in self:
            if (
                line.display_type
                in (*NON_ACCOUNTABLE_DISPLAY_TYPES, "payment_term", "cogs")
                or line.is_imported
            ):
                continue
            account_taxes = line.account_id.sudo().tax_ids
            if line.product_id or (
                line.display_type != "discount" and (account_taxes or not line.tax_ids)
            ):
                line.tax_ids = line._get_computed_taxes()

    @_debug.perf.timed
    def _get_computed_taxes(self):
        self.check_singleton()

        company_domain = self.env["account.tax"]._check_company_domain(
            self.move_id.company_id
        )
        all_account_taxes = self.account_id.sudo().tax_ids
        if self.move_id.is_sale_document(include_receipts=True):
            filtered_taxes_id = self.product_id.sudo().taxes_id.filtered_domain(
                company_domain
            )
            account_taxes = all_account_taxes.filtered(
                lambda tax: tax.type_tax_use == "sale"
            )
            tax_ids = filtered_taxes_id or account_taxes
        elif self.move_id.is_purchase_document(include_receipts=True):
            filtered_supplier_taxes_id = (
                self.product_id.sudo().supplier_taxes_id.filtered_domain(company_domain)
            )
            account_taxes = all_account_taxes.filtered(
                lambda tax: tax.type_tax_use == "purchase"
            )
            tax_ids = filtered_supplier_taxes_id or account_taxes
        elif self.env.context.get("account_default_taxes"):
            tax_ids = all_account_taxes
        else:
            tax_ids = (
                False
                if self.env.context.get("skip_computed_taxes")
                or self.move_id.is_entry()
                else all_account_taxes
            )

        if self.company_id and tax_ids:
            tax_ids = tax_ids._filter_taxes_by_company(self.company_id)

        if tax_ids and self.move_id.fiscal_position_id:
            mapped_tax_ids = self.move_id.fiscal_position_id.map_tax(tax_ids)
            if _debug.logic.enabled and mapped_tax_ids != tax_ids:
                _debug.logic(
                    "fiscal_position_mapped_taxes",
                    move=self.move_id,
                    line=self,
                    fiscal_position_id=self.move_id.fiscal_position_id,
                    tax_ids=tax_ids,
                    mapped_tax_ids=mapped_tax_ids,
                )
            tax_ids = mapped_tax_ids

        return tax_ids.with_env(self.env) if tax_ids else tax_ids

    @api.depends("account_id", "company_id", "currency_rate", "display_type")
    def _compute_discount_allocation_key(self):
        for line in self:
            if line.display_type == "discount":
                line.discount_allocation_key = frozendict(
                    {
                        "account_id": line.account_id.id,
                        "move_id": line.move_id.id,
                        "currency_rate": line.currency_rate,
                    }
                )
            else:
                line.discount_allocation_key = False

    @_debug.perf.timed
    def _prepare_discount_allocation_amounts(self):
        amounts_per_line = {}
        for line in self.move_id.line_ids:
            if line.display_type != "product":
                continue
            allocation_account = line.move_id._get_discount_allocation_account()
            if not allocation_account or line.account_id == allocation_account:
                continue
            amount_currency = line.currency_id.round(
                line.move_id.direction_sign
                * line.quantity
                * line.price_unit
                * line.discount
                / 100
            )
            if not amount_currency:
                continue
            balance = line.company_currency_id.round(
                amount_currency / line.currency_rate
            )
            amounts_per_line[line] = [
                (line.account_id, amount_currency, balance),
                (allocation_account, -amount_currency, -balance),
            ]
        _debug.pipeline(
            "discount_allocations_prepared",
            lines=self,
            allocated_lines=len(amounts_per_line),
        )
        return amounts_per_line

    @api.depends(
        "company_id",
        "move_id.move_type",
        "move_id.line_ids.display_type",
        "move_id.line_ids.account_id",
        "move_id.line_ids.discount",
        "move_id.line_ids.price_unit",
        "move_id.line_ids.quantity",
        "move_id.line_ids.currency_id",
        "move_id.line_ids.currency_rate",
        "move_id.line_ids.analytic_distribution",
    )
    @_debug.perf.timed
    def _compute_discount_allocation(self):
        line2discounted_amount = self._prepare_discount_allocation_amounts()

        distribution_totals = defaultdict(lambda: defaultdict(float))
        for line, discounted_amounts in line2discounted_amount.items():
            for account, _amount_currency, amount in discounted_amounts:
                for analytic_account_id, percentage in (
                    line.analytic_distribution or {}
                ).items():
                    distribution_totals[
                        frozendict(
                            {
                                "move_id": line.move_id.id,
                                "account_id": account.id,
                                "currency_rate": line.currency_rate,
                            }
                        )
                    ][analytic_account_id] += amount * percentage / 100
        _debug.pipeline(
            "discount_allocation_amounts",
            lines=self,
            discounted_lines=len(line2discounted_amount),
            distribution_keys=len(distribution_totals),
        )

        for line in self:
            line.discount_allocation_dirty = True
            if line not in line2discounted_amount:
                line.discount_allocation_needed = False
                continue

            discount_allocation_needed = {}
            for account, amount_currency, amount in line2discounted_amount[line]:
                key = frozendict(
                    {
                        "move_id": line.move_id.id,
                        "account_id": account.id,
                        "currency_rate": line.currency_rate,
                    }
                )
                dist = distribution_totals[key]
                total = sum(dist.values()) or 1
                discount_allocation_needed[key] = frozendict(
                    {
                        "display_type": "discount",
                        "name": _("Discount"),
                        "amount_currency": amount_currency,
                        "balance": amount,
                        "analytic_distribution": {
                            account_id: 100 * value / total
                            for account_id, value in dist.items()
                        },
                    }
                )
            line.discount_allocation_needed = discount_allocation_needed

    @api.depends(
        "tax_ids",
        "tax_tag_ids",
        "account_id",
        "company_id",
        "analytic_distribution",
        "display_type",
        "move_id.invoice_payment_term_id.early_discount",
    )
    @_debug.perf.timed
    def _compute_epd_key(self):
        for line in self:
            pay_term = line.move_id.invoice_payment_term_id
            if (
                line.display_type == "epd"
                and pay_term.early_discount
                and pay_term.early_pay_discount_computation == "mixed"
            ):
                line.epd_key = frozendict(
                    {
                        "account_id": line.account_id.id,
                        "analytic_distribution": line.analytic_distribution,
                        "tax_ids": [Command.set(line.tax_ids.ids)],
                        "tax_tag_ids": [Command.set(line.tax_tag_ids.ids)],
                        "move_id": line.move_id.id,
                    }
                )
            else:
                line.epd_key = False

    @api.depends(
        "move_id.needed_terms",
        "account_id",
        "analytic_distribution",
        "tax_ids",
        "tax_tag_ids",
        "company_id",
        "price_subtotal",
    )
    @_debug.perf.timed
    def _compute_epd(self):
        self.epd_dirty = True
        self.epd_needed = False

        candidate_invoice_lines = self.filtered(
            lambda l: (
                l.move_id.invoice_payment_term_id.early_discount
                and l.display_type == "product"
                and l.tax_ids
                and l.move_id.invoice_payment_term_id.early_pay_discount_computation
                == "mixed"
            )
        )
        result_per_invoice_line = {}
        if _debug.logic.enabled and candidate_invoice_lines:
            _debug.logic(
                "_compute_epd_eligible",
                candidate_invoice_lines_count=len(candidate_invoice_lines),
                records_count=len(self),
                move_id=candidate_invoice_lines.move_id,
            )
        for move in candidate_invoice_lines.move_id:
            result_per_invoice_line.update(move._prepare_epd_needed_per_line())

        for invoice_line in candidate_invoice_lines:
            epd_needed = result_per_invoice_line[invoice_line]
            invoice_line.epd_needed = {k: frozendict(v) for k, v in epd_needed.items()}

    @api.model
    def _get_epd_grouping_function(self):
        def grouping_function(base_line, tax_data):
            del tax_data
            return {
                "account_id": base_line["account_id"].id,
                "analytic_distribution": base_line["analytic_distribution"],
                "tax_ids": [
                    Command.set(
                        [
                            line_tax_data["tax"].id
                            for line_tax_data in base_line["tax_details"]["taxes_data"]
                        ]
                    )
                ],
            }

        return grouping_function

    @api.depends(
        "move_id.move_type",
        "move_id.reversed_entry_id",
        "balance",
        "tax_repartition_line_id",
        "tax_ids",
    )
    @_debug.perf.timed
    def _compute_is_refund(self):
        for line in self:
            is_refund = False
            if line.move_id.move_type in ("out_refund", "in_refund"):
                is_refund = True
            elif line.move_id.move_type == "entry":
                if line.tax_repartition_line_id:
                    is_refund = line.tax_repartition_line_id.document_type == "refund"
                else:
                    tax_type = line.tax_ids.mapped("type_tax_use")
                    if "sale" in tax_type and "purchase" in tax_type:
                        is_refund = line.credit == 0
                    else:
                        tax_type = line.tax_ids[:1].type_tax_use
                        if (tax_type == "sale" and line.credit == 0) or (
                            tax_type == "purchase" and line.debit == 0
                        ):
                            is_refund = True

                    if line.tax_ids and line.move_id.reversed_entry_id:
                        is_refund = not is_refund
            line.is_refund = is_refund

    @api.depends("date_maturity", "discount_date", "display_type")
    def _compute_term_key(self):
        for line in self:
            if line.display_type == "payment_term":
                line.term_key = frozendict(
                    {
                        "move_id": line.move_id.id,
                        "date_maturity": fields.Date.to_date(line.date_maturity),
                        "discount_date": line.discount_date,
                    }
                )
            else:
                line.term_key = False

    @api.depends("account_id", "partner_id", "product_id")
    @_debug.perf.timed
    def _compute_analytic_distribution(self):
        cache = {}
        AnalyticAccount = self.env["account.analytic.account"]
        lines_info = {}
        all_account_ids = set()
        for line in self:
            if line.display_type == "product" or not line.move_id.is_invoice(
                include_receipts=True
            ):
                related_distribution = line._related_analytic_distribution()
                account_ids = {
                    int(account_id)
                    for ids in related_distribution
                    for account_id in ids.split(",")
                    if account_id.strip()
                }
                lines_info[line] = (related_distribution, account_ids)
                all_account_ids |= account_ids

        if not lines_info:
            return

        existing_accounts = AnalyticAccount.browse(sorted(all_account_ids)).exists()
        existing_ids = set(existing_accounts.ids)
        existing_accounts.mapped("root_plan_id")

        for line, (related_distribution, account_ids) in lines_info.items():
            root_plans = AnalyticAccount.browse(
                [aid for aid in account_ids if aid in existing_ids]
            ).root_plan_id

            arguments = frozendict(
                line._get_analytic_distribution_arguments(root_plans)
            )
            if arguments not in cache:
                cache[arguments] = self.env[
                    "account.analytic.distribution.model"
                ]._get_distribution(arguments)
            line.analytic_distribution = (
                related_distribution | cache[arguments] or line.analytic_distribution
            )
        _debug.logic(
            "_compute_analytic_distribution",
            line_count=len(lines_info),
            argument_set_count=len(cache),
            model_hit_count=sum(1 for v in cache.values() if v),
        )

    def _get_analytic_distribution_arguments(self, root_plans):
        return {
            "product_id": self.product_id.id,
            "product_categ_id": self.product_id.categ_id.id,
            "partner_id": self.partner_id.id,
            "partner_tag_id": self.partner_id.tag_ids.ids,
            "account_prefix": self.account_id.code,
            "company_id": self.company_id.id,
            "related_root_plan_ids": root_plans,
        }

    @api.depends("discount_date", "date_maturity")
    @api.depends_context("tz")
    def _compute_payment_date(self):
        for line in self:
            today = fields.Date.context_today(line)
            line.payment_date = (
                line.discount_date
                if line.discount_date and today <= line.discount_date
                else line.date_maturity
            )

    @api.depends("matched_debit_ids", "matched_credit_ids")
    def _compute_reconciled_lines_ids(self):
        accessible_lines = set(
            (
                self.matched_debit_ids.debit_move_id
                + self.matched_credit_ids.credit_move_id
            )._filtered_access("read")
        )
        for line in self:
            line.sudo().reconciled_lines_ids = (
                line.matched_debit_ids.debit_move_id
                + line.matched_credit_ids.credit_move_id
            ).filtered(accessible_lines.__contains__)

    @api.depends("reconciled_lines_ids", "matched_debit_ids", "matched_credit_ids")
    def _compute_reconciled_lines_excluding_exchange_diff_ids(self):
        for line in self:
            excluded_ids = (
                line.matched_debit_ids + line.matched_credit_ids
            ).exchange_move_id.line_ids
            line.sudo().reconciled_lines_excluding_exchange_diff_ids = (
                line.reconciled_lines_ids - excluded_ids
            )

    @api.depends(
        "display_type",
        "sequence",
        "move_id.line_ids.display_type",
        "move_id.line_ids.sequence",
    )
    @_debug.perf.timed
    def _compute_parent_id(self):
        parent_id_vals_to_lines = defaultdict(list)
        for move, lines in self.grouped("move_id").items():
            if not move:
                parent_id_vals_to_lines[False].extend(lines._ids)
                continue
            last_section = False
            last_sub = False
            for line in move.line_ids.sorted("sequence"):
                if line.display_type == "line_section":
                    last_section = line
                    value = False
                    last_sub = False
                elif line.display_type == "line_subsection":
                    value = last_section
                    last_sub = line
                elif line.display_type in {"line_note", "product"}:
                    value = last_sub or last_section
                else:
                    value = False
                parent_id_vals_to_lines[value].append(line.id)

        _debug.pipeline(
            "parent_ids_grouped", lines=self, parents=len(parent_id_vals_to_lines)
        )
        for val, record_ids in parent_id_vals_to_lines.items():
            (self.browse(record_ids) & self).parent_id = val

    @api.depends("journal_id.type")
    def _compute_no_followup(self):
        for aml in self:
            aml.no_followup = aml.journal_id.type == "general"

    def _inverse_no_followup(self):
        for aml in self:
            move = aml.move_id
            if move.is_invoice():
                move.no_followup = aml.no_followup

    @_debug.perf.timed
    def _search_payment_date(self, operator, value):
        if operator == "in":
            return Domain.OR(self._search_payment_date("=", v) for v in value)
        if operator in Domain.NEGATIVE_OPERATORS:
            _debug.logic("payment_date_search_unsupported", operator=operator)
            return NotImplemented
        if operator == "=":
            operator = "<="
        today = fields.Date.context_today(self)
        return [
            "|",
            "|",
            "&",
            ("discount_date", ">=", today),
            ("discount_date", operator, value),
            "&",
            ("discount_date", "<", today),
            ("date_maturity", operator, value),
            "&",
            ("discount_date", "=", False),
            ("date_maturity", operator, value),
        ]

    @_debug.perf.timed
    def action_payment_items_register_payment(self):
        _debug.lifecycle("action_payment_items_register_payment", records=self)
        return self.action_register_payment(ctx={"default_group_payment": True})

    @_debug.perf.timed
    def action_register_payment(self, ctx=None):
        _debug.lifecycle("action_register_payment", records=self)
        context = {
            "active_model": "account.move.line",
            "active_ids": self.ids,
        }
        if ctx:
            context.update(ctx)
        return {
            "name": _("Pay"),
            "res_model": "account.payment.register",
            "view_mode": "form",
            "views": [[False, "form"]],
            "context": context,
            "target": "new",
            "type": "ir.actions.act_window",
        }

    @_debug.perf.timed
    def _search_journal_group_id(self, operator, value):
        return self.env["account.move"]._search_journal_group_id(operator, value)

    @api.onchange("partner_id")
    def _inverse_partner_id(self):
        self._conditional_add_to_compute(
            "account_id",
            lambda line: line.display_type == "payment_term",
        )

    @api.onchange("product_id")
    def _inverse_product_id(self):
        if self.product_id or not self.account_id:
            self._conditional_add_to_compute(
                "account_id",
                lambda line: (
                    line.display_type == "product" and line.move_id.is_invoice(True)
                ),
            )

    @api.onchange("amount_currency", "currency_id")
    def _inverse_amount_currency(self):
        for line in self:
            if (
                line.currency_id == line.company_id.currency_id
                and line.balance != line.amount_currency
            ):
                line.balance = line.amount_currency
            elif (
                line.currency_id != line.company_id.currency_id
                and not line.move_id.is_invoice(True)
                and not self.env.is_protected(self._fields["balance"], line)
            ):
                line.balance = line.company_id.currency_id.round(
                    line.amount_currency / line.currency_rate
                )

    @api.onchange("debit")
    def _inverse_debit(self):
        for line in self:
            line.is_storno = line.debit < 0
            if line.debit:
                line.credit = 0
            line.balance = line.debit - line.credit

    @api.onchange("credit")
    def _inverse_credit(self):
        for line in self:
            line.is_storno = line.credit < 0
            if line.credit:
                line.debit = 0
            line.balance = line.debit - line.credit

    def _analytic_distribution_consumes_update(self):
        return True

    def _get_count_id(self, query):
        return SQL("move_id")

    def _inverse_analytic_distribution(self):
        self._update_analytic_distribution_from_origin()

    def _update_analytic_distribution_from_origin(self):
        if self.env.context.get("skip_analytic_sync"):
            return
        lines_to_modify = (
            self.env["account.move.line"]
            .browse([line.id for line in self if line.parent_state == "posted"])
            .with_context(skip_analytic_sync=True)
        )
        old_distributions = dict(
            self.env.execute_query(
                SQL(
                    "SELECT id, analytic_distribution FROM account_move_line WHERE id = ANY(%s)",
                    self.ids,
                )
            )
        )
        _debug.perf.count("analytic_distributions_fetched", rows=len(old_distributions))
        for line in self:
            line.analytic_distribution = self._merge_distribution(
                old_distribution=old_distributions.get(line._origin.id) or {},
                new_distribution=line.analytic_distribution or {},
            )
        lines_to_modify.analytic_line_ids.unlink()
        lines_to_modify._create_analytic_lines()

    @api.onchange("account_id")
    def _inverse_account_id(self):
        self._update_analytic_distribution_from_origin()
        self._conditional_add_to_compute(
            "tax_ids",
            lambda line: (
                line.account_id.sudo().tax_ids.filtered(
                    lambda tax: tax._serves_company(line.company_id)
                )
                and not line.product_id.sudo().taxes_id.filtered(
                    lambda tax: tax._serves_company(line.company_id)
                )
            ),
        )

    def _inverse_reconciled_lines_ids(self):
        self._reconcile_plan([line + line.reconciled_lines_ids for line in self])

    @_debug.perf.timed
    def _check_account_is_usable(self):
        for line in self.filtered(
            lambda x: x.display_type not in NON_ACCOUNTABLE_DISPLAY_TYPES
        ):
            account = line.account_id
            if not account:
                continue

            if not (
                account.active
                or line.is_imported
                or self.env.context.get("skip_account_deprecation_check")
            ):
                _debug.logic("archived_account_refused", line=line, account=account)
                raise UserError(
                    _(
                        "The account %(name)s (%(code)s) is archived.",
                        name=account.name,
                        code=account.code,
                    )
                )

            if not line.journal_id._is_account_allowed(account):
                _debug.logic(
                    "journal_account_refused",
                    line=line,
                    account=account,
                    journal=line.journal_id,
                )
                raise UserError(
                    _(
                        "Account %(name)s (%(code)s) is not one of the accounts "
                        "allowed on journal %(journal)s.",
                        name=account.name,
                        code=account.code,
                        journal=line.journal_id.display_name,
                    )
                )

            account_currency = account.currency_id
            if account_currency and account_currency not in (
                line.company_currency_id,
                line.currency_id,
            ):
                _debug.logic(
                    "account_currency_mismatch",
                    line=line,
                    account=account,
                    account_currency=account_currency,
                    line_currency=line.currency_id,
                )
                raise UserError(
                    _(
                        "Account %(name)s (%(code)s) is restricted to %(account_currency)s, "
                        "but this journal item is in %(line_currency)s. Use an account "
                        "without a secondary currency, or change the item's currency.",
                        name=account.name,
                        code=account.code,
                        account_currency=account_currency.name,
                        line_currency=line.currency_id.name
                        or line.company_currency_id.name,
                    )
                )

    @api.constrains("account_id", "tax_ids", "tax_line_id", "reconciled")
    @_debug.perf.timed
    def _check_off_balance(self):
        for move in self.move_id:
            accounts = move.line_ids.account_id
            if not any(a.account_type == "off_balance" for a in accounts):
                continue
            if any(a.account_type != "off_balance" for a in accounts):
                _debug.logic("off_balance_mixed_accounts", move=move, accounts=accounts)
                raise UserError(
                    _(
                        'If you want to use "Off-Balance Sheet" accounts, all the accounts of the journal entry must be of this type'
                    )
                )
            for line in move.line_ids.filtered(
                lambda l: l.account_id.account_type == "off_balance"
            ):
                if line.tax_ids or line.tax_line_id:
                    _debug.logic("off_balance_line_taxed", move=move, line=line)
                    raise UserError(
                        _("You cannot use taxes on lines with an Off-Balance account")
                    )
                if line.reconciled:
                    _debug.logic("off_balance_line_reconciled", move=move, line=line)
                    raise UserError(
                        _(
                            'Lines from "Off-Balance Sheet" accounts cannot be reconciled'
                        )
                    )

    @api.constrains("account_id", "display_type")
    @_debug.perf.timed
    def _check_payable_receivable(self):
        for line in self:
            account_type = line.account_id.account_type
            if line.move_id.is_sale_document(include_receipts=True):
                if account_type == "liability_payable":
                    _debug.logic("payable_on_sale_refused", line=line)
                    raise UserError(
                        _(
                            "Account %s is of payable type, but is used in a sale operation.",
                            line.account_id.code,
                        )
                    )
                if (line.display_type == "payment_term") ^ (
                    account_type == "asset_receivable"
                ):
                    _debug.logic(
                        "receivable_term_mismatch",
                        line=line,
                        display_type=line.display_type,
                        account_type=account_type,
                    )
                    raise UserError(
                        _(
                            "Any journal item on a receivable account must have a due date and vice versa."
                        )
                    )
            if line.move_id.is_purchase_document(include_receipts=True):
                if account_type == "asset_receivable":
                    _debug.logic("receivable_on_purchase_refused", line=line)
                    raise UserError(
                        _(
                            "Account %s is of receivable type, but is used in a purchase operation.",
                            line.account_id.code,
                        )
                    )
                if (line.display_type == "payment_term") ^ (
                    account_type == "liability_payable"
                ):
                    _debug.logic(
                        "payable_term_mismatch",
                        line=line,
                        display_type=line.display_type,
                        account_type=account_type,
                    )
                    raise UserError(
                        _(
                            "Any journal item on a payable account must have a due date and vice versa."
                        )
                    )

    def _affect_tax_report(self):
        self.check_singleton()
        return (
            self.tax_ids
            or self.tax_line_id
            or self.tax_tag_ids.filtered(lambda x: x.applicability == "taxes")
        )

    @_debug.perf.timed
    def _check_tax_lock_date(self):
        for line in self:
            move = line.move_id
            if move.state != "posted":
                continue
            violated_lock_dates = move.company_id._get_lock_date_violations(
                move.date,
                fiscalyear=False,
                sale=False,
                purchase=False,
                tax=True,
                hard=True,
            )
            if violated_lock_dates and line._affect_tax_report():
                _debug.logic(
                    "tax_lock_date_violated",
                    move=move,
                    line=line,
                    violations=violated_lock_dates,
                )
                raise UserError(
                    _(
                        "The operation is refused as it would impact an already issued tax statement. "
                        "Please change the journal entry date or the following lock dates to proceed: %(lock_date_info)s.",
                        lock_date_info=self.env["res.company"]._format_lock_dates(
                            violated_lock_dates
                        ),
                    )
                )
        return True

    @api.constrains("tax_ids", "tax_repartition_line_id")
    @_debug.perf.timed
    def _check_caba_non_caba_shared_tags(self):
        def get_base_repartition(base_aml, taxes):
            if not taxes:
                return self.env["account.tax.repartition.line"]

            is_refund = base_aml.is_refund
            repartition_field = (
                is_refund and "refund_repartition_line_ids"
            ) or "invoice_repartition_line_ids"
            return taxes.mapped(repartition_field)

        for aml in self:
            caba_taxes = aml.tax_ids.filtered(
                lambda x: x.tax_exigibility == "on_payment"
            )
            non_caba_taxes = aml.tax_ids - caba_taxes

            caba_base_tags = (
                get_base_repartition(aml, caba_taxes)
                .filtered(lambda x: x.repartition_type == "base")
                .tag_ids
            )
            non_caba_base_tags = (
                get_base_repartition(aml, non_caba_taxes)
                .filtered(lambda x: x.repartition_type == "base")
                .tag_ids
            )

            common_tags = caba_base_tags & non_caba_base_tags

            if not common_tags:
                tax_tags = aml.tax_repartition_line_id.tag_ids
                comparison_tags = (
                    non_caba_base_tags
                    if aml.tax_repartition_line_id.tax_id.tax_exigibility
                    == "on_payment"
                    else caba_base_tags
                )
                common_tags = tax_tags & comparison_tags

            if common_tags:
                _debug.logic(
                    "caba_shared_tags_refused",
                    line=aml,
                    caba_taxes=caba_taxes,
                    non_caba_taxes=non_caba_taxes,
                    tags=common_tags,
                )
                raise ValidationError(
                    _(
                        "Taxes exigible on payment and on invoice cannot be mixed on the same journal item if they share some tag."
                    )
                )

    @api.constrains(
        "matching_number",
        "matched_debit_ids",
        "matched_credit_ids",
        "full_reconcile_id",
    )
    @_debug.perf.timed
    def _constrains_matching_number(self):
        if _debug.logic.enabled:
            _debug.logic(
                "matching_numbers_checked",
                lines=self,
                prefixes=sorted({(line.matching_number or "-")[:1] for line in self}),
            )
        for line in self:
            if line.matching_number:
                if not re.match(r"^((P?\d+)|(I.+))$", line.matching_number):
                    raise ValidationError(_("Invalid matching number format"))
                if line.matching_number.startswith("I") and (
                    line.matched_debit_ids or line.matched_credit_ids
                ):
                    raise ValidationError(
                        _("A temporary number can not be used in a real matching")
                    )
                if line.matching_number.startswith("P") and not (
                    line.matched_debit_ids or line.matched_credit_ids
                ):
                    raise ValidationError(
                        _("A partial matching number must have partials")
                    )
                if line.matching_number.startswith("P") and line.full_reconcile_id:
                    raise ValidationError(
                        _(
                            "A fully reconciled line cannot keep a partial matching number"
                        )
                    )
                if line.matching_number.isdecimal() and not line.full_reconcile_id:
                    raise ValidationError(
                        _("A full matching number requires a full reconciliation")
                    )
                if line.full_reconcile_id and line.matching_number != str(
                    line.full_reconcile_id.id
                ):
                    _debug.logic(
                        "matching_number_full_mismatch",
                        line=line,
                        matching_number=line.matching_number,
                        full=line.full_reconcile_id,
                    )
                    raise ValidationError(
                        _("The matching number must equal the full reconciliation id")
                    )
            elif line.matched_debit_ids or line.matched_credit_ids:
                _debug.logic("reconciled_line_unnumbered", line=line)
                raise ValidationError(
                    _("A reconciled line must have a matching number")
                )

    def _is_partially_deductible(self):
        self.check_singleton()
        return float_compare(self.deductible_amount, 100, precision_digits=2) < 0

    @api.constrains("deductible_amount")
    def _constrains_deductible_amount(self):
        for line in self:
            if not line.move_id.is_purchase_document(
                include_receipts=True
            ) and float_compare(line.deductible_amount, 100, precision_digits=2):
                raise ValidationError(
                    _("Only vendor bills allow for deductibility of product/services.")
                )
            if (
                float_compare(line.deductible_amount, 0, precision_digits=2) < 0
                or float_compare(line.deductible_amount, 100, precision_digits=2) > 0
            ):
                raise ValidationError(
                    _("The deductibility must be a value between 0 and 100.")
                )

    @api.model
    def _get_tracked_fnames(self):
        return [
            fname
            for fname, field in self._fields.items()
            if getattr(field, "tracking", False)
            and not getattr(field, "related", False)
        ]

    def _snapshot_tracked_values(self, vals):
        if self.env.context.get("tracking_disable"):
            return {}
        tracked = set(self._get_tracked_fnames()) & set(vals)
        return {
            line.id: {fname: line[fname] for fname in tracked}
            for line in self.filtered(lambda l: l.move_id.posted_before)
        }

    def _log_tracked_change(self, body_for_link, tracked_pair):
        if self.env.context.get("tracking_disable"):
            return
        loggable = {
            move: lines
            for move, lines in self.grouped("move_id").items()
            if move.posted_before
        }
        if not loggable:
            _debug.logic(
                "tracked_change_skipped", lines=self, reason="not_posted_before"
            )
            return
        tracked_fnames = self._get_tracked_fnames()
        ref_fields = self.fields_get(tracked_fnames)
        _debug.pipeline("tracked_changes_logging", lines=self, moves=len(loggable))
        for move, lines in loggable.items():
            for line in lines:
                record, initial_values = tracked_pair(line, tracked_fnames)
                tracking_value_ids = record._mail_track(ref_fields, initial_values)[1]
                if tracking_value_ids:
                    move._message_log(
                        body=body_for_link(line._get_html_link(title=f"#{line.id}")),
                        tracking_value_ids=tracking_value_ids,
                    )

    def invalidate_model(self, fnames=None, flush=True):
        if fnames is None or "move_id" in fnames:
            field = self._fields["move_id"]
            lines = self.env.cache.get_records(self, field)
            move_ids = {id_ for id_ in self.env.cache.get_values(lines, field) if id_}
            if move_ids:
                self.env["account.move"].browse(move_ids).invalidate_recordset()
        return super().invalidate_model(fnames, flush)

    def invalidate_recordset(self, fnames=None, flush=True):
        if fnames is None or "move_id" in fnames:
            field = self._fields["move_id"]
            move_ids = {id_ for id_ in self.env.cache.get_values(self, field) if id_}
            if move_ids:
                self.env["account.move"].browse(move_ids).invalidate_recordset()
        return super().invalidate_recordset(fnames, flush)

    @api.model
    @_debug.perf.timed
    def search_fetch(self, domain, field_names=None, offset=0, limit=None, order=None):
        if field_names is not None and "cumulated_balance" not in field_names:
            return super().search_fetch(domain, field_names, offset, limit, order)

        def to_tuple(t):
            return tuple(map(to_tuple, t)) if isinstance(t, (list, tuple)) else t

        order = order or self._order
        if not re.search(r"\bid\b", order):
            order += ", id"
        _debug.logic("cumulated_balance_order_injected", order=order, limit=limit)
        contextualized = self.with_context(
            domain_cumulated_balance=to_tuple(domain or []),
            order_cumulated_balance=order,
        )
        return super(AccountMoveLine, contextualized).search_fetch(
            domain, field_names, offset, limit, order
        )

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        _debug.lifecycle("default_get", records=self)
        defaults = super().default_get(fields)
        quick_encode_suggestion = self.env.context.get("quick_encoding_vals")
        if (
            quick_encode_suggestion
            and self.env.context.get("default_display_type")
            not in NON_ACCOUNTABLE_DISPLAY_TYPES
        ):
            _debug.logic(
                "defaults_from_quick_encoding",
                account_id=quick_encode_suggestion.get("account_id"),
            )
            defaults["account_id"] = quick_encode_suggestion["account_id"]
            defaults["price_unit"] = quick_encode_suggestion["price_unit"]
            defaults["tax_ids"] = [Command.set(quick_encode_suggestion["tax_ids"])]
        elif (
            journal := self.env["account.journal"].browse(
                self.env.context.get("journal_id")
            )
        ) and journal.default_account_id:
            _debug.logic("defaults_from_journal", journal=journal)
            defaults["account_id"] = journal.default_account_id.id
        return defaults

    def _normalize_vals(self, vals):
        if "debit" in vals or "credit" in vals:
            vals = vals.copy()

            if (
                vals.get("move_id")
                and self.env["account.move"]
                .browse(vals["move_id"])
                .company_id.account_storno
            ):
                vals["is_storno"] = vals.get("is_storno", False) or (
                    vals.get("debit", 0) < 0 or vals.get("credit", 0) < 0
                )

            debit = vals.pop("debit", 0)
            credit = vals.pop("credit", 0)
            if "balance" not in vals:
                vals["balance"] = debit - credit
        if (
            vals.get("matching_number")
            and not vals["matching_number"].startswith("I")
            and not self.env.context.get("skip_matching_number_check")
        ):
            vals = {**vals, "matching_number": f"I{vals['matching_number']}"}

        return vals

    @_debug.perf.timed
    def _prepare_create_values(self, vals_list):
        result_vals_list = super()._prepare_create_values(vals_list)
        for init_vals, res_vals in zip(vals_list, result_vals_list, strict=True):
            if (
                "amount_currency" in init_vals
                and "balance" not in init_vals
                and "debit" not in init_vals
                and "credit" not in init_vals
            ):
                res_vals.pop("balance", 0)
                res_vals.pop("debit", 0)
                res_vals.pop("credit", 0)

            if res_vals.get("display_type") in NON_ACCOUNTABLE_DISPLAY_TYPES:
                res_vals.pop("account_id", None)

        return result_vals_list

    @contextmanager
    def _sync_invoice(self, container):
        if container["records"].env.context.get("skip_invoice_line_sync"):
            _debug.logic("invoice_sync_skipped", reason="skip_invoice_line_sync")
            yield
            return

        def existing():
            return {
                line: {
                    "amount_currency": line.currency_id.round(line.amount_currency),
                    "balance": line.company_id.currency_id.round(line.balance),
                    "currency_rate": line.currency_rate,
                    "move_type": line.move_id.move_type,
                }
                for line in container["records"]
                .with_context(
                    skip_invoice_line_sync=True,
                )
                .filtered(lambda l: l.move_id.is_invoice(True))
            }

        def changed(line, fname):
            return line not in before or before[line][fname] != after[line][fname]

        before = existing()
        _debug.pipeline("invoice_sync_before", invoice_lines=len(before))
        yield  # noqa: RUF075 - deliberate: on exception the transaction aborts and rolls back, so skipping the post-write currency/balance sync here changes nothing that would otherwise be persisted
        after = existing()
        amount_currency_synced = 0  # debuglog
        balance_synced = 0  # debuglog
        for line in after:
            if (
                (changed(line, "balance") or changed(line, "move_type"))
                and not self.env.is_protected(self._fields["amount_currency"], line)
                and (
                    not changed(line, "amount_currency")
                    or (line not in before and not line.amount_currency)
                )
                and line.currency_id == line.company_id.currency_id
            ):
                line.amount_currency = line.balance
                amount_currency_synced += 1  # debuglog
            if (
                (
                    changed(line, "amount_currency")
                    or changed(line, "currency_rate")
                    or changed(line, "move_type")
                )
                and not self.env.is_protected(self._fields["balance"], line)
                and (
                    not changed(line, "balance")
                    or (line not in before and not line.balance)
                )
            ):
                balance = line.company_id.currency_id.round(
                    line.amount_currency / line.currency_rate
                )
                line.balance = balance
                balance_synced += 1  # debuglog
        _debug.pipeline(
            "invoice_sync_after",
            lines=container["records"],
            invoice_lines=len(after),
            amount_currency_synced=amount_currency_synced,
            balance_synced=balance_synced,
        )

        self.env.add_to_compute(self._fields["debit"], container["records"])
        self.env.add_to_compute(self._fields["credit"], container["records"])

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
        moves = self.env["account.move"].browse(
            OrderedSet(vals["move_id"] for vals in vals_list if vals.get("move_id"))
        )
        container = {"records": self}
        move_container = {"records": moves}
        _debug.pipeline("lines_create_targets", moves=moves, count=len(vals_list))
        with (
            moves._check_balanced(move_container),
            ExitStack() as exit_stack,
            self.env.protecting(
                self.env["account.move"]._get_field_protections({}, moves)
            ),
            moves._sync_dynamic_lines(move_container),
            self._sync_invoice(container),
        ):
            lines = super().create([self._normalize_vals(vals) for vals in vals_list])
            exit_stack.enter_context(
                self.env.protecting(
                    [
                        protected
                        for vals, line in zip(vals_list, lines, strict=True)
                        for protected in self.env[
                            "account.move"
                        ]._get_field_protections(vals, line)
                    ]
                )
            )
            container["records"] = lines
        _debug.pipeline("lines_created_synced", lines=lines, moves=moves)

        lines._check_tax_lock_date()

        lines._log_tracked_change(
            lambda link: _("Journal Item %s created", link),
            lambda line, fnames: (line, dict.fromkeys(fnames)),
        )

        lines.move_id._sync_business_models(["line_ids"])
        lines.filtered(
            lambda l: l.parent_state == "draft"
        ).analytic_line_ids.with_context(skip_analytic_sync=True).unlink()
        return lines

    @_debug.perf.timed
    def _check_write_on_hashed_entry(self, vals):
        guarded_fnames = set(self._get_fields_integrity_hash()) | {
            "inalterable_hash",
            "deductible_amount",
        }
        if {"debit", "credit"} & guarded_fnames:
            guarded_fnames.add("balance")
        violated_fields = set(vals) & guarded_fnames
        hashed_moves = self.move_id.filtered("inalterable_hash")
        if not (hashed_moves and violated_fields):
            return
        AccountMove = self.env["account.move"]
        if not any(
            AccountMove._field_will_change(line, vals, fname)
            for line in self.filtered(lambda l: l.move_id.inalterable_hash)
            for fname in violated_fields
        ):
            return
        _debug.logic(
            "hashed_entry_write_blocked",
            moves=hashed_moves,
            fields=violated_fields,
        )
        raise UserError(
            _(
                "You cannot edit the following fields: %(fields)s.\n"
                "The following entries are already hashed:\n%(entries)s",
                fields=[f["string"] for f in self.fields_get(violated_fields).values()],
                entries="\n".join(hashed_moves.mapped("name")),
            )
        )

    @_debug.perf.timed
    def _classify_write(self, vals):
        protected_fields = self._get_fields_lock_date_protected()
        fiscal_fields = set(protected_fields["fiscal"])
        tax_fields = set(protected_fields["tax"])
        reconciliation_fields = set(protected_fields["reconciliation"])
        AccountMove = self.env["account.move"]

        line_to_write = self
        lines_to_unreconcile = self.browse()
        st_lines_to_unreconcile = self.env["account.bank.statement.line"]
        tax_lock_check_ids = []
        matching2lines = None

        for line in self:
            changed_fields = {
                fname
                for fname in vals
                if AccountMove._field_will_change(line, vals, fname)
            }
            if not changed_fields:
                line_to_write -= line
                continue

            posted = line.parent_state == "posted"
            if posted and changed_fields & {"tax_ids", "tax_line_id"}:
                _debug.logic("posted_tax_change_refused", line=line)
                raise UserError(
                    _(
                        "You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so."
                    )
                )
            if posted and changed_fields & fiscal_fields:
                line.move_id._check_fiscal_lock_dates()
            if posted and changed_fields & tax_fields:
                tax_lock_check_ids.append(line.id)

            if not (line.matching_number and changed_fields & reconciliation_fields):
                continue
            changing_fields = changed_fields & reconciliation_fields
            if matching2lines is None:
                matching2lines = self._reconciled_by_number()
            whole_reconciliation_here = all(
                reconciled_line in self
                for reconciled_line in matching2lines[line.matching_number]
            )
            if changing_fields - {"account_id"} or not whole_reconciliation_here:
                lines_to_unreconcile += line
                st_lines_to_unreconcile += (
                    line.matched_debit_ids.debit_move_id
                    + line.matched_credit_ids.credit_move_id
                ).statement_line_id

        _debug.logic(
            "write_classified",
            lines=self,
            to_write=line_to_write,
            to_unreconcile=lines_to_unreconcile,
            st_lines=st_lines_to_unreconcile,
            tax_lock_checks=len(tax_lock_check_ids),
            reconciliation_touched=matching2lines is not None,
        )
        return (
            line_to_write,
            lines_to_unreconcile,
            st_lines_to_unreconcile,
            tax_lock_check_ids,
        )

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if not vals:
            return True
        account_to_write = (
            self.env["account.account"].browse(vals["account_id"])
            if "account_id" in vals
            else None
        )

        if account_to_write and not account_to_write.active:
            raise UserError(_("You cannot use an archived account."))

        vals = self._normalize_vals(vals)

        self._check_write_on_hashed_entry(vals)

        (
            line_to_write,
            lines_to_unreconcile,
            st_lines_to_unreconcile,
            tax_lock_check_ids,
        ) = self._classify_write(vals)

        if _debug.logic.enabled and lines_to_unreconcile:
            _debug.logic(
                "write_reconciliation_fields_changed_unreconciling",
                lines_to_unreconcile=lines_to_unreconcile,
            )
        lines_to_unreconcile.remove_move_reconcile()
        st_lines_locked = self.env["account.bank.statement.line"]
        for st_line in st_lines_to_unreconcile:
            try:
                st_line.move_id._check_fiscal_lock_dates()
                st_line.move_id.line_ids._check_tax_lock_date()
            except UserError:
                st_lines_locked += st_line
        st_lines_to_unreconcile -= st_lines_locked
        if _debug.logic.enabled and st_lines_locked:
            _debug.logic(
                "write_statement_lines_kept_lock", st_lines_locked=st_lines_locked
            )
        if st_lines_to_unreconcile:
            st_lines_to_unreconcile.action_undo_reconciliation()

        self.browse(tax_lock_check_ids)._check_tax_lock_date()

        move_container = {"records": self.move_id}
        with (
            self.move_id._check_balanced(move_container),
            self.env.protecting(
                self.env["account.move"]._get_field_protections(vals, self)
            ),
            self.move_id._sync_dynamic_lines(move_container),
            self._sync_invoice({"records": self}),
        ):
            self = line_to_write
            if not self:
                _debug.logic("write_no_field_would_change")
                return True
            tracking_snapshot = self._snapshot_tracked_values(vals)

            result = super().write(vals)
            self.move_id._sync_business_models(["line_ids"])
            if any(field in vals for field in ["account_id", "currency_id"]):
                self._check_account_is_usable()

            self.browse(tax_lock_check_ids)._check_tax_lock_date()

            self._log_tracked_change(
                lambda link: _("Journal Item %s updated", link),
                lambda line, fnames: (line, tracking_snapshot.get(line.id, {})),
            )
            if "analytic_line_ids" in vals:
                self.filtered(
                    lambda l: l.parent_state == "draft"
                ).analytic_line_ids.with_context(skip_analytic_sync=True).unlink()

        return result

    def _is_valid_field_parameter(self, field, name):
        return name == "tracking" or super()._is_valid_field_parameter(field, name)

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_except_posted(self):
        _debug.lifecycle("_unlink_except_posted", records=self)
        if not self.env.context.get("force_delete"):
            non_zero_lines = self.filtered(lambda l: l.balance or l.amount_currency)
            restricted = non_zero_lines.move_id.filtered(lambda m: m.state == "posted")
            if restricted:
                raise UserError(
                    _(
                        "You can't delete a posted journal item. Don’t play games with your accounting records; reset the journal entry to draft before deleting it."
                    )
                )

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _prevent_automatic_line_deletion(self):
        _debug.lifecycle("_prevent_automatic_line_deletion", records=self)
        if not self.env.context.get("dynamic_unlink"):
            for line in self:
                if line.display_type == "tax" and line.move_id.line_ids.tax_ids:
                    _debug.logic("tax_line_deletion_blocked", line=line)
                    raise ValidationError(
                        _(
                            "You cannot delete a tax line as it would impact the tax report"
                        )
                    )
                if line.display_type == "payment_term":
                    _debug.logic("term_line_deletion_blocked", line=line)
                    raise ValidationError(
                        _(
                            "You cannot delete a payable/receivable line as it would not be consistent "
                            "with the payment terms"
                        )
                    )

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _except_hashed_entry_lines(self):
        _debug.lifecycle("_except_hashed_entry_lines", records=self)
        for line in self:
            if line.move_id.inalterable_hash:
                raise UserError(
                    _(
                        "You cannot delete journal items belonging to a locked journal entry."
                    )
                )

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        if not self:
            return True

        self.remove_move_reconcile()

        non_zero_lines = self.filtered(lambda l: l.balance or l.amount_currency)
        moves_to_check = non_zero_lines.move_id.filtered(lambda m: m.state == "posted")
        moves_to_check._check_fiscal_lock_dates()

        self._check_tax_lock_date()

        blank_line = self.browse([False])
        self._log_tracked_change(
            lambda link: _("Journal Item %s deleted", link),
            lambda line, fnames: (
                blank_line,
                {fname: line[fname] for fname in fnames},
            ),
        )

        move_container = {"records": self.move_id}
        with (
            self.move_id._check_balanced(move_container),
            self.move_id._sync_dynamic_lines(move_container),
        ):
            return super().unlink()

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name=None):
        names = []
        if move_name and move_name != "/":
            names.append(move_name)
        if move_ref and move_ref != "/":
            names.append(f"({move_ref})")
        if line_name and line_name not in [
            "/",
            move_name,
            f"{move_ref} - {move_name}",
            move_ref,
        ]:
            names.append(line_name)
        name = " ".join(names)
        return name or _("Draft Entry")

    @api.depends("move_id", "ref", "product_id")
    def _compute_display_name(self):
        for line in self:
            line.display_name = line._format_aml_name(
                line.name or line.product_id.display_name, line.ref, line.move_id.name
            )

    @api.depends(
        "account_id",
        "company_id",
        "move_id",
        "product_id",
        "display_type",
        "analytic_distribution",
    )
    @_debug.perf.timed
    def _compute_has_invalid_analytics(self):
        SKIPPED_ACCOUNT_TYPES = {
            "asset_receivable",
            "liability_payable",
            "asset_cash",
            "liability_credit_card",
        }
        lines_to_validate = self.filtered(
            lambda line: (
                line.display_type == "product"
                and line.account_id.account_type not in SKIPPED_ACCOUNT_TYPES
            )
        )
        (self - lines_to_validate).has_invalid_analytics = False
        for line in lines_to_validate:
            line.has_invalid_analytics = False
            try:
                line.with_context(validate_analytic=True)._check_distribution(
                    company_id=line.company_id.id,
                    product=line.product_id.id,
                    account=line.account_id.id,
                    business_domain=line._get_domain_analytic_business(),
                )
            except ValidationError:
                line.has_invalid_analytics = True

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        vals_list = super().copy_data(default=default)

        for line, vals in zip(self, vals_list, strict=True):
            if line.display_type == "payment_term" and line.move_id.is_invoice(True):
                vals.pop("name", None)
            if line.display_type in NON_ACCOUNTABLE_DISPLAY_TYPES:
                vals.pop("balance", None)
                vals.pop("account_id", None)
            if line.display_type == "product" and line.move_id.is_invoice(True):
                vals.pop("balance", None)
            if self.env.context.get("include_business_fields"):
                line._copy_data_extend_business_fields(vals)
        return vals_list

    def _field_to_sql(
        self, alias: str, field_expr: str, query: (Query | None) = None
    ) -> SQL:
        fname, property_name = fields.parse_field_expr(field_expr)
        if fname != "payment_date":
            return super()._field_to_sql(alias, field_expr, query)
        _debug.logic("payment_date_field_to_sql", alias=alias, property=property_name)
        sql = SQL(
            """
            CASE
                 WHEN %(discount_date)s >= %(today)s THEN %(discount_date)s
                 ELSE %(date_maturity)s
            END""",
            today=fields.Date.context_today(self),
            discount_date=super()._field_to_sql(alias, "discount_date", query),
            date_maturity=super()._field_to_sql(alias, "date_maturity", query),
        )
        if property_name:
            sql = self._fields[fname].property_to_sql(
                sql, property_name, self, alias, query
            )
        return sql

    @_debug.perf.timed
    def _search_panel_get_domain_image(
        self, field_name, domain, set_count=False, limit=False
    ):
        _debug.logic(
            "search_panel_image_routed",
            field=field_name,
            account_root=field_name == "account_root_id" and not set_count,
        )
        if field_name != "account_root_id" or set_count:
            return super()._search_panel_get_domain_image(
                field_name, domain, set_count, limit
            )

        domain = Domain(domain)
        if domain.is_false():
            _debug.logic("account_root_image_skipped", reason="false_domain")
            return {}

        query_account = self.env["account.account"]._search(
            [("company_ids", "in", self.env.companies.ids), ("code", "!=", False)]
        )
        account_code_alias = self.env["account.account"]._field_to_sql(
            "account_account", "code", query_account
        )

        query_line = self._search(domain, limit=1)
        query_line.add_where(SQL("account_account.id = account_move_line.account_id"))

        account_codes = self.env.execute_query(
            SQL(
                """
            SELECT %(account_code_alias)s AS code
              FROM %(account_table)s
             WHERE EXISTS(%(line_select)s)
               AND %(where_clause)s
            """,
                account_code_alias=account_code_alias,
                account_table=query_account.from_clause,
                line_select=query_line.select(),
                where_clause=query_account.where_clause,
            )
        )
        _debug.perf.count("account_root_codes_fetched", rows=len(account_codes))
        return {
            (root := self.env["account.root"]._from_account_code(code)).id: {
                "id": root.id,
                "display_name": root.display_name,
            }
            for (code,) in account_codes
        }

    def _get_reconciliation_aml_field_value(self, field, shadowed_aml_values):
        self.check_singleton()
        if shadowed_aml_values and field in shadowed_aml_values.get(self, {}):
            return shadowed_aml_values[self][field]
        else:
            return self[field]

    @api.model
    def _get_reconciliation_accounting_rate(self, aml, currency, shadowed_aml_values):
        balance = aml._get_reconciliation_aml_field_value(
            "balance", shadowed_aml_values
        )
        amount_currency = aml._get_reconciliation_aml_field_value(
            "amount_currency", shadowed_aml_values
        )
        if not aml.company_currency_id.is_zero(balance) and not currency.is_zero(
            amount_currency
        ):
            return abs(amount_currency / balance)
        return None

    @api.model
    def _get_reconciliation_odoo_rate(
        self, aml, other_aml, currency, shadowed_aml_values
    ):
        if forced_rate := self.env.context.get("forced_rate_from_register_payment"):
            return forced_rate

        def is_payment(record):
            return record.move_id.origin_payment_id or record.move_id.statement_line_id

        if other_aml and not is_payment(aml) and is_payment(other_aml):
            return self._get_reconciliation_accounting_rate(
                other_aml, currency, shadowed_aml_values
            )
        if aml.move_id.is_invoice(include_receipts=True):
            exchange_rate_date = aml.move_id.invoice_date
        else:
            exchange_rate_date = aml._get_reconciliation_aml_field_value(
                "date", shadowed_aml_values
            )
        return currency._get_conversion_rate(
            aml.company_currency_id, currency, aml.company_id, exchange_rate_date
        )

    @api.model
    @_debug.perf.timed
    def _prepare_move_line_residual_amounts(
        self,
        aml_values,
        counterpart_currency,
        shadowed_aml_values=None,
        other_aml_values=None,
    ):
        def get_odoo_rate(aml, other_aml, currency):
            return self._get_reconciliation_odoo_rate(
                aml, other_aml, currency, shadowed_aml_values
            )

        def get_accounting_rate(aml, currency):
            return self._get_reconciliation_accounting_rate(
                aml, currency, shadowed_aml_values
            )

        aml = aml_values["aml"]
        other_aml = (other_aml_values or {}).get("aml")
        remaining_amount_curr = aml_values["amount_residual_currency"]
        remaining_amount = aml_values["amount_residual"]
        company_currency = aml.company_currency_id
        currency = aml._get_reconciliation_aml_field_value(
            "currency_id", shadowed_aml_values
        )
        account = aml._get_reconciliation_aml_field_value(
            "account_id", shadowed_aml_values
        )
        has_zero_residual = company_currency.is_zero(remaining_amount)
        has_zero_residual_currency = currency.is_zero(remaining_amount_curr)
        is_rec_pay_account = account.account_type in (
            "asset_receivable",
            "liability_payable",
        )

        available_residual_per_currency = {}

        if not has_zero_residual:
            available_residual_per_currency[company_currency] = {
                "residual": remaining_amount,
                "rate": 1,
            }
        if currency != company_currency and not has_zero_residual_currency:
            available_residual_per_currency[currency] = {
                "residual": remaining_amount_curr,
                "rate": get_accounting_rate(aml, currency),
            }

        if (
            currency == company_currency
            and is_rec_pay_account
            and not has_zero_residual
            and counterpart_currency != company_currency
        ):
            rate = get_odoo_rate(aml, other_aml, counterpart_currency)
            residual_in_foreign_curr = counterpart_currency.round(
                remaining_amount * rate
            )
            if not counterpart_currency.is_zero(residual_in_foreign_curr):
                available_residual_per_currency[counterpart_currency] = {
                    "residual": residual_in_foreign_curr,
                    "rate": rate,
                }
        elif (
            currency == counterpart_currency
            and currency != company_currency
            and not has_zero_residual_currency
        ):
            available_residual_per_currency[counterpart_currency] = {
                "residual": remaining_amount_curr,
                "rate": get_accounting_rate(aml, currency),
            }
        return available_residual_per_currency

    @api.model
    @_debug.perf.timed
    def _prepare_reconciliation_context(
        self, debit_values, credit_values, shadowed_aml_values=None
    ):
        debit_aml = debit_values["aml"]
        credit_aml = credit_values["aml"]
        debit_currency = debit_aml._get_reconciliation_aml_field_value(
            "currency_id", shadowed_aml_values
        )
        credit_currency = credit_aml._get_reconciliation_aml_field_value(
            "currency_id", shadowed_aml_values
        )
        company_currency = debit_aml.company_currency_id

        debit_available = self._prepare_move_line_residual_amounts(
            debit_values,
            credit_currency,
            shadowed_aml_values=shadowed_aml_values,
            other_aml_values=credit_values,
        )
        credit_available = self._prepare_move_line_residual_amounts(
            credit_values,
            debit_currency,
            shadowed_aml_values=shadowed_aml_values,
            other_aml_values=debit_values,
        )
        recon_currency = pick_reconciliation_currency(
            debit_currency,
            credit_currency,
            company_currency,
            debit_available,
            credit_available,
        )
        debit_recon_values = debit_available.get(recon_currency)
        credit_recon_values = credit_available.get(recon_currency)
        if _debug.logic.enabled:
            _debug.logic(
                "recon_context_recon",
                debit=debit_aml,
                debit_currency=debit_currency,
                credit=credit_aml,
                credit_currency=credit_currency,
                company=company_currency,
                recon_currency=recon_currency,
                debit_available=sorted(c.id for c in debit_available),
                credit_available=sorted(c.id for c in credit_available),
            )

        context = {
            "shadowed_aml_values": shadowed_aml_values,
            "debit_aml": debit_aml,
            "credit_aml": credit_aml,
            "debit_currency": debit_currency,
            "credit_currency": credit_currency,
            "company_currency": company_currency,
            "debit_available": debit_available,
            "credit_available": credit_available,
            "recon_currency": recon_currency,
            "debit_recon_values": debit_recon_values,
            "credit_recon_values": credit_recon_values,
            "remaining_debit_amount": debit_values["amount_residual"],
            "remaining_credit_amount": credit_values["amount_residual"],
            "remaining_debit_amount_curr": debit_values["amount_residual_currency"],
            "remaining_credit_amount_curr": credit_values["amount_residual_currency"],
        }
        if not debit_recon_values or not credit_recon_values:
            return context

        recon_debit_amount = debit_recon_values["residual"]
        recon_credit_amount = -credit_recon_values["residual"]
        compare_amounts = recon_currency.compare_amounts(
            recon_debit_amount, recon_credit_amount
        )
        context.update(
            {
                "exchange_line_mode": (
                    recon_currency == company_currency
                    and debit_currency == credit_currency
                    and (
                        not debit_available.get(debit_currency)
                        or not credit_available.get(credit_currency)
                    )
                ),
                "min_recon_amount": min(recon_debit_amount, recon_credit_amount),
                "debit_fully_matched": compare_amounts <= 0,
                "credit_fully_matched": compare_amounts >= 0,
            }
        )
        return context

    @api.model
    @_debug.perf.timed
    def _prepare_reconciliation_exchange_difference(self, context, partials):
        exchange_lines_to_fix = self.env["account.move.line"]
        amounts_list = []
        debit_aml = context["debit_aml"]
        credit_aml = context["credit_aml"]
        company_currency = context["company_currency"]

        def book(aml, key, amount):
            nonlocal exchange_lines_to_fix
            exchange_lines_to_fix += aml
            amounts_list.append({key: amount})

        if context["recon_currency"] == company_currency:
            if context["debit_fully_matched"]:
                amount = (
                    context["remaining_debit_amount_curr"]
                    - partials["partial_debit_amount_currency"]
                )
                if not context["debit_currency"].is_zero(amount):
                    book(debit_aml, "amount_residual_currency", amount)
                    context["remaining_debit_amount_curr"] -= amount
            if context["credit_fully_matched"]:
                amount = (
                    context["remaining_credit_amount_curr"]
                    + partials["partial_credit_amount_currency"]
                )
                if not context["credit_currency"].is_zero(amount):
                    book(credit_aml, "amount_residual_currency", amount)
                    context["remaining_credit_amount_curr"] -= amount
        else:
            partial_amount = partials["partial_amount"]
            if context["debit_fully_matched"]:
                amount = context["remaining_debit_amount"] - partial_amount
                booked = not company_currency.is_zero(amount)
            else:
                amount = partials["partial_debit_amount"] - partial_amount
                booked = company_currency.compare_amounts(amount, 0.0) > 0
            if booked:
                book(debit_aml, "amount_residual", amount)
                context["remaining_debit_amount"] -= amount
                if context["debit_currency"] == company_currency:
                    context["remaining_debit_amount_curr"] -= amount

            if context["credit_fully_matched"]:
                amount = context["remaining_credit_amount"] + partial_amount
                booked = not company_currency.is_zero(amount)
            else:
                amount = partial_amount - partials["partial_credit_amount"]
                booked = company_currency.compare_amounts(amount, 0.0) < 0
            if booked:
                book(credit_aml, "amount_residual", amount)
                context["remaining_credit_amount"] -= amount
                if context["credit_currency"] == company_currency:
                    context["remaining_credit_amount_curr"] -= amount

        if not exchange_lines_to_fix:
            return None
        _debug.logic(
            "exchange_difference",
            exchange_lines_to_fix=exchange_lines_to_fix,
            amounts_list=amounts_list,
            exchange_line_mode=context.get("exchange_line_mode"),
        )

        shadowed = context["shadowed_aml_values"]
        exchange_values = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
            amounts_list,
            exchange_date=max(
                debit_aml._get_reconciliation_aml_field_value("date", shadowed),
                credit_aml._get_reconciliation_aml_field_value("date", shadowed),
            ),
        )
        exchange_values["to_post"] = (
            debit_aml.parent_state == "posted" and credit_aml.parent_state == "posted"
        )
        return exchange_values

    @api.model
    @_debug.perf.timed
    def _prepare_reconciliation_single_partial(
        self, debit_values, credit_values, shadowed_aml_values=None
    ):
        res = {"debit_values": debit_values, "credit_values": credit_values}
        context = self._prepare_reconciliation_context(
            debit_values, credit_values, shadowed_aml_values
        )
        if not context["debit_recon_values"]:
            res["debit_values"] = None
        if not context["credit_recon_values"]:
            res["credit_values"] = None
        if res["debit_values"] is None or res["credit_values"] is None:
            return res

        partials = prepare_partial_amounts(context)

        if not self.env.context.get(
            "no_exchange_difference"
        ) and not self.env.context.get("no_exchange_difference_no_recursive"):
            exchange_values = self._prepare_reconciliation_exchange_difference(
                context, partials
            )
            if exchange_values:
                res["exchange_values"] = exchange_values

        debit_values["amount_residual"] = (
            context["remaining_debit_amount"] - partials["partial_amount"]
        )
        credit_values["amount_residual"] = (
            context["remaining_credit_amount"] + partials["partial_amount"]
        )
        debit_values["amount_residual_currency"] = (
            context["remaining_debit_amount_curr"]
            - partials["partial_debit_amount_currency"]
        )
        credit_values["amount_residual_currency"] = (
            context["remaining_credit_amount_curr"]
            + partials["partial_credit_amount_currency"]
        )

        res["partial_values"] = {
            "amount": partials["partial_amount"],
            "debit_amount_currency": partials["partial_debit_amount_currency"],
            "credit_amount_currency": partials["partial_credit_amount_currency"],
            "debit_move_id": context["debit_aml"].id,
            "credit_move_id": context["credit_aml"].id,
        }
        _debug.logic(
            "partial_residual_after",
            debit=context["debit_aml"],
            credit=context["credit_aml"],
            amount=partials["partial_amount"],
            exchange=bool(res.get("exchange_values")),
            d=debit_values["amount_residual"],
            c=credit_values["amount_residual"],
        )

        if context["debit_currency"].is_zero(
            debit_values["amount_residual_currency"]
        ) and context["company_currency"].is_zero(debit_values["amount_residual"]):
            res["debit_values"] = None
        if context["credit_currency"].is_zero(
            credit_values["amount_residual_currency"]
        ) and context["company_currency"].is_zero(credit_values["amount_residual"]):
            res["credit_values"] = None
        return res

    @api.model
    @_debug.perf.timed
    def _prepare_reconciliation_amls(self, values_list, shadowed_aml_values=None):
        debit_values_list = iter(
            [
                x
                for x in values_list
                if x["aml"]._get_reconciliation_aml_field_value(
                    "balance", shadowed_aml_values
                )
                > 0.0
                or x["aml"]._get_reconciliation_aml_field_value(
                    "amount_currency", shadowed_aml_values
                )
                > 0.0
            ]
        )
        credit_values_list = iter(
            [
                x
                for x in values_list
                if x["aml"]._get_reconciliation_aml_field_value(
                    "balance", shadowed_aml_values
                )
                < 0.0
                or x["aml"]._get_reconciliation_aml_field_value(
                    "amount_currency", shadowed_aml_values
                )
                < 0.0
            ]
        )
        debit_values = None
        credit_values = None
        fully_reconciled_aml_ids = set()

        all_results = []
        exhausted_side = None  # debuglog
        while True:
            if not debit_values:
                debit_values = next(debit_values_list, None)
                if not debit_values:
                    exhausted_side = "debit"  # debuglog
                    break

            if not credit_values:
                credit_values = next(credit_values_list, None)
                if not credit_values:
                    exhausted_side = "credit"  # debuglog
                    break

            results = self._prepare_reconciliation_single_partial(
                debit_values,
                credit_values,
                shadowed_aml_values=shadowed_aml_values,
            )
            if results.get("partial_values"):
                all_results.append(results)
            if results["debit_values"] is None:
                fully_reconciled_aml_ids.add(debit_values["aml"].id)
                debit_values = None
            if results["credit_values"] is None:
                fully_reconciled_aml_ids.add(credit_values["aml"].id)
                credit_values = None

        _debug.pipeline(
            "amls_paired_into_partials",
            amls=len(values_list),
            partials=len(all_results),
            fully_reconciled=len(fully_reconciled_aml_ids),
            exhausted_side=exhausted_side,
        )
        return all_results, fully_reconciled_aml_ids

    @api.model
    @_debug.perf.timed
    def _prepare_reconciliation_plan(
        self, plan, amls_values_map, shadowed_aml_values=None
    ):
        all_fully_reconciled_aml_ids = set()
        all_results = []

        def process_amls(amls):
            remaining_amls = amls.filtered(
                lambda aml: aml.id not in all_fully_reconciled_aml_ids
            )
            if len(remaining_amls.mapped("partner_id")) > 1:
                remaining_amls = remaining_amls.sorted(
                    lambda aml: (aml.partner_id and aml.partner_id.id) or False
                )
            amls_results, fully_reconciled_aml_ids = self._prepare_reconciliation_amls(
                [amls_values_map[aml] for aml in remaining_amls],
                shadowed_aml_values=shadowed_aml_values,
            )
            all_fully_reconciled_aml_ids.update(fully_reconciled_aml_ids)
            all_results.extend(amls_results)

        def process_leaf(plan_node):
            for child_node in plan_node.get("nodes", []):
                process_leaf(child_node)

            process_amls(plan_node["amls"])

        process_leaf(plan)
        return all_results

    @_debug.perf.timed
    def _check_amls_exigibility_for_reconciliation(self, shadowed_aml_values=None):
        not_reconciled_partial_matching_numbers = set(
            self.filtered(
                lambda aml: (
                    not aml.reconciled
                    and aml.matching_number
                    and aml.matching_number.startswith("P")
                )
            ).mapped("matching_number")
        )
        amls = self.filtered(
            lambda aml: (
                not aml.reconciled
                or aml.matching_number not in not_reconciled_partial_matching_numbers
            )
        )

        if not amls:
            _debug.logic("exigibility_check_skipped", reason="no_open_amls", lines=self)
            return

        if any(aml.reconciled for aml in amls):
            _debug.logic("already_reconciled_refused", reconcile=amls)
            raise UserError(
                _(
                    "You are trying to reconcile some entries that are already reconciled."
                )
            )
        if any(aml.parent_state == "cancel" for aml in amls):
            raise UserError(_("You can not reconcile cancelled entries."))
        accounts = amls.mapped(
            lambda x: x._get_reconciliation_aml_field_value(
                "account_id", shadowed_aml_values
            )
        )
        if not accounts:
            raise UserError(
                _("You can not reconcile journal items that carry no account.")
            )
        if len(accounts) > 1:
            _debug.logic(
                "reconcile_accounts_mismatch", reconcile=amls, accounts=accounts
            )
            raise UserError(
                _(
                    "Entries are not from the same account: %s",
                    ", ".join(accounts.mapped("display_name")),
                )
            )
        if len(amls.company_id.root_id) > 1:
            raise UserError(
                _(
                    "Entries don't belong to the same company: %s",
                    ", ".join(amls.company_id.mapped("display_name")),
                )
            )
        if not accounts.reconcile and accounts.account_type not in (
            "asset_cash",
            "liability_credit_card",
        ):
            _debug.logic(
                "account_not_reconcilable",
                reconcile=amls,
                account=accounts,
                account_type=accounts.account_type,
            )
            raise UserError(
                _(
                    "Account %s does not allow reconciliation. First change the configuration of this account "
                    "to allow it.",
                    accounts.display_name,
                )
            )

    @api.model
    @_debug.perf.timed
    def _optimize_reconciliation_plan(
        self, reconciliation_plan, shadowed_aml_values=None
    ):
        def value_of(aml, field):
            return aml._get_reconciliation_aml_field_value(field, shadowed_aml_values)

        def sort_key(aml):
            key = (
                value_of(aml, "date_maturity") or value_of(aml, "date"),
                value_of(aml, "currency_id"),
            )
            if self.env.context.get("reduced_line_sorting"):
                return key
            return (*key, value_of(aml, "amount_currency"), value_of(aml, "balance"))

        def as_node(amls):
            return {"amls": amls, "aml_ids": set(amls.ids)}

        def process_amls(amls):
            sorted_amls = amls.sorted(key=sort_key)
            currencies = sorted_amls.mapped(lambda x: value_of(x, "currency_id"))
            results = as_node(sorted_amls)
            if len(currencies) != 1:
                results["nodes"] = [
                    as_node(
                        sorted_amls.filtered(
                            lambda x, currency=currency: (
                                value_of(x, "currency_id") == currency
                            )
                        )
                    )
                    for currency in currencies
                ]
            return results

        def process_children(children):
            node = {
                "nodes": [],
                "aml_ids": set(),
            }
            for child in children:
                results = process_leaf(child)
                if results:
                    node["nodes"].append(results)
                    node["aml_ids"].update(results["aml_ids"])
            node["amls"] = self.browse(node["aml_ids"])
            return node

        def process_leaf(item):
            if not item:
                return None

            if isinstance(item, models.BaseModel):
                return process_amls(item)
            else:
                return process_children(item)

        plan_list = []
        all_aml_ids = set()
        empty_items = 0  # debuglog
        for item in reconciliation_plan:
            plan_node = process_leaf(item)
            if not plan_node or not plan_node.get("amls"):
                empty_items += 1  # debuglog
                continue

            amls = plan_node["amls"]
            amls._check_amls_exigibility_for_reconciliation(
                shadowed_aml_values=shadowed_aml_values
            )
            plan_list.append(plan_node)
            all_aml_ids.update(plan_node["aml_ids"])

        if _debug.logic.enabled:
            _debug.logic(
                "plan_nodes_built",
                nodes=len(plan_list),
                empty_items=empty_items,
                nested_nodes=sum(1 for node in plan_list if node.get("nodes")),
                amls=len(all_aml_ids),
                reduced_sorting=bool(self.env.context.get("reduced_line_sorting")),
            )
        return plan_list, self.browse(all_aml_ids)

    @_debug.perf.timed
    def _reconcile_pre_hook(self):
        invoices = self.move_id.filtered(
            lambda move: move.is_invoice(include_receipts=True)
        )
        return {
            "not_paid_invoices": invoices.filtered(
                lambda inv: inv.payment_state not in ("paid", "in_payment")
            ),
            "in_payment_invoices": invoices.filtered(
                lambda inv: inv.payment_state == "in_payment"
            ),
        }

    @_debug.perf.timed
    def _reconcile_post_hook(self, data):
        (
            data["not_paid_invoices"].filtered(
                lambda inv: inv.payment_state in ("paid", "in_payment")
            )
            + data["in_payment_invoices"].filtered(
                lambda inv: inv.payment_state == "paid"
            )
        )._invoice_paid_hook()

    @api.model
    @_debug.perf.timed
    def _reconcile_plan(self, reconciliation_plan):
        plan_list, all_amls = self._optimize_reconciliation_plan(reconciliation_plan)
        _debug.pipeline(
            "plan_over",
            reconcile=all_amls,
            plan_list_count=len(plan_list),
            all_amls=all_amls,
        )
        move_container = {"records": all_amls.move_id}
        with (
            all_amls.move_id._check_balanced(move_container),
            all_amls.move_id._sync_dynamic_lines(move_container),
        ):
            self._reconcile_plan_with_sync(plan_list, all_amls)

    @_debug.perf.timed
    def _reconcile_plan_with_sync(self, plan_list, all_amls):
        all_amls.fetch(["move_id", "matched_debit_ids", "matched_credit_ids"])
        pre_hook_data = all_amls._reconcile_pre_hook()
        aml_values_map = {
            aml: {
                "aml": aml,
                "amount_residual": aml.amount_residual,
                "amount_residual_currency": aml.amount_residual_currency,
                "parent_state": aml.parent_state,
            }
            for aml in all_amls
        }
        self._create_reconciliation_partials(plan_list, aml_values_map)
        self._create_reconciliation_cash_basis_moves(plan_list)
        involved_amls = self._create_full_reconciles(
            plan_list, all_amls, aml_values_map
        )
        _debug.pipeline(
            "done_involved", reconcile=all_amls, involved_amls=involved_amls
        )
        involved_amls._reconcile_post_hook(pre_hook_data)

    @_debug.perf.timed
    def _create_reconciliation_partials(self, plan_list, aml_values_map):
        partials_values_list = []
        exchange_diff_values_list = []
        exchange_index_per_partial_index = {}
        all_plan_results = []
        for plan in plan_list:
            plan_results = self.with_context(
                no_exchange_difference=self.env.context.get("no_exchange_difference"),
                no_exchange_difference_no_recursive=self.env.context.get(
                    "no_exchange_difference_no_recursive", False
                ),
            )._prepare_reconciliation_plan(plan, aml_values_map)
            all_plan_results.append(plan_results)
            for results in plan_results:
                if (
                    results.get("exchange_values")
                    and results["exchange_values"]["move_values"]["line_ids"]
                ):
                    exchange_index_per_partial_index[len(partials_values_list)] = len(
                        exchange_diff_values_list
                    )
                    exchange_diff_values_list.append(results["exchange_values"])
                partials_values_list.append(results["partial_values"])

        partials = self.env["account.partial.reconcile"].create(partials_values_list)
        _debug.pipeline(
            "_create_reconciliation_partials_diff",
            partials_values_list_count=len(partials_values_list),
            partials=partials,
            exchange_diff_values_list_count=len(exchange_diff_values_list),
        )
        if self.env.context.get("add_caba_vals"):
            partials._set_draft_caba_move_vals()
        start_range = 0
        for plan_results, plan in zip(all_plan_results, plan_list, strict=True):
            size = len(plan_results)
            plan["partials"] = partials[start_range : start_range + size]
            start_range += size

        exchange_moves = self._create_exchange_difference_moves(
            exchange_diff_values_list
        )
        for partial_index, exchange_index in exchange_index_per_partial_index.items():
            partials[partial_index].exchange_move_id = exchange_moves[exchange_index]

    @_debug.perf.timed
    def _create_reconciliation_cash_basis_moves(self, plan_list):
        if self.env.context.get("move_reverse_cancel") or self.env.context.get(
            "no_cash_basis"
        ):
            _debug.logic("_create_reconciliation_cash_basis_moves_skipped_context")
            return
        for plan in plan_list:
            amls = plan["amls"]
            needed = any(
                amls.company_id.mapped("tax_exigibility")
            ) and amls.account_id.account_type in (
                "asset_receivable",
                "liability_payable",
            )
            _debug.logic("cash_basis_moves", needed=needed, amls=amls)
            if needed:
                plan["partials"].with_context(
                    no_exchange_difference_no_recursive=False
                )._create_tax_cash_basis_moves()
                plan["partials"]._set_draft_caba_move_vals()

    @_debug.perf.timed
    def _create_full_reconciles(self, plan_list, all_amls, aml_values_map):
        def is_line_reconciled(aml, has_multiple_currencies):
            if aml.reconciled:
                return True
            if not aml.matched_debit_ids and not aml.matched_credit_ids:
                return False
            if has_multiple_currencies:
                return aml.company_currency_id.is_zero(aml.amount_residual)
            return aml.currency_id.is_zero(aml.amount_residual_currency)

        full_batches = []
        all_aml_ids = set()
        number2lines = all_amls._reconciled_by_number()
        batched_aml_ids = set()
        for plan in plan_list:
            plan_amls = plan["amls"]
            if not plan_amls or batched_aml_ids.issuperset(plan_amls.ids):
                continue
            involved_amls = plan_amls._filter_reconciled_by_number(number2lines)
            all_aml_ids.update(involved_amls.ids)
            batched_aml_ids.update(
                aml.id for aml in involved_amls if aml in aml_values_map
            )
            has_multiple_currencies = len(involved_amls.currency_id) > 1
            full_batches.append(
                {
                    "amls": involved_amls,
                    "is_fully_reconciled": all(
                        is_line_reconciled(involved_aml, has_multiple_currencies)
                        for involved_aml in involved_amls
                    ),
                }
            )

        all_amls = self.browse(list(all_aml_ids))
        all_amls.fetch(["move_id", "matched_debit_ids", "matched_credit_ids"])

        full_reconcile_values_list = []
        for full_batch in full_batches:
            if not full_batch["is_fully_reconciled"]:
                continue
            amls = full_batch["amls"]
            if len(amls.full_reconcile_id) == 1 and all(
                aml.full_reconcile_id for aml in amls
            ):
                continue
            involved_partials = amls.matched_debit_ids | amls.matched_credit_ids
            full_reconcile_values_list.append(
                {
                    "partial_reconcile_ids": [
                        Command.link(partial.id) for partial in involved_partials
                    ],
                    "reconciled_line_ids": [Command.link(aml.id) for aml in amls],
                }
            )
        _debug.pipeline(
            "_create_full_reconciles_reconcile_create",
            full_batches_count=len(full_batches),
            full_reconcile_values_list_count=len(full_reconcile_values_list),
        )
        self.env["account.full.reconcile"].create(full_reconcile_values_list)
        return all_amls

    def _get_exchange_journal(self, company):
        return company.currency_exchange_journal_id

    def _get_exchange_account(self, company, amount):
        if amount > 0.0:
            return company.expense_currency_exchange_account_id
        return company.income_currency_exchange_account_id

    @_debug.perf.timed
    def _prepare_exchange_difference_move_vals(
        self, amounts_list, company=None, exchange_date=None, **kwargs
    ):
        company = (
            (
                self.move_id.filtered(lambda m: m.is_invoice(True)) or self.move_id
            ).company_id
            or company
        )[:1]
        if not company:
            _debug.logic("exchange_move_skipped", reason="no_company", lines=self)
            return None

        journal = self._get_exchange_journal(company)
        _debug.logic(
            "exchange_journal_resolved",
            company=company,
            journal=journal,
            exchange_date=exchange_date,
        )
        accounting_exchange_date = (
            journal.with_context(move_date=exchange_date).accounting_date
            if journal
            else date.min
        )

        move_vals = {
            "move_type": "entry",
            "name": "/",
            "date": accounting_exchange_date,
            "journal_id": journal.id,
            "line_ids": [],
            "always_tax_exigible": True,
        }
        to_reconcile = []
        for line, amounts in zip(self, amounts_list, strict=True):
            move_vals["date"] = max(move_vals["date"], line.date)

            if "amount_residual" in amounts:
                amount_residual = amounts["amount_residual"]
                amount_residual_currency = 0.0
                if line.currency_id == line.company_id.currency_id:
                    amount_residual_currency = amount_residual
                amount_residual_to_fix = amount_residual
                if line.company_currency_id.is_zero(amount_residual):
                    continue
            elif "amount_residual_currency" in amounts:
                amount_residual = 0.0
                amount_residual_currency = amounts["amount_residual_currency"]
                amount_residual_to_fix = amount_residual_currency
                if line.currency_id.is_zero(amount_residual_currency):
                    continue
            else:
                continue

            sequence = len(move_vals["line_ids"])
            line_vals = line._prepare_exchange_difference_line_vals(
                company,
                sequence,
                amount_residual,
                amount_residual_currency,
                amount_residual_to_fix,
                kwargs.get("exchange_analytic_distribution"),
            )
            move_vals["line_ids"] += [Command.create(vals) for vals in line_vals]
            to_reconcile.append((line, sequence))

        _debug.pipeline(
            "exchange_move_vals_prepared",
            lines=self,
            line_vals=len(move_vals["line_ids"]),
            to_reconcile=len(to_reconcile),
            date=move_vals["date"],
        )
        return {"move_values": move_vals, "to_reconcile": to_reconcile}

    @_debug.perf.timed
    def _prepare_exchange_difference_line_vals(
        self,
        company,
        sequence,
        amount_residual,
        amount_residual_currency,
        amount_residual_to_fix,
        analytic_distribution=None,
    ):
        self.check_singleton()
        counterpart_account = self._get_exchange_account(
            company, amount_residual_to_fix
        )
        _debug.logic(
            "exchange_counterpart_chosen",
            line=self,
            account=counterpart_account,
            side="expense" if amount_residual_to_fix > 0.0 else "income",
            residual_only=not amount_residual,
        )
        name = _("Currency exchange rate difference")
        debit = -amount_residual if amount_residual < 0.0 else 0.0
        credit = max(0.0, amount_residual)
        counterpart_vals = {
            "name": name,
            "debit": credit,
            "credit": debit,
            "amount_currency": amount_residual_currency,
            "account_id": counterpart_account.id,
            "currency_id": self.currency_id.id,
            "partner_id": self.partner_id.id,
            "sequence": sequence + 1,
        }
        if analytic_distribution:
            counterpart_vals["analytic_distribution"] = analytic_distribution
        return [
            {
                "name": name,
                "debit": debit,
                "credit": credit,
                "amount_currency": -amount_residual_currency,
                "full_reconcile_id": self.full_reconcile_id.id,
                "account_id": self.account_id.id,
                "currency_id": self.currency_id.id,
                "partner_id": self.partner_id.id,
                "sequence": sequence,
                "reconciled_lines_ids": [Command.set(self.ids)],
            },
            counterpart_vals,
        ]

    @api.model
    @_debug.perf.timed
    def _create_exchange_difference_moves(self, exchange_diff_values_list):
        if not exchange_diff_values_list:
            return self.env["account.move"]

        exchange_move_values_list = []
        journal_ids = set()
        for exchange_diff_values in exchange_diff_values_list:
            move_vals = exchange_diff_values["move_values"]
            exchange_move_values_list.append(move_vals)

            if not move_vals["journal_id"]:
                raise UserError(
                    _(
                        "You have to configure the 'Exchange Gain or Loss Journal' in your company settings, to manage"
                        " automatically the booking of accounting entries related to differences between exchange rates."
                    )
                )

            journal_ids.add(move_vals["journal_id"])

        journals = self.env["account.journal"].browse(list(journal_ids))
        for journal in journals:
            if not journal.company_id.expense_currency_exchange_account_id:
                raise UserError(
                    _(
                        "You should configure the 'Loss Exchange Rate Account' in your company settings, to manage"
                        " automatically the booking of accounting entries related to differences between exchange rates."
                    )
                )
            if not journal.company_id.income_currency_exchange_account_id.id:
                raise UserError(
                    _(
                        "You should configure the 'Gain Exchange Rate Account' in your company settings, to manage"
                        " automatically the booking of accounting entries related to differences between exchange rates."
                    )
                )

        exchange_moves = (
            self.env["account.move"]
            .with_context(no_exchange_difference=True)
            .create(exchange_move_values_list)
        )
        _debug.pipeline(
            "_create_exchange_difference_moves_created",
            exchange_moves=exchange_moves,
            journals=sorted(journal_ids),
        )

        exchange_moves_to_post = self.env["account.move"]
        for exchange_move, vals in zip(
            exchange_moves, exchange_diff_values_list, strict=True
        ):
            if vals["to_post"]:
                exchange_moves_to_post |= exchange_move

        if exchange_moves_to_post:
            exchange_moves_to_post.with_context(validate_analytic=False)._post(
                soft=False
            )

        return exchange_moves

    def reconcile(self):
        return self._reconcile_plan([self])

    def remove_move_reconcile(self):
        partials = self.matched_debit_ids | self.matched_credit_ids
        _debug.pipeline(
            "remove_move_reconcile_unlinking", reconcile=self, partials=partials
        )
        partials.unlink()

    @_debug.perf.timed
    def action_unreconcile_match_entries(self):
        _debug.lifecycle("action_unreconcile_match_entries", records=self)
        active_ids = self.env.context.get("active_ids")
        if active_ids:
            move_lines = (
                self.env["account.move.line"].browse(active_ids)._all_reconciled_lines()
            )
            move_lines.remove_move_reconcile()

    @_debug.perf.timed
    def _reconcile_marked(self):
        temp_numbers = list(
            {
                line.matching_number
                for line in self
                if line.matching_number and line.matching_number.startswith("I")
            }
        )
        _debug.logic("marked_matching_numbers", lines=self, numbers=len(temp_numbers))
        if temp_numbers:
            for _matching_number, account, lines in self._read_group(
                domain=[("matching_number", "in", temp_numbers)],
                groupby=["matching_number", "account_id"],
                aggregates=["id:recordset"],
            ):
                if all(move.state == "posted" for move in lines.move_id):
                    if not account.reconcile:
                        _debug.logic("account_reconcile_forced_on", account=account)
                        _logger.info(
                            "%s has reconciled lines, changing the config",
                            account.display_name,
                        )
                        account.reconcile = True
                    lines.with_context(
                        no_exchange_difference=True, no_cash_basis=True
                    ).reconcile()

    def _get_matched_move_ids(self):
        return self.matched_debit_ids | self.matched_credit_ids

    def _get_domain_analytic_business(self):
        self.check_singleton()
        move = self.move_id
        if move.is_sale_document(include_receipts=True):
            return "invoice"
        if move.is_purchase_document(include_receipts=True):
            return "bill"
        return "general"

    @_debug.perf.timed
    def _check_analytic_distribution(self):
        lines_with_missing_analytic_distribution = self.env["account.move.line"]
        for line in self.filtered(lambda line: line.display_type == "product"):
            try:
                line._check_distribution(
                    company_id=line.company_id.id,
                    product=line.product_id.id,
                    account=line.account_id.id,
                    business_domain=line._get_domain_analytic_business(),
                )
            except ValidationError:
                lines_with_missing_analytic_distribution += line
        if lines_with_missing_analytic_distribution:
            _debug.logic(
                "analytic_distribution_incomplete",
                lines=lines_with_missing_analytic_distribution,
                moves=self.move_id,
            )
            msg = _("One or more lines require a 100% analytic distribution.")
            if len(self.move_id) == 1:
                raise ValidationError(msg)
            raise RedirectWarning(
                message=msg,
                action={
                    "view_mode": "list",
                    "name": _("Items With Missing Analytic Distribution"),
                    "res_model": "account.move.line",
                    "type": "ir.actions.act_window",
                    "domain": [
                        ("id", "in", lines_with_missing_analytic_distribution.ids)
                    ],
                    "views": [
                        (self.env.ref("account.view_account_move_line_list").id, "list")
                    ],
                },
                button_text=_("See items"),
            )

    @_debug.perf.timed
    def _create_analytic_lines(self):
        self._check_analytic_distribution()
        analytic_line_vals = []
        for line in self:
            analytic_line_vals.extend(line._prepare_analytic_lines())
        _debug.pipeline(
            "_create_analytic_lines_line",
            analytic_line_vals_count=len(analytic_line_vals),
            records=self,
        )

        context = dict(self.env.context)
        context.pop("default_account_id", None)
        context["skip_analytic_sync"] = True
        self.env["account.analytic.line"].with_context(context).create(
            analytic_line_vals
        )

    @_debug.perf.timed
    def _prepare_analytic_lines(self):
        self.check_singleton()
        analytic_line_vals = []
        if self.analytic_distribution:
            distribution_on_each_plan = {}
            for account_ids, distribution in self.analytic_distribution.items():
                line_values = self._prepare_analytic_distribution_line(
                    float(distribution), account_ids, distribution_on_each_plan
                )
                if not self.company_currency_id.is_zero(line_values.get("amount")):
                    analytic_line_vals.append(line_values)

            self._round_analytic_distribution_line(analytic_line_vals)
        return analytic_line_vals

    @_debug.perf.timed
    def _prepare_analytic_distribution_line(
        self, distribution, account_ids, distribution_on_each_plan
    ):
        self.check_singleton()
        account_field_values = {}
        decimal_precision = self.env["decimal.precision"].get_precision(
            "Percentage Analytic"
        )
        amount = 0
        for account in (
            self.env["account.analytic.account"]
            .browse(map(int, account_ids.split(",")))
            .exists()
        ):
            distribution_plan = (
                distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            )
            if (
                float_compare(
                    distribution_plan, 100, precision_digits=decimal_precision
                )
                == 0
            ):
                amount = (
                    -self.balance
                    * (100 - distribution_on_each_plan.get(account.root_plan_id, 0))
                    / 100.0
                )
            else:
                amount = -self.balance * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.name or (
            (self.ref or "/") + " -- " + (self.partner_id.name or "/")
        )
        return {
            "name": default_name,
            "date": self.date,
            **account_field_values,
            "partner_id": self.partner_id.id,
            "unit_amount": self.quantity,
            "product_id": (self.product_id and self.product_id.id) or False,
            "product_uom_id": (self.product_uom_id and self.product_uom_id.id) or False,
            "amount": amount,
            "general_account_id": self.account_id.id,
            "ref": self.ref,
            "move_line_id": self.id,
            "user_id": self.move_id.invoice_user_id.id or self.env.uid,
            "company_id": self.company_id.id or self.env.company.id,
            "category": "invoice"
            if self.move_id.is_sale_document()
            else "vendor_bill"
            if self.move_id.is_purchase_document()
            else "other",
        }

    def _related_analytic_distribution(self):
        return {}

    def _update_analytic_distribution(self):
        if self.env.context.get("skip_analytic_sync"):
            return
        for line in self:
            distribution = defaultdict(float)
            for analytic_line in line.analytic_line_ids:
                key = analytic_line._get_distribution_key()
                if line.balance:
                    distribution[key] += -analytic_line.amount / line.balance * 100
                else:
                    distribution[key] = 100
            line.with_context(skip_analytic_sync=True).analytic_distribution = dict(
                distribution
            )
            _debug.pipeline(
                "analytic_lines", line=line, distribution=dict(distribution)
            )

    def _round_analytic_distribution_line(self, analytic_lines_vals):
        if not analytic_lines_vals:
            return

        rounding_error = 0
        for line in analytic_lines_vals:
            rounded_amount = self.company_currency_id.round(line["amount"])
            rounding_error += rounded_amount - line["amount"]
            line["amount"] = rounded_amount

        for line in analytic_lines_vals:
            if self.company_currency_id.is_zero(rounding_error):
                break
            amt = max(
                self.company_currency_id.rounding,
                abs(
                    self.company_currency_id.round(
                        rounding_error / len(analytic_lines_vals)
                    )
                ),
            )
            if rounding_error < 0.0:
                line["amount"] += amt
                rounding_error += amt
            else:
                line["amount"] -= amt
                rounding_error -= amt

    @_debug.perf.timed
    def _prepare_installments_data(
        self, payment_currency=None, payment_date=None, next_payment_date=None
    ):
        move = self.move_id
        move.check_singleton()

        payment_date = payment_date or fields.Date.context_today(self)

        term_lines = self.sorted(
            key=lambda line: (line.date_maturity or date.max, line.date)
        )
        sign = move.direction_sign
        installments = []
        first_installment_mode = False
        current_installment_mode = False
        for i, line in enumerate(term_lines, start=1):
            installment = {
                "number": i,
                "line": line,
                "date_maturity": line.date_maturity or line.date,
                "amount_residual_currency": line.amount_residual_currency,
                "amount_residual": line.amount_residual,
                "amount_residual_currency_unsigned": -sign
                * line.amount_residual_currency,
                "amount_residual_unsigned": -sign * line.amount_residual,
                "type": "other",
                "reconciled": line.reconciled,
            }
            installments.append(installment)

            if line.reconciled:
                continue

            if move._is_eligible_for_early_payment_discount(
                payment_currency or line.currency_id, payment_date
            ):
                installment.update(
                    {
                        "amount_residual_currency": line.discount_amount_currency,
                        "amount_residual": line.discount_balance,
                        "amount_residual_currency_unsigned": -sign
                        * line.discount_amount_currency,
                        "amount_residual_unsigned": -sign * line.discount_balance,
                        "discount_amount_currency": line.amount_currency
                        - line.discount_amount_currency,
                        "discount_amount": line.balance - line.discount_balance,
                        "type": "early_payment_discount",
                    }
                )
                continue

            if line.display_type == "payment_term":
                if (
                    next_payment_date
                    and (line.date_maturity or line.date) <= next_payment_date
                ):
                    current_installment_mode = "before_date"
                elif (line.date_maturity or line.date) < payment_date:
                    first_installment_mode = current_installment_mode = "overdue"
                elif not first_installment_mode:
                    first_installment_mode = "next"
                    current_installment_mode = "next"
                elif current_installment_mode == "overdue":
                    current_installment_mode = "next"
                installment["type"] = current_installment_mode

        if _debug.logic.enabled:
            _debug.logic(
                "installments_classified",
                move=move,
                count=len(installments),
                types=sorted({item["type"] for item in installments}),
                first_mode=first_installment_mode,
                next_payment_date=next_payment_date,
            )
        return installments

    def _get_fields_integrity_hash(self):
        hash_version = self.env.context.get("hash_version", MAX_HASH_VERSION)
        if hash_version == 1:
            return ["debit", "credit", "account_id", "partner_id"]
        elif hash_version in (2, 3, 4):
            return ["name", "debit", "credit", "account_id", "partner_id"]
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

    @_debug.perf.timed
    def _reconciled_lines(self):
        ids = []
        for aml in self.filtered("reconciled"):
            ids.extend(
                [r.debit_move_id.id for r in aml.matched_debit_ids]
                if aml.credit > 0
                else [r.credit_move_id.id for r in aml.matched_credit_ids]
            )
            ids.append(aml.id)
        return ids

    @_debug.perf.timed
    def _reconciled_by_number(self) -> dict:
        matching_numbers = [n for n in set(self.mapped("matching_number")) if n]
        if matching_numbers:
            return {
                number: lines.with_env(self.env)
                for number, lines in self.sudo()._read_group(
                    domain=[("matching_number", "in", matching_numbers)],
                    groupby=["matching_number"],
                    aggregates=["id:recordset"],
                )
            }
        return {}

    def _filter_reconciled_by_number(self, mapping: dict):
        matching_numbers = [
            n
            for n in set(self.mapped("matching_number"))
            if n and not n.startswith("I")
        ]

        return self | self.browse(
            [
                _id
                for number in matching_numbers
                for _id in mapping.get(number, self.browse()).ids
            ]
        )

    def _all_reconciled_lines(self):
        return self._filter_reconciled_by_number(self._reconciled_by_number())

    def _get_attachment_domains(self):
        domains = [
            [
                ("res_model", "=", "account.move"),
                ("res_id", "in", self.move_id.ids),
                ("res_field", "in", (False, "invoice_pdf_report_file")),
            ]
        ]
        if self.statement_id:
            domains.append(
                [
                    ("res_model", "=", "account.bank.statement"),
                    ("res_id", "in", self.statement_id.ids),
                ]
            )
        if self.payment_id:
            domains.append(
                [
                    ("res_model", "=", "account.payment"),
                    ("res_id", "in", self.payment_id.ids),
                ]
            )
        _debug.logic("attachment_domains_built", lines=self, domains=len(domains))
        return domains

    @api.model
    def _get_attachment_by_record(self, id_model2attachments, move_line):
        return (
            id_model2attachments.get(("account.move", move_line.move_id.id))
            or id_model2attachments.get(
                ("account.bank.statement", move_line.statement_id.id)
            )
            or id_model2attachments.get(("account.payment", move_line.payment_id.id))
        )

    @api.model
    def _get_domain_tax_exigible(self):
        return Domain(
            [
                "|",
                ("move_id.always_tax_exigible", "=", True),
                "|",
                "&",
                ("tax_line_id", "=", False),
                ("tax_ids", "=", False),
                "|",
                ("move_id.tax_cash_basis_rec_id", "!=", False),
                "|",
                ("tax_line_id.tax_exigibility", "!=", "on_payment"),
                (
                    "tax_ids.tax_exigibility",
                    "!=",
                    "on_payment",
                ),
            ]
        )

    def _get_invoiced_qty_per_product(self):
        qties = defaultdict(float)
        for aml in self:
            qty = aml.product_uom_id._get_quantity_reconcile(
                aml.quantity, aml.product_id.uom_id
            )
            if aml.move_id.move_type == "out_invoice":
                qties[aml.product_id] += qty
            elif aml.move_id.move_type == "out_refund":
                qties[aml.product_id] -= qty
        return qties

    def _get_fields_lock_date_protected(self):
        tax_fnames = ["balance", "tax_line_id", "tax_ids", "tax_tag_ids"]
        fiscal_fnames = tax_fnames + [
            "account_id",
            "journal_id",
            "amount_currency",
            "currency_id",
            "partner_id",
        ]
        reconciliation_fnames = [
            "account_id",
            "date",
            "balance",
            "amount_currency",
            "currency_id",
        ]
        return {
            "tax": tax_fnames,
            "fiscal": fiscal_fnames,
            "reconciliation": reconciliation_fnames,
        }

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Journal Items"),
                "template": "/account/static/xls/aml_import_template.xlsx",
            }
        ]

    @_debug.perf.timed
    def _prepare_edi_vals_to_export(self):
        self.check_singleton()

        if float_compare(self.discount, 100.0, precision_digits=2) == 0:
            gross_price_subtotal = self.currency_id.round(
                self.price_unit * self.quantity
            )
            _debug.logic("edi_gross_from_unit_price", line=self, reason="full_discount")
        else:
            gross_price_subtotal = self.currency_id.round(
                self.price_subtotal / (1 - self.discount / 100.0)
            )

        return {
            "line": self,
            "price_unit_after_discount": self.currency_id.round(
                self.price_unit * (1 - (self.discount / 100.0))
            ),
            "price_subtotal_before_discount": gross_price_subtotal,
            "price_subtotal_unit": self.currency_id.round(
                self.price_subtotal / self.quantity
            )
            if self.quantity
            else 0.0,
            "price_total_unit": self.currency_id.round(self.price_total / self.quantity)
            if self.quantity
            else 0.0,
            "price_discount": gross_price_subtotal - self.price_subtotal,
            "price_discount_unit": (gross_price_subtotal - self.price_subtotal)
            / self.quantity
            if self.quantity
            else 0.0,
            "gross_price_total_unit": self.currency_id.round(
                gross_price_subtotal / self.quantity
            )
            if self.quantity
            else 0.0,
            "unece_uom_code": self.product_id.product_tmpl_id.uom_id._get_unece_code(),
        }

    def _get_journal_items_full_name(self, name, display_name):
        return (
            name
            if not display_name or display_name in name
            else f"{display_name}\n{name}"
        )

    @_debug.perf.timed
    def _is_edi_line_tax_required(self):
        return self.product_id.type != "combo"

    def _prepare_aml_values(self, **kwargs):
        self.check_singleton()
        return {
            "name": self.name,
            "account_id": self.account_id.id,
            "currency_id": self.currency_id.id,
            "amount_currency": self.amount_currency,
            "balance": self.balance,
            "reconcile_model_id": self.reconcile_model_id.id,
            "analytic_distribution": self.analytic_distribution,
            "tax_repartition_line_id": self.tax_repartition_line_id.id,
            "tax_ids": [Command.set(self.tax_ids.ids)] + kwargs.pop("tax_ids", []),
            "tax_tag_ids": [Command.set(self.tax_tag_ids.ids)],
            "group_tax_id": self.group_tax_id.id,
            "partner_id": self.partner_id.id,
            **kwargs,
        }

    def _filter_aml_lot_valuation(self):
        self.check_singleton()
        return self.move_id.state == "posted"

    @_debug.perf.timed
    def _get_child_lines(self):
        self.check_singleton()

        section_lines = self.move_id.invoice_line_ids.filtered(
            lambda l: self in (l.parent_id, l.parent_id.parent_id)
        )
        result = []
        for taxes, lines_for_tax_group in groupby(
            section_lines, key=lambda l: l.tax_ids
        ):
            lines_for_tax_group = sum(
                lines_for_tax_group, start=self.env["account.move.line"]
            )
            tax_labels = [tax.tax_label for tax in taxes if tax.tax_label]
            for section_line, move_lines in (
                lines_for_tax_group.sorted("sequence").grouped("parent_id").items()
            ):
                lines_to_sum = (
                    move_lines if section_line != self else lines_for_tax_group
                )
                subtotal = sum(l.price_subtotal for l in lines_to_sum)
                total = sum(l.price_total for l in lines_to_sum)
                if not subtotal and not tax_labels:
                    continue
                if (
                    section_line.collapse_composition
                    or section_line.parent_id.collapse_composition
                ):
                    result.append(
                        {
                            "name": section_line.name,
                            "taxes": tax_labels
                            if not section_line.parent_id.collapse_prices
                            else [],
                            "price_subtotal": subtotal,
                            "price_total": total,
                            "display_type": "product",
                            "quantity": 1,
                            "line_uom": False,
                            "product_uom_id": False,
                            "discount": 0.0,
                        }
                    )
                else:
                    result.extend(
                        {
                            "name": line.name,
                            "taxes": tax_labels if line == self else [],
                            "price_subtotal": subtotal
                            if line == section_line
                            else line.price_subtotal,
                            "price_total": total
                            if line == section_line
                            else line.price_total,
                            "display_type": line.display_type,
                            "quantity": line.quantity,
                            "line_uom": line.product_uom_id,
                            "product_uom_id": line.product_id.uom_id,
                            "discount": line.discount,
                        }
                        for line in section_line | move_lines
                    )

        _debug.logic(
            "child_lines_grouped",
            line=self,
            section_lines=section_lines,
            rows=len(result),
            placeholder=not result,
        )
        return result or [
            {
                "name": self.name,
                "taxes": [],
                "price_subtotal": 0.0,
                "price_total": 0.0,
                "quantity": 0,
                "display_type": "product",
            }
        ]

    def get_section_subtotal(self):
        section_lines = self._get_section_lines()
        return sum(section_lines.mapped("price_subtotal"))

    def get_line_parent_section(self):
        if (
            self.display_type == "product"
            and self.parent_id.display_type == "line_subsection"
        ):
            return self.parent_id.parent_id

        return self.parent_id

    def _get_section_lines(self):
        self.check_singleton()
        return self.move_id.invoice_line_ids.filtered(self._is_line_in_section)

    def _is_line_in_section(self, line):
        self.check_singleton()
        is_direct_child = line.parent_id == self
        is_indirect_child = (
            self.display_type == "line_section"
            and line.parent_id
            and line.parent_id.display_type == "line_subsection"
            and line.parent_id.parent_id == self
        )
        return is_direct_child or is_indirect_child

    @_debug.perf.timed
    def open_reconcile_view(self):
        _debug.lifecycle("open_reconcile_view", records=self)
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_account_moves_all_grouped_matching"
        )
        ids = (
            self._all_reconciled_lines()
            .filtered(lambda l: l.matched_debit_ids or l.matched_credit_ids)
            .ids
        )
        action["domain"] = [("id", "in", ids)]
        return clean_action(action, self.env)

    @_debug.perf.timed
    def action_view_business_doc(self):
        _debug.lifecycle("action_view_business_doc", records=self)
        return self.move_id.action_view_business_doc()

    @_debug.perf.timed
    def action_automatic_entry(self, default_action=None):
        _debug.lifecycle("action_automatic_entry", records=self)
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.account_automatic_entry_wizard_action"
        )
        ctx = dict(self.env.context)
        ctx.pop("active_id", None)
        ctx.pop("default_journal_id", None)
        ctx["active_ids"] = self.ids
        ctx["active_model"] = "account.move.line"
        if default_action:
            ctx["default_action"] = default_action
        action["context"] = ctx
        return action

    @_debug.perf.timed
    def action_add_from_catalog(self):
        _debug.lifecycle("action_add_from_catalog", records=self)
        move = self.env["account.move"].browse(self.env.context.get("order_id"))
        return move.with_context(child_field="line_ids").action_add_from_catalog()

    def _get_product_catalog_lines_data(self, **kwargs):
        if self:
            self.product_id.check_singleton()
            return {
                **self[0].move_id._get_product_price_and_data(self[0].product_id),
                "quantity": sum(
                    self.mapped(
                        lambda line: line.product_uom_id._get_quantity_report(
                            qty=line.quantity,
                            to_unit=line.product_id.uom_id,
                        )
                    )
                ),
                "readOnly": self.move_id._is_readonly() or len(self) > 1,
                "uomDisplayName": (len(self) == 1 and self.product_uom_id.display_name)
                or self.product_id.uom_id.display_name,
            }
        return {
            "quantity": 0,
        }

    def _conditional_add_to_compute(self, fname, condition):
        field = self._fields[fname]
        to_reset = self.filtered(
            lambda line: condition(line) and not self.env.is_protected(field, line)
        )
        to_reset.invalidate_recordset([fname])
        self.env.add_to_compute(field, to_reset)

    def _copy_data_extend_business_fields(self, values):
        self.check_singleton()

    def _get_downpayment_lines(self):
        return self.env["account.move.line"]

    def _filtered_discount_lines(self):
        return self.filtered(lambda line: line.display_type == "discount")

    def _is_empty_line(self):
        self.check_singleton()
        return (
            self.display_type == "product"
            and not self.product_id
            and not (self.name or "").strip()
            and self.currency_id.is_zero(self.price_unit)
            and self.currency_id.is_zero(self.price_total)
        )
