import ast
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from functools import lru_cache

from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.sql import create_index
from odoo.addons.web.controllers.utils import clean_action

from odoo.addons.account.models.account_move import MAX_HASH_VERSION


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "analytic.mixin"
    _description = "Journal Item"
    _order = "date desc, move_name desc, id"
    _check_company_auto = True
    _rec_names_search = ['name', 'move_id', 'product_id']

    # ==============================================================================================
    #                                          JOURNAL ENTRY
    # ==============================================================================================

    # === Parent fields === #
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry',
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
        check_company=True,
    )
    journal_id = fields.Many2one(
        related='move_id.journal_id', store=True, precompute=True,
        index=True,
        copy=False,
    )
    company_id = fields.Many2one(
        related='move_id.company_id', store=True, readonly=True, precompute=True,
        index=True,
    )
    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='move_id.company_currency_id', readonly=True, store=True, precompute=True,
    )
    move_name = fields.Char(
        string='Number',
        related='move_id.name', store=True,
        index='btree',
    )
    parent_state = fields.Selection(related='move_id.state', store=True)
    date = fields.Date(
        related='move_id.date', store=True,
        copy=False,
        group_operator='min',
    )
    ref = fields.Char(
        related='move_id.ref', store=True,
        copy=False,
        index='trigram',
    )
    is_storno = fields.Boolean(
        string="Company Storno Accounting",
        related='move_id.is_storno',
        help="Utility field to express whether the journal item is subject to storno accounting",
    )
    sequence = fields.Integer(compute='_compute_sequence', store=True, readonly=False, precompute=True)
    move_type = fields.Selection(related='move_id.move_type')

    # === Accountable fields === #
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        compute='_compute_account_id', store=True, readonly=False, precompute=True,
        inverse='_inverse_account_id',
        index=True,
        auto_join=True,
        ondelete="cascade",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('is_off_balance', '=', False)]",
        check_company=True,
        tracking=True,
    )
    name = fields.Char(
        string='Label',
        compute='_compute_name', store=True, readonly=False, precompute=True,
        tracking=True,
    )
    debit = fields.Monetary(
        string='Debit',
        compute='_compute_debit_credit', inverse='_inverse_debit', store=True, precompute=True,
        currency_field='company_currency_id',
    )
    credit = fields.Monetary(
        string='Credit',
        compute='_compute_debit_credit', inverse='_inverse_credit', store=True, precompute=True,
        currency_field='company_currency_id',
    )
    balance = fields.Monetary(
        string='Balance',
        compute='_compute_balance', store=True, readonly=False, precompute=True,
        currency_field='company_currency_id',
    )
    cumulated_balance = fields.Monetary(
        string='Cumulated Balance',
        compute='_compute_cumulated_balance',
        currency_field='company_currency_id',
        exportable=False,
        help="Cumulated balance depending on the domain and the order chosen in the view.")
    currency_rate = fields.Float(
        compute='_compute_currency_rate',
        help="Currency rate from company currency to document currency.",
    )
    amount_currency = fields.Monetary(
        string='Amount in Currency',
        group_operator=None,
        compute='_compute_amount_currency', inverse='_inverse_amount_currency', store=True, readonly=False, precompute=True,
        help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id', store=True, readonly=False, precompute=True,
        required=True,
    )
    is_same_currency = fields.Boolean(compute='_compute_same_currency')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        compute='_compute_partner_id', inverse='_inverse_partner_id', store=True, readonly=False, precompute=True,
        ondelete='restrict',
    )

    # === Origin fields === #
    reconcile_model_id = fields.Many2one(
        comodel_name='account.reconcile.model',
        string="Reconciliation Model",
        copy=False,
        readonly=True,
        check_company=True,
    )
    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string="Originator Payment",
        related='move_id.payment_id', store=True,
        auto_join=True,
        index='btree_not_null',
        help="The payment that created this entry")
    statement_line_id = fields.Many2one(
        comodel_name='account.bank.statement.line',
        string="Originator Statement Line",
        related='move_id.statement_line_id', store=True,
        auto_join=True,
        index='btree_not_null',
        help="The statement line that created this entry")
    statement_id = fields.Many2one(
        related='statement_line_id.statement_id', store=True,
        auto_join=True,
        index='btree_not_null',
        copy=False,
        help="The bank statement used for bank reconciliation")

    # === Tax fields === #
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        compute='_compute_tax_ids', store=True, readonly=False, precompute=True,
        context={'active_test': False},
        check_company=True,
    )
    group_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Originator Group of Taxes",
        index='btree_not_null',
    )
    tax_line_id = fields.Many2one(
        comodel_name='account.tax',
        string='Originator Tax',
        related='tax_repartition_line_id.tax_id', store=True, precompute=True,
        ondelete='restrict',
        help="Indicates that this journal item is a tax line")
    tax_group_id = fields.Many2one(  # used in the widget tax-group-custom-field
        string='Originator tax group',
        related='tax_line_id.tax_group_id', store=True, precompute=True,
    )
    tax_base_amount = fields.Monetary(
        string="Base Amount",
        readonly=True,
        currency_field='company_currency_id',
    )
    tax_repartition_line_id = fields.Many2one(
        comodel_name='account.tax.repartition.line',
        string="Originator Tax Distribution Line",
        ondelete='restrict',
        readonly=True,
        check_company=True,
        help="Tax distribution line that caused the creation of this move line, if any")
    tax_tag_ids = fields.Many2many(
        string="Tags",
        comodel_name='account.account.tag',
        ondelete='restrict',
        context={'active_test': False},
        tracking=True,
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.",
    )
    tax_audit = fields.Char(
        string="Tax Audit String",
        compute="_compute_tax_audit", store=True,
        help="Computed field, listing the tax grids impacted by this line, and the amount it applies to each of them.")
    # Technical field. True if the balance of this move line needs to be
    # inverted when computing its total for each tag (for sales invoices, for # example)
    tax_tag_invert = fields.Boolean(
        string="Invert Tags",
        compute='_compute_tax_tag_invert', store=True, readonly=False, copy=False,
    )

    # === Reconciliation fields === #
    amount_residual = fields.Monetary(
        string='Residual Amount',
        compute='_compute_amount_residual', store=True,
        currency_field='company_currency_id',
        help="The residual amount on a journal item expressed in the company currency.",
    )
    amount_residual_currency = fields.Monetary(
        string='Residual Amount in Currency',
        compute='_compute_amount_residual', store=True,
        help="The residual amount on a journal item expressed in its currency (possibly not the "
             "company currency).",
    )
    reconciled = fields.Boolean(compute='_compute_amount_residual', store=True)
    full_reconcile_id = fields.Many2one(
        comodel_name='account.full.reconcile',
        string="Matching",
        copy=False,
        index='btree_not_null',
        readonly=True,
    )
    matched_debit_ids = fields.One2many(
        comodel_name='account.partial.reconcile', inverse_name='credit_move_id',
        string='Matched Debits',
        readonly=True,
        help='Debit journal items that are matched with this journal item.',
    )
    matched_credit_ids = fields.One2many(
        comodel_name='account.partial.reconcile', inverse_name='debit_move_id',
        string='Matched Credits',
        readonly=True,
        help='Credit journal items that are matched with this journal item.',
    )
    matching_number = fields.Char(
        string="Matching #",
        compute='_compute_matching_number', store=True,
        help="Matching number for this line, 'P' if it is only partially reconcile, or the name of "
             "the full reconcile if it exists.",
    )
    is_account_reconcile = fields.Boolean(
        string='Account Reconcile',
        related='account_id.reconcile',
    )

    # === Related fields ===
    account_type = fields.Selection(
        related='account_id.account_type',
        string="Internal Type",
    )
    account_internal_group = fields.Selection(related='account_id.internal_group')
    account_root_id = fields.Many2one(
        related='account_id.root_id',
        string="Account Root",
        store=True,
    )

    # ==============================================================================================
    #                                          INVOICE
    # ==============================================================================================

    display_type = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('cogs', 'Cost of Goods Sold'),
            ('tax', 'Tax'),
            ('rounding', "Rounding"),
            ('payment_term', 'Payment Term'),
            ('line_section', 'Section'),
            ('line_note', 'Note'),
            ('epd', 'Early Payment Discount')
        ],
        compute='_compute_display_type', store=True, readonly=False, precompute=True,
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        inverse='_inverse_product_id',
        ondelete='restrict',
    )
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        compute='_compute_product_uom_id', store=True, readonly=False, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]",
        ondelete="restrict",
    )
    product_uom_category_id = fields.Many2one(
        comodel_name='uom.category',
        related='product_id.uom_id.category_id',
    )
    quantity = fields.Float(
        string='Quantity',
        compute='_compute_quantity', store=True, readonly=False, precompute=True,
        digits='Product Unit of Measure',
        help="The optional quantity expressed by this line, eg: number of product sold. "
             "The quantity is not a legal requirement but is very useful for some reports.",
    )
    date_maturity = fields.Date(
        string='Due Date',
        index=True,
        tracking=True,
        help="This field is used for payable and receivable journal entries. "
             "You can put the limit date for the payment of this line.",
    )

    # === Price fields === #
    price_unit = fields.Float(
        string='Unit Price',
        compute="_compute_price_unit", store=True, readonly=False, precompute=True,
        digits='Product Price',
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
    )

    # === Invoice sync fields === #
    term_key = fields.Binary(compute='_compute_term_key', exportable=False)
    tax_key = fields.Binary(compute='_compute_tax_key', exportable=False)
    compute_all_tax = fields.Binary(compute='_compute_all_tax', exportable=False)
    compute_all_tax_dirty = fields.Boolean(compute='_compute_all_tax')
    epd_key = fields.Binary(compute='_compute_epd_key', exportable=False)
    epd_needed = fields.Binary(compute='_compute_epd_needed', exportable=False)
    epd_dirty = fields.Boolean(compute='_compute_epd_needed')

    # === Analytic fields === #
    analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='move_line_id',
        string='Analytic lines',
    )
    analytic_distribution = fields.Json(
        inverse="_inverse_analytic_distribution",
    ) # add the inverse function used to trigger the creation/update of the analytic lines accordingly (field originally defined in the analytic mixin)

    # === Early Pay fields === #
    discount_date = fields.Date(
        string='Discount Date',
        store=True,
        help='Last date at which the discounted amount must be paid in order for the Early Payment Discount to be granted'
    )
    # Discounted amount to pay when the early payment discount is applied
    discount_amount_currency = fields.Monetary(
        string='Discount amount in Currency',
        store=True,
        currency_field='currency_id',
    )
    # Discounted balance when the early payment discount is applied
    discount_balance = fields.Monetary(
        string='Discount Balance',
        store=True,
        currency_field='company_currency_id',
    )
    discount_percentage = fields.Float(store=True,)

    # === Misc Information === #
    blocked = fields.Boolean(
        string='No Follow-up',
        default=False,
        help="You can check this box to mark this journal item as a litigation with the "
             "associated partner",
    )
    is_refund = fields.Boolean(compute='_compute_is_refund')

    _sql_constraints = [
        (
            "check_credit_debit",
            "CHECK(display_type IN ('line_section', 'line_note') OR credit * debit=0)",
            "Wrong credit or debit value in accounting entry !"
        ),
        (
            "check_amount_currency_balance_sign",
            """CHECK(
                display_type IN ('line_section', 'line_note')
                OR (
                    (balance <= 0 AND amount_currency <= 0)
                    OR
                    (balance >= 0 AND amount_currency >= 0)
                )
            )""",
            "The amount expressed in the secondary currency must be positive when account is debited and negative when "
            "account is credited. If the currency is the same as the one from the company, this amount must strictly "
            "be equal to the balance."
        ),
        (
            "check_accountable_required_fields",
            "CHECK(display_type IN ('line_section', 'line_note') OR account_id IS NOT NULL)",
            "Missing required account on accountable line."
        ),
        (
            "check_non_accountable_fields_null",
            "CHECK(display_type NOT IN ('line_section', 'line_note') OR (amount_currency = 0 AND debit = 0 AND credit = 0 AND account_id IS NULL))",
            "Forbidden balance or account on non-accountable line"
        ),
    ]

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_id')
    def _compute_display_type(self):
        for line in self.filtered(lambda l: not l.display_type):
            # avoid cyclic dependencies with _compute_account_id
            account_set = self.env.cache.contains(line, line._fields['account_id'])
            tax_set = self.env.cache.contains(line, line._fields['tax_line_id'])
            line.display_type = (
                'tax' if tax_set and line.tax_line_id else
                'payment_term' if account_set and line.account_id.account_type in ['asset_receivable', 'liability_payable'] else
                'product'
            ) if line.move_id.is_invoice() else 'product'

    # Do not depend on `move_id.partner_id`, the inverse is taking care of that
    def _compute_partner_id(self):
        for line in self:
            line.partner_id = line.move_id.partner_id.commercial_partner_id

    @api.depends('move_id.currency_id')
    def _compute_currency_id(self):
        for line in self:
            if line.display_type == 'cogs':
                line.currency_id = line.company_currency_id
            elif line.move_id.is_invoice(include_receipts=True):
                line.currency_id = line.move_id.currency_id
            else:
                line.currency_id = line.currency_id or line.company_id.currency_id

    @api.depends('product_id', 'move_id.payment_reference')
    def _compute_name(self):
        def get_name(line):
            values = []
            if line.partner_id.lang:
                product = line.product_id.with_context(lang=line.partner_id.lang)
            else:
                product = line.product_id
            if not product:
                return False

            if product.partner_ref:
                values.append(product.partner_ref)
            if line.journal_id.type == 'sale':
                if product.description_sale:
                    values.append(product.description_sale)
            elif line.journal_id.type == 'purchase':
                if product.description_purchase:
                    values.append(product.description_purchase)
            return '\n'.join(values) if values else False

        for line in self:
            if line.display_type == 'payment_term':
                if not line.name or line._origin.name == line._origin.move_id.payment_reference:
                    line.name = line.move_id.payment_reference or False
                continue
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            if not line.name or line._origin.name == get_name(line._origin):
                line.name = get_name(line)

    def _compute_account_id(self):
        term_lines = self.filtered(lambda line: line.display_type == 'payment_term')
        if term_lines:
            moves = term_lines.move_id
            self.env.cr.execute("""
                WITH previous AS (
                    SELECT DISTINCT ON (line.move_id)
                           'account.move' AS model,
                           line.move_id AS id,
                           NULL AS account_type,
                           line.account_id AS account_id
                      FROM account_move_line line
                     WHERE line.move_id = ANY(%(move_ids)s)
                       AND line.display_type = 'payment_term'
                       AND line.id != ANY(%(current_ids)s)
                ),
                properties AS(
                    SELECT DISTINCT ON (property.company_id, property.name, property.res_id)
                           'res.partner' AS model,
                           SPLIT_PART(property.res_id, ',', 2)::integer AS id,
                           CASE
                               WHEN property.name = 'property_account_receivable_id' THEN 'asset_receivable'
                               ELSE 'liability_payable'
                           END AS account_type,
                           SPLIT_PART(property.value_reference, ',', 2)::integer AS account_id
                      FROM ir_property property
                      JOIN res_company company ON property.company_id = company.id
                     WHERE property.name IN ('property_account_receivable_id', 'property_account_payable_id')
                       AND property.company_id = ANY(%(company_ids)s)
                       AND property.res_id = ANY(%(partners)s)
                  ORDER BY property.company_id, property.name, property.res_id, account_id
                ),
                default_properties AS(
                    SELECT DISTINCT ON (property.company_id, property.name)
                           'res.partner' AS model,
                           company.partner_id AS id,
                           CASE
                               WHEN property.name = 'property_account_receivable_id' THEN 'asset_receivable'
                               ELSE 'liability_payable'
                           END AS account_type,
                           SPLIT_PART(property.value_reference, ',', 2)::integer AS account_id
                      FROM ir_property property
                      JOIN res_company company ON property.company_id = company.id
                     WHERE property.name IN ('property_account_receivable_id', 'property_account_payable_id')
                       AND property.company_id = ANY(%(company_ids)s)
                       AND property.res_id IS NULL
                  ORDER BY property.company_id, property.name, account_id
                ),
                fallback AS (
                    SELECT DISTINCT ON (account.company_id, account.account_type)
                           'res.company' AS model,
                           account.company_id AS id,
                           account.account_type AS account_type,
                           account.id AS account_id
                      FROM account_account account
                     WHERE account.company_id = ANY(%(company_ids)s)
                       AND account.account_type IN ('asset_receivable', 'liability_payable')
                       AND account.deprecated = 'f'
                )
                SELECT * FROM previous
                UNION ALL
                SELECT * FROM default_properties
                UNION ALL
                SELECT * FROM properties
                UNION ALL
                SELECT * FROM fallback
            """, {
                'company_ids': moves.company_id.ids,
                'move_ids': moves.ids,
                'partners': [f'res.partner,{pid}' for pid in moves.commercial_partner_id.ids],
                'current_ids': term_lines.ids
            })
            accounts = {
                (model, id, account_type): account_id
                for model, id, account_type, account_id in self.env.cr.fetchall()
            }
            for line in term_lines:
                account_type = 'asset_receivable' if line.move_id.is_sale_document(include_receipts=True) else 'liability_payable'
                move = line.move_id
                account_id = (
                    accounts.get(('account.move', move.id, None))
                    or accounts.get(('res.partner', move.commercial_partner_id.id, account_type))
                    or accounts.get(('res.partner', move.company_id.partner_id.id, account_type))
                    or accounts.get(('res.company', move.company_id.id, account_type))
                )
                if line.move_id.fiscal_position_id:
                    account_id = line.move_id.fiscal_position_id.map_account(self.env['account.account'].browse(account_id))
                line.account_id = account_id

        product_lines = self.filtered(lambda line: line.display_type == 'product' and line.move_id.is_invoice(True))
        for line in product_lines:
            if line.product_id:
                fiscal_position = line.move_id.fiscal_position_id
                accounts = line.with_company(line.company_id).product_id\
                    .product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
                if line.move_id.is_sale_document(include_receipts=True):
                    line.account_id = accounts['income'] or line.account_id
                elif line.move_id.is_purchase_document(include_receipts=True):
                    line.account_id = accounts['expense'] or line.account_id
            elif line.partner_id:
                line.account_id = self.env['account.account']._get_most_frequent_account_for_partner(
                    company_id=line.company_id.id,
                    partner_id=line.partner_id.id,
                    move_type=line.move_id.move_type,
                )
        for line in self:
            if not line.account_id and line.display_type not in ('line_section', 'line_note'):
                previous_two_accounts = line.move_id.line_ids.filtered(
                    lambda l: l.account_id and l.display_type == line.display_type
                )[-2:].account_id
                if len(previous_two_accounts) == 1 and len(line.move_id.line_ids) > 2:
                    line.account_id = previous_two_accounts
                else:
                    line.account_id = line.move_id.journal_id.default_account_id

    @api.depends('move_id')
    def _compute_balance(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note'):
                line.balance = False
            elif not line.move_id.is_invoice(include_receipts=True):
                # Only act as a default value when none of balance/debit/credit is specified
                # balance is always the written field because of `_sanitize_vals`
                line.balance = -sum((line.move_id.line_ids - line).mapped('balance'))
            else:
                line.balance = 0

    @api.depends('balance', 'move_id.is_storno')
    def _compute_debit_credit(self):
        for line in self:
            if not line.is_storno:
                line.debit = line.balance if line.balance > 0.0 else 0.0
                line.credit = -line.balance if line.balance < 0.0 else 0.0
            else:
                line.debit = line.balance if line.balance < 0.0 else 0.0
                line.credit = -line.balance if line.balance > 0.0 else 0.0

    @api.depends('currency_id', 'company_id', 'move_id.date')
    def _compute_currency_rate(self):
        @lru_cache()
        def get_rate(from_currency, to_currency, company, date):
            return self.env['res.currency']._get_conversion_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                company=company,
                date=date,
            )
        for line in self:
            if line.currency_id:
                line.currency_rate = get_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line),
                )
            else:
                line.currency_rate = 1

    @api.depends('currency_id', 'company_currency_id')
    def _compute_same_currency(self):
        for record in self:
            record.is_same_currency = record.currency_id == record.company_currency_id

    @api.depends('currency_rate', 'balance')
    def _compute_amount_currency(self):
        for line in self:
            if line.amount_currency is False:
                line.amount_currency = line.currency_id.round(line.balance * line.currency_rate)
            if line.currency_id == line.company_id.currency_id:
                line.amount_currency = line.balance

    @api.depends('full_reconcile_id.name', 'matched_debit_ids', 'matched_credit_ids')
    def _compute_matching_number(self):
        for record in self:
            if record.full_reconcile_id:
                record.matching_number = record.full_reconcile_id.name
            elif record.matched_debit_ids or record.matched_credit_ids:
                record.matching_number = 'P'
            else:
                record.matching_number = None

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

    @api.depends('debit', 'credit', 'amount_currency', 'account_id', 'currency_id', 'company_id',
                 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        need_residual_lines = self.filtered(lambda x: x.account_id.reconcile or x.account_id.account_type in ('asset_cash', 'liability_credit_card'))
        # Run the residual amount computation on all lines stored in the db. By
        # using _origin, new records (with a NewId) are excluded and the
        # computation works automagically for virtual onchange records as well.
        stored_lines = need_residual_lines._origin

        if stored_lines:
            self.env['account.partial.reconcile'].flush_model()
            self.env['res.currency'].flush_model(['decimal_places'])

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
            amounts_map = {
                (line_id, flag): (amount, amount_currency)
                for line_id, flag, amount, amount_currency in self.env.cr.fetchall()
            }
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
            debit_amount, debit_amount_currency = amounts_map.get((line._origin.id, 'debit'), (0.0, 0.0))
            credit_amount, credit_amount_currency = amounts_map.get((line._origin.id, 'credit'), (0.0, 0.0))

            # Subtract the values from the account.partial.reconcile to compute the residual amounts.
            line.amount_residual = comp_curr.round(line.balance - debit_amount + credit_amount)
            line.amount_residual_currency = foreign_curr.round(line.amount_currency - debit_amount_currency + credit_amount_currency)
            line.reconciled = (
                comp_curr.is_zero(line.amount_residual)
                and foreign_curr.is_zero(line.amount_residual_currency)
            )

    @api.depends('move_id.move_type', 'tax_ids', 'tax_repartition_line_id', 'debit', 'credit', 'tax_tag_ids', 'is_refund',
                 'move_id.tax_cash_basis_origin_move_id')
    def _compute_tax_tag_invert(self):
        for record in self:
            origin_move_id = record.move_id.tax_cash_basis_origin_move_id or record.move_id
            if not record.tax_repartition_line_id and not record.tax_ids:
                # Invoices imported from other softwares might only have kept the tags, not the taxes.
                record.tax_tag_invert = record.tax_tag_ids and origin_move_id.is_inbound()

            elif origin_move_id.move_type == 'entry':
                # For misc operations, cash basis entries and write-offs from the bank reconciliation widget
                tax = record.tax_repartition_line_id.tax_id or record.tax_ids[:1]
                is_refund = record.is_refund
                tax_type = tax.type_tax_use
                if record.display_type == 'epd':  # In case of early payment, tax_tag_invert is independent of the balance of the line
                    record.tax_tag_invert = tax_type == 'purchase'
                else:
                    record.tax_tag_invert = (tax_type == 'purchase' and is_refund) or (tax_type == 'sale' and not is_refund)
            else:
                # For invoices with taxes
                record.tax_tag_invert = origin_move_id.is_inbound()

    @api.depends('tax_tag_ids', 'debit', 'credit', 'journal_id', 'tax_tag_invert')
    def _compute_tax_audit(self):
        separator = '        '

        for record in self:
            currency = record.company_id.currency_id
            audit_str = ''
            for tag in record.tax_tag_ids:
                tag_amount = (record.tax_tag_invert and -1 or 1) * (tag.tax_negate and -1 or 1) * record.balance

                if tag.applicability == 'taxes' and tag.name[0] in {'+', '-'}:
                    # Then, the tag comes from a report expression, and hence has a + or - sign (also in its name)
                    tag_name = tag.name[1:]
                else:
                    # Then, it's a financial tag (sign is always +, and never shown in tag name)
                    tag_name = tag.name

                audit_str += separator if audit_str else ''
                audit_str += tag_name + ': ' + formatLang(self.env, tag_amount, currency_obj=currency)

            record.tax_audit = audit_str

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            # vendor bills should have the product purchase UOM
            if line.move_id.is_purchase_document():
                line.product_uom_id = line.product_id.uom_po_id
            else:
                line.product_uom_id = line.product_id.uom_id

    @api.depends('display_type')
    def _compute_quantity(self):
        for line in self:
            if line.display_type == 'product':
                line.quantity = line.quantity if line.quantity else 1
            else:
                line.quantity = False

    @api.depends('display_type')
    def _compute_sequence(self):
        seq_map = {
            'tax': 10000,
            'rounding': 11000,
            'payment_term': 12000,
        }
        for line in self:
            line.sequence = seq_map.get(line.display_type, 100)

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal

    @api.depends('product_id', 'product_uom_id')
    def _compute_price_unit(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            if line.move_id.is_sale_document(include_receipts=True):
                document_type = 'sale'
            elif line.move_id.is_purchase_document(include_receipts=True):
                document_type = 'purchase'
            else:
                document_type = 'other'
            line.price_unit = line.product_id._get_tax_included_unit_price(
                line.move_id.company_id,
                line.move_id.currency_id,
                line.move_id.date,
                document_type,
                fiscal_position=line.move_id.fiscal_position_id,
                product_uom=line.product_uom_id,
            )

    @api.depends('product_id', 'product_uom_id')
    def _compute_tax_ids(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note', 'payment_term'):
                continue
            # /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
            if line.product_id or line.account_id.tax_ids or not line.tax_ids:
                line.tax_ids = line._get_computed_taxes()

    def _get_computed_taxes(self):
        self.ensure_one()

        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            else:
                tax_ids = self.account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'sale')
            if not tax_ids and self.display_type == 'product':
                tax_ids = self.move_id.company_id.account_sale_tax_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            else:
                tax_ids = self.account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'purchase')
            if not tax_ids and self.display_type == 'product':
                tax_ids = self.move_id.company_id.account_purchase_tax_id
        else:
            # Miscellaneous operation.
            tax_ids = False if self.env.context.get('skip_computed_taxes') else self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == self.company_id)

        if tax_ids and self.move_id.fiscal_position_id:
            tax_ids = self.move_id.fiscal_position_id.map_tax(tax_ids)

        return tax_ids

    @api.depends('tax_ids', 'currency_id', 'partner_id', 'account_id', 'group_tax_id', 'analytic_distribution')
    def _compute_tax_key(self):
        for line in self:
            if line.tax_repartition_line_id:
                line.tax_key = frozendict({
                    'tax_repartition_line_id': line.tax_repartition_line_id.id,
                    'group_tax_id': line.group_tax_id.id,
                    'account_id': line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                    'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
                    'partner_id': line.partner_id.id,
                    'move_id': line.move_id.id,
                    'display_type': line.display_type,
                })
            else:
                line.tax_key = frozendict({'id': line.id})

    @api.depends('tax_ids', 'currency_id', 'partner_id', 'analytic_distribution', 'balance', 'partner_id', 'move_id.partner_id', 'price_unit', 'quantity')
    def _compute_all_tax(self):
        for line in self:
            sign = line.move_id.direction_sign
            if line.display_type == 'tax':
                line.compute_all_tax = {}
                line.compute_all_tax_dirty = False
                continue
            if line.display_type == 'product' and line.move_id.is_invoice(True):
                amount_currency = sign * line.price_unit * (1 - line.discount / 100)
                handle_price_include = True
                quantity = line.quantity
            else:
                amount_currency = line.amount_currency
                handle_price_include = False
                quantity = 1
            compute_all_currency = line.tax_ids.compute_all(
                amount_currency,
                currency=line.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=line.move_id.always_tax_exigible,
                fixed_multiplicator=sign,
            )
            rate = line.amount_currency / line.balance if line.balance else 1
            line.compute_all_tax_dirty = True
            line.compute_all_tax = {
                frozendict({
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'group_tax_id': tax['group'] and tax['group'].id or False,
                    'account_id': tax['account_id'] or line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_distribution': ((tax['analytic'] or not tax['use_in_tax_closing']) and line.move_id.state == 'draft') and line.analytic_distribution,
                    'tax_ids': [(6, 0, tax['tax_ids'])],
                    'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                    'partner_id': line.move_id.partner_id.id or line.partner_id.id,
                    'move_id': line.move_id.id,
                    'display_type': line.display_type,
                }): {
                    'name': tax['name'] + (' ' + _('(Discount)') if line.display_type == 'epd' else ''),
                    'balance': tax['amount'] / rate,
                    'amount_currency': tax['amount'],
                    'tax_base_amount': tax['base'] / rate * (-1 if line.tax_tag_invert else 1),
                }
                for tax in compute_all_currency['taxes']
                if tax['amount']
            }
            if not line.tax_repartition_line_id:
                line.compute_all_tax[frozendict({'id': line.id})] = {
                    'tax_tag_ids': [(6, 0, compute_all_currency['base_tags'])],
                }

    @api.depends('tax_ids', 'account_id', 'company_id')
    def _compute_epd_key(self):
        for line in self:
            if line.display_type == 'epd' and line.company_id.early_pay_discount_computation == 'mixed':
                line.epd_key = frozendict({
                    'account_id': line.account_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'tax_ids': [Command.set(line.tax_ids.ids)],
                    'tax_tag_ids': [Command.set(line.tax_tag_ids.ids)],
                    'move_id': line.move_id.id,
                })
            else:
                line.epd_key = False

    @api.depends('move_id.needed_terms', 'account_id', 'analytic_distribution', 'tax_ids', 'tax_tag_ids', 'company_id')
    def _compute_epd_needed(self):
        for line in self:
            needed_terms = line.move_id.needed_terms
            line.epd_dirty = True
            line.epd_needed = False
            if line.display_type != 'product' or not line.tax_ids.ids or line.company_id.early_pay_discount_computation != 'mixed':
                continue

            amount_total = abs(sum(x['amount_currency'] for x in needed_terms.values()))
            percentages_to_apply = []
            names = []
            for term in needed_terms.values():
                if term.get('discount_percentage'):
                    percentages_to_apply.append({
                        'discount_percentage': term['discount_percentage'],
                        'term_percentage': abs(term['amount_currency'] / amount_total) if amount_total else 0
                    })
                    names.append(f"{term['discount_percentage']}%")

            discount_percentage_name = ', '.join(names)
            epd_needed = {}
            for percentages in percentages_to_apply:
                percentage = percentages['discount_percentage'] / 100
                line_percentage = percentages['term_percentage']
                taxes = line.tax_ids.filtered(lambda t: t.amount_type != 'fixed')
                epd_needed_vals = epd_needed.setdefault(
                    frozendict({
                        'move_id': line.move_id.id,
                        'account_id': line.account_id.id,
                        'analytic_distribution': line.analytic_distribution,
                        'tax_ids': [Command.set(taxes.ids)],
                        'tax_tag_ids': line.compute_all_tax[frozendict({'id': line.id})]['tax_tag_ids'],
                        'display_type': 'epd',
                    }),
                    {
                        'name': _("Early Payment Discount (%s)", discount_percentage_name),
                        'amount_currency': 0.0,
                        'balance': 0.0,
                        'price_subtotal': 0.0,
                    },
                )
                epd_needed_vals['amount_currency'] -= line.currency_id.round(line.amount_currency * percentage * line_percentage)
                epd_needed_vals['balance'] -= line.currency_id.round(line.balance * percentage * line_percentage)
                epd_needed_vals['price_subtotal'] -= line.currency_id.round(line.price_subtotal * percentage * line_percentage)
                epd_needed_vals = epd_needed.setdefault(
                    frozendict({
                        'move_id': line.move_id.id,
                        'account_id': line.account_id.id,
                        'display_type': 'epd',
                    }),
                    {
                        'name': _("Early Payment Discount (%s)", discount_percentage_name),
                        'amount_currency': 0.0,
                        'balance': 0.0,
                        'price_subtotal': 0.0,
                        'tax_ids': [Command.clear()],
                    },
                )
                epd_needed_vals['amount_currency'] += line.currency_id.round(line.amount_currency * percentage * line_percentage)
                epd_needed_vals['balance'] += line.currency_id.round(line.balance * percentage * line_percentage)
                epd_needed_vals['price_subtotal'] += line.currency_id.round(line.price_subtotal * percentage * line_percentage)
            line.epd_needed = {k: frozendict(v) for k, v in epd_needed.items()}

    @api.depends('move_id.move_type', 'balance', 'tax_repartition_line_id', 'tax_ids')
    def _compute_is_refund(self):
        for line in self:
            is_refund = False
            if line.move_id.move_type in ('out_refund', 'in_refund'):
                is_refund = True
            elif line.move_id.move_type == 'entry':
                if line.tax_repartition_line_id:
                    is_refund = bool(line.tax_repartition_line_id.refund_tax_id)
                else:
                    tax_type = line.tax_ids[:1].type_tax_use
                    if tax_type == 'sale' and line.credit == 0:
                        is_refund = True
                    elif tax_type == 'purchase' and line.debit == 0:
                        is_refund = True

                    if line.tax_ids and line.move_id.reversed_entry_id:
                        is_refund = not is_refund
            line.is_refund = is_refund

    @api.depends('date_maturity')
    def _compute_term_key(self):
        for line in self:
            if line.display_type == 'payment_term':
                line.term_key = frozendict({
                    'move_id': line.move_id.id,
                    'date_maturity': fields.Date.to_date(line.date_maturity),
                    'discount_date': line.discount_date,
                    'discount_percentage': line.discount_percentage
                })
            else:
                line.term_key = False

    @api.depends('account_id', 'partner_id', 'product_id')
    def _compute_analytic_distribution(self):
        for line in self:
            if line.display_type == 'product' or not line.move_id.is_invoice(include_receipts=True):
                distribution = self.env['account.analytic.distribution.model']._get_distribution({
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "partner_id": line.partner_id.id,
                    "partner_category_id": line.partner_id.category_id.ids,
                    "account_prefix": line.account_id.code,
                    "company_id": line.company_id.id,
                })
                line.analytic_distribution = distribution or line.analytic_distribution

    # -------------------------------------------------------------------------
    # INVERSE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('partner_id')
    def _inverse_partner_id(self):
        self._conditional_add_to_compute('account_id', lambda line: (
            line.display_type == 'payment_term'  # recompute based on settings
        ))

    @api.onchange('product_id')
    def _inverse_product_id(self):
        if self.product_id or not self.account_id:
            self._conditional_add_to_compute('account_id', lambda line: (
                line.display_type == 'product' and line.move_id.is_invoice(True)
            ))

    @api.onchange('amount_currency', 'currency_id')
    def _inverse_amount_currency(self):
        for line in self:
            if line.currency_id == line.company_id.currency_id and line.balance != line.amount_currency:
                line.balance = line.amount_currency
            elif (
                line.currency_id != line.company_id.currency_id
                and not line.move_id.is_invoice(True)
                and not self.env.is_protected(self._fields['balance'], line)
            ):
                line.balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)

    @api.onchange('debit')
    def _inverse_debit(self):
        for line in self:
            if line.debit:
                line.credit = 0
            line.balance = line.debit - line.credit

    @api.onchange('credit')
    def _inverse_credit(self):
        for line in self:
            if line.credit:
                line.debit = 0
            line.balance = line.debit - line.credit

    def _inverse_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['account.move.line'].browse([
            line.id for line in self if line.parent_state == "posted"
        ])
        lines_to_modify.analytic_line_ids.unlink()
        lines_to_modify._create_analytic_lines()

    @api.onchange('account_id')
    def _inverse_account_id(self):
        self._inverse_analytic_distribution()
        self._conditional_add_to_compute('tax_ids', lambda line: (
            line.account_id.tax_ids
            and not line.product_id.taxes_id.filtered(lambda tax: tax.company_id == line.company_id)
        ))

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    def _check_constrains_account_id_journal_id(self):
        # Avoid using api.constrains here as in case of a write on
        # account move and account move line in the same operation, the check would be done
        # before all write are complete, causing a false positive
        self.flush_recordset()
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

            if not is_account_control_ok:
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

    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        for line in self:
            account_type = line.account_id.account_type
            if line.move_id.is_sale_document(include_receipts=True):
                if account_type == 'liability_payable':
                    raise UserError(_("Account %s is of payable type, but is used in a sale operation.", line.account_id.code))
                if (line.display_type == 'payment_term') ^ (account_type == 'asset_receivable'):
                    raise UserError(_("Any journal item on a receivable account must have a due date and vice versa."))
            if line.move_id.is_purchase_document(include_receipts=True):
                if account_type == 'asset_receivable':
                    raise UserError(_("Account %s is of receivable type, but is used in a purchase operation.", line.account_id.code))
                if (line.display_type == 'payment_term') ^ (account_type == 'liability_payable'):
                    raise UserError(_("Any journal item on a payable account must have a due date and vice versa."))

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

            is_refund = base_aml.is_refund
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
    # CRUD/ORM
    # -------------------------------------------------------------------------
    def check_field_access_rights(self, operation, field_names):
        result = super().check_field_access_rights(operation, field_names)
        if not field_names:
            weirdos = ['term_key', 'tax_key', 'compute_all_tax', 'epd_key', 'epd_needed']
            result = [fname for fname in result if fname not in weirdos]
        return result

    def invalidate_model(self, fnames=None, flush=True):
        # Invalidate cache of related moves
        if fnames is None or 'move_id' in fnames:
            field = self._fields['move_id']
            lines = self.env.cache.get_records(self, field)
            move_ids = {id_ for id_ in self.env.cache.get_values(lines, field) if id_}
            if move_ids:
                self.env['account.move'].browse(move_ids).invalidate_recordset()
        return super().invalidate_model(fnames=fnames, flush=flush)

    def invalidate_recordset(self, fnames=None, flush=True):
        # Invalidate cache of related moves
        if fnames is None or 'move_id' in fnames:
            field = self._fields['move_id']
            move_ids = {id_ for id_ in self.env.cache.get_values(self, field) if id_}
            if move_ids:
                self.env['account.move'].browse(move_ids).invalidate_recordset()
        return super().invalidate_recordset(fnames=fnames, flush=flush)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        def to_tuple(t):
            return tuple(map(to_tuple, t)) if isinstance(t, (list, tuple)) else t
        # Make an explicit order because we will need to reverse it
        order = (order or self._order) + ', id'
        # Add the domain and order by in order to compute the cumulated balance in _compute_cumulated_balance
        contextualized = self.with_context(
            domain_cumulated_balance=to_tuple(self._apply_analytic_distribution_domain(domain or [])),
            order_cumulated_balance=order,
        )
        return super(AccountMoveLine, contextualized).search_read(domain, fields, offset, limit, order)

    def init(self):
        """ change index on partner_id to a multi-column index on (partner_id, ref), the new index will behave in the
            same way when we search on partner_id, with the addition of being optimal when having a query that will
            search on partner_id and ref at the same time (which is the case when we open the bank reconciliation widget)
        """
        create_index(self._cr, 'account_move_line_partner_id_ref_idx', 'account_move_line', ["partner_id", "ref"])
        create_index(self._cr, 'account_move_line_date_name_id_idx', 'account_move_line', ["date desc", "move_name desc", "id"])
        super().init()

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        quick_encode_suggestion = self.env.context.get('quick_encoding_vals')
        if quick_encode_suggestion and self.env.context.get('default_display_type') not in ('line_section', 'line_note'):
            defaults['account_id'] = quick_encode_suggestion['account_id']
            defaults['price_unit'] = quick_encode_suggestion['price_unit']
            defaults['tax_ids'] = [Command.set(quick_encode_suggestion['tax_ids'])]
        return defaults

    def _sanitize_vals(self, vals):
        if 'debit' in vals or 'credit' in vals:
            vals = vals.copy()
            if 'balance' in vals:
                vals.pop('debit', None)
                vals.pop('credit', None)
            else:
                vals['balance'] = vals.pop('debit', 0) - vals.pop('credit', 0)
        return vals

    def _prepare_create_values(self, vals_list):
        result_vals_list = super()._prepare_create_values(vals_list)
        for init_vals, res_vals in zip(vals_list, result_vals_list):
            # Allow computing the balance based on the amount_currency if it wasn't specified in the create vals.
            if (
                'amount_currency' in init_vals
                and 'balance' not in init_vals
                and 'debit' not in init_vals
                and 'credit' not in init_vals
            ):
                res_vals.pop('balance', 0)
                res_vals.pop('debit', 0)
                res_vals.pop('credit', 0)

            if res_vals['display_type'] in ('line_section', 'line_note'):
                res_vals.pop('account_id')

        return result_vals_list

    @contextmanager
    def _sync_invoice(self, container):
        if container['records'].env.context.get('skip_invoice_line_sync'):
            yield
            return  # avoid infinite recursion

        def existing():
            return {
                line: {
                    'amount_currency': line.currency_id.round(line.amount_currency),
                    'balance': line.company_id.currency_id.round(line.balance),
                    'currency_rate': line.currency_rate,
                    'price_subtotal': line.currency_id.round(line.price_subtotal),
                    'move_type': line.move_id.move_type,
                } for line in container['records'].with_context(
                    skip_invoice_line_sync=True,
                ).filtered(lambda l: l.move_id.is_invoice(True))
            }

        def changed(fname):
            return line not in before or before[line][fname] != after[line][fname]

        before = existing()
        yield
        after = existing()
        protected = container.get('protected', {})
        for line in after:
            if (
                line.display_type == 'product'
                and 'amount_currency' not in protected.get(line, {})
                and (not changed('amount_currency') or line not in before)
            ):
                amount_currency = line.move_id.direction_sign * line.currency_id.round(line.price_subtotal)
                if line.amount_currency != amount_currency or line not in before:
                    line.amount_currency = amount_currency
                if line.currency_id == line.company_id.currency_id:
                    line.balance = amount_currency

        after = existing()
        for line in after:
            if (
                (changed('amount_currency') or changed('currency_rate') or changed('move_type'))
                and 'balance' not in protected.get(line, {})
                and (not changed('balance') or (line not in before and not line.balance))
            ):
                balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
                line.balance = balance
        # Since this method is called during the sync, inside of `create`/`write`, these fields
        # already have been computed and marked as so. But this method should re-trigger it since
        # it changes the dependencies.
        self.env.add_to_compute(self._fields['debit'], container['records'])
        self.env.add_to_compute(self._fields['credit'], container['records'])

    @api.model_create_multi
    def create(self, vals_list):
        moves = self.env['account.move'].browse({vals['move_id'] for vals in vals_list})
        container = {'records': self}
        move_container = {'records': moves}
        with moves._check_balanced(move_container),\
             moves._sync_dynamic_lines(move_container),\
             self._sync_invoice(container):
            lines = super().create([self._sanitize_vals(vals) for vals in vals_list])
            container['records'] = lines
            container['protected'] = {line: set(vals.keys()) for line, vals in zip(lines, vals_list)}

        for line in lines:
            if line.move_id.state == 'posted':
                line._check_tax_lock_date()

        lines.move_id._synchronize_business_models(['line_ids'])
        lines._check_constrains_account_id_journal_id()
        return lines

    def write(self, vals):
        if not vals:
            return True
        protected_fields = self._get_lock_date_protected_fields()
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

        line_to_write = self
        vals = self._sanitize_vals(vals)
        for line in self:
            if not any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in vals):
                line_to_write -= line
                continue

            if line.parent_state == 'posted' and any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in ('tax_ids', 'tax_line_id')):
                raise UserError(_('You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so.'))

            # Check the lock date.
            if line.parent_state == 'posted' and any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in protected_fields['fiscal']):
                line.move_id._check_fiscalyear_lock_date()

            # Check the tax lock date.
            if line.parent_state == 'posted' and any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in protected_fields['tax']):
                line._check_tax_lock_date()

            # Check the reconciliation.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in protected_fields['reconciliation']):
                line._check_reconciliation()

        move_container = {'records': self.move_id}
        with self.move_id._check_balanced(move_container),\
             self.move_id._sync_dynamic_lines(move_container),\
             self._sync_invoice({'records': self, 'protected': {line: set(vals.keys()) for line in self}}):
            self = line_to_write
            if not self:
                return True
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

            result = super().write(vals)
            self.move_id._synchronize_business_models(['line_ids'])
            if any(field in vals for field in ['account_id', 'currency_id']):
                self._check_constrains_account_id_journal_id()

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
        # EXTENDS models
        return name == 'tracking' or super()._valid_field_parameter(field, name)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted(self):
        # Prevent deleting lines on posted entries
        if not self._context.get('force_delete') and any(m.state == 'posted' for m in self.move_id):
            raise UserError(_('You cannot delete an item linked to a posted entry.'))

    @api.ondelete(at_uninstall=False)
    def _prevent_automatic_line_deletion(self):
        if not self.env.context.get('dynamic_unlink'):
            for line in self:
                if line.display_type == 'tax' and line.move_id.line_ids.tax_ids:
                    raise ValidationError(_(
                        "You cannot delete a tax line as it would impact the tax report"
                    ))
                elif line.display_type == 'payment_term':
                    raise ValidationError(_(
                        "You cannot delete a payable/receivable line as it would not be consistent "
                        "with the payment terms"
                    ))

    def unlink(self):
        if not self:
            return

        # Check the lines are not reconciled (partially or not).
        self._check_reconciliation()

        # Check the lock date. (Only relevant if the move is posted)
        self.move_id.filtered(lambda m: m.state == 'posted')._check_fiscalyear_lock_date()

        # Check the tax lock date.
        self._check_tax_lock_date()

        move_container = {'records': self.move_id}
        with self.move_id._check_balanced(move_container),\
             self.move_id._sync_dynamic_lines(move_container):
            res = super().unlink()

        return res

    def name_get(self):
        return [(line.id, " ".join(
            element for element in (
                line.move_id.name,
                line.ref and f"({line.ref})",
                line.name or line.product_id.display_name,
            ) if element
        )) for line in self]

    def copy_data(self, default=None):
        data_list = super().copy_data(default=default)

        for line, values in zip(self, data_list):
            # Don't copy the name of a payment term line.
            if line.display_type == 'payment_term' and line.move_id.is_invoice(True):
                del values['name']
            # Don't copy restricted fields of notes
            if line.display_type in ('line_section', 'line_note'):
                del values['balance']
                del values['account_id']
            # Will be recomputed from the price_unit
            if line.display_type == 'product' and line.move_id.is_invoice(True):
                del values['balance']
            if self._context.get('include_business_fields'):
                line._copy_data_extend_business_fields(values)
        return data_list

    def _search_panel_domain_image(self, field_name, domain, set_count=False, limit=False):
        if field_name != 'account_root_id' or set_count:
            return super()._search_panel_domain_image(field_name, domain, set_count, limit)

        # Override in order to not read the complete move line table and use the index instead
        query = self._search(domain, limit=1)

        # if domain is logically equivalent to false
        if not isinstance(query, Query):
            return {}

        query.order = None
        query.add_where('account.id = account_move_line.account_id')
        query_str, query_param = query.select()
        self.env.cr.execute(f"""
            SELECT account.root_id
              FROM account_account account
             WHERE EXISTS ({query_str})
        """, query_param)
        return {
            root.id: {'id': root.id, 'display_name': root.display_name}
            for root in self.env['account.root'].browse(id for [id] in self.env.cr.fetchall())
        }

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

    @api.model
    def _prepare_reconciliation_single_partial(self, debit_vals, credit_vals):
        """ Prepare the values to create an account.partial.reconcile later when reconciling the dictionaries passed
        as parameters, each one representing an account.move.line.
        :param debit_vals:  The values of account.move.line to consider for a debit line.
        :param credit_vals: The values of account.move.line to consider for a credit line.
        :return:            A dictionary:
            * debit_vals:   None if the line has nothing left to reconcile.
            * credit_vals:  None if the line has nothing left to reconcile.
            * partial_vals: The newly computed values for the partial.
        """

        def is_payment(vals):
            return vals.get('is_payment') or (
                vals.get('record')
                and bool(vals['record'].move_id.payment_id or vals['record'].move_id.statement_line_id)
            )

        def get_odoo_rate(vals, other_line=None):
            if not is_payment(vals) and other_line and is_payment(other_line):
                return get_accounting_rate(other_line)
            if vals.get('record') and vals['record'].move_id.is_invoice(include_receipts=True):
                exchange_rate_date = vals['record'].move_id.invoice_date
            else:
                exchange_rate_date = vals['date']
            return recon_currency._get_conversion_rate(company_currency, recon_currency, vals['company'], exchange_rate_date)

        def get_accounting_rate(vals):
            if company_currency.is_zero(vals['balance']) or vals['currency'].is_zero(vals['amount_currency']):
                return None
            else:
                return abs(vals['amount_currency']) / abs(vals['balance'])

        # ==== Determine the currency in which the reconciliation will be done ====
        # In this part, we retrieve the residual amounts, check if they are zero or not and determine in which
        # currency and at which rate the reconciliation will be done.

        res = {
            'debit_vals': debit_vals,
            'credit_vals': credit_vals,
        }
        remaining_debit_amount_curr = debit_vals['amount_residual_currency']
        remaining_credit_amount_curr = credit_vals['amount_residual_currency']
        remaining_debit_amount = debit_vals['amount_residual']
        remaining_credit_amount = credit_vals['amount_residual']

        company_currency = debit_vals['company'].currency_id
        has_debit_zero_residual = company_currency.is_zero(remaining_debit_amount)
        has_credit_zero_residual = company_currency.is_zero(remaining_credit_amount)
        has_debit_zero_residual_currency = debit_vals['currency'].is_zero(remaining_debit_amount_curr)
        has_credit_zero_residual_currency = credit_vals['currency'].is_zero(remaining_credit_amount_curr)
        is_rec_pay_account = debit_vals.get('record') \
                             and debit_vals['record'].account_type in ('asset_receivable', 'liability_payable')

        if debit_vals['currency'] == credit_vals['currency'] == company_currency \
                and not has_debit_zero_residual \
                and not has_credit_zero_residual:
            # Everything is expressed in company's currency and there is something left to reconcile.
            recon_currency = company_currency
            debit_rate = credit_rate = 1.0
            recon_debit_amount = remaining_debit_amount
            recon_credit_amount = -remaining_credit_amount
        elif debit_vals['currency'] == company_currency \
                and is_rec_pay_account \
                and not has_debit_zero_residual \
                and credit_vals['currency'] != company_currency \
                and not has_credit_zero_residual_currency:
            # The credit line is using a foreign currency but not the opposite line.
            # In that case, convert the amount in company currency to the foreign currency one.
            recon_currency = credit_vals['currency']
            debit_rate = get_odoo_rate(debit_vals, other_line=credit_vals)
            credit_rate = get_accounting_rate(credit_vals)
            recon_debit_amount = recon_currency.round(remaining_debit_amount * debit_rate)
            recon_credit_amount = -remaining_credit_amount_curr

            # If there is nothing left after applying the rate to reconcile in foreign currency,
            # try to fallback on the company currency instead.
            if recon_currency.is_zero(recon_debit_amount) or recon_currency.is_zero(recon_credit_amount):
                recon_currency = company_currency
                debit_rate = 1
                recon_debit_amount = remaining_debit_amount
                recon_credit_amount = -remaining_credit_amount

        elif debit_vals['currency'] != company_currency \
                and is_rec_pay_account \
                and not has_debit_zero_residual_currency \
                and credit_vals['currency'] == company_currency \
                and not has_credit_zero_residual:
            # The debit line is using a foreign currency but not the opposite line.
            # In that case, convert the amount in company currency to the foreign currency one.
            recon_currency = debit_vals['currency']
            debit_rate = get_accounting_rate(debit_vals)
            credit_rate = get_odoo_rate(credit_vals, other_line=debit_vals)
            recon_debit_amount = remaining_debit_amount_curr
            recon_credit_amount = recon_currency.round(-remaining_credit_amount * credit_rate)

            # If there is nothing left after applying the rate to reconcile in foreign currency,
            # try to fallback on the company currency instead.
            if recon_currency.is_zero(recon_debit_amount) or recon_currency.is_zero(recon_credit_amount):
                recon_currency = company_currency
                credit_rate = 1
                recon_debit_amount = remaining_debit_amount
                recon_credit_amount = -remaining_credit_amount

        elif debit_vals['currency'] == credit_vals['currency'] \
                and debit_vals['currency'] != company_currency \
                and not has_debit_zero_residual_currency \
                and not has_credit_zero_residual_currency:
            # Both lines are sharing the same foreign currency.
            recon_currency = debit_vals['currency']
            debit_rate = get_accounting_rate(debit_vals)
            credit_rate = get_accounting_rate(credit_vals)
            recon_debit_amount = remaining_debit_amount_curr
            recon_credit_amount = -remaining_credit_amount_curr
        elif debit_vals['currency'] == credit_vals['currency'] \
                and debit_vals['currency'] != company_currency \
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
            debit_rate = get_accounting_rate(debit_vals)
            credit_rate = get_accounting_rate(credit_vals)
            recon_debit_amount = remaining_debit_amount
            recon_credit_amount = -remaining_credit_amount

        # Check if there is something left to reconcile. Move to the next loop iteration if not.
        skip_reconciliation = False
        if recon_currency.is_zero(recon_debit_amount):
            res['debit_vals'] = None
            skip_reconciliation = True
        if recon_currency.is_zero(recon_credit_amount):
            res['credit_vals'] = None
            skip_reconciliation = True
        if skip_reconciliation:
            return res

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
                partial_debit_amount_currency = debit_vals['currency'].round(debit_rate * min_recon_amount)
                partial_debit_amount_currency = min(partial_debit_amount_currency, remaining_debit_amount_curr)
            else:
                partial_debit_amount_currency = 0.0
            if credit_rate:
                partial_credit_amount_currency = credit_vals['currency'].round(credit_rate * min_recon_amount)
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
            if debit_vals['currency'] == company_currency:
                partial_debit_amount_currency = partial_amount
            else:
                partial_debit_amount_currency = min_recon_amount
            if credit_vals['currency'] == company_currency:
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
                    if not debit_vals['currency'].is_zero(debit_exchange_amount):
                        if debit_vals.get('record'):
                            exchange_lines_to_fix += debit_vals['record']
                        amounts_list.append({'amount_residual_currency': debit_exchange_amount})
                        remaining_debit_amount_curr -= debit_exchange_amount
                if credit_fully_matched:
                    credit_exchange_amount = remaining_credit_amount_curr + partial_credit_amount_currency
                    if not credit_vals['currency'].is_zero(credit_exchange_amount):
                        if credit_vals.get('record'):
                            exchange_lines_to_fix += credit_vals['record']
                        amounts_list.append({'amount_residual_currency': credit_exchange_amount})
                        remaining_credit_amount_curr += credit_exchange_amount

            else:
                if debit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    debit_exchange_amount = remaining_debit_amount - partial_amount
                    if not company_currency.is_zero(debit_exchange_amount):
                        if debit_vals.get('record'):
                            exchange_lines_to_fix += debit_vals['record']
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_vals['currency'] == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    debit_exchange_amount = partial_debit_amount - partial_amount
                    if company_currency.compare_amounts(debit_exchange_amount, 0.0) > 0:
                        if debit_vals.get('record'):
                            exchange_lines_to_fix += debit_vals['record']
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_vals['currency'] == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount

                if credit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    credit_exchange_amount = remaining_credit_amount + partial_amount
                    if not company_currency.is_zero(credit_exchange_amount):
                        if credit_vals.get('record'):
                            exchange_lines_to_fix += credit_vals['record']
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount -= credit_exchange_amount
                        if credit_vals['currency'] == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    credit_exchange_amount = partial_amount - partial_credit_amount
                    if company_currency.compare_amounts(credit_exchange_amount, 0.0) < 0:
                        if credit_vals.get('record'):
                            exchange_lines_to_fix += credit_vals['record']
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount -= credit_exchange_amount
                        if credit_vals['currency'] == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount

            if exchange_lines_to_fix:
                res['exchange_vals'] = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    exchange_date=max(debit_vals['date'], credit_vals['date']),
                )

        # ==== Create partials ====

        remaining_debit_amount -= partial_amount
        remaining_credit_amount += partial_amount
        remaining_debit_amount_curr -= partial_debit_amount_currency
        remaining_credit_amount_curr += partial_credit_amount_currency

        res['partial_vals'] = {
            'amount': partial_amount,
            'debit_amount_currency': partial_debit_amount_currency,
            'credit_amount_currency': partial_credit_amount_currency,
            'debit_move_id': debit_vals.get('record') and debit_vals['record'].id,
            'credit_move_id': credit_vals.get('record') and credit_vals['record'].id,
        }

        debit_vals['amount_residual'] = remaining_debit_amount
        debit_vals['amount_residual_currency'] = remaining_debit_amount_curr
        credit_vals['amount_residual'] = remaining_credit_amount
        credit_vals['amount_residual_currency'] = remaining_credit_amount_curr

        if debit_fully_matched:
            res['debit_vals'] = None
        if credit_fully_matched:
            res['credit_vals'] = None
        return res

    @api.model
    def _prepare_reconciliation_partials(self, vals_list):
        ''' Prepare the partials on the current journal items to perform the reconciliation.
        Note: The order of records in self is important because the journal items will be reconciled using this order.
        :return: a tuple of 1) list of vals for partial reconciliation creation, 2) the list of vals for the exchange difference entries to be created
        '''
        debit_vals_list = iter([x for x in vals_list if x['balance'] > 0.0 or x['amount_currency'] > 0.0])
        credit_vals_list = iter([x for x in vals_list if x['balance'] < 0.0 or x['amount_currency'] < 0.0])
        debit_vals = None
        credit_vals = None

        partials_vals_list = []
        exchange_data = {}

        while True:

            # ==== Find the next available lines ====
            # For performance reasons, the partials are created all at once meaning the residual amounts can't be
            # trusted from one iteration to another. That's the reason why all residual amounts are kept as variables
            # and reduced "manually" every time we append a dictionary to 'partials_vals_list'.

            # Move to the next available debit line.
            if not debit_vals:
                debit_vals = next(debit_vals_list, None)
                if not debit_vals:
                    break

            # Move to the next available credit line.
            if not credit_vals:
                credit_vals = next(credit_vals_list, None)
                if not credit_vals:
                    break

            # ==== Compute the amounts to reconcile ====

            res = self._prepare_reconciliation_single_partial(debit_vals, credit_vals)
            if res.get('partial_vals'):
                if res.get('exchange_vals'):
                    exchange_data[len(partials_vals_list)] = res['exchange_vals']
                partials_vals_list.append(res['partial_vals'])
            if res['debit_vals'] is None:
                debit_vals = None
            if res['credit_vals'] is None:
                credit_vals = None

        return partials_vals_list, exchange_data

    def _create_reconciliation_partials(self):
        '''create the partial reconciliation between all the records in self
         :return: A recordset of account.partial.reconcile.
        '''
        partials_vals_list, exchange_data = self._prepare_reconciliation_partials([
            {
                'record': line,
                'balance': line.balance,
                'amount_currency': line.amount_currency,
                'amount_residual': line.amount_residual,
                'amount_residual_currency': line.amount_residual_currency,
                'company': line.company_id,
                'currency': line.currency_id,
                'date': line.date,
            }
            for line in self
        ])
        partials = self.env['account.partial.reconcile'].create(partials_vals_list)

        # ==== Create exchange difference moves ====
        for index, exchange_vals in exchange_data.items():
            partials[index].exchange_move_id = self._create_exchange_difference_move(exchange_vals)

        return partials

    def _prepare_exchange_difference_move_vals(self, amounts_list, company=None, exchange_date=None, **kwargs):
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
            'always_tax_exigible': True,
        }
        to_reconcile = []

        for line, amounts in zip(self, amounts_list):
            move_vals['date'] = max(move_vals['date'], line.date)

            if 'amount_residual' in amounts:
                amount_residual = amounts['amount_residual']
                amount_residual_currency = 0.0
                if line.currency_id == line.company_id.currency_id:
                    amount_residual_currency = amount_residual
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
            line_vals = [
                {
                    'name': _('Currency exchange rate difference'),
                    'debit': -amount_residual if amount_residual < 0.0 else 0.0,
                    'credit': amount_residual if amount_residual > 0.0 else 0.0,
                    'amount_currency': -amount_residual_currency,
                    'account_id': line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.partner_id.id,
                    'sequence': sequence,
                },
                {
                    'name': _('Currency exchange rate difference'),
                    'debit': amount_residual if amount_residual > 0.0 else 0.0,
                    'credit': -amount_residual if amount_residual < 0.0 else 0.0,
                    'amount_currency': amount_residual_currency,
                    'account_id': exchange_line_account.id,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.partner_id.id,
                    'sequence': sequence + 1,
                },
            ]

            if kwargs.get('exchange_analytic_distribution'):
                line_vals[1].update({'analytic_distribution': kwargs['exchange_analytic_distribution']})

            move_vals['line_ids'] += [Command.create(vals) for vals in line_vals]
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
        exchange_move = self.env['account.move'].with_context(skip_invoice_sync=True).create(move_vals)
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
        caba_lines_to_reconcile = defaultdict(lambda: self.env['account.move.line']) # in the form {(move, account, repartition_line): move_lines}
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

            caba_rounding_diff_label = _("Cash basis rounding difference")
            move_vals['date'] = max(move_vals['date'], move.date)
            for caba_treatment, line in move_values['to_process_lines']:

                vals = {
                    'name': caba_rounding_diff_label,
                    'currency_id': line.currency_id.id,
                    'partner_id': line.partner_id.id,
                    'tax_ids': [Command.set(line.tax_ids.ids)],
                    'tax_tag_ids': [Command.set(line.tax_tag_ids.ids)],
                    'debit': line.debit,
                    'credit': line.credit,
                    'amount_currency': line.amount_currency,
                }

                if caba_treatment == 'tax':
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
                            'amount_currency': account_vals_to_fix[grouping_key]['amount_currency'] + line.amount_currency,
                        })
                    else:
                        account_vals_to_fix[grouping_key] = {
                            **vals,
                            'account_id': line.account_id.id,
                            'tax_base_amount': line.tax_base_amount,
                            'tax_repartition_line_id': line.tax_repartition_line_id.id,
                        }

                    if line.account_id.reconcile:
                        caba_lines_to_reconcile[(move, line.account_id, line.tax_repartition_line_id)] |= line

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
                        account_vals_to_fix[grouping_key]['amount_currency'] += vals['amount_currency']

            # ==========================================================================
            # Subtract the balance of all previously generated cash basis journal entries
            # in order to retrieve the residual balance of each involved transfer account.
            # ==========================================================================

            cash_basis_moves = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', move.id)])
            caba_transition_accounts = self.env['account.account']
            for line in cash_basis_moves.line_ids:
                grouping_key = None
                if line.tax_repartition_line_id:
                    # Tax line.
                    transition_account = line.tax_line_id.cash_basis_transition_account_id
                    grouping_key = self.env['account.partial.reconcile']._get_cash_basis_tax_line_grouping_key_from_record(
                        line,
                        account=transition_account,
                    )
                    caba_transition_accounts |= transition_account
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
                account_vals_to_fix[grouping_key]['amount_currency'] -= line.amount_currency

            # Collect the caba lines affecting the transition account.
            for transition_line in filter(lambda x: x.account_id in caba_transition_accounts, cash_basis_moves.line_ids):
                caba_reconcile_key = (transition_line.move_id, transition_line.account_id, transition_line.tax_repartition_line_id)
                caba_lines_to_reconcile[caba_reconcile_key] |= transition_line

            # ==========================================================================
            # Generate the exchange difference journal items:
            # - to reset the balance of all transfer account to zero.
            # - fix rounding issues on the tax account/base tax account.
            # ==========================================================================

            currency = move_values['currency']

            # To know which rate to use for the adjustment, get the rate used by the most recent cash basis move
            last_caba_move = max(cash_basis_moves, key=lambda m: m.date) if cash_basis_moves else self.env['account.move']
            currency_line = last_caba_move.line_ids.filtered(lambda x: x.currency_id == currency)[:1]
            currency_rate = currency_line.balance / currency_line.amount_currency if currency_line.amount_currency else 1.0

            existing_line_vals_list = move_vals['line_ids']
            next_sequence = len(existing_line_vals_list)
            for grouping_key, values in account_vals_to_fix.items():

                if currency.is_zero(values['amount_currency']):
                    continue

                # There is a rounding error due to multiple payments on the foreign currency amount
                balance = currency.round(currency_rate * values['amount_currency'])

                if values.get('tax_repartition_line_id'):
                    # Tax line
                    tax_repartition_line = self.env['account.tax.repartition.line'].browse(values['tax_repartition_line_id'])
                    account = tax_repartition_line.account_id or self.env['account.account'].browse(values['account_id'])

                    existing_line_vals_list.extend([
                        Command.create({
                            **values,
                            'debit': balance if balance > 0.0 else 0.0,
                            'credit': -balance if balance < 0.0 else 0.0,
                            'amount_currency': values['amount_currency'],
                            'account_id': account.id,
                            'sequence': next_sequence,
                        }),
                        Command.create({
                            **values,
                            'debit': -balance if balance < 0.0 else 0.0,
                            'credit': balance if balance > 0.0 else 0.0,
                            'amount_currency': -values['amount_currency'],
                            'account_id': values['account_id'],
                            'tax_ids': [],
                            'tax_tag_ids': [],
                            'tax_base_amount': 0,
                            'tax_repartition_line_id': False,
                            'sequence': next_sequence + 1,
                        }),
                    ])
                else:
                    # Base line
                    existing_line_vals_list.extend([
                        Command.create({
                            **values,
                            'debit': balance if balance > 0.0 else 0.0,
                            'credit': -balance if balance < 0.0 else 0.0,
                            'amount_currency': values['amount_currency'],
                            'sequence': next_sequence,
                        }),
                        Command.create({
                            **values,
                            'debit': -balance if balance < 0.0 else 0.0,
                            'credit': balance if balance > 0.0 else 0.0,
                            'amount_currency': -values['amount_currency'],
                            'tax_ids': [],
                            'tax_tag_ids': [],
                            'sequence': next_sequence + 1,
                        }),
                    ])

                next_sequence += 2

        return caba_lines_to_reconcile

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

        not_paid_invoices = self.move_id.filtered(lambda move:
            move.is_invoice(include_receipts=True)
            and move.payment_state not in ('paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.account_type not in ('asset_cash', 'liability_credit_card'):
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

        if self._context.get('reduced_line_sorting'):
            sorting_f = lambda line: (line.date_maturity or line.date, line.currency_id)
        else:
            sorting_f = lambda line: (line.date_maturity or line.date, line.currency_id, line.amount_currency)
        sorted_lines = self.sorted(key=sorting_f)

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines._all_reconciled_lines()
        involved_partials = involved_lines.matched_credit_ids | involved_lines.matched_debit_ids

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

        is_cash_basis_needed = account.company_id.tax_exigibility and account.account_type in ('asset_receivable', 'liability_payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        def is_line_reconciled(line, has_multiple_currencies):
            # Check if the journal item passed as parameter is now fully reconciled.
            return line.reconciled \
                   or (line.company_currency_id.is_zero(line.amount_residual)
                       if has_multiple_currencies
                       else line.currency_id.is_zero(line.amount_residual_currency)
                   )

        has_multiple_currencies = len(involved_lines.currency_id) > 1
        if all(is_line_reconciled(line, has_multiple_currencies) for line in involved_lines):
            # ==== Create the exchange difference move ====
            # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
            # when importing a full accounting including the reconciliation like Winbooks.

            exchange_move = self.env['account.move']
            caba_lines_to_reconcile = None
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
                # If we are fully reversing the entry, no need to fix anything since the journal entry
                # is exactly the mirror of the source journal entry.
                if is_cash_basis_needed and not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
                    caba_lines_to_reconcile = involved_lines._add_exchange_difference_cash_basis_vals(exchange_diff_vals)

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
            results['full_reconcile'] = self.env['account.full.reconcile'] \
                .with_context(
                    skip_invoice_sync=True,
                    skip_invoice_line_sync=True,
                    skip_account_move_synchronization=True,
                    check_move_validity=False,
                ) \
                .create({
                    'exchange_move_id': exchange_move and exchange_move.id,
                    'partial_reconcile_ids': [Command.set(involved_partials.ids)],
                    'reconciled_line_ids': [Command.set(involved_lines.ids)],
                })

            # === Cash basis rounding autoreconciliation ===
            # In case a cash basis rounding difference line got created for the transition account, we reconcile it with the corresponding lines
            # on the cash basis moves (so that it reaches full reconciliation and creates an exchange difference entry for this account as well)

            if caba_lines_to_reconcile:
                for (dummy, account, repartition_line), amls_to_reconcile in caba_lines_to_reconcile.items():
                    if not account.reconcile:
                        continue

                    exchange_line = exchange_move.line_ids.filtered(
                        lambda l: l.account_id == account and l.tax_repartition_line_id == repartition_line
                    )

                    (exchange_line + amls_to_reconcile).filtered(lambda l: not l.reconciled).reconcile()

        not_paid_invoices.filtered(lambda move:
            move.payment_state in ('paid', 'in_payment')
        )._invoice_paid_hook()

        return results

    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        (self.matched_debit_ids + self.matched_credit_ids).unlink()

    # -------------------------------------------------------------------------
    # ANALYTIC
    # -------------------------------------------------------------------------

    def _validate_analytic_distribution(self):
        for line in self.filtered(lambda line: line.display_type == 'product'):
            line._validate_distribution(**{
                        'product': line.product_id.id,
                        'account': line.account_id.id,
                        'business_domain': line.move_id.move_type in ['out_invoice', 'out_refund', 'out_receipt'] and 'invoice'
                                           or line.move_id.move_type in ['in_invoice', 'in_refund', 'in_receipt'] and 'bill'
                                           or 'general',
                        'company_id': line.company_id.id,
            })

    def _create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic distribution.
        """
        self._validate_analytic_distribution()
        analytic_line_vals = []
        for line in self:
            analytic_line_vals.extend(line._prepare_analytic_lines())

        self.env['account.analytic.line'].create(analytic_line_vals)

    def _prepare_analytic_lines(self):
        self.ensure_one()
        analytic_line_vals = []
        if self.analytic_distribution:
            # distribution_on_each_plan corresponds to the proportion that is distributed to each plan to be able to
            # give the real amount when we achieve a 100% distribution
            distribution_on_each_plan = {}

            for account_id, distribution in self.analytic_distribution.items():
                line_values = self._prepare_analytic_distribution_line(float(distribution), account_id, distribution_on_each_plan)
                if not self.currency_id.is_zero(line_values.get('amount')):
                    analytic_line_vals.append(line_values)
        return analytic_line_vals

    def _prepare_analytic_distribution_line(self, distribution, account_id, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_id = int(account_id)
        account = self.env['account.analytic.account'].browse(account_id)
        distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
            amount = -self.balance * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
        else:
            amount = -self.balance * distribution / 100.0
        distribution_on_each_plan[account.root_plan_id] = distribution_plan
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            'account_id': account_id,
            'partner_id': self.partner_id.id,
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_line_id': self.id,
            'user_id': self.move_id.invoice_user_id.id or self._uid,
            'company_id': account.company_id.id or self.company_id.id or self.env.company.id,
            'category': 'invoice' if self.move_id.is_sale_document() else 'vendor_bill' if self.move_id.is_purchase_document() else 'other',
        }

    # -------------------------------------------------------------------------
    # MISC
    # -------------------------------------------------------------------------

    def _get_integrity_hash_fields(self):
        # Use the new hash version by default, but keep the old one for backward compatibility when generating the integrity report.
        hash_version = self._context.get('hash_version', MAX_HASH_VERSION)
        if hash_version == 1:
            return ['debit', 'credit', 'account_id', 'partner_id']
        elif hash_version in (2, 3):
            return ['name', 'debit', 'credit', 'account_id', 'partner_id']
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

    def _reconciled_lines(self):
        ids = []
        for aml in self.filtered('reconciled'):
            ids.extend([r.debit_move_id.id for r in aml.matched_debit_ids] if aml.credit > 0 else [r.credit_move_id.id for r in aml.matched_credit_ids])
            ids.append(aml.id)
        return ids

    def _all_reconciled_lines(self):
        reconciliation_lines = self.filtered(lambda x: x.account_id.reconcile or x.account_id.account_type in ('asset_cash', 'liability_credit_card'))
        current_lines = reconciliation_lines
        current_partials = self.env['account.partial.reconcile']
        while current_lines:
            current_partials = (current_lines.matched_debit_ids + current_lines.matched_credit_ids) - current_partials
            current_lines = (current_partials.debit_move_id + current_partials.credit_move_id) - current_lines
            reconciliation_lines += current_lines
        return reconciliation_lines

    def _get_attachment_domains(self):
        self.ensure_one()
        domains = [[('res_model', '=', 'account.move'), ('res_id', '=', self.move_id.id)]]
        if self.statement_id:
            domains.append([('res_model', '=', 'account.bank.statement'), ('res_id', '=', self.statement_id.id)])
        if self.payment_id:
            domains.append([('res_model', '=', 'account.payment'), ('res_id', '=', self.payment_id.id)])
        return domains

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

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.
        :return: A python dictionary.
        """
        self.ensure_one()
        is_invoice = self.move_id.is_invoice(include_receipts=True)
        sign = -1 if self.move_id.is_inbound(include_receipts=True) else 1

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
            analytic_distribution=self.analytic_distribution,
            price_subtotal=sign * self.amount_currency,
            is_refund=self.is_refund,
            rate=(abs(self.amount_currency) / abs(self.balance)) if self.balance else 1.0
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
            analytic_distribution=self.analytic_distribution,
            tax_amount=sign * self.amount_currency,
        )

    def _get_invoiced_qty_per_product(self):
        qties = defaultdict(float)
        for aml in self:
            qty = aml.product_uom_id._compute_quantity(aml.quantity, aml.product_id.uom_id)
            if aml.move_id.move_type == 'out_invoice':
                qties[aml.product_id] += qty
            elif aml.move_id.move_type == 'out_refund':
                qties[aml.product_id] -= qty
        return qties

    def _get_lock_date_protected_fields(self):
        """ Returns the names of the fields that should be protected by the accounting fiscal year and tax lock dates
        """
        tax_fnames = ['balance', 'tax_line_id', 'tax_ids', 'tax_tag_ids']
        fiscal_fnames = tax_fnames + ['account_id', 'journal_id', 'amount_currency', 'currency_id', 'partner_id']
        reconciliation_fnames = ['account_id', 'date', 'balance', 'amount_currency', 'currency_id', 'partner_id']
        return {
            'tax': tax_fnames,
            'fiscal': fiscal_fnames,
            'reconciliation': reconciliation_fnames,
        }

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Journal Items'),
            'template': '/account/static/xls/aml_import_template.xlsx'
        }]

    def _is_eligible_for_early_payment_discount(self, currency, reference_date):
        self.ensure_one()
        return self.display_type == 'payment_term' \
            and self.currency_id == currency \
            and self.move_id.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt') \
            and not self.matched_debit_ids \
            and not self.matched_credit_ids \
            and self.discount_date \
            and reference_date <= self.discount_date

    # -------------------------------------------------------------------------
    # PUBLIC ACTIONS
    # -------------------------------------------------------------------------

    def open_reconcile_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_grouped_matching')
        ids = self._all_reconciled_lines().filtered(lambda l: l.matched_debit_ids or l.matched_credit_ids).ids
        action['domain'] = [('id', 'in', ids)]
        return clean_action(action, self.env)

    def action_open_business_doc(self):
        return self.move_id.action_open_business_doc()

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

    # -------------------------------------------------------------------------
    # TOOLING
    # -------------------------------------------------------------------------

    def _conditional_add_to_compute(self, fname, condition):
        field = self._fields[fname]
        to_reset = self.filtered(lambda line:
            condition(line)
            and not self.env.is_protected(field, line)
        )
        to_reset.invalidate_recordset([fname])
        self.env.add_to_compute(field, to_reset)

    # -------------------------------------------------------------------------
    # HOOKS
    # -------------------------------------------------------------------------

    def _copy_data_extend_business_fields(self, values):
        self.ensure_one()

    def _get_downpayment_lines(self):
        ''' Return the downpayment move lines associated with the move line.
        This method is overridden in the sale order module.
        '''
        return self.env['account.move.line']
