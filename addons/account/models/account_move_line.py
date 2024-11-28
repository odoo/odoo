from collections import defaultdict
from contextlib import contextmanager
from datetime import date
import logging
import re

from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from odoo.tools import frozendict, format_date, float_compare, format_list, Query
from odoo.tools.sql import create_index, SQL
from odoo.addons.web.controllers.utils import clean_action

from odoo.addons.account.models.account_move import MAX_HASH_VERSION


_logger = logging.getLogger(__name__)


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

    journal_group_id = fields.Many2one(
        string='Ledger',
        comodel_name='account.journal.group',
        store=False,
        search='_search_journal_group_id',
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
        aggregator='min',
    )
    invoice_date = fields.Date(
        related='move_id.invoice_date', store=True,
        copy=False,
        aggregator='min',
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
        index=False,  # covered by account_move_line_account_id_date_idx defined in init()
        auto_join=True,
        ondelete="cascade",
        domain="[('deprecated', '=', False), ('account_type', '!=', 'off_balance')]",
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
        tracking=True,
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
    is_imported = fields.Boolean()  # Technical field indicating if the line was captured automatically by import/ocr etc

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
        related='move_id.origin_payment_id', store=True,
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
        tracking=True,
    )
    group_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Originator Group of Taxes",
        index='btree_not_null',
        check_company=True,
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
        aggregator=None,
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
        copy=False,
        index='btree',
        help="Matching number for this line, 'P' if it is only partially reconcile, or the name of "
             "the full reconcile if it exists.",
    )  # can also start with `I` for imports: see `_reconcile_marked`
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
        depends_context='company',
    )
    product_category_id = fields.Many2one(related='product_id.product_tmpl_id.categ_id')

    # ==============================================================================================
    #                                          INVOICE
    # ==============================================================================================

    display_type = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('cogs', 'Cost of Goods Sold'),
            ('tax', 'Tax'),
            ('discount', "Discount"),
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
        check_company=True,
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
    tax_calculation_rounding_method = fields.Selection(
        related='company_id.tax_calculation_rounding_method',
        string='Tax calculation rounding method', readonly=True)
    # === Invoice sync fields === #
    term_key = fields.Binary(compute='_compute_term_key', exportable=False)
    epd_key = fields.Binary(compute='_compute_epd_key', exportable=False)
    epd_needed = fields.Binary(compute='_compute_epd_needed', exportable=False)
    epd_dirty = fields.Boolean(compute='_compute_epd_needed')
    discount_allocation_key = fields.Binary(compute='_compute_discount_allocation_key', exportable=False)
    discount_allocation_needed = fields.Binary(compute='_compute_discount_allocation_needed', exportable=False)
    discount_allocation_dirty = fields.Boolean(compute='_compute_discount_allocation_needed')

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
        aggregator=None,
    )
    # Discounted balance when the early payment discount is applied
    discount_balance = fields.Monetary(
        string='Discount Balance',
        store=True,
        currency_field='company_currency_id',
    )

    # === Payment Fields === #
    # payment_date is the closest date to the date the aml was created between discount_date and date_maturity.
    payment_date = fields.Date(
        string='Next Payment Date',
        compute='_compute_payment_date',
        search='_search_payment_date',
    )

    # === Misc Information === #
    is_refund = fields.Boolean(compute='_compute_is_refund')

    _sql_constraints = [
        (
            "check_credit_debit",
            "CHECK(display_type IN ('line_section', 'line_note') OR credit * debit=0)",
            "Wrong credit or debit value in accounting entry!"
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

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if res['views'].get('list') and self.env['ir.ui.view'].sudo().browse(res['views']['list']['id']).name == "account.move.line.payment.list":
            if toolbar := res['views']['list'].get('toolbar'):
                # We dont want any additionnal action in the "account.move.line.payment.list" view toolbar
                toolbar['action'] = []
        return res

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

    @api.depends('product_id', 'move_id.ref', 'move_id.payment_reference')
    def _compute_name(self):
        def get_name(line):
            values = []
            if line.partner_id.lang:
                product = line.product_id.with_context(lang=line.partner_id.lang)
            else:
                product = line.product_id
            if not product:
                return False

            if line.journal_id.type == 'sale':
                values.append(product.display_name)
                if product.description_sale:
                    values.append(product.description_sale)
            elif line.journal_id.type == 'purchase':
                values.append(product.display_name)
                if product.description_purchase:
                    values.append(product.description_purchase)
            return '\n'.join(values)

        term_by_move = (self.move_id.line_ids | self).filtered(lambda l: l.display_type == 'payment_term').sorted(lambda l: l.date_maturity or date.max).grouped('move_id')
        for line in self.filtered(lambda l: l.move_id.inalterable_hash is False):
            if line.display_type == 'payment_term':
                term_lines = term_by_move.get(line.move_id, self.env['account.move.line'])
                n_terms = len(line.move_id.invoice_payment_term_id.line_ids)
                if line.move_id.payment_reference and line.move_id.ref:
                    name = f'{line.move_id.ref} - {line.move_id.payment_reference}'
                else:
                    name = line.move_id.payment_reference or ''

                if n_terms > 1:
                    index = term_lines._ids.index(line.id) if line in term_lines else len(term_lines)
                    name = _('%(name)s installment #%(number)s', name=name, number=index + 1).lstrip()
                if n_terms > 1 or not line.name or line._origin.name == line._origin.move_id.payment_reference or (
                    line._origin.move_id.payment_reference and line._origin.move_id.ref
                    and line._origin.name == f'{line._origin.move_id.ref} - {line._origin.move_id.payment_reference}'
                ):
                    line.name = name
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
                fallback AS (
                    SELECT DISTINCT ON (account_companies.res_company_id, account.account_type)
                           'res.company' AS model,
                           account_companies.res_company_id AS id,
                           account.account_type AS account_type,
                           account.id AS account_id
                      FROM account_account account
                      JOIN account_account_res_company_rel account_companies
                           ON account_companies.account_account_id = account.id
                     WHERE account_companies.res_company_id = ANY(%(company_ids)s)
                       AND account.account_type IN ('asset_receivable', 'liability_payable')
                       AND account.deprecated = 'f'
                )
                SELECT * FROM previous
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
                    or move.with_company(move.company_id).commercial_partner_id['property_account_receivable_id' if account_type == 'asset_receivable' else 'property_account_payable_id'].id
                    or move.with_company(move.company_id).company_id.partner_id['property_account_receivable_id' if account_type == 'asset_receivable' else 'property_account_payable_id'].id
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
                account_id = self.env['account.account']._get_most_frequent_account_for_partner(
                    company_id=line.company_id.id,
                    partner_id=line.partner_id.id,
                    move_type=line.move_id.move_type,
                )
                if account_id:
                    line.account_id = account_id
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
                # balance is always the written field because of `_sanitize_vals`.
                # Virtual record holds just the differences coming from the onchange
                # so we need to recover balance of stored lines to calculate correctly the
                # new line balance.
                active_line_ids = [lid for lid in self.env.context.get('line_ids', []) if isinstance(lid, int)]
                existing_lines = self.env['account.move.line'].browse(active_line_ids)
                outdated_lines = line.move_id.line_ids._origin
                new_lines = line.move_id.line_ids - line
                line.balance = -sum((existing_lines - outdated_lines + new_lines).mapped('balance'))
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

    @api.depends('currency_id', 'company_id', 'move_id.invoice_currency_rate', 'move_id.date')
    def _compute_currency_rate(self):
        for line in self:
            if line.move_id.is_invoice(include_receipts=True):
                line.currency_rate = line.move_id.invoice_currency_rate
            elif line.currency_id:
                line.currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line),
                )
            else:
                line.currency_rate = 1

    # TODO: remove in master
    def _get_rate_date(self):
        self.ensure_one()
        return self.move_id.invoice_date or self.move_id.date or fields.Date.context_today(self)

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

    @api.depends_context('order_cumulated_balance', 'domain_cumulated_balance')
    def _compute_cumulated_balance(self):
        if not self.env.context.get('order_cumulated_balance'):
            # We do not come from search_fetch, so we are not in a list view, so it doesn't make any sense to compute the cumulated balance
            self.cumulated_balance = 0
            return

        # get the where clause
        query = self._where_calc(list(self.env.context.get('domain_cumulated_balance') or []))
        sql_order = self._order_to_sql(self.env.context.get('order_cumulated_balance'), query, reverse=True)
        result = dict(self.env.execute_query(query.select(
            SQL.identifier(query.table, "id"),
            SQL(
                "SUM(%s) OVER (ORDER BY %s ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)",
                SQL.identifier(query.table, "balance"),
                sql_order,
            ),
        )))
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
        """ Compute 'price_subtotal' / 'price_total' outside of `_sync_tax_lines` because those values must be visible for the
        user on the UI with draft moves and the dynamic lines are synchronized only when saving the record.
        """
        AccountTax = self.env['account.tax']
        for line in self:
            # TODO remove the need of cogs lines to have a price_subtotal/price_total
            if line.display_type not in ('product', 'cogs'):
                line.price_total = line.price_subtotal = False
                continue

            base_line = line.move_id._prepare_product_base_line_for_taxes_computation(line)
            AccountTax._add_tax_details_in_base_line(base_line, line.company_id)
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_total = base_line['tax_details']['raw_total_included_currency']

    @api.depends('product_id', 'product_uom_id')
    def _compute_price_unit(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note') or line.is_imported:
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
            if (line.product_id or line.account_id.tax_ids or not line.tax_ids) and not line.is_imported:
                line.tax_ids = line._get_computed_taxes()

    def _get_computed_taxes(self):
        self.ensure_one()

        company_domain = self.env['account.tax']._check_company_domain(self.move_id.company_id)
        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            filtered_taxes_id = self.product_id.taxes_id.filtered_domain(company_domain)
            tax_ids = filtered_taxes_id or self.account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'sale')

        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            filtered_supplier_taxes_id = self.product_id.supplier_taxes_id.filtered_domain(company_domain)
            tax_ids = filtered_supplier_taxes_id or self.account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'purchase')

        else:
            tax_ids = False if self.env.context.get('skip_computed_taxes') else self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids._filter_taxes_by_company(self.company_id)

        if tax_ids and self.move_id.fiscal_position_id:
            tax_ids = self.move_id.fiscal_position_id.map_tax(tax_ids)

        return tax_ids

    @api.depends('account_id', 'company_id')
    def _compute_discount_allocation_key(self):
        for line in self:
            if line.display_type == 'discount':
                line.discount_allocation_key = frozendict({
                    'account_id': line.account_id.id,
                    'move_id': line.move_id.id,
                    'currency_rate': line.currency_rate,
                })
            else:
                line.discount_allocation_key = False

    @api.depends('account_id', 'company_id', 'discount', 'price_unit', 'quantity', 'currency_rate')
    def _compute_discount_allocation_needed(self):
        for line in self:
            line.discount_allocation_dirty = True
            discount_allocation_account = line.move_id._get_discount_allocation_account()

            if not discount_allocation_account or line.display_type != 'product' or line.currency_id.is_zero(line.discount):
                line.discount_allocation_needed = False
                continue

            discounted_amount_currency = line.currency_id.round(line.move_id.direction_sign * line.quantity * line.price_unit * line.discount/100)
            discount_allocation_needed = {}
            discount_allocation_needed_vals = discount_allocation_needed.setdefault(
                frozendict({
                    'account_id': line.account_id.id,
                    'move_id': line.move_id.id,
                    'currency_rate': line.currency_rate,
                }),
                {
                    'display_type': 'discount',
                    'name': _("Discount"),
                    'amount_currency': 0.0,
                },
            )
            discount_allocation_needed_vals['amount_currency'] += discounted_amount_currency
            discount_allocation_needed_vals = discount_allocation_needed.setdefault(
                frozendict({
                    'move_id': line.move_id.id,
                    'account_id': discount_allocation_account.id,
                    'currency_rate': line.currency_rate,
                }),
                {
                    'display_type': 'discount',
                    'name': _("Discount"),
                    'amount_currency': 0.0,
                },
            )
            discount_allocation_needed_vals['amount_currency'] -= discounted_amount_currency
            line.discount_allocation_needed = {k: frozendict(v) for k, v in discount_allocation_needed.items()}

    @api.depends('tax_ids', 'account_id', 'company_id')
    def _compute_epd_key(self):
        for line in self:
            pay_term = line.move_id.invoice_payment_term_id
            if line.display_type == 'epd' and pay_term.early_discount and pay_term.early_pay_discount_computation == 'mixed':
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
        # TODO: The computation of early payment is weird because based on the 'price_subtotal'
        # that already have it's own taxes computation (by design because the sync_dynamic lines only
        # work when saving the record).
        # However, the early payment lines also have some taxes and the sync_dynamic_line will compute the tax lines based on
        # product base lines + epd base lines that could lead to a different amount when using the round globally.
        for line in self:
            line.epd_dirty = True
            line.epd_needed = False
            has_epd = line.move_id.invoice_payment_term_id.early_discount
            discount_percentage = line.move_id.invoice_payment_term_id.discount_percentage

            if not has_epd or line.display_type != 'product' or not line.tax_ids.ids or line.move_id.invoice_payment_term_id.early_pay_discount_computation != 'mixed':
                continue
            discount_percentage_name = f"{discount_percentage}%"
            epd_needed = {}
            percentage = discount_percentage / 100
            taxes = line.tax_ids.filtered(lambda t: t.amount_type != 'fixed')
            epd_needed_vals = epd_needed.setdefault(
                frozendict({
                    'move_id': line.move_id.id,
                    'account_id': line.account_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'tax_ids': [Command.set(taxes.ids)],
                    'display_type': 'epd',
                }),
                {
                    'name': _("Early Payment Discount (%s)", discount_percentage_name),
                    'amount_currency': 0.0,
                    'balance': 0.0,
                },
            )
            sign = line.move_id.direction_sign
            rate = line.move_id.invoice_currency_rate
            amount_currency = line.currency_id.round(sign * line.price_subtotal * percentage)
            balance = line.company_currency_id.round(sign * line.price_subtotal * percentage / rate) if rate else 0.0
            epd_needed_vals['amount_currency'] -= amount_currency
            epd_needed_vals['balance'] -= balance
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
                    'tax_ids': [Command.clear()],
                },
            )
            epd_needed_vals['amount_currency'] += amount_currency
            epd_needed_vals['balance'] += balance
            line.epd_needed = {k: frozendict(v) for k, v in epd_needed.items()}

    @api.depends('move_id.move_type', 'balance', 'tax_repartition_line_id', 'tax_ids')
    def _compute_is_refund(self):
        for line in self:
            is_refund = False
            if line.move_id.move_type in ('out_refund', 'in_refund'):
                is_refund = True
            elif line.move_id.move_type == 'entry':
                if line.tax_repartition_line_id:
                    is_refund = line.tax_repartition_line_id.document_type == 'refund'
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
                })
            else:
                line.term_key = False

    @api.depends('account_id', 'partner_id', 'product_id')
    def _compute_analytic_distribution(self):
        cache = {}
        for line in self:
            if line.display_type == 'product' or not line.move_id.is_invoice(include_receipts=True):
                arguments = frozendict({
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "partner_id": line.partner_id.id,
                    "partner_category_id": line.partner_id.category_id.ids,
                    "account_prefix": line.account_id.code,
                    "company_id": line.company_id.id,
                })
                if arguments not in cache:
                    cache[arguments] = self.env['account.analytic.distribution.model']._get_distribution(arguments)
                line.analytic_distribution = cache[arguments] or line.analytic_distribution

    @api.depends('discount_date', 'date_maturity')
    def _compute_payment_date(self):
        for line in self:
            line.payment_date = line.discount_date if line.discount_date and date.today() <= line.discount_date else line.date_maturity

    def _search_payment_date(self, operator, value):
        if operator == '=':
            operator = '<='
        return [
                '|',
                '|',
                '&', ('discount_date', '>=', str(date.today())), ('discount_date', operator, value),
                '&', ('discount_date', '<', str(date.today())), ('date_maturity', operator, value),
                '&', ('discount_date', '=', False), ('date_maturity', operator, value),
            ]

    def action_payment_items_register_payment(self):
        return self.action_register_payment(ctx={'default_group_payment': True})

    def action_register_payment(self, ctx=None):
        ''' Open the account.payment.register wizard to pay the selected journal items.
        :return: An action opening the account.payment.register wizard.
        '''
        context = {
            'active_model': 'account.move.line',
            'active_ids': self.ids,
        }
        if ctx:
            context.update(ctx)
        return {
            'name': _('Pay'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'context': context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

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

        context = dict(self.env.context)
        context.pop('default_account_id', None)
        lines_to_modify.with_context(context)._create_analytic_lines()

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
        # Avoid using api.constrains for fields journal_id and account_id as in case of a write on
        # account move and account move line in the same operation, the check would be done
        # before all write are complete, causing a false positive
        self.flush_recordset()
        for line in self.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):
            account = line.account_id
            journal = line.move_id.journal_id

            if account.deprecated and not self.env.context.get('skip_account_deprecation_check'):
                raise UserError(_('The account %(name)s (%(code)s) is deprecated.', name=account.name, code=account.code))

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
            if line.account_id.account_type == 'off_balance':
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
                    "The Unit of Measure (UoM) '%(uom)s' you have selected for product '%(product)s', "
                    "is incompatible with its category : %(category)s.",
                    uom=line.product_uom_id.name,
                    product=line.product_id.name,
                    category=line.product_id.product_tmpl_id.uom_id.category_id.name
                ))

    def _affect_tax_report(self):
        self.ensure_one()
        return self.tax_ids or self.tax_line_id or self.tax_tag_ids.filtered(lambda x: x.applicability == "taxes")

    def _check_tax_lock_date(self):
        for line in self:
            move = line.move_id
            if move.state != 'posted':
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
                raise UserError(_("The operation is refused as it would impact an already issued tax statement. "
                                  "Please change the journal entry date or the following lock dates to proceed: %(lock_date_info)s.",
                                  lock_date_info=self.env['res.company']._format_lock_dates(violated_lock_dates)))
        return True

    def _check_reconciliation(self):
        for line in self:
            if line.matched_debit_ids or line.matched_credit_ids:
                raise UserError(_("You cannot do this modification on a reconciled journal entry. "
                                  "You can just change some non legal fields or you must unreconcile first.\n"
                                  "Journal Entry (id): %(entry)s (%(id)s)", entry=line.move_id.name, id=line.move_id.id))

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

    @api.constrains('matching_number', 'matched_debit_ids', 'matched_credit_ids')
    def _constrains_matching_number(self):
        for line in self:
            if line.matching_number:
                if not re.match(r'^((P?\d+)|(I.+))$', line.matching_number):
                    raise Exception("Invalid matching number format")
                elif line.matching_number.startswith('I') and (line.matched_debit_ids or line.matched_credit_ids):
                    raise ValidationError(_("A temporary number can not be used in a real matching"))
                elif line.matching_number.startswith('P') and not (line.matched_debit_ids or line.matched_credit_ids):
                    raise Exception("Should have partials")
                elif line.matching_number.startswith('P') and line.full_reconcile_id:
                    raise Exception("Should not be partial number")
                elif line.matching_number.isdecimal() and not line.full_reconcile_id:
                    raise Exception("Should not be full number")
                elif line.full_reconcile_id and line.matching_number != str(line.full_reconcile_id.id):
                    raise Exception("Matching number should be the full reconcile")
            elif line.matched_debit_ids or line.matched_credit_ids:
                raise Exception("Should have number")

    # -------------------------------------------------------------------------
    # CRUD/ORM
    # -------------------------------------------------------------------------
    def check_field_access_rights(self, operation, field_names):
        result = super().check_field_access_rights(operation, field_names)
        if not field_names:
            weirdos = ['term_key', 'epd_key', 'epd_needed', 'discount_allocation_key', 'discount_allocation_needed']
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
        return super().invalidate_model(fnames, flush)

    def invalidate_recordset(self, fnames=None, flush=True):
        # Invalidate cache of related moves
        if fnames is None or 'move_id' in fnames:
            field = self._fields['move_id']
            move_ids = {id_ for id_ in self.env.cache.get_values(self, field) if id_}
            if move_ids:
                self.env['account.move'].browse(move_ids).invalidate_recordset()
        return super().invalidate_recordset(fnames, flush)

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        def to_tuple(t):
            return tuple(map(to_tuple, t)) if isinstance(t, (list, tuple)) else t
        order = (order or self._order)
        if not re.search(r'\bid\b', order):
            # Make an explicit order because we will need to reverse it
            order += ', id'
        # Add the domain and order by in order to compute the cumulated balance in _compute_cumulated_balance
        contextualized = self.with_context(
            domain_cumulated_balance=to_tuple(domain or []),
            order_cumulated_balance=order,
        )
        return super(AccountMoveLine, contextualized).search_fetch(domain, field_names, offset, limit, order)

    def init(self):
        """ change index on partner_id to a multi-column index on (partner_id, ref), the new index will behave in the
            same way when we search on partner_id, with the addition of being optimal when having a query that will
            search on partner_id and ref at the same time (which is the case when we open the bank reconciliation widget)
        """
        create_index(self._cr, 'account_move_line_partner_id_ref_idx', 'account_move_line', ["partner_id", "ref"])
        create_index(self._cr, 'account_move_line_date_name_id_idx', 'account_move_line', ["date desc", "move_name desc", "id"])
        # Match exactly how the ORM converts domains to ensure the query planner uses it
        create_index(self._cr, 'account_move_line__unreconciled_index', 'account_move_line', ['account_id', 'partner_id'],
                     where="(reconciled IS NULL OR reconciled = false OR reconciled IS NOT true) AND parent_state = 'posted'")
        create_index(self.env.cr,
                     indexname='account_move_line_journal_id_neg_amnt_residual_idx',
                     tablename='account_move_line',
                     expressions=['journal_id'],
                     where="amount_residual < 0 AND parent_state = 'posted'")
        # covers the standard index on account_id
        create_index(self.env.cr,
                     indexname='account_move_line_account_id_date_idx',
                     tablename='account_move_line',
                     expressions=['account_id', 'date'])
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
        if (
            vals.get('matching_number')
            and not vals['matching_number'].startswith('I')
            and not self.env.context.get('skip_matching_number_check')
        ):
            vals['matching_number'] = f"I{vals['matching_number']}"

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

        lines._check_tax_lock_date()

        if not self.env.context.get('tracking_disable'):
            # Log changes to move lines on each move
            tracked_fields = [fname for fname, f in self._fields.items() if hasattr(f, 'tracking') and f.tracking and not (hasattr(f, 'related') and f.related)]
            ref_fields = self.env['account.move.line'].fields_get(tracked_fields)
            empty_values = dict.fromkeys(tracked_fields)
            for move_id, modified_lines in lines.grouped('move_id').items():
                if not move_id.posted_before:
                    continue
                for line in modified_lines:
                    if tracking_value_ids := line._mail_track(ref_fields, empty_values)[1]:
                        line.move_id._message_log(
                            body=_("Journal Item %s created", line._get_html_link(title=f"#{line.id}")),
                            tracking_value_ids=tracking_value_ids
                        )

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

        inalterable_fields = set(self._get_integrity_hash_fields()).union({'inalterable_hash'})
        hashed_moves = self.move_id.filtered('inalterable_hash')
        violated_fields = set(vals) & inalterable_fields
        if hashed_moves and violated_fields:
            raise UserError(_(
                "You cannot edit the following fields: %(fields)s.\n"
                "The following entries are already hashed:\n%(entries)s",
                fields=format_list(self.env, [f['string'] for f in self.fields_get(violated_fields).values()]),
                entries='\n'.join(hashed_moves.mapped('name')),
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
                line.move_id._check_fiscal_lock_dates()

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
                            msg = _("Journal Item %s updated", line._get_html_link(title=f"#{line.id}"))
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
            raise UserError(_("You can't delete a posted journal item. Don’t play games with your accounting records; reset the journal entry to draft before deleting it."))

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

    @api.ondelete(at_uninstall=False)  # Hashed entres are legally required to not be deleted.
    def _except_hashed_entry_lines(self):
        """ Lines belonginig to a hashed (locked) entry should not be allowed to be deleted in order to protect the
        hash chain.
        """
        for line in self:
            if line.move_id.inalterable_hash:
                raise UserError(_('You cannot delete journal items belonging to a locked journal entry.'))

    def unlink(self):
        if not self:
            return True

        # Check the lines are not reconciled (partially or not).
        self._check_reconciliation()

        # Check the lock date. (Only relevant if the move is posted)
        self.move_id.filtered(lambda m: m.state == 'posted')._check_fiscal_lock_dates()

        # Check the tax lock date.
        self._check_tax_lock_date()

        if not self.env.context.get('tracking_disable'):
            # Log changes to move lines on each move
            tracked_fields = [fname for fname, f in self._fields.items() if hasattr(f, 'tracking') and f.tracking and not (hasattr(f, 'related') and f.related)]
            ref_fields = self.env['account.move.line'].fields_get(tracked_fields)
            empty_line = self.browse([False])  # all falsy fields but not failing `ensure_one` checks
            for move_id, modified_lines in self.grouped('move_id').items():
                if not move_id.posted_before:
                    continue
                for line in modified_lines:
                    if tracking_value_ids := empty_line._mail_track(ref_fields, line)[1]:
                        line.move_id._message_log(
                            body=_("Journal Item %s deleted", line._get_html_link(title=f"#{line.id}")),
                            tracking_value_ids=tracking_value_ids
                        )

        move_container = {'records': self.move_id}
        with self.move_id._check_balanced(move_container),\
             self.move_id._sync_dynamic_lines(move_container):
            res = super().unlink()

        return res

    @api.depends('move_id', 'ref', 'product_id')
    def _compute_display_name(self):
        for line in self:
            line.display_name = " ".join(
                element for element in (
                    line.move_id.name,
                    line.ref and f"({line.ref})",
                    line.name or line.product_id.display_name,
                ) if element
            )

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)

        for line, vals in zip(self, vals_list):
            # Don't copy the name of a payment term line.
            if line.display_type == 'payment_term' and line.move_id.is_invoice(True):
                del vals['name']
            # Don't copy restricted fields of notes
            if line.display_type in ('line_section', 'line_note'):
                del vals['balance']
                del vals['account_id']
            # Will be recomputed from the price_unit
            if line.display_type == 'product' and line.move_id.is_invoice(True):
                del vals['balance']
            if self._context.get('include_business_fields'):
                line._copy_data_extend_business_fields(vals)
        return vals_list

    def _field_to_sql(self, alias: str, fname: str, query: (Query | None) = None, flush: bool = True) -> SQL:
        if fname != 'payment_date':
            return super()._field_to_sql(alias, fname, query, flush)
        return SQL("""
            CASE
                 WHEN %(discount_date)s >= %(today)s THEN %(discount_date)s
                 ELSE %(date_maturity)s
            END""",
            today=fields.Date.context_today(self),
            discount_date=super()._field_to_sql(alias, "discount_date", query, flush),
            date_maturity=super()._field_to_sql(alias, "date_maturity", query, flush),
        )

    def _search_panel_domain_image(self, field_name, domain, set_count=False, limit=False):
        if field_name != 'account_root_id' or set_count:
            return super()._search_panel_domain_image(field_name, domain, set_count, limit)

        # if domain is logically equivalent to false
        if expression.is_false(self, domain):
            return {}

        # Override in order to not read the complete move line table and use the index instead
        query_account = self.env['account.account']._search([('company_ids', 'in', self.env.companies.ids), ('code', '!=', False)])
        account_code_alias = self.env['account.account']._field_to_sql('account_account', 'code', query_account)

        query_line = self._search(domain, limit=1)
        query_line.add_where('account_account.id = account_move_line.account_id')

        account_codes = self.env.execute_query(SQL(
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
        ))
        return {
            (root := self.env['account.root']._from_account_code(code)).id: {'id': root.id, 'display_name': root.display_name}
            for code, in account_codes
        }

    # -------------------------------------------------------------------------
    # RECONCILIATION
    # -------------------------------------------------------------------------

    def _get_reconciliation_aml_field_value(self, field, shadowed_aml_values):
        self.ensure_one()
        if shadowed_aml_values and field in shadowed_aml_values.get(self, {}):
            return shadowed_aml_values[self][field]
        else:
            return self[field]

    @api.model
    def _prepare_move_line_residual_amounts(self, aml_values, counterpart_currency, shadowed_aml_values=None, other_aml_values=None):
        """ Prepare the available residual amounts for each currency.
        :param aml_values: The values of account.move.line to consider.
        :param counterpart_currency: The currency of the opposite line this line will be reconciled with.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :param other_aml_values:    The other aml values to be reconciled with the current one.
        :return: A mapping currency -> dictionary containing:
            * residual: The residual amount left for this currency.
            * rate:     The rate applied regarding the company's currency.
        """

        def is_payment(aml):
            return aml.move_id.origin_payment_id or aml.move_id.statement_line_id

        def get_odoo_rate(aml, other_aml, currency):
            if forced_rate := self._context.get('forced_rate_from_register_payment'):
                return forced_rate
            if other_aml and not is_payment(aml) and is_payment(other_aml):
                return get_accounting_rate(other_aml, currency)
            if aml.move_id.is_invoice(include_receipts=True):
                exchange_rate_date = aml.move_id.invoice_date
            else:
                exchange_rate_date = aml._get_reconciliation_aml_field_value('date', shadowed_aml_values)
            return currency._get_conversion_rate(aml.company_currency_id, currency, aml.company_id, exchange_rate_date)

        def get_accounting_rate(aml, currency):
            if forced_rate := self._context.get('forced_rate_from_register_payment'):
                return forced_rate
            balance = aml._get_reconciliation_aml_field_value('balance', shadowed_aml_values)
            amount_currency = aml._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values)
            if not aml.company_currency_id.is_zero(balance) and not currency.is_zero(amount_currency):
                return abs(amount_currency / balance)

        aml = aml_values['aml']
        other_aml = (other_aml_values or {}).get('aml')
        remaining_amount_curr = aml_values['amount_residual_currency']
        remaining_amount = aml_values['amount_residual']
        company_currency = aml.company_currency_id
        currency = aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        account = aml._get_reconciliation_aml_field_value('account_id', shadowed_aml_values)
        has_zero_residual = company_currency.is_zero(remaining_amount)
        has_zero_residual_currency = currency.is_zero(remaining_amount_curr)
        is_rec_pay_account = account.account_type in ('asset_receivable', 'liability_payable')

        available_residual_per_currency = {}

        if not has_zero_residual:
            available_residual_per_currency[company_currency] = {
                'residual': remaining_amount,
                'rate': 1,
            }
        if currency != company_currency and not has_zero_residual_currency:
            available_residual_per_currency[currency] = {
                'residual': remaining_amount_curr,
                'rate': get_accounting_rate(aml, currency),
            }

        if currency == company_currency \
            and is_rec_pay_account \
            and not has_zero_residual \
            and counterpart_currency != company_currency:
            rate = get_odoo_rate(aml, other_aml, counterpart_currency)
            residual_in_foreign_curr = counterpart_currency.round(remaining_amount * rate)
            if not counterpart_currency.is_zero(residual_in_foreign_curr):
                available_residual_per_currency[counterpart_currency] = {
                    'residual': residual_in_foreign_curr,
                    'rate': rate,
                }
        elif currency == counterpart_currency \
            and currency != company_currency \
            and not has_zero_residual_currency:
            available_residual_per_currency[counterpart_currency] = {
                'residual': remaining_amount_curr,
                'rate': get_accounting_rate(aml, currency),
            }
        return available_residual_per_currency

    @api.model
    def _prepare_reconciliation_single_partial(self, debit_values, credit_values, shadowed_aml_values=None):
        """ Prepare the values to create an account.partial.reconcile later when reconciling the dictionaries passed
        as parameters, each one representing an account.move.line.
        :param debit_values:  The values of account.move.line to consider for a debit line.
        :param credit_values: The values of account.move.line to consider for a credit line.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :return: A dictionary:
            * debit_values:     None if the line has nothing left to reconcile.
            * credit_values:    None if the line has nothing left to reconcile.
            * partial_values:   The newly computed values for the partial.
            * exchange_values:  The values to create an exchange difference linked to this partial.
        """
        # ==== Determine the currency in which the reconciliation will be done ====
        # In this part, we retrieve the residual amounts, check if they are zero or not and determine in which
        # currency and at which rate the reconciliation will be done.
        res = {
            'debit_values': debit_values,
            'credit_values': credit_values,
        }
        debit_aml = debit_values['aml']
        credit_aml = credit_values['aml']
        debit_currency = debit_aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        credit_currency = credit_aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        company_currency = debit_aml.company_currency_id

        remaining_debit_amount_curr = debit_values['amount_residual_currency']
        remaining_credit_amount_curr = credit_values['amount_residual_currency']
        remaining_debit_amount = debit_values['amount_residual']
        remaining_credit_amount = credit_values['amount_residual']

        debit_available_residual_amounts = self._prepare_move_line_residual_amounts(
            debit_values,
            credit_currency,
            shadowed_aml_values=shadowed_aml_values,
            other_aml_values=credit_values,
        )
        credit_available_residual_amounts = self._prepare_move_line_residual_amounts(
            credit_values,
            debit_currency,
            shadowed_aml_values=shadowed_aml_values,
            other_aml_values=debit_values,
        )

        if debit_currency != company_currency \
            and debit_currency in debit_available_residual_amounts \
            and debit_currency in credit_available_residual_amounts:
            recon_currency = debit_currency
        elif credit_currency != company_currency \
            and credit_currency in debit_available_residual_amounts \
            and credit_currency in credit_available_residual_amounts:
            recon_currency = credit_currency
        else:
            recon_currency = company_currency

        debit_recon_values = debit_available_residual_amounts.get(recon_currency)
        credit_recon_values = credit_available_residual_amounts.get(recon_currency)

        # Check if there is something left to reconcile. Move to the next loop iteration if not.
        skip_reconciliation = False
        if not debit_recon_values:
            res['debit_values'] = None
            skip_reconciliation = True
        if not credit_recon_values:
            res['credit_values'] = None
            skip_reconciliation = True
        if skip_reconciliation:
            return res

        recon_debit_amount = debit_recon_values['residual']
        recon_credit_amount = -credit_recon_values['residual']

        # ==== Match both lines together and compute amounts to reconcile ====

        # Special case for exchange difference lines. In that case, both lines are sharing the same foreign
        # currency but at least one has no amount in foreign currency.
        # In that case, we don't want a rate for the opposite line because the exchange difference is supposed
        # to reduce only the amount in company currency but not the foreign one.
        exchange_line_mode = \
            recon_currency == company_currency \
            and debit_currency == credit_currency \
            and (
                not debit_available_residual_amounts.get(debit_currency)
                or not credit_available_residual_amounts.get(credit_currency)
            )

        # Determine which line is fully matched by the other.
        compare_amounts = recon_currency.compare_amounts(recon_debit_amount, recon_credit_amount)
        min_recon_amount = min(recon_debit_amount, recon_credit_amount)
        debit_fully_matched = compare_amounts <= 0
        credit_fully_matched = compare_amounts >= 0

        # ==== Computation of partial amounts ====
        if recon_currency == company_currency:
            if exchange_line_mode:
                debit_rate = None
                credit_rate = None
            else:
                debit_rate = debit_available_residual_amounts.get(debit_currency, {}).get('rate')
                credit_rate = credit_available_residual_amounts.get(credit_currency, {}).get('rate')

            # Compute the partial amount expressed in company currency.
            partial_amount = min_recon_amount

            # Compute the partial amount expressed in foreign currency.
            if debit_rate:
                partial_debit_amount_currency = debit_currency.round(debit_rate * min_recon_amount)
                partial_debit_amount_currency = min(partial_debit_amount_currency, remaining_debit_amount_curr)
            else:
                partial_debit_amount_currency = 0.0
            if credit_rate:
                partial_credit_amount_currency = credit_currency.round(credit_rate * min_recon_amount)
                partial_credit_amount_currency = min(partial_credit_amount_currency, -remaining_credit_amount_curr)
            else:
                partial_credit_amount_currency = 0.0

        else:
            # recon_currency != company_currency
            if exchange_line_mode:
                debit_rate = None
                credit_rate = None
            else:
                debit_rate = debit_recon_values['rate']
                credit_rate = credit_recon_values['rate']

            # Compute the partial amount expressed in foreign currency.
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
            if debit_currency == company_currency:
                partial_debit_amount_currency = partial_amount
            else:
                partial_debit_amount_currency = min_recon_amount
            if credit_currency == company_currency:
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
                    if not debit_currency.is_zero(debit_exchange_amount):
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual_currency': debit_exchange_amount})
                        remaining_debit_amount_curr -= debit_exchange_amount
                if credit_fully_matched:
                    credit_exchange_amount = remaining_credit_amount_curr + partial_credit_amount_currency
                    if not credit_currency.is_zero(credit_exchange_amount):
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual_currency': credit_exchange_amount})
                        remaining_credit_amount_curr += credit_exchange_amount

            else:
                if debit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    debit_exchange_amount = remaining_debit_amount - partial_amount
                    if not company_currency.is_zero(debit_exchange_amount):
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_currency == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    debit_exchange_amount = partial_debit_amount - partial_amount
                    if company_currency.compare_amounts(debit_exchange_amount, 0.0) > 0:
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_currency == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount

                if credit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    credit_exchange_amount = remaining_credit_amount + partial_amount
                    if not company_currency.is_zero(credit_exchange_amount):
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount -= credit_exchange_amount
                        if credit_currency == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    credit_exchange_amount = partial_amount - partial_credit_amount
                    if company_currency.compare_amounts(credit_exchange_amount, 0.0) < 0:
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount -= credit_exchange_amount
                        if credit_currency == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount

            if exchange_lines_to_fix:
                res['exchange_values'] = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    exchange_date=max(
                        debit_aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
                        credit_aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
                    ),
                )

        # ==== Create partials ====

        remaining_debit_amount -= partial_amount
        remaining_credit_amount += partial_amount
        remaining_debit_amount_curr -= partial_debit_amount_currency
        remaining_credit_amount_curr += partial_credit_amount_currency

        res['partial_values'] = {
            'amount': partial_amount,
            'debit_amount_currency': partial_debit_amount_currency,
            'credit_amount_currency': partial_credit_amount_currency,
            'debit_move_id': debit_aml.id,
            'credit_move_id': credit_aml.id,
        }

        debit_values['amount_residual'] = remaining_debit_amount
        debit_values['amount_residual_currency'] = remaining_debit_amount_curr
        credit_values['amount_residual'] = remaining_credit_amount
        credit_values['amount_residual_currency'] = remaining_credit_amount_curr

        if debit_fully_matched:
            res['debit_values'] = None
        if credit_fully_matched:
            res['credit_values'] = None
        return res

    @api.model
    def _prepare_reconciliation_amls(self, values_list, shadowed_aml_values=None):
        """ Prepare the partials on the current journal items to perform the reconciliation.
        Note: The order of records in self is important because the journal items will be reconciled using this order.

        :param values_list: A list of dictionaries, one for each aml.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :return: a tuple of
            1) list of vals for partial reconciliation creation,
            2) the list of vals for the exchange difference entries to be created
        """
        debit_values_list = iter([
            x
            for x in values_list
            if x['aml']._get_reconciliation_aml_field_value('balance', shadowed_aml_values) > 0.0
               or x['aml']._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values) > 0.0
        ])
        credit_values_list = iter([
            x
            for x in values_list
            if x['aml']._get_reconciliation_aml_field_value('balance', shadowed_aml_values) < 0.0
               or x['aml']._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values) < 0.0
        ])
        debit_values = None
        credit_values = None
        fully_reconciled_aml_ids = set()

        all_results = []
        while True:

            # ==== Find the next available lines ====
            # For performance reasons, the partials are created all at once meaning the residual amounts can't be
            # trusted from one iteration to another. That's the reason why all residual amounts are kept as variables
            # and reduced "manually" every time we append a dictionary to 'partials_values_list'.

            # Move to the next available debit line.
            if not debit_values:
                debit_values = next(debit_values_list, None)
                if not debit_values:
                    break

            # Move to the next available credit line.
            if not credit_values:
                credit_values = next(credit_values_list, None)
                if not credit_values:
                    break

            # ==== Compute the amounts to reconcile ====

            results = self._prepare_reconciliation_single_partial(
                debit_values,
                credit_values,
                shadowed_aml_values=shadowed_aml_values,
            )
            if results.get('partial_values'):
                all_results.append(results)
            if results['debit_values'] is None:
                fully_reconciled_aml_ids.add(debit_values['aml'].id)
                debit_values = None
            if results['credit_values'] is None:
                fully_reconciled_aml_ids.add(credit_values['aml'].id)
                credit_values = None

        return all_results, fully_reconciled_aml_ids

    @api.model
    def _prepare_reconciliation_plan(self, plan, amls_values_map, shadowed_aml_values=None):
        """ Perform virtually the reconciliation of the plan passed as parameter.

        :param plan: The plan to know which lines to reconcile in which order.
        :param amls_values_map: A mapping aml => amount_residual/amount_residual_currency
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :return: A list of all results returned by the '_prepare_reconciliation_amls' method.
        """
        all_fully_reconciled_aml_ids = set()
        all_results = []

        def process_amls(amls):
            remaining_amls = amls.filtered(lambda aml: aml.id not in all_fully_reconciled_aml_ids)
            amls_results, fully_reconciled_aml_ids = self._prepare_reconciliation_amls(
                [
                    amls_values_map[aml]
                    for aml in remaining_amls
                ],
                shadowed_aml_values=shadowed_aml_values,
            )
            all_fully_reconciled_aml_ids.update(fully_reconciled_aml_ids)
            for amls_result in amls_results:
                all_results.append(amls_result)

        def process_leaf(plan_node):
            # Sub plan to evaluate.
            for child_node in plan_node.get('nodes', []):
                process_leaf(child_node)

            # Group of amls to evaluate.
            process_amls(plan_node['amls'])

        process_leaf(plan)
        return all_results

    def _check_amls_exigibility_for_reconciliation(self, shadowed_aml_values=None):
        """ Ensure the current journal items are eligible to be reconciled together.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        """
        if not self:
            return

        if any(aml.reconciled for aml in self):
            raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
        if any(aml.parent_state != 'posted' for aml in self):
            raise UserError(_("You can only reconcile posted entries."))
        accounts = self.mapped(lambda x: x._get_reconciliation_aml_field_value('account_id', shadowed_aml_values))
        if len(accounts) > 1:
            raise UserError(_(
                "Entries are not from the same account: %s",
                ", ".join(accounts.mapped('display_name')),
            ))
        if len(self.company_id.root_id) > 1:
            raise UserError(_(
                "Entries don't belong to the same company: %s",
                ", ".join(self.company_id.mapped('display_name')),
            ))
        if not accounts.reconcile and accounts.account_type not in ('asset_cash', 'liability_credit_card'):
            raise UserError(_(
                "Account %s does not allow reconciliation. First change the configuration of this account "
                "to allow it.",
                accounts.display_name,
            ))

    @api.model
    def _optimize_reconciliation_plan(self, reconciliation_plan, shadowed_aml_values=None):
        """ Decode the initial reconciliation plan passed as parameter and converted it into a list of tree depicting
        the way the reconciliation should be done.
        Also, this method is responsible sorting the amls and splitting them by currency.
        Then, this method checks the parameter to ensure we are not going to perform any invalid reconciliation like
        a cross-account/cross-company partial.

        The split by currencies is made as follows.
        Suppose account.move.line(1, 2) are expressed in currency1 and account.move.line(3, 4) are expressed
        in currency2.
        If the reconciliation plan is [account.move.line(1, 2, 3, 4)], the optimizer will convert it into:
        [[account.move.line(1, 2), account.move.line(3, 4)]]

        :param reconciliation_plan: A list of reconciliation to perform.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :return: A list of dictionaries containing:
            * amls: A recordset.
            * aml_ids: The recordset ids.
            * nodes: A list of sub-nodes.
        """

        def process_amls(amls):
            if self._context.get('reduced_line_sorting'):
                sorted_amls = amls.sorted(key=lambda aml: (
                    aml._get_reconciliation_aml_field_value('date_maturity', shadowed_aml_values)
                        or aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
                    aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values),
                ))
            else:
                sorted_amls = amls.sorted(key=lambda aml: (
                    aml._get_reconciliation_aml_field_value('date_maturity', shadowed_aml_values)
                        or aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
                    aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values),
                    aml._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values),
                    aml._get_reconciliation_aml_field_value('balance', shadowed_aml_values),
                ))
            currencies = sorted_amls.mapped(lambda x: x._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values))
            results = {
                'amls': sorted_amls,
                'aml_ids': set(sorted_amls.ids),
            }

            if len(currencies) != 1:
                nodes = results['nodes'] = []
                for currency in currencies:
                    amls_in_currency = sorted_amls\
                        .filtered(lambda x: x._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values) == currency)
                    nodes.append({
                        'amls': amls_in_currency,
                        'aml_ids': set(amls_in_currency.ids),
                    })
            return results

        def process_children(children):
            node = {
                'nodes': [],
                'aml_ids': set(),
            }
            for child in children:
                results = process_leaf(child)
                if results:
                    node['nodes'].append(results)
                    node['aml_ids'].update(results['aml_ids'])
            node['amls'] = self.browse(node['aml_ids'])
            return node

        def process_leaf(item):
            if not item:
                return

            if isinstance(item, models.BaseModel):
                # Group of amls to evaluate.
                return process_amls(item)
            else:
                # Sub plan to evaluate.
                return process_children(item)

        plan_list = []
        all_aml_ids = set()
        for item in reconciliation_plan:
            plan_node = process_leaf(item)
            if not plan_node or not plan_node.get('amls'):
                continue

            # Check the amls to be reconciled all together.
            amls = plan_node['amls']
            amls._check_amls_exigibility_for_reconciliation(shadowed_aml_values=shadowed_aml_values)
            plan_list.append(plan_node)
            all_aml_ids.update(plan_node['aml_ids'])

        return plan_list, self.browse(all_aml_ids)

    def _reconcile_pre_hook(self):
        not_paid_invoices = self.move_id.filtered(lambda move:
            move.is_invoice(include_receipts=True)
            and move.payment_state not in ('paid', 'in_payment')
        )
        return {'not_paid_invoices': not_paid_invoices}

    def _reconcile_post_hook(self, data):
        data['not_paid_invoices']\
            .filtered(lambda move: move.payment_state in ('paid', 'in_payment'))\
            ._invoice_paid_hook()

    @api.model
    def _reconcile_plan(self, reconciliation_plan):
        """ Reconcile the amls following the reconciliation plan.
        The plan passed as parameter is a list of either a recordset of amls, either another plan.

        For example:
        [account.move.line(1, 2), account.move.line(3, 4)] means:
        - account.move.line(1, 2) will be reconciled first.
        - account.move.line(3, 4) will be reconciled after.

        [[account.move.line(1, 2), account.move.line(3, 4)]] means:
        - account.move.line(1, 2) will be reconciled first.
        - account.move.line(3, 4) will be reconciled after.
        - account.move.line(1, 2, 3, 4).filtered(lambda x: not x.reconciled) will be reconciled at the end.

        :param reconciliation_plan: A list of reconciliation to perform.
        """
        # ==== Prepare the reconciliation ====
        # Batch the amls all together to know what should be reconciled and when.
        plan_list, all_amls = self._optimize_reconciliation_plan(reconciliation_plan)
        move_container = {'records': all_amls.move_id}
        with all_amls.move_id._check_balanced(move_container),\
             all_amls.move_id._sync_dynamic_lines(move_container):
            self._reconcile_plan_with_sync(plan_list, all_amls)

    def _reconcile_plan_with_sync(self, plan_list, all_amls):
        # Parameter allowing to disable the exchange journal entries on partials.
        disable_partial_exchange_diff = bool(self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))

        # ==== Prefetch the fields all at once to speedup the reconciliation ====
        # All of those fields will be cached by the orm. Since the amls are split into multiple batches, the orm is not
        # able to prefetch the data for all of them at once. For that reason, we force the orm to populate the cache
        # before doing anything.
        all_amls.move_id
        all_amls.matched_debit_ids
        all_amls.matched_credit_ids

        # ==== Track the invoice's state to call the hook when they become paid ====
        pre_hook_data = all_amls._reconcile_pre_hook()

        # ==== Collect amls data ====
        # All residual amounts are collected and updated until the creation of partials in batch.
        # This is done that way to minimize the orm time for fields invalidation/mark as recompute and
        # recomputation.
        aml_values_map = {
            aml: {
                'aml': aml,
                'amount_residual': aml.amount_residual,
                'amount_residual_currency': aml.amount_residual_currency,
            }
            for aml in all_amls
        }

        # ==== Prepare the partials ====
        partials_values_list = []
        exchange_diff_values_list = []
        exchange_diff_partial_index = []
        all_plan_results = []
        partial_index = 0
        for plan in plan_list:
            plan_results = self\
                .with_context(no_exchange_difference=self._context.get('no_exchange_difference') or disable_partial_exchange_diff)\
                ._prepare_reconciliation_plan(plan, aml_values_map)
            all_plan_results.append(plan_results)
            for results in plan_results:
                partials_values_list.append(results['partial_values'])
                if results.get('exchange_values') and results['exchange_values']['move_values']['line_ids']:
                    exchange_diff_values_list.append(results['exchange_values'])
                    exchange_diff_partial_index.append(partial_index)
                    partial_index += 1

        # ==== Create the partials ====
        # Link the newly created partials to the plan. There are needed later for caba exchange entries.
        partials = self.env['account.partial.reconcile'].create(partials_values_list)
        start_range = 0
        for plan_results, plan in zip(all_plan_results, plan_list):
            size = len(plan_results)
            plan['partials'] = partials[start_range:start_range + size]
            start_range += size

        # ==== Create the partial exchange journal entries ====
        exchange_moves = self._create_exchange_difference_moves(exchange_diff_values_list)
        for index, exchange_move in zip(exchange_diff_partial_index, exchange_moves):
            partials[index].exchange_move_id = exchange_move

        # ==== Create entries for cash basis taxes ====
        def is_cash_basis_needed(amls):
            return any(amls.company_id.mapped('tax_exigibility')) \
                and amls.account_id.account_type in ('asset_receivable', 'liability_payable')

        if not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
            for plan in plan_list:
                if is_cash_basis_needed(plan['amls']):
                    plan['partials']._create_tax_cash_basis_moves()

        # ==== Prepare full reconcile creation ====
        # First, we need to find all sub-set of amls that are candidates for a full.

        def is_line_reconciled(aml, has_multiple_currencies):
            # Check if the journal item passed as parameter is now fully reconciled.
            if aml.reconciled:
                return True
            if not aml.matched_debit_ids and not aml.matched_credit_ids:
                # Suppose a journal item having balance = 0 but an amount_currency like an exchange difference.
                return False
            if has_multiple_currencies:
                return aml.company_currency_id.is_zero(aml.amount_residual)
            else:
                return aml.currency_id.is_zero(aml.amount_residual_currency)

        full_batches = []
        all_aml_ids = set()
        number2lines = all_amls._reconciled_by_number()
        for plan in plan_list:
            for aml in plan['amls']:
                if 'full_batch_index' in aml_values_map[aml]:
                    continue

                involved_amls = plan['amls']._filter_reconciled_by_number(number2lines)
                all_aml_ids.update(involved_amls.ids)
                full_batch_index = len(full_batches)
                has_multiple_currencies = len(involved_amls.currency_id) > 1
                is_fully_reconciled = all(
                    is_line_reconciled(involved_aml, has_multiple_currencies)
                    for involved_aml in involved_amls
                )
                full_batches.append({
                    'amls': involved_amls,
                    'is_fully_reconciled': is_fully_reconciled,
                })
                for involved_aml in involved_amls:
                    if aml_values_map.get(involved_aml):
                        aml_values_map[involved_aml]['full_batch_index'] = full_batch_index

        # ==== Prefetch the fields all at once to speedup the reconciliation ====
        # Again, we do the same optimization for the prefetching. We need to do it again since most of the values have
        # been invalidated with the creation of the account.partial.reconcile records.
        all_amls = self.browse(list(all_aml_ids))
        all_amls.move_id
        all_amls.matched_debit_ids
        all_amls.matched_credit_ids

        # ==== Prepare the full exchange journal entries ====
        # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
        # when importing a full accounting including the reconciliation like Winbooks.

        exchange_diff_values_list = []
        exchange_diff_full_batch_index = []
        if not self._context.get('no_exchange_difference'):
            for full_batch_index, full_batch in enumerate(full_batches):
                involved_amls = full_batch['amls']
                if not full_batch['is_fully_reconciled']:
                    continue

                # In normal cases, the exchange differences are already generated by the partial at this point meaning
                # there is no journal item left with a zero amount residual in one currency but not in the other.
                # However, after a migration coming from an older version with an older partial reconciliation or due to
                # some rounding issues (when dealing with different decimal places for example), we could need an extra
                # exchange difference journal entry to handle them.
                exchange_lines_to_fix = self.env['account.move.line']
                amounts_list = []
                exchange_max_date = date.min
                for aml in involved_amls:
                    if not aml.company_currency_id.is_zero(aml.amount_residual):
                        exchange_lines_to_fix += aml
                        amounts_list.append({'amount_residual': aml.amount_residual})
                    elif not aml.currency_id.is_zero(aml.amount_residual_currency):
                        exchange_lines_to_fix += aml
                        amounts_list.append({'amount_residual_currency': aml.amount_residual_currency})
                    exchange_max_date = max(exchange_max_date, aml.date)
                exchange_diff_values = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    company=involved_amls.company_id,
                    exchange_date=exchange_max_date,
                )

                # Exchange difference for cash basis entries.
                # If we are fully reversing the entry, no need to fix anything since the journal entry
                # is exactly the mirror of the source journal entry.
                caba_lines_to_reconcile = None
                if is_cash_basis_needed(involved_amls) and not self._context.get('move_reverse_cancel'):
                    caba_lines_to_reconcile = involved_amls._add_exchange_difference_cash_basis_vals(exchange_diff_values)

                # Prepare the exchange difference.
                if exchange_diff_values['move_values']['line_ids']:
                    exchange_diff_full_batch_index.append(full_batch_index)
                    exchange_diff_values_list.append(exchange_diff_values)
                    full_batch['caba_lines_to_reconcile'] = caba_lines_to_reconcile

        # ==== Create the full exchange journal entries ====
        exchange_moves = self._create_exchange_difference_moves(exchange_diff_values_list)
        for full_batch_index, exchange_move in zip(exchange_diff_full_batch_index, exchange_moves):
            full_batch = full_batches[full_batch_index]
            amls = full_batch['amls']
            full_batch['exchange_move'] = exchange_move
            exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == amls.account_id)
            full_batch['amls'] |= exchange_move_lines

        # ==== Create the full reconcile ====
        # Note we are using Command.link and not Command.set because Command.set is triggering an unlink that is
        # slowing down the assignation of the co-fields. Indeed, unlink is forcing a flush.
        full_reconcile_values_list = []
        full_reconcile_full_batch_index = []
        for full_batch_index, full_batch in enumerate(full_batches):
            amls = full_batch['amls']
            involved_partials = amls.matched_debit_ids + amls.matched_credit_ids
            if full_batch['is_fully_reconciled']:
                full_reconcile_values_list.append({
                    'exchange_move_id': full_batch.get('exchange_move') and full_batch['exchange_move'].id,
                    'partial_reconcile_ids': [Command.link(partial.id) for partial in involved_partials],
                    'reconciled_line_ids': [Command.link(aml.id) for aml in amls],
                })
                full_reconcile_full_batch_index.append(full_batch_index)

        self.env['account.full.reconcile'].create(full_reconcile_values_list)

        # === Cash basis rounding autoreconciliation ===
        # In case a cash basis rounding difference line got created for the transition account, we reconcile it with the corresponding lines
        # on the cash basis moves (so that it reaches full reconciliation and creates an exchange difference entry for this account as well)
        for full_batch in full_batches:
            if not full_batch.get('caba_lines_to_reconcile'):
                continue

            caba_lines_to_reconcile = full_batch['caba_lines_to_reconcile']
            exchange_move = full_batch['exchange_move']
            for (dummy, account, repartition_line), amls_to_reconcile in caba_lines_to_reconcile.items():
                if not account.reconcile:
                    continue

                exchange_line = exchange_move.line_ids.filtered(
                    lambda l: l.account_id == account and l.tax_repartition_line_id == repartition_line
                )

                (exchange_line + amls_to_reconcile)\
                    .filtered(lambda l: not l.reconciled)\
                    .reconcile()

        all_amls._reconcile_post_hook(pre_hook_data)

    def _create_reconciliation_partials(self):
        '''create the partial reconciliation between all the records in self
         :return: A recordset of account.partial.reconcile.
        '''
        partials_vals_list, exchange_data = self._prepare_reconciliation_partials([
            {
                'aml': line,
                'amount_residual': line.amount_residual,
                'amount_residual_currency': line.amount_residual_currency,
            }
            for line in self
        ])
        partials = self.env['account.partial.reconcile'].create(partials_vals_list)

        # ==== Create exchange difference moves ====
        for index, exchange_values in exchange_data.items():
            partials[index].exchange_move_id = self._create_exchange_difference_move(exchange_values)

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
        company = (
            (self.move_id.filtered(lambda m: m.is_invoice(True)) or self.move_id).company_id
            or company
        )[:1]
        if not company:
            return

        journal = company.currency_exchange_journal_id
        expense_exchange_account = company.expense_currency_exchange_account_id
        income_exchange_account = company.income_currency_exchange_account_id
        accounting_exchange_date = journal.with_context(move_date=exchange_date).accounting_date if journal else date.min

        move_vals = {
            'move_type': 'entry',
            'name': '/', # do not trigger the compute name before posting as it will most likely be posted immediately after
            'date': accounting_exchange_date,
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
                    'full_reconcile_id': line.full_reconcile_id.id,
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

        return {'move_values': move_vals, 'to_reconcile': to_reconcile}

    @api.model
    def _create_exchange_difference_moves(self, exchange_diff_values_list):
        """ Create the exchange difference journal entry on the current journal items.

        :param exchange_diff_values_list:   A list of values to create and reconcile the exchange differences
                                            See the '_prepare_exchange_difference_move_vals' method.
        :return: An account.move recordset.
        """
        exchange_move_values_list = []
        journal_ids = set()
        for exchange_diff_values in exchange_diff_values_list:
            move_vals = exchange_diff_values['move_values']
            exchange_move_values_list.append(move_vals)

            if not move_vals['journal_id']:
                raise UserError(_(
                    "You have to configure the 'Exchange Gain or Loss Journal' in your company settings, to manage"
                    " automatically the booking of accounting entries related to differences between exchange rates."
                ))

            journal_ids.add(move_vals['journal_id'])

        if not exchange_move_values_list:
            return self.env['account.move']

        # ==== Check the config ====
        journals = self.env['account.journal'].browse(list(journal_ids))
        for journal in journals:
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

        # ==== Create the move ====
        exchange_moves = self.env['account.move'].create(exchange_move_values_list)
        exchange_moves._post(soft=False)

        # ==== Reconcile ====
        reconciliation_plan = []
        for exchange_move, exchange_diff_values in zip(exchange_moves, exchange_diff_values_list):
            for source_line, sequence in exchange_diff_values['to_reconcile']:
                exchange_diff_line = exchange_move.line_ids[sequence]
                reconciliation_plan.append((source_line + exchange_diff_line))

        self\
            .with_context(no_exchange_difference=True)\
            ._reconcile_plan(reconciliation_plan)

        return exchange_moves

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
        move_vals = exchange_diff_vals['move_values']
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
        """ Reconcile the current move lines all together. """
        return self._reconcile_plan([self])

    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        (self.matched_debit_ids + self.matched_credit_ids).unlink()

    def action_unreconcile_match_entries(self):
        """ This method will do the unreconcile action in the list view of the moves """
        active_ids = self._context.get('active_ids')
        if active_ids:
            move_lines = self.env['account.move.line'].browse(active_ids)._all_reconciled_lines()
            move_lines.remove_move_reconcile()

    def _reconcile_marked(self):
        """Process the pending reconciliation of entries marked (i.e. uring imports).

        The entries can be marked using the string `I*` as matching number where `*` can be anything.
        Once all the entries using identical numbers are posted, this function proceeds to do the real matching.
        """
        temp_numbers = list({
            line.matching_number
            for line in self
            if line.matching_number and line.matching_number.startswith('I')
        })
        if temp_numbers:
            for _matching_number, account, lines in self._read_group(
                domain=[('matching_number', 'in', temp_numbers)],
                groupby=['matching_number', 'account_id'],
                aggregates=['id:recordset'],
            ):
                if all(move.state == 'posted' for move in lines.move_id):
                    if not account.reconcile:
                        _logger.info("%s has reconciled lines, changing the config", account.display_name)
                        account.reconcile = True
                    lines.with_context(no_exchange_difference=True, no_cash_basis=True).reconcile()

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
            for account_ids, distribution in self.analytic_distribution.items():
                line_values = self._prepare_analytic_distribution_line(float(distribution), account_ids, distribution_on_each_plan)
                if not self.currency_id.is_zero(line_values.get('amount')):
                    analytic_line_vals.append(line_values)
        return analytic_line_vals

    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_field_values = {}
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        amount = 0
        for account in self.env['account.analytic.account'].browse(map(int, account_ids.split(","))).exists():
            distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
                amount = -self.balance * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
            else:
                amount = -self.balance * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            **account_field_values,
            'partner_id': self.partner_id.id,
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_line_id': self.id,
            'user_id': self.move_id.invoice_user_id.id or self._uid,
            'company_id': self.company_id.id or self.env.company.id,
            'category': 'invoice' if self.move_id.is_sale_document() else 'vendor_bill' if self.move_id.is_purchase_document() else 'other',
        }

    # -------------------------------------------------------------------------
    # INSTALLMENTS
    # -------------------------------------------------------------------------

    def _get_installments_data(self, payment_currency=None, payment_date=None, next_payment_date=None):
        move = self.move_id
        move.ensure_one()

        payment_date = payment_date or fields.Date.context_today(self)

        term_lines = self.sorted(key=lambda line: (line.date_maturity, line.date))
        sign = move.direction_sign
        installments = []
        first_installment_mode = False
        current_installment_mode = False
        for i, line in enumerate(term_lines, start=1):
            installment = {
                'number': i,
                'line': line,
                'date_maturity': line.date_maturity or line.date,
                'amount_residual_currency': line.amount_residual_currency,
                'amount_residual': line.amount_residual,
                'amount_residual_currency_unsigned': -sign * line.amount_residual_currency,
                'amount_residual_unsigned': -sign * line.amount_residual,
                'type': 'other',
                'reconciled': line.reconciled,
            }
            installments.append(installment)

            # Already reconciled.
            if line.reconciled:
                continue

            # Early payment discount.
            # In that case, we want to report the difference of the epd and display it on the UI.
            if move._is_eligible_for_early_payment_discount(payment_currency or line.currency_id, payment_date):
                installment.update({
                    'amount_residual_currency': line.discount_amount_currency,
                    'amount_residual': line.discount_balance,
                    'amount_residual_currency_unsigned': -sign * line.discount_amount_currency,
                    'amount_residual_unsigned': -sign * line.discount_balance,
                    'discount_amount_currency': line.amount_currency - line.discount_amount_currency,
                    'discount_amount': line.balance - line.discount_balance,
                    'type': 'early_payment_discount',
                })
                continue

            # Installments.
            # In case of overdue, all of them are sum as a default amount to be paid.
            # The next installment is added for the difference.
            if line.display_type == 'payment_term':
                if next_payment_date and (line.date_maturity or line.date) <= next_payment_date:
                    current_installment_mode = 'before_date'
                elif (line.date_maturity or line.date) < payment_date:
                    # Collect all overdue installments.
                    first_installment_mode = current_installment_mode = 'overdue'
                elif not first_installment_mode:
                    # Suggest the next installment in case of no overdue.
                    first_installment_mode = 'next'
                    current_installment_mode = 'next'
                elif current_installment_mode == 'overdue':
                    # After an overdue, just add the next installment for the difference.
                    current_installment_mode = 'next'
                installment['type'] = current_installment_mode

        return installments

    # -------------------------------------------------------------------------
    # MISC
    # -------------------------------------------------------------------------

    def _get_integrity_hash_fields(self):
        # Use the new hash version by default, but keep the old one for backward compatibility when generating the integrity report.
        hash_version = self._context.get('hash_version', MAX_HASH_VERSION)
        if hash_version == 1:
            return ['debit', 'credit', 'account_id', 'partner_id']
        elif hash_version in (2, 3, 4):
            return ['name', 'debit', 'credit', 'account_id', 'partner_id']
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

    def _reconciled_lines(self):
        ids = []
        for aml in self.filtered('reconciled'):
            ids.extend([r.debit_move_id.id for r in aml.matched_debit_ids] if aml.credit > 0 else [r.credit_move_id.id for r in aml.matched_credit_ids])
            ids.append(aml.id)
        return ids

    def _reconciled_by_number(self) -> dict:
        """Get the mapping of all the lines matched with the lines in self grouped by matching number."""
        matching_numbers = [n for n in set(self.mapped('matching_number')) if n]
        if matching_numbers:
            return dict(self._read_group(
                domain=[('matching_number', 'in', matching_numbers)],
                groupby=['matching_number'],
                aggregates=['id:recordset'],
            ))
        return {}

    def _filter_reconciled_by_number(self, mapping: dict):
        """Get all the the lines matched with the lines in self.

        Uses a mapping built with `_reconciled_by_number` to avoid multiple calls to the database.
        """
        matching_numbers = [n for n in set(self.mapped('matching_number')) if n]
        return self | self.browse([_id for number in matching_numbers for _id in mapping[number].ids])

    def _all_reconciled_lines(self):
        """Get all the the lines matched with the lines in self."""
        return self._filter_reconciled_by_number(self._reconciled_by_number())

    def _get_attachment_domains(self):
        self.ensure_one()
        domains = [[
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.move_id.id),
            ('res_field', 'in', (False, 'invoice_pdf_report_file')),
        ]]
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

    def _prepare_edi_vals_to_export(self):
        ''' The purpose of this helper is the same as '_prepare_edi_vals_to_export' but for a single invoice line.
        This includes the computation of the tax details for each invoice line or the management of the discount.
        Indeed, in some EDI, we need to provide extra values depending the discount such as:
        - the discount as an amount instead of a percentage.
        - the price_unit but after subtraction of the discount.

        :return: A python dict containing default pre-processed values.
        '''
        self.ensure_one()

        if self.discount == 100.0:
            gross_price_subtotal = self.currency_id.round(self.price_unit * self.quantity)
        else:
            gross_price_subtotal = self.currency_id.round(self.price_subtotal / (1 - self.discount / 100.0))

        res = {
            'line': self,
            'price_unit_after_discount': self.currency_id.round(self.price_unit * (1 - (self.discount / 100.0))),
            'price_subtotal_before_discount': gross_price_subtotal,
            'price_subtotal_unit': self.currency_id.round(self.price_subtotal / self.quantity) if self.quantity else 0.0,
            'price_total_unit': self.currency_id.round(self.price_total / self.quantity) if self.quantity else 0.0,
            'price_discount': gross_price_subtotal - self.price_subtotal,
            'price_discount_unit': (gross_price_subtotal - self.price_subtotal) / self.quantity if self.quantity else 0.0,
            'gross_price_total_unit': self.currency_id.round(gross_price_subtotal / self.quantity) if self.quantity else 0.0,
            'unece_uom_code': self.product_id.product_tmpl_id.uom_id._get_unece_code(),
        }
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # Hide total amount_currency from read_group when view is not grouped by currency_id. Avoids mix of currencies
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'currency_id' not in groupby and 'amount_currency:sum' in fields:
            for group_line in res:
                group_line['amount_currency'] = False
        return res

    def _get_journal_items_full_name(self, name, display_name):
        return name if not display_name or display_name in name else f"{display_name} {name}"

    def _check_edi_line_tax_required(self):
        return self.product_id.type != 'combo'

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

    def action_automatic_entry(self, default_action=None):
        action = self.env['ir.actions.act_window']._for_xml_id('account.account_automatic_entry_wizard_action')
        # Force the values of the move line in the context to avoid issues
        ctx = dict(self.env.context)
        ctx.pop('active_id', None)
        ctx.pop('default_journal_id', None)
        ctx['active_ids'] = self.ids
        ctx['active_model'] = 'account.move.line'
        if default_action:
            ctx['default_action'] = default_action
        action['context'] = ctx
        return action

    def action_add_from_catalog(self):
        """ Will open the catalog view """
        move = self.env['account.move'].browse(self.env.context.get('order_id'))
        return move.action_add_from_catalog()

    # -------------------------------------------------------------------------
    # Catalog
    # -------------------------------------------------------------------------
    def _get_product_catalog_lines_data(self, **kwargs):
        """
        Return information about account_move_line in `self`.
        If `self` is empty, this method returns only the default value(s) needed for the product
        catalog. In this case, the quantity that equals 0.
        Otherwise, it returns a quantity and a price based on the product of the move line(s) and whether
        the product is read-only or not.
        A product is considered read-only if the order is considered read-only or if `self` contains multiple records.
        Note: This method cannot be called with multiple records that have different products linked.

        :param products: Recordset of `product.product`.
        :param dict kwargs: additional values given for inherited models.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'quantity': float,
                'price': float,
                'readOnly': bool,
                'min_qty': int, (optional)
            }
        """
        if self:
            self.product_id.ensure_one()
            return {
                **self[0].move_id._get_product_price_and_data(self[0].product_id),
                'quantity': sum(
                    self.mapped(
                        lambda line: line.product_uom_id._compute_quantity(
                            qty=line.quantity,
                            to_unit=line.product_id.uom_id,
                        )
                    )
                ),
                'readOnly': self.move_id._is_readonly() or len(self) > 1,
            }
        return {
            'quantity': 0,
        }
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
