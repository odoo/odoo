import logging
import re
from urllib.parse import urlencode

from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    clean_context,
    email_normalize,
    float_repr,
    float_round,
    format_date,
    is_html_empty,
    parse_version,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

EXPENSE_REVIEW_STATE = [
    ("submitted", "Submitted"),
    ("approved", "Approved"),
    ("refused", "Refused"),
]


class HrExpense(models.Model):
    _name = "hr.expense"
    _inherit = [
        "mixin.mail.thread.main.attachment",
        "mixin.mail.activity",
        "mixin.analytic",
        "mixin.approval.state.sync",
    ]
    _description = "Expense"
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Description",
        compute="_compute_name",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
        required=True,
    )
    date = fields.Date(
        string="Expense Date",
        default=fields.Date.context_today,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        compute="_compute_employee_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        domain=[("filter_for_expense", "=", True)],
        check_company=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_from_employee_id",
        store=True,
        copy=False,
    )
    manager_id = fields.Many2one(
        comodel_name="res.users",
        compute="_compute_from_employee_id",
        store=True,
        copy=False,
        domain=lambda self: [
            ("share", "=", False),
            "|",
            ("employee_id.expense_manager_id", "in", self.env.user.id),
            (
                "all_group_ids",
                "in",
                self.env.ref("hr_expense.group_hr_expense_team_approver").ids,
            ),
        ],
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Category",
        domain=[("can_be_expensed", "=", True)],
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    product_description = fields.Html(compute="_compute_product_description")
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_uom_id",
        precompute=True,
        store=True,
        copy=True,
    )
    product_has_cost = fields.Boolean(compute="_compute_from_product")
    product_has_tax = fields.Boolean(
        string="Whether tax is defined on a selected product",
        compute="_compute_from_product",
    )
    quantity = fields.Float(
        digits="Product Unit",
        default=1,
        required=True,
    )
    description = fields.Text(string="Internal Notes")
    message_main_attachment_checksum = fields.Char(
        related="message_main_attachment_id.checksum"
    )
    nb_attachment = fields.Integer(
        string="Number of Attachments",
        compute="_compute_nb_attachment",
    )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Attachments",
        domain=[("res_model", "=", "hr.expense")],
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("posted", "Posted"),
            ("in_payment", "In Payment"),
            ("paid", "Paid"),
            ("refused", "Refused"),
        ],
        string="Status",
        compute="_compute_state",
        default="draft",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        tracking=True,
    )
    review_state = fields.Selection(
        selection=EXPENSE_REVIEW_STATE,
        string="Review Status",
        copy=False,
        readonly=True,
    )
    approval_date = fields.Datetime(readonly=True)
    duplicate_expense_ids = fields.Many2many(
        comodel_name="hr.expense",
        compute="_compute_duplicate_expense_ids",
    )
    same_receipt_expense_ids = fields.Many2many(
        comodel_name="hr.expense",
        compute="_compute_same_receipt_expense_ids",
    )

    split_expense_origin_id = fields.Many2one(
        comodel_name="hr.expense",
        string="Origin Split Expense",
        help="Original expense from a split.",
    )
    tax_amount_currency = fields.Monetary(
        string="Tax amount in Currency",
        currency_field="currency_id",
        compute="_compute_tax_amount_currency",
        precompute=True,
        store=True,
        help="Tax amount in currency",
    )
    tax_amount = fields.Monetary(
        string="Tax amount",
        currency_field="company_currency_id",
        compute="_compute_tax_amount",
        precompute=True,
        store=True,
        help="Tax amount in company currency",
    )
    total_amount_currency = fields.Monetary(
        string="Total In Currency",
        currency_field="currency_id",
        compute="_compute_total_amount_currency",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
    )
    total_amount = fields.Monetary(
        string="Total",
        currency_field="company_currency_id",
        compute="_compute_total_amount",
        inverse="_inverse_total_amount",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
    )
    untaxed_amount_currency = fields.Monetary(
        string="Total Untaxed Amount In Currency",
        currency_field="currency_id",
        compute="_compute_tax_amount_currency",
        precompute=True,
        store=True,
    )
    untaxed_amount = fields.Monetary(
        string="Total Untaxed Amount",
        currency_field="currency_id",
        compute="_compute_tax_amount",
        precompute=True,
        store=True,
    )
    amount_residual = fields.Monetary(
        related="account_move_id.amount_residual",
        string="Amount Due",
        currency_field="company_currency_id",
        readonly=True,
    )
    price_unit = fields.Float(
        string="Unit Price",
        min_display_digits="Product Price",
        compute="_compute_price_unit",
        precompute=True,
        store=True,
        copy=True,
        readonly=True,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        precompute=True,
        default=lambda self: self.env.company.currency_id,
        store=True,
        readonly=False,
        required=True,
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Report Company Currency",
        readonly=True,
    )
    is_multiple_currency = fields.Boolean(
        string="Is currency_id different from the company_currency_id",
        compute="_compute_is_multiple_currency",
    )
    currency_rate = fields.Float(
        digits=(16, 9),
        compute="_compute_currency_rate",
        readonly=True,
        tracking=True,
    )
    label_currency_rate = fields.Char(
        compute="_compute_currency_rate",
        readonly=True,
    )

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="payment_channel_id.journal_id",
        readonly=True,
    )
    selectable_payment_channel_ids = fields.Many2many(
        comodel_name="account.payment.channel",
        compute="_compute_selectable_payment_channel_ids",
        compute_sudo=True,
    )
    payment_channel_id = fields.Many2one(
        comodel_name="account.payment.channel",
        string="Payment Method",
        compute="_compute_payment_channel_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', selectable_payment_channel_ids)]",
        help="The payment method used when the expense is paid by the company.",
    )
    account_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        index="btree_not_null",
        copy=False,
        readonly=True,
    )
    payment_mode = fields.Selection(
        selection=[
            ("own_account", "Employee (to reimburse)"),
            ("company_account", "Company"),
        ],
        string="Paid By",
        default="own_account",
        required=True,
        tracking=True,
    )
    vendor_id = fields.Many2one(comodel_name="res.partner")
    account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_account_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card'))]",
        check_company=True,
        help="An expense account is expected",
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="expense_tax",
        column1="expense_id",
        column2="tax_id",
        string="Included taxes",
        compute="_compute_tax_ids",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('type_tax_use', '=', 'purchase')]",
        check_company=True,
        help="Both price-included and price-excluded taxes will behave as price-included taxes for expenses.",
    )

    is_editable = fields.Boolean(
        string="Is Editable By Current User",
        compute="_compute_is_editable",
        readonly=True,
    )
    can_reset = fields.Boolean(
        compute="_compute_can_reset",
        readonly=True,
    )
    can_approve = fields.Boolean(
        compute="_compute_can_approve",
        readonly=True,
    )

    former_sheet_id = fields.Integer(string="Former Report")

    @api.constrains("state", "review_state", "total_amount", "total_amount_currency")
    def _check_non_zero(self):
        for expense in self:
            total_amount_is_zero = expense.company_currency_id.is_zero(
                expense.total_amount
            )
            total_amount_currency_is_zero = expense.currency_id.is_zero(
                expense.total_amount_currency
            )
            if (expense.state != "draft" or expense.review_state) and (
                total_amount_is_zero or total_amount_currency_is_zero
            ):
                _debug.logic(
                    "non_zero_refused",
                    expense=expense,
                    state=expense.state,
                    review_state=expense.review_state or "none",
                    company_zero=total_amount_is_zero,
                    currency_zero=total_amount_currency_is_zero,
                )
                raise ValidationError(_("Only draft expenses can have a total of 0."))

    @api.constrains("account_move_id")
    def _check_o2o_payment(self):
        for expense in self:
            if len(expense.account_move_id.origin_payment_id.expense_ids) > 1:
                _debug.logic(
                    "o2o_payment_refused",
                    expense=expense,
                    payment=expense.account_move_id.origin_payment_id,
                    sharing=expense.account_move_id.origin_payment_id.expense_ids,
                )
                raise ValidationError(
                    _("Only one expense can be linked to a particular payment")
                )

    @api.depends("product_has_cost")
    def _compute_currency_id(self):
        for expense in self:
            if expense.product_has_cost and expense.state == "draft":
                expense.currency_id = expense.company_currency_id

    @api.depends_context("uid")
    @api.depends("employee_id", "manager_id", "state")
    def _compute_is_editable(self):
        is_hr_admin = (
            self.env.user.has_group("hr_expense.group_hr_expense_manager")
            or self.env.su
        )
        is_team_approver = self.env.user.has_group(
            "hr_expense.group_hr_expense_team_approver"
        )
        is_all_approver = self.env.user.has_group("hr_expense.group_hr_expense_user")

        expenses_employee_ids_under_user_ones = set()
        if is_team_approver:
            expenses_employee_ids_under_user_ones = set(
                self.env["hr.employee"]
                .sudo()
                .search(
                    [
                        ("id", "in", self.employee_id.ids),
                        ("id", "child_of", self.env.user.employee_ids.ids),
                        ("id", "not in", self.env.user.employee_ids.ids),
                    ]
                )
                .ids
            )
        for expense in self:
            if not expense.company_id:
                continue
            if (
                expense.state not in {"draft", "submitted", "approved"}
                and not self.env.su
            ):
                expense.is_editable = False
                continue

            if is_hr_admin:
                expense.is_editable = True
                continue

            employee = expense.employee_id
            is_own_expense = employee.user_id == self.env.user
            if is_own_expense and expense.state == "draft":
                expense.is_editable = True
                continue

            managers = (
                expense.manager_id
                | employee.expense_manager_id
                | employee.sudo().department_id.manager_id.user_id.sudo(self.env.su)
            )
            if is_all_approver:
                managers |= self.env.user
            if expense.employee_id.id in expenses_employee_ids_under_user_ones:
                managers |= self.env.user
            if not is_own_expense and self.env.user in managers:
                expense.is_editable = True
                continue
            expense.is_editable = False

    @api.onchange("product_has_cost")
    def _onchange_product_has_cost(self):
        if not self.product_has_cost and self.state == "draft":
            self.quantity = 1

    @api.depends_context("lang")
    @api.depends("product_id")
    def _compute_product_description(self):
        for expense in self:
            expense.product_description = (
                not is_html_empty(expense.product_id.description)
                and expense.product_id.description
            )

    @api.depends("product_id")
    def _compute_name(self):
        for expense in self:
            expense.name = expense.name or expense.product_id.display_name

    def _set_expense_currency_rate(self, date_today):
        _debug.perf.count("currency_rate_fetch", expenses=self)
        for expense in self:
            company_currency = (
                expense.company_currency_id or self.env.company.currency_id
            )
            expense.currency_rate = expense.env["res.currency"]._get_conversion_rate(
                from_currency=expense.currency_id or company_currency,
                to_currency=company_currency,
                company=expense.company_id,
                date=expense.date or date_today,
            )

    @api.depends("currency_id", "total_amount_currency", "date")
    def _compute_currency_rate(self):
        date_today = fields.Date.context_today(self)
        for expense in self:
            if expense.is_multiple_currency:
                if (
                    expense.currency_id != expense._origin.currency_id
                    or expense.total_amount_currency
                    != expense._origin.total_amount_currency
                    or expense.date != expense._origin.date
                ):
                    expense._set_expense_currency_rate(date_today=date_today)
                else:
                    expense.currency_rate = (
                        expense.total_amount / expense.total_amount_currency
                        if expense.total_amount_currency
                        else 1.0
                    )
            else:
                expense.currency_rate = 1.0
                expense.label_currency_rate = False
                continue

            company_currency = (
                expense.company_currency_id or expense.env.company.currency_id
            )
            expense.label_currency_rate = _(
                "1 %(exp_cur)s = %(rate)s %(comp_cur)s",
                exp_cur=(expense.currency_id or company_currency).name,
                rate=float_repr(expense.currency_rate, 6),
                comp_cur=company_currency.name,
            )

    @api.depends("currency_id", "company_currency_id")
    def _compute_is_multiple_currency(self):
        for expense in self:
            expense_currency = (
                expense.currency_id
                or expense.company_currency_id
                or expense.env.company.currency_id
            )
            expense_company_currency = (
                expense.company_currency_id or expense.env.company.currency_id
            )
            expense.is_multiple_currency = expense_currency != expense_company_currency

    @api.depends("product_id")
    def _compute_from_product(self):
        for expense in self:
            expense.product_has_cost = (
                expense.product_id
                and not expense.company_currency_id.is_zero(
                    expense.product_id.standard_price
                )
            )
            expense.product_has_tax = bool(
                expense.product_id.sudo().supplier_taxes_id.filtered_domain(
                    self.env["account.tax"]._check_company_domain(expense.company_id)
                )
            )

    @api.depends("product_id.uom_id")
    def _compute_uom_id(self):
        for expense in self:
            expense.product_uom_id = expense.product_id.uom_id

    @api.depends(
        "amount_residual",
        "account_move_id.state",
        "account_move_id.payment_state",
        "review_state",
    )
    def _compute_state(self):
        for expense in self:
            move = expense.account_move_id
            if move.state == "cancel":
                expense.state = "paid"
                continue
            if move:
                if expense.payment_mode == "company_account":
                    expense.state = "paid"
                elif move.state == "draft" or move.payment_state == "not_paid":
                    expense.state = "posted"
                elif move.payment_state == "in_payment" or (
                    move.payment_state == "partial"
                    and not expense.company_currency_id.is_zero(expense.amount_residual)
                ):
                    expense.state = self.env[
                        "account.move"
                    ]._get_invoice_in_payment_state()
                else:
                    expense.state = "paid"
                continue
            expense.state = expense.review_state or "draft"
        _debug.perf.count("state_computed", expenses=self)

    @api.depends("employee_id", "employee_id.department_id")
    def _compute_from_employee_id(self):
        for expense in self:
            expense.department_id = expense.employee_id.department_id
            expense.manager_id = expense._get_default_responsible_for_approval()

    @api.depends("quantity", "price_unit", "tax_ids")
    def _compute_total_amount_currency(self):
        AccountTax = self.env["account.tax"]
        for expense in self.filtered("product_has_cost"):
            base_line = expense._prepare_base_line_for_taxes_computation(
                price_unit=expense.price_unit, quantity=expense.quantity
            )
            AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
            AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
            expense.total_amount_currency = base_line["tax_details"][
                "total_included_currency"
            ]

    @api.onchange("total_amount_currency")
    def _inverse_total_amount_currency(self):
        for expense in self:
            if not expense.is_editable:
                raise UserError(
                    _(
                        "Uh-oh! You can’t edit this expense.\n\n"
                        "Reach out to the administrators, flash your best smile, and see if they'll grant you the magical access you seek."
                    )
                )
            expense.price_unit = (
                (expense.total_amount / expense.quantity)
                if expense.quantity != 0
                else 0.0
            )

    @api.depends(
        "date",
        "company_id",
        "currency_id",
        "company_currency_id",
        "is_multiple_currency",
        "total_amount_currency",
        "product_id",
        "employee_id.user_id.partner_id",
        "quantity",
    )
    def _compute_total_amount(self):
        AccountTax = self.env["account.tax"]
        for expense in self:
            if not expense.company_id:
                continue

            if expense.is_multiple_currency:
                base_line = expense._prepare_base_line_for_taxes_computation(
                    price_unit=expense.total_amount_currency * expense.currency_rate,
                    quantity=1.0,
                    currency_id=expense.company_currency_id,
                    rate=1.0,
                )
                AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
                AccountTax._round_base_lines_tax_details(
                    [base_line], expense.company_id
                )
                expense.total_amount = base_line["tax_details"][
                    "total_included_currency"
                ]
            else:
                expense.total_amount = expense.total_amount_currency

    def _inverse_total_amount(self):
        AccountTax = self.env["account.tax"]
        for expense in self:
            if expense.is_multiple_currency:
                base_line = expense._prepare_base_line_for_taxes_computation(
                    price_unit=expense.total_amount,
                    quantity=1.0,
                    currency=expense.company_currency_id,
                )
                AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
                AccountTax._round_base_lines_tax_details(
                    [base_line], expense.company_id
                )
                tax_details = base_line["tax_details"]
                expense.tax_amount = (
                    tax_details["total_included_currency"]
                    - tax_details["total_excluded_currency"]
                )
                expense.untaxed_amount = tax_details["total_excluded_currency"]
            else:
                expense.total_amount_currency = expense.total_amount
                expense.tax_amount = expense.tax_amount_currency
                expense.untaxed_amount = expense.untaxed_amount_currency
            expense.currency_rate = (
                expense.total_amount / expense.total_amount_currency
                if expense.total_amount_currency
                else 1.0
            )
            expense.price_unit = (
                expense.total_amount / expense.quantity
                if expense.quantity
                else expense.total_amount
            )

    @api.depends("product_id", "company_id")
    def _compute_tax_ids(self):
        for _expense in self.filtered("company_id"):
            expense = _expense.with_company(_expense.company_id)
            expense.tax_ids = expense.product_id.supplier_taxes_id.filtered_domain(
                self.env["account.tax"]._check_company_domain(expense.company_id)
            )

    @api.depends("total_amount_currency", "tax_ids")
    def _compute_tax_amount_currency(self):
        AccountTax = self.env["account.tax"]
        for expense in self:
            if not expense.company_id:
                continue

            base_line = expense._prepare_base_line_for_taxes_computation(
                price_unit=expense.total_amount_currency,
                quantity=1.0,
            )
            AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
            AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
            tax_details = base_line["tax_details"]
            expense.tax_amount_currency = (
                tax_details["total_included_currency"]
                - tax_details["total_excluded_currency"]
            )
            expense.untaxed_amount_currency = tax_details["total_excluded_currency"]

    @api.depends("total_amount", "currency_rate", "tax_ids", "is_multiple_currency")
    def _compute_tax_amount(self):
        AccountTax = self.env["account.tax"]
        for expense in self:
            if not expense.company_id:
                continue

            if expense.is_multiple_currency:
                base_line = expense._prepare_base_line_for_taxes_computation(
                    price_unit=expense.total_amount,
                    quantity=1.0,
                    currency=expense.company_currency_id,
                )
                AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
                AccountTax._round_base_lines_tax_details(
                    [base_line], expense.company_id
                )
                tax_details = base_line["tax_details"]
                expense.tax_amount = (
                    tax_details["total_included_currency"]
                    - tax_details["total_excluded_currency"]
                )
                expense.untaxed_amount = tax_details["total_excluded_currency"]
            else:
                expense.tax_amount = expense.tax_amount_currency
                expense.untaxed_amount = expense.untaxed_amount_currency

    @api.depends("total_amount", "total_amount_currency")
    def _compute_price_unit(self):
        for expense in self:
            if expense.state != "draft":
                continue

            if not expense.company_id:
                continue

            product_id = expense.product_id
            if expense._is_product_price_computation_required():
                expense.price_unit = product_id._get_prices(
                    "standard_price",
                    uom=expense.product_uom_id,
                    company=expense.company_id,
                )[product_id.id]
            else:
                expense.price_unit = (
                    expense.company_currency_id.round(
                        expense.total_amount / expense.quantity
                    )
                    if expense.quantity
                    else 0.0
                )

    @api.depends("selectable_payment_channel_ids")
    def _compute_payment_channel_id(self):
        for expense in self:
            expense.payment_channel_id = expense.selectable_payment_channel_ids[:1]

    @api.depends("company_id")
    def _compute_selectable_payment_channel_ids(self):
        for company, expenses in self.grouped("company_id").items():
            allowed_method_line_ids = (
                company.company_expense_allowed_payment_channel_ids
            )
            if allowed_method_line_ids:
                expenses.selectable_payment_channel_ids = allowed_method_line_ids
            else:
                expenses.selectable_payment_channel_ids = self.env[
                    "account.payment.channel"
                ].search(  # noqa: E8507 - one query per company; expenses sharing one were merged above
                    [
                        *self.env["account.journal"]._check_company_domain(company),
                        ("payment_type", "=", "outbound"),
                        ("journal_id.active", "=", True),
                    ]
                )

    @api.depends("product_id", "company_id")
    def _compute_account_id(self):
        for _expense in self:
            expense = _expense.with_company(_expense.company_id)
            if not expense.product_id:
                expense.account_id = _expense.company_id.expense_account_id
                continue
            account = expense.product_id.product_tmpl_id._get_product_accounts()[
                "expense"
            ]
            if account:
                expense.account_id = account

    @api.depends("company_id")
    def _compute_employee_id(self):
        if self.env.context.get("default_employee_id"):
            return
        for expense in self:
            employee = self.env.user.with_company(expense.company_id).employee_id
            if not employee and not self.env.user.has_group(
                "hr_expense.group_hr_expense_team_approver"
            ):
                raise ValidationError(
                    _("The current user has no related employee. Please, create one.")
                )
            expense.employee_id = employee

    @api.depends("attachment_ids")
    def _compute_same_receipt_expense_ids(self):
        self.same_receipt_expense_ids = [Command.clear()]

        expenses_with_attachments = self.filtered(
            lambda expense: (
                expense.attachment_ids and not expense.split_expense_origin_id
            )
        )
        if not expenses_with_attachments:
            return

        with _debug.perf(
            "same_receipt_scan", cr=self.env.cr, expenses=expenses_with_attachments
        ) as span:
            expenses_groupby_checksum = dict(
                self.env["ir.attachment"]._read_group(
                    domain=[
                        ("res_model", "=", "hr.expense"),
                        (
                            "checksum",
                            "in",
                            expenses_with_attachments.attachment_ids.mapped("checksum"),
                        ),
                    ],
                    groupby=["checksum"],
                    aggregates=["res_id:array_agg"],
                )
            )
            span.set(checksums=len(expenses_groupby_checksum))

            for expense in expenses_with_attachments:
                same_receipt_ids = set()
                for attachment in expense.attachment_ids:
                    same_receipt_ids.update(
                        expenses_groupby_checksum[attachment.checksum]
                    )
                same_receipt_ids.remove(expense.id)

                expense.same_receipt_expense_ids = [Command.set(list(same_receipt_ids))]

    @api.depends("employee_id", "product_id", "total_amount_currency")
    def _compute_duplicate_expense_ids(self):
        self.duplicate_expense_ids = [Command.clear()]

        expenses = self.filtered(
            lambda expense: (
                expense.employee_id
                and expense.product_id
                and expense.total_amount_currency
            )
        )
        if expenses.ids:
            duplicates_query = """
              SELECT ARRAY_AGG(DISTINCT he.id)
                FROM hr_expense AS he
                JOIN hr_expense AS ex ON he.employee_id = ex.employee_id
                                     AND he.product_id = ex.product_id
                                     AND he.date = ex.date
                                     AND he.total_amount_currency = ex.total_amount_currency
                                     AND he.company_id = ex.company_id
                                     AND he.currency_id = ex.currency_id
               WHERE ex.id = ANY(%(expense_ids)s)
               GROUP BY he.employee_id, he.product_id, he.date, he.total_amount_currency, he.company_id, he.currency_id
              HAVING COUNT(he.id) > 1
            """
            with _debug.perf(
                "duplicate_scan", cr=self.env.cr, expenses=expenses
            ) as span:
                self.env.cr.execute(
                    duplicates_query, {"expense_ids": list(expenses.ids)}
                )

                groups = 0  # debuglog
                for duplicates_ids in (x[0] for x in self.env.cr.fetchall()):
                    groups += 1  # debuglog
                    expenses_duplicates = expenses.filtered(
                        lambda expense, duplicates_ids=duplicates_ids: (
                            expense.id in duplicates_ids
                        )
                    )
                    expenses_duplicates.duplicate_expense_ids = [
                        Command.set(duplicates_ids)
                    ]
                    expenses -= expenses_duplicates
                span.set(groups=groups)

    @api.depends("product_id", "account_id", "employee_id")
    def _compute_analytic_distribution(self):
        for expense in self:
            distribution = self.env[
                "account.analytic.distribution.model"
            ]._get_distribution(
                {
                    "product_id": expense.product_id.id,
                    "product_categ_id": expense.product_id.categ_id.id,
                    "partner_id": expense.employee_id.partner_id.id,
                    "partner_tag_id": expense.employee_id.partner_id.tag_ids.ids,
                    "account_prefix": expense.account_id.code,
                    "company_id": expense.company_id.id,
                }
            )
            expense.analytic_distribution = (
                distribution or expense.analytic_distribution
            )

    def _compute_nb_attachment(self):
        attachment_data = self.env["ir.attachment"]._read_group(
            [("res_model", "=", "hr.expense"), ("res_id", "in", self.ids)],
            ["res_id"],
            ["__count"],
        )
        attachment = dict(attachment_data)
        for expense in self:
            expense.nb_attachment = attachment.get(expense._origin.id, 0)

    @api.depends_context("uid")
    @api.depends("employee_id", "state")
    def _compute_can_reset(self):
        user = self.env.user
        is_team_approver = (
            user.has_group("hr_expense.group_hr_expense_team_approver") or self.env.su
        )
        is_all_approver = (
            user.has_groups(
                "hr_expense.group_hr_expense_user,hr_expense.group_hr_expense_manager"
            )
            or self.env.su
        )

        valid_company_ids = set(self.env.companies.ids)
        expenses_employee_ids_under_user_ones = set()
        if is_team_approver:
            expenses_employee_ids_under_user_ones = set(
                self.env["hr.employee"]
                .sudo()
                .search(
                    [
                        ("id", "in", self.employee_id.ids),
                        ("id", "child_of", user.employee_ids.ids),
                        ("id", "not in", user.employee_ids.ids),
                    ]
                )
                .ids
            )

        for expense in self:
            expense.can_reset = expense.company_id.id in valid_company_ids and (
                is_all_approver
                or expense.employee_id.id in expenses_employee_ids_under_user_ones
                or expense.employee_id.expense_manager_id == user
                or (
                    expense.state in {"draft", "submitted"}
                    and expense.employee_id.user_id == user
                )
            )

    @api.depends_context("uid")
    @api.depends("employee_id")
    def _compute_can_approve(self):
        cannot_reason_per_record_id = self._get_cannot_approve_reason()
        for expense in self:
            expense.can_approve = not cannot_reason_per_record_id[expense.id]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_approved(self):
        for expense in self:
            if expense.state in {"approved", "posted", "in_payment", "paid"}:
                _debug.logic("unlink_refused", expense=expense, state=expense.state)
                raise UserError(_("You cannot delete a posted or approved expense."))

    def write(self, vals):
        _debug.lifecycle("write", expenses=self, fields=list(vals))
        if any(field in vals for field in ("is_editable", "can_approve", "can_refuse")):
            _debug.logic("write_refused", reason="security_field", fields=list(vals))
            raise UserError(
                _("You cannot edit the security fields of an expense manually")
            )

        if any(
            field in vals
            for field in (
                "tax_ids",
                "analytic_distribution",
                "account_id",
                "manager_id",
            )
        ):
            if any((not expense.is_editable and not self.env.su) for expense in self):
                _debug.logic("write_refused", reason="not_editable", fields=list(vals))
                raise UserError(
                    _(
                        "Uh-oh! You can’t edit this expense.\n\n"
                        "Reach out to the administrators, flash your best smile, and see if they'll grant you the magical access you seek."
                    )
                )

        res = super().write(vals)

        if vals.get("state") == "approved" or vals.get("review_state") == "approved":
            _debug.pipeline("write_approval_check", kind="approved", expenses=self)
            self.filtered(
                lambda expense: (
                    expense.manager_id - expense.employee_id.user_id
                    or expense.employee_id.expense_manager_id
                )
            )._check_can_approve()
        elif vals.get("state") == "refused" or vals.get("review_state") == "refused":
            _debug.pipeline("write_approval_check", kind="refused", expenses=self)
            self._check_can_refuse()

        if "currency_id" in vals:
            _debug.pipeline("write_rerate", expenses=self, currency=vals["currency_id"])
            self._set_expense_currency_rate(date_today=fields.Date.context_today(self))
            for expense in self:
                expense.total_amount = (
                    expense.total_amount_currency * expense.currency_rate
                )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        expenses = super().create(vals_list)
        _debug.lifecycle("create", expenses=expenses, count=len(vals_list))
        expenses.update_activities_and_mails()
        return expenses

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        res = super()._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get("employee_id"):
            employee_user = (
                self.env["hr.employee"].browse(updated_values["employee_id"]).user_id
            )
            if employee_user:
                res.append((employee_user.partner_id.id, subtype_ids, False))
        return res

    @api.model
    def _get_employee_from_email(self, email_address):
        if not email_address:
            return self.env["hr.employee"]
        employee = self.env["hr.employee"].search(
            [
                ("user_id", "!=", False),
                "|",
                ("work_email", "ilike", email_address),
                ("user_id.email", "ilike", email_address),
            ]
        )

        if len(employee) > 1:
            _debug.logic("employee_from_email", by="company_match", matched=employee)
            return employee.filtered(lambda e: e.company_id == e.user_id.company_id)

        if not employee:
            _debug.logic(
                "employee_from_email",
                by="userless_work_email",
                email=email_address,
            )
            return self.env["hr.employee"].search(
                [
                    ("user_id", "=", False),
                    ("work_email", "ilike", email_address),
                ],
                limit=1,
            )

        _debug.logic("employee_from_email", by="unique_user", matched=employee)
        return employee

    @api.model
    def _parse_product(self, expense_description):
        product_code = expense_description.split(" ")[0]
        product = self.env["product.product"].search(
            [("can_be_expensed", "=", True), ("default_code", "=ilike", product_code)],
            limit=1,
        )
        if product:
            expense_description = expense_description.replace(product_code, "", 1)

        return product, expense_description

    @api.model
    def _parse_price(self, expense_description, currencies):
        symbols, symbols_pattern, float_pattern = [], "", r"[+-]?(\d+[.,]?\d*)"
        price = 0.0
        for currency in currencies:
            symbols += [re.escape(currency.symbol), re.escape(currency.name)]
        symbols_pattern = "|".join(symbols)
        price_pattern = (
            f"(({symbols_pattern})?\\s?{float_pattern}\\s?({symbols_pattern})?)"
        )
        matches = re.findall(price_pattern, expense_description)
        currency = currencies[:1]
        if matches:
            match = max(
                matches, key=lambda match: len([group for group in match if group])
            )
            full_str = match[0]
            currency_str = match[1] or match[3]
            price = match[2].replace(",", ".")

            if currency_str and currencies:
                currencies = currencies.filtered(
                    lambda c: currency_str in [c.symbol, c.name]
                )
                currency = currencies[:1] or currency
            expense_description = expense_description.replace(full_str, " ")
            expense_description = re.sub(r" +", " ", expense_description.strip())

        return float(price), currency, expense_description

    @api.model
    def _parse_expense_subject(self, expense_description, currencies):
        product, expense_description = self._parse_product(expense_description)
        price, currency_id, expense_description = self._parse_price(
            expense_description, currencies
        )

        return product, price, currency_id, expense_description

    def _send_expense_success_mail(self, msg_dict, expense):
        if expense.employee_id.user_id:
            mail_template_id = "hr_expense.hr_expense_template_register"
        else:
            mail_template_id = "hr_expense.hr_expense_template_register_no_user"
        _debug.logic(
            "success_mail_template", expense=expense, template=mail_template_id
        )
        rendered_body = self.env["ir.qweb"]._render(
            mail_template_id, {"expense": expense}
        )
        body = self.env["mixin.mail.render"]._replace_local_links(rendered_body)
        if expense.employee_id.user_id.partner_id:
            expense.message_post(
                body=body,
                email_layout_xmlid="mail.mail_notification_light",
                partner_ids=expense.employee_id.user_id.partner_id.ids,
                subject=f"Re: {msg_dict.get('subject', '')}",
                subtype_xmlid="mail.mt_note",
            )
        else:
            _debug.pipeline("success_mail_direct", expense=expense)
            self.env["mail.mail"].sudo().create(
                {
                    "author_id": self.env.user.partner_id.id,
                    "auto_delete": True,
                    "body_html": body,
                    "email_from": self.env.user.email_formatted,
                    "email_to": msg_dict.get("email_from", False),
                    "references": msg_dict.get("message_id"),
                    "subject": f"Re: {msg_dict.get('subject', '')}",
                }
            ).send()

    @api.model
    def _get_empty_list_mail_alias(self):
        use_mailgateway = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("hr_expense.use_mailgateway")
        )
        expense_alias = (
            self.env.ref("hr_expense.mail_alias_expense", raise_if_not_found=False)
            if use_mailgateway
            else False
        )
        if expense_alias and expense_alias.alias_domain and expense_alias.alias_name:
            params = urlencode({"subject": _("Lunch with customer $12.32")}).replace(
                "+", "%20"
            )
            return Markup(
                """<div class="text-muted mt-4">%(send_string)s <a class="text-body" href="mailto:%(alias_email)s?%(params)s">%(alias_email)s</a></div>"""
            ) % {
                "alias_email": expense_alias.display_name,
                "params": params,
                "send_string": _("Tip: try sending receipts by email"),
            }
        return ""

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "state" not in init_values:
            return super()._track_subtype(init_values)

        match self.state:
            case "draft":
                return self.env.ref("hr_expense.mt_expense_reset")
            case "cancel":
                return self.env.ref("hr_expense.mt_expense_refused")
            case "paid":
                return self.env.ref("hr_expense.mt_expense_paid")
            case "approved":
                if init_values["state"] in {
                    "posted",
                    "in_payment",
                    "paid",
                }:
                    subtype = (
                        "hr_expense.mt_expense_entry_draft"
                        if self.account_move_id
                        else "hr_expense.mt_expense_entry_delete"
                    )
                    return self.env.ref(subtype)
                return self.env.ref("hr_expense.mt_expense_approved")
            case _:
                return super()._track_subtype(init_values)

    def _get_approval_sync_state_field(self):
        return "review_state"

    def _get_approval_sync_kinds(self):
        return {
            False: "draft",
            "submitted": "pending",
            "approved": "approved",
            "refused": "refused",
        }

    def _get_approval_category_xmlid(self):
        return "hr_expense.approval_category_expense"

    def _get_legacy_approval_activity_xmlids(self):
        return ("hr_expense.mail_act_expense_approval",)

    def _prepare_approval_request_values(self, category):
        vals = super()._prepare_approval_request_values(category)
        vals["request_owner_id"] = (self.employee_id.user_id or self.env.user).id
        vals["amount"] = self.total_amount_currency
        vals["currency_id"] = self.currency_id.id
        return vals

    def _filter_approval_step_user_ids(self, step, user_ids):
        self.check_singleton()
        return {
            user.id
            for user in self.env["res.users"].browse(sorted(user_ids))
            if not self._get_cannot_approve_reason(user)[self.id]
        }

    def _check_approval_sync_policy(self, kind):
        if kind == "approved":
            self._check_can_approve()
            self.with_context(validate_analytic=True)._check_approval_distribution()
            if self._get_duplicate_expenses_to_review():
                _debug.logic("approval_sync_refused", reason="duplicates", expense=self)
                raise UserError(
                    _(
                        "%(expense)s may duplicate another expense. Approve it from "
                        "the expense, where its duplicates can be reviewed.",
                        expense=self.name,
                    )
                )
        elif kind == "refused":
            self._check_can_refuse()

    def _apply_approval_sync_outcome(self, kind):
        self.check_singleton()
        _debug.pipeline("approval_sync_outcome", expense=self, kind=kind)
        if kind == "progress":
            return
        if kind == "approved":
            self._do_approve(check=False)
            return
        self._do_refuse(
            self.sudo().approval_request_id.refusal_note
            or (
                _("Refused through its approval request.")
                if kind == "refused"
                else _("Cancelled through its approval request.")
            )
        )

    def update_activities_and_mails(self):
        expenses_activity_done = self.env["hr.expense"]
        expenses_activity_unlink = self.env["hr.expense"]
        expenses_submitted_to_review = self.env["hr.expense"]
        for expense in self.filtered(
            lambda expense: not expense.sudo().approval_request_id
        ):
            if expense.state == "submitted":
                expense.with_context(mail_activity_quick_update=True).activity_schedule(
                    "hr_expense.mail_act_expense_approval",
                    user_id=expense.manager_id.id
                    or expense.sudo()._get_default_responsible_for_approval().id
                    or self.env.user.id,
                )
                expenses_submitted_to_review |= expense
            elif expense.state == "approved":
                expenses_activity_done |= expense
            elif expense.state in {"draft", "refused"}:
                expenses_activity_unlink |= expense

        _debug.pipeline(
            "activities_synced",
            submitted=expenses_submitted_to_review,
            done=expenses_activity_done,
            unlinked=expenses_activity_unlink,
        )
        if expenses_activity_done:
            expenses_activity_done.activity_feedback(
                ["hr_expense.mail_act_expense_approval"]
            )
        if expenses_activity_unlink:
            expenses_activity_unlink.activity_unlink(
                ["hr_expense.mail_act_expense_approval"]
            )

        installed_module_version = (
            self.sudo().env.ref("base.module_hr_expense").db_version
        )
        if expenses_submitted_to_review and parse_version(installed_module_version)[
            2:
        ] < parse_version("2.1"):
            _debug.logic(
                "submitted_mail_by_version",
                db_version=installed_module_version,
                expenses=expenses_submitted_to_review,
            )
            self._send_submitted_expenses_mail()

    @api.model
    def _cron_send_submitted_expenses_mail(self):
        with _debug.perf("cron_submitted_mail", cr=self.env.cr) as span:
            expenses_submitted_to_review = self.search([("state", "=", "submitted")])
            span.set(expenses=len(expenses_submitted_to_review))
            if expenses_submitted_to_review:
                expenses_submitted_to_review._send_submitted_expenses_mail()

    def _send_submitted_expenses_mail(self):
        new_mails = []
        for company, expenses_submitted_per_company in self.grouped(
            "company_id"
        ).items():
            parent_company_mails = company.parent_ids[::-1].mapped("email_formatted")
            mail_from = (
                self.env.user.email
                or company.email_formatted
                or (parent_company_mails and parent_company_mails[0])
            )

            if not mail_from:
                _logger.warning(
                    _(
                        "Failed to send mails for submitted expenses. No valid email was found for the company"
                    )
                )
                continue

            for manager in expenses_submitted_per_company.grouped("manager_id"):
                if not manager:
                    continue
                manager_langs = tuple(
                    lang for lang in manager.partner_id.mapped("lang") if lang
                )
                mail_lang = (
                    (manager_langs and manager_langs[0]) or self.env.lang or "en_US"
                )
                body = self.env["ir.qweb"]._render(
                    template="hr_expense.hr_expense_template_submitted_expenses",
                    values={
                        "manager_name": manager.name,
                        "url": "/odoo/expenses-to-process",
                        "company": company,
                    },
                    lang=mail_lang,
                )
                new_mails.append(
                    {
                        "author_id": self.env.user.partner_id.id,
                        "auto_delete": True,
                        "body_html": body,
                        "email_from": mail_from,
                        "email_to": manager.employee_id.work_email or manager.email,
                        "subject": _("New expenses waiting for your approval"),
                    }
                )
            if new_mails:
                self.env["mail.mail"].sudo().create(new_mails).send()

    @api.model
    def get_empty_list_help(self, help_message):
        return super().get_empty_list_help(
            (help_message or "") + self._get_empty_list_mail_alias()
        )

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        email_address = email_normalize(msg_dict.get("email_from"))
        employee = self._get_employee_from_email(email_address)

        if not employee:
            _debug.logic("message_new_no_employee", email=email_address or "none")
            return super().message_new(msg_dict, custom_values=custom_values)

        expense_description = msg_dict.get("subject", "")

        if employee.user_id:
            company = employee.user_id.company_id
            currencies = company.currency_id | employee.user_id.company_ids.mapped(
                "currency_id"
            )
        else:
            company = employee.company_id
            currencies = company.currency_id

        if not company:
            company = self.env.company

        self = self.with_company(company)

        product, price, currency_id, expense_description = self._parse_expense_subject(
            expense_description, currencies
        )
        _debug.pipeline(
            "message_new_parsed",
            employee=employee,
            company=company,
            product=product,
            price=price,
            currency=currency_id,
        )
        vals = {
            "employee_id": employee.id,
            "name": expense_description,
            "total_amount_currency": price,
            "product_id": product.id if product else None,
            "product_uom_id": product.uom_id.id,
            "tax_ids": [
                Command.set(
                    product.supplier_taxes_id.filtered_domain(
                        self.env["account.tax"]._check_company_domain(company)
                    ).ids
                )
            ],
            "quantity": 1,
            "company_id": company.id,
            "currency_id": currency_id.id,
        }

        if product:
            account = product.product_tmpl_id._get_product_accounts()["expense"]
            if account:
                vals["account_id"] = account.id

        expense = super().message_new(msg_dict, dict(custom_values or {}, **vals))
        _debug.lifecycle("message_new", expense=expense, employee=employee)
        self._send_expense_success_mail(msg_dict, expense)
        return expense

    def action_view_split_expense(self):
        self.check_singleton()
        split_expense_ids = self.search(
            [("split_expense_origin_id", "=", self.split_expense_origin_id.id)]
        )
        return split_expense_ids._get_records_action(name=_("Split Expenses"))

    def action_submit(self):
        user = self.env.user
        for expense in self:
            if user.employee_id != expense.employee_id and not expense.can_approve:
                _debug.logic(
                    "submit_refused",
                    reason="not_own_and_cannot_approve",
                    expense=expense,
                    user=user,
                )
                raise UserError(
                    _("You do not have the required permission to submit this expense.")
                )
            if not expense.product_id:
                raise UserError(_("You can not submit an expense without a category."))
            if not expense.manager_id:
                expense.sudo().manager_id = (
                    expense._get_default_responsible_for_approval()
                )
        expenses_autovalidated = self.filtered(
            lambda expense: expense._can_be_autovalidated()
        )
        _debug.pipeline(
            "submit",
            expenses=self,
            autovalidated=expenses_autovalidated,
            submitted=self - expenses_autovalidated,
        )
        (self - expenses_autovalidated).review_state = "submitted"
        if expenses_autovalidated:
            expenses_autovalidated._do_approve(check=False)
        self.sudo().update_activities_and_mails()

    def _can_be_autovalidated(self):
        self.check_singleton()
        return (
            not self.manager_id and not self.employee_id.expense_manager_id
        ) or self.manager_id == self.employee_id.user_id

    def action_approve(self):
        self._check_can_approve()
        self._check_approval_distribution()
        duplicates = self._get_duplicate_expenses_to_review()
        if duplicates:
            _debug.logic(
                "approve_needs_duplicate_review", expenses=self, duplicates=duplicates
            )
            action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
                "hr_expense.hr_expense_approve_duplicate_action"
            )
            action["context"] = {"default_expense_ids": duplicates.ids}
            return action
        self._do_approve(False)
        return None

    def _check_approval_distribution(self):
        for expense in self:
            expense._check_distribution(
                account=expense.account_id.id,
                product=expense.product_id.id,
                business_domain="expense",
                company_id=expense.company_id.id,
            )

    def _get_duplicate_expenses_to_review(self):
        return self.duplicate_expense_ids.filtered(
            lambda exp: (
                exp.state in {"submitted", "approved", "posted", "paid", "in_payment"}
            )
        )

    def action_refuse(self):
        self._check_can_refuse()
        return self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "hr_expense.hr_expense_refuse_wizard_action"
        )

    def action_post(self):
        self._check_can_create_move()

        company_expenses = self.filtered(
            lambda expense: expense.payment_mode == "company_account"
        )
        employee_expenses = self - company_expenses
        if len(employee_expenses.company_id) > 1:
            _debug.logic(
                "post_refused",
                reason="multi_company_employee_paid",
                companies=employee_expenses.company_id,
            )
            raise UserError(
                _(
                    "You can't post simultaneously employee-paid expenses belonging to different companies"
                )
            )

        _debug.pipeline(
            "post", company_paid=company_expenses, employee_paid=employee_expenses
        )
        if company_expenses:
            company_expenses._create_company_paid_moves()
            company_expenses.account_move_id.origin_payment_id.action_post()

        if employee_expenses:
            return employee_expenses.with_context(
                company_paid_move_ids=company_expenses.account_move_id.ids
            )._post_wizard()
        return None

    def action_pay(self):
        return self.account_move_id.with_context(
            default_partner_bank_id=(
                self.account_move_id.partner_bank_id.id
                if len(self.account_move_id.partner_bank_id) <= 1
                else None
            )
        ).action_register_payment()

    def action_reset(self):
        self._check_can_reset_approval()
        self = self.with_context(clean_context(self.env.context))
        moves_sudo = self.sudo().account_move_id
        draft_moves_sudo = moves_sudo.filtered(lambda m: m.state == "draft")
        non_draft_moves_sudo = moves_sudo - draft_moves_sudo
        non_draft_moves_sudo._reverse_moves(
            default_values_list=[
                {"invoice_date": fields.Date.context_today(move_sudo)}
                for move_sudo in non_draft_moves_sudo
            ],
            cancel=True,
        )
        _debug.pipeline(
            "reset",
            expenses=self,
            reversed_moves=non_draft_moves_sudo,
            unlinked_moves=draft_moves_sudo,
        )
        draft_moves_sudo.unlink()
        self._do_reset_approval()

    def attach_document(self, **kwargs):
        self._message_set_main_attachment_id(
            self.env["ir.attachment"].browse(kwargs["attachment_ids"][-1:]), force=True
        )

    @api.model
    def _get_untitled_expense_name(self, *args):
        return _("Untitled Expense %s", *args)

    @api.model
    def create_expense_from_attachments(self, attachment_ids=None, view_type="list"):
        if not attachment_ids:
            raise UserError(_("No attachment was provided"))
        attachments = self.env["ir.attachment"].browse(attachment_ids)
        expenses = self.env["hr.expense"]

        if any(
            attachment.res_id or attachment.res_model != "hr.expense"
            for attachment in attachments
        ):
            raise UserError(_("Invalid attachments!"))

        product = self.env["product.product"].search([("can_be_expensed", "=", True)])
        if product:
            product = (
                product.filtered(lambda p: p.default_code == "EXP_GEN")[:1]
                or product[0]
            )
        else:
            _debug.logic("no_expensable_product", attachments=attachments)
            raise UserError(
                _(
                    "You need to have at least one category that can be expensed in your database to proceed!"
                )
            )

        for attachment in attachments:
            vals = {
                "name": self._get_untitled_expense_name(
                    format_date(self.env, fields.Date.context_today(self))
                ),
                "price_unit": 0,
                "product_id": product.id,
            }
            if product.property_account_expense_id:
                vals["account_id"] = product.property_account_expense_id.id
            expense = self.env["hr.expense"].create(vals)
            attachment.write({"res_model": "hr.expense", "res_id": expense.id})

            expense._message_set_main_attachment_id(attachment, force=True)
            expenses += expense
        _debug.lifecycle(
            "created_from_attachments",
            attachments=attachments,
            expenses=expenses,
            product=product,
        )
        return expenses.ids

    def action_show_same_receipt_expense_ids(self):
        self.check_singleton()
        return self.same_receipt_expense_ids._get_records_action(
            name=_(
                "Expenses with a similar receipt to %(other_expense_name)s",
                other_expense_name=self.name,
            ),
        )

    @api.model
    def get_expense_dashboard(self):
        expense_state = {
            "draft": {
                "description": _("To Submit"),
                "amount": 0.0,
                "currency": self.env.company.currency_id.id,
            },
            "submitted": {
                "description": _("Waiting Approval"),
                "amount": 0.0,
                "currency": self.env.company.currency_id.id,
            },
            "approved": {
                "description": _("Waiting Reimbursement"),
                "amount": 0.0,
                "currency": self.env.company.currency_id.id,
            },
        }
        if not self.env.user.employee_ids:
            _debug.logic("dashboard_no_employee", user=self.env.user)
            return expense_state
        fetched_expenses = self._read_group(
            [
                ("employee_id", "in", self.env.user.employee_ids.ids),
                "|",
                ("state", "in", ("draft", "submitted")),
                "&",
                ("payment_mode", "=", "own_account"),
                ("state", "=", "approved"),
            ],
            ["state"],
            ["total_amount:sum"],
        )
        for state, total_amount_sum in fetched_expenses:
            expense_state[state]["amount"] += total_amount_sum
        return expense_state

    def action_approve_duplicates(self):
        root = self.env["ir.model.data"]._xmlid_to_res_id("base.partner_root")
        for expense in self.duplicate_expense_ids:
            expense.message_post(
                body=_(
                    "%(user)s confirms this expense is not a duplicate with similar expense.",
                    user=self.env.user.name,
                ),
                author_id=root,
            )

    def action_split_wizard(self):
        self.check_singleton()
        if self.filtered(
            lambda expense: expense.state in {"posted", "paid", "in_payment"}
        ):
            raise UserError(_("You cannot split an expense that is already posted."))
        if not self.is_editable:
            raise UserError(_("You do not have the rights to edit this expense."))

        splits = self.env["hr.expense.split"].create(self._prepare_split_vals())

        wizard = self.env["hr.expense.split.wizard"].create(
            [
                {
                    "expense_split_line_ids": splits.ids,
                    "expense_id": self.id,
                }
            ]
        )
        return {
            "name": _("Expense split"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [[False, "form"]],
            "res_model": "hr.expense.split.wizard",
            "res_id": wizard.id,
            "target": "new",
            "context": self.env.context,
        }

    def action_view_account_move(self):
        self.check_singleton()
        if self.payment_mode == "own_account":
            res_model = "account.move"
            record_id = self.account_move_id
        else:
            res_model = "account.payment"
            record_id = self.account_move_id.origin_payment_id

        return {
            "type": "ir.actions.act_window",
            "res_model": res_model,
            "name": record_id.name,
            "view_mode": "form",
            "res_id": record_id.id,
            "views": [(False, "form")],
        }

    def _check_can_approve(self):
        if not all(self.mapped("can_approve")):
            _debug.logic("approve_refused", expenses=self)
            reasons_list = tuple(
                reason
                for reason in self._get_cannot_approve_reason().values()
                if reason
            )
            reasons = _(
                "You cannot approve:\n %(reasons)s", reasons="\n".join(reasons_list)
            )
            raise UserError(reasons)

    def _get_cannot_approve_reason(self, user=None):
        bypass = self.env.su and user is None
        companies = self.env.companies if user is None else user.company_ids
        user = user or self.env.user
        is_team_approver = (
            user.has_group("hr_expense.group_hr_expense_team_approver") or bypass
        )
        is_approver = user.has_group("hr_expense.group_hr_expense_user") or bypass
        is_hr_admin = user.has_group("hr_expense.group_hr_expense_manager") or bypass

        valid_company_ids = set(companies.ids)

        expenses_employee_ids_under_user_ones = set()
        if is_team_approver:
            expenses_employee_ids_under_user_ones = set(
                self.env["hr.employee"]
                .sudo()
                .search(
                    [
                        ("id", "in", self.employee_id.ids),
                        ("id", "child_of", user.employee_ids.ids),
                        ("id", "not in", user.employee_ids.ids),
                    ]
                )
                .ids
            )
        reasons_per_record_id = {}
        for expense in self:
            reason = False
            expense_employee = expense.employee_id
            is_expense_team_approver = (
                is_team_approver
                or expense_employee.id in expenses_employee_ids_under_user_ones
                or (expense_employee.expense_manager_id == user)
            )
            if expense.company_id.id not in valid_company_ids:
                reason = _(
                    "%(expense_name)s: Your are neither a Manager nor a HR Officer of this expense's company",
                    expense_name=expense.name,
                )

            elif not is_expense_team_approver:
                reason = _(
                    "%(expense_name)s: You are neither a Manager nor a HR Officer",
                    expense_name=expense.name,
                )

            elif not is_hr_admin:
                current_managers = (
                    expense_employee.expense_manager_id
                    | expense_employee.sudo().department_id.manager_id.user_id.sudo(
                        self.env.su
                    )
                    | expense.manager_id
                )
                if expense_employee.id in expenses_employee_ids_under_user_ones:
                    current_managers |= user

                if expense_employee.user_id == user:
                    reason = _(
                        "%(expense_name)s: It is your own expense",
                        expense_name=expense.name,
                    )

                elif user not in current_managers and not is_approver:
                    reason = _(
                        "%(expense_name)s: It is not from your department",
                        expense_name=expense.name,
                    )
            reasons_per_record_id[expense.id] = reason
        return reasons_per_record_id

    def _check_can_refuse(self):
        if not all(self.mapped("can_approve")):
            _debug.logic("refuse_refused", expenses=self)
            reasons = _(
                "You cannot refuse:\n %(reasons)s",
                reasons="\n".join(self._get_cannot_approve_reason().values()),
            )
            raise UserError(reasons)

    def _check_can_reset_approval(self):
        if not all(self.mapped("can_reset")):
            _debug.logic("reset_refused", reason="cannot_reset", expenses=self)
            raise UserError(
                _(
                    "Only HR Officers, accountants, or the concerned employee can reset to draft."
                )
            )
        if any(
            state not in {False, "draft"}
            for state in self.account_move_id.mapped("state")
        ):
            _debug.logic(
                "reset_refused", reason="posted_move", moves=self.account_move_id
            )
            raise UserError(
                _(
                    "You cannot reset to draft an expense linked to a posted journal entry."
                )
            )

    def _check_can_create_move(self):
        if any(expense.state != "approved" for expense in self):
            _debug.logic("create_move_refused", reason="not_approved", expenses=self)
            raise UserError(
                _("You can only generate an accounting entry for approved expense(s).")
            )

        if False in self.mapped("payment_mode"):
            _debug.logic("create_move_refused", reason="no_payment_mode", expenses=self)
            raise UserError(
                _(
                    "Please specify if the expenses were paid by the company, or the employee."
                )
            )

    def _do_approve(self, check=True):
        if check:
            self._check_can_approve()
        expenses_to_approve = self.filtered(lambda s: s.state in {"submitted", "draft"})
        _debug.lifecycle(
            "approve", expenses=self, approving=expenses_to_approve, checked=check
        )
        for expense in expenses_to_approve:
            expense.write(
                {
                    "review_state": "approved",
                    "manager_id": self.env.user.id,
                    "approval_date": fields.Datetime().now(),
                }
            )
        self.update_activities_and_mails()

    def _do_reset_approval(self):
        _debug.lifecycle("reset_approval", expenses=self)
        self.sudo().write(
            {"review_state": False, "approval_date": False, "account_move_id": False}
        )
        self.update_activities_and_mails()

    def _do_refuse(self, reason):
        draft_moves_sudo = self.sudo().account_move_id.filtered(
            lambda move: move.state == "draft"
        )
        if self.sudo().account_move_id - draft_moves_sudo:
            _debug.logic(
                "refuse_refused",
                reason="posted_move",
                moves=self.sudo().account_move_id - draft_moves_sudo,
            )
            raise UserError(
                _("You cannot cancel an expense linked to a posted journal entry")
            )

        if draft_moves_sudo:
            draft_moves_sudo.unlink()

        _debug.lifecycle("refuse", expenses=self, unlinked_moves=draft_moves_sudo)
        self.with_context(approval_refusal_note=reason).review_state = "refused"
        subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment")
        for expense in self:
            expense.message_post_with_source(
                "hr_expense.hr_expense_template_refuse_reason",
                subtype_id=subtype_id,
                render_values={"reason": reason, "name": expense.name},
            )
        self.update_activities_and_mails()

    def _prepare_split_vals(self):
        self.check_singleton()
        _debug.pipeline("split_values", expense=self)
        half_price = self.total_amount_currency / 2
        price_round_up = float_round(
            half_price,
            precision_digits=self.currency_id.decimal_places,
            rounding_method="UP",
        )
        price_round_down = float_round(
            half_price,
            precision_digits=self.currency_id.decimal_places,
            rounding_method="DOWN",
        )

        return [
            {
                "name": self.name,
                "product_id": self.product_id.id,
                "total_amount_currency": price,
                "tax_ids": self.tax_ids.ids,
                "currency_id": self.currency_id.id,
                "company_id": self.company_id.id,
                "analytic_distribution": self.analytic_distribution,
                "employee_id": self.employee_id.id,
                "review_state": self.review_state,
                "approval_date": self.approval_date,
                "manager_id": self.manager_id.id,
                "expense_id": self.id,
            }
            for price in (price_round_up, price_round_down)
        ]

    def _get_default_responsible_for_approval(self):
        self.check_singleton()
        approver_group = "hr_expense.group_hr_expense_team_approver"

        employee = self.employee_id.sudo()
        expense_manager = employee.expense_manager_id - employee.user_id
        if expense_manager:
            _debug.logic(
                "approver", by="expense_manager", expense=self, user=expense_manager
            )
            return expense_manager.sudo(False)

        department_manager = (
            employee.department_id.manager_id.user_id - employee.user_id
        )
        if department_manager and department_manager.has_groups(approver_group):
            _debug.logic(
                "approver",
                by="department_manager",
                expense=self,
                user=department_manager,
            )
            return department_manager.sudo(False)

        employee_team_leader = employee.parent_id.user_id
        if employee_team_leader:
            _debug.logic(
                "approver", by="team_leader", expense=self, user=employee_team_leader
            )
            return employee_team_leader.sudo(False)

        _debug.logic("approver", by="none", expense=self)
        return self.env["res.users"]

    def _is_product_price_computation_required(self):
        self.check_singleton()
        return self.product_has_cost

    def _post_wizard(self):
        if "company_account" in set(self.mapped("payment_mode")):
            raise UserError(
                _("Only expense paid by the employee can be posted with the wizard")
            )

        wizard_name = (
            _("Post expenses paid by the employee")
            if self.env.context.get("company_paid_move_ids")
            else _("Post expenses")
        )
        return {
            "type": "ir.actions.act_window",
            "name": wizard_name,
            "view_mode": "form",
            "views": [(False, "form")],
            "res_model": "hr.expense.post.wizard",
            "res_id": self.env["hr.expense.post.wizard"].create({}).id,
            "target": "new",
            "context": self.with_context(active_ids=self.ids).env.context,
        }

    def _post_without_wizard(self):
        self._check_can_create_move()
        today = fields.Date.context_today(self)
        employee_expenses = self.filtered(
            lambda expense: expense.payment_mode == "own_account"
        )

        _debug.pipeline(
            "post_without_wizard",
            expenses=self,
            employee_paid=employee_expenses,
            companies=len(employee_expenses.company_id),
        )
        for company, expenses in employee_expenses.grouped("company_id").items():
            expenses = expenses.with_company(company)
            company_domain = self.env["account.journal"]._check_company_domain(company)
            journal = company.expense_journal_id or expenses.env[  # noqa: E8507 - one lookup per company; expenses sharing one were merged above
                "account.journal"
            ].search([*company_domain, ("type", "=", "purchase")], limit=1)
            expense_receipt_vals_list = [
                {
                    **new_receipt_vals,
                    "journal_id": journal.id,
                    "invoice_date": today,
                }
                for new_receipt_vals in expenses._prepare_receipts_vals()
            ]
            moves = self.env["account.move"].sudo().create(expense_receipt_vals_list)
            _debug.lifecycle(
                "receipt_moves_created",
                company=company,
                journal=journal,
                moves=moves,
                expenses=expenses,
            )
            for move in moves:
                move._message_set_main_attachment_id(
                    move.attachment_ids, force=True, filter_xml=False
                )
            moves.action_post()

    def _create_company_paid_moves(self):
        self = self.with_context(clean_context(self.env.context))
        company_account_expenses = self.filtered(
            lambda expense: expense.payment_mode == "company_account"
        )
        moves_sudo = self.env["account.move"].sudo()

        if company_account_expenses:
            move_vals_list, payment_vals_list = zip(
                *[
                    expense._prepare_payments_vals()
                    for expense in company_account_expenses
                ],
                strict=True,
            )

            payment_moves_sudo = self.env["account.move"].sudo().create(move_vals_list)
            for payment_vals, move in zip(
                payment_vals_list, payment_moves_sudo, strict=True
            ):
                payment_vals["move_id"] = move.id

            self.env["account.payment"].sudo().create(payment_vals_list)
            _debug.lifecycle(
                "company_paid_moves_created",
                expenses=company_account_expenses,
                moves=payment_moves_sudo,
            )

            moves_sudo |= payment_moves_sudo

        return moves_sudo.sudo(self.env.su)

    def _prepare_receipts_vals(self):
        attachments_data = [
            Command.create(
                attachment.copy_data(
                    {
                        "res_model": "account.move",
                        "res_id": False,
                        "raw": attachment.raw,
                    }
                )[0]
            )
            for attachment in self.attachment_ids
        ]

        return_vals = []
        for employee_sudo, expenses_sudo in self.sudo().grouped("employee_id").items():
            multiple_expenses_name = _(
                "Expenses of %(employee)s", employee=employee_sudo.name
            )
            move_ref = (
                expenses_sudo.name
                if len(expenses_sudo) == 1
                else multiple_expenses_name
            )
            return_vals.append(
                {
                    **expenses_sudo._prepare_move_vals(),
                    "ref": move_ref,
                    "move_type": "in_receipt",
                    "partner_id": employee_sudo.partner_id.id,
                    "commercial_partner_id": employee_sudo.partner_id.commercial_partner_id.id,
                    "currency_id": expenses_sudo.company_currency_id.id,
                    "line_ids": [
                        Command.create(expense_sudo._prepare_move_lines_vals())
                        for expense_sudo in expenses_sudo
                    ],
                    "partner_bank_id": employee_sudo.primary_bank_account_id.id,
                    "attachment_ids": attachments_data,
                }
            )
        return return_vals

    def _prepare_payments_vals(self):
        self.check_singleton()

        journal = self.journal_id
        payment_channel = self.payment_channel_id
        if not payment_channel:
            raise UserError(
                _(
                    "You need to add a manual payment method on the journal (%s)",
                    journal.name,
                )
            )

        AccountTax = self.env["account.tax"]
        rate = (
            abs(self.total_amount_currency / self.total_amount)
            if self.total_amount
            else 0.0
        )
        base_line = self._prepare_base_line_for_taxes_computation(
            price_unit=self.total_amount_currency,
            quantity=1.0,
            account_id=self._get_base_account(),
            rate=rate,
        )
        base_lines = [base_line]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(
            base_lines,
            self.company_id,
            include_caba_tags=self.payment_mode == "company_account",
        )
        tax_results = AccountTax._prepare_tax_lines(base_lines, self.company_id)

        move_lines = []
        base_move_line = {}
        for base_line, to_update in tax_results["base_lines_to_update"]:
            base_move_line = {
                "name": self._get_move_line_name(),
                "account_id": base_line["account_id"].id,
                "product_id": base_line["product_id"].id,
                "analytic_distribution": base_line["analytic_distribution"],
                "expense_id": self.id,
                "tax_ids": [Command.set(base_line["tax_ids"].ids)],
                "tax_tag_ids": to_update["tax_tag_ids"],
                "amount_currency": to_update["amount_currency"],
                "balance": to_update["balance"],
                "currency_id": base_line["currency_id"].id,
                "partner_id": self.vendor_id.id,
            }
            move_lines.append(base_move_line)

        total_tax_line_balance = 0.0
        for tax_line in tax_results["tax_lines_to_add"]:
            total_tax_line_balance += tax_line["balance"]
            move_lines.append(tax_line)
        base_move_line["balance"] = self.total_amount - total_tax_line_balance

        move_lines.append(
            {
                "name": self._get_move_line_name(),
                "account_id": self._get_expense_account_destination(),
                "balance": -self.total_amount,
                "amount_currency": self.currency_id.round(-self.total_amount_currency),
                "currency_id": self.currency_id.id,
                "partner_id": self.vendor_id.id,
            }
        )
        payment_vals = {
            "date": self.date,
            "memo": self.name,
            "journal_id": journal.id,
            "amount": self.total_amount_currency,
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.vendor_id.id,
            "currency_id": self.currency_id.id,
            "payment_channel_id": payment_channel.id,
            "company_id": self.company_id.id,
        }
        move_vals = {
            **self._prepare_move_vals(),
            "date": self.date or fields.Date.context_today(self),
            "ref": self.name,
            "journal_id": journal.id,
            "partner_id": self.vendor_id.id,
            "currency_id": self.currency_id.id,
            "line_ids": [Command.create(line) for line in move_lines],
            "attachment_ids": [
                Command.create(
                    attachment.copy_data(
                        {
                            "res_model": "account.move",
                            "res_id": False,
                            "raw": attachment.raw,
                        }
                    )[0]
                )
                for attachment in self.attachment_ids
            ],
        }
        return move_vals, payment_vals

    def _prepare_move_vals(self):
        return {
            "name": "/",
            "expense_ids": [Command.set(self.ids)],
        }

    def _prepare_move_lines_vals(self):
        self.check_singleton()
        return {
            "name": self._get_move_line_name(),
            "account_id": self._get_base_account().id,
            "quantity": self.quantity or 1,
            "price_unit": self.price_unit,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "analytic_distribution": self.analytic_distribution,
            "expense_id": self.id,
            "partner_id": False
            if self.payment_mode == "company_account"
            else self.employee_id.sudo().partner_id.id,
            "tax_ids": [Command.set(self.tax_ids.ids)],
        }

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        self.check_singleton()
        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            self,
            **{
                "partner_id": self.vendor_id,
                "special_mode": "total_included",
                "rate": self.currency_rate,
                **kwargs,
            },
        )

    def _get_move_line_name(self):
        self.check_singleton()
        expense_name = self.name.split("\n")[0][:64]
        return _(
            "%(employee_name)s: %(expense_name)s",
            employee_name=self.employee_id.name,
            expense_name=expense_name,
        )

    def _get_base_account(self):
        account = self.account_id
        if account:
            _debug.logic("base_account", by="expense", expense=self, account=account)
            return account

        if self.product_id:
            account = self.product_id.product_tmpl_id._get_product_accounts()["expense"]
            source = "product"  # debuglog
        else:
            account = self.env.company.expense_account_id
            source = "company"  # debuglog

        if account:
            _debug.logic("base_account", by=source, expense=self, account=account)
            return account

        journal = self.journal_id
        if journal.type == "purchase":
            account = journal.default_account_id
            _debug.logic("base_account", by="journal", expense=self, account=account)

        if not account:
            _debug.logic("base_account", by="none", expense=self, journal=journal)
            raise UserError(
                self.env._(
                    "Odoo had a look at your expense, its product, your company and the journal but came back with empty hands.\n"
                    "Give Odoo a hand to find an account by setting up an expense account.\n"
                    "%(expense)s %(expense_name)s.\n",
                    expense=self,
                    expense_name=self.name,
                )
            )
        return account

    def _get_expense_account_destination(self):
        ids = set()
        for expense in self:
            if expense.payment_mode == "company_account":
                account_dest = (
                    expense.payment_channel_id.payment_account_id
                    or expense._get_outstanding_account_id()
                )
            elif not expense.employee_id.sudo().partner_id:
                _debug.logic(
                    "destination_account_no_partner",
                    expense=expense,
                    employee=expense.employee_id,
                )
                raise UserError(
                    self.env._(
                        "No work contact found for the employee %(name)s, please configure one.",
                        name=expense.employee_id.name,
                    )
                )
            else:
                partner = expense.employee_id.sudo().partner_id.with_company(
                    expense.company_id
                )
                account_dest = (
                    partner.property_account_payable_id
                    or partner.parent_id.property_account_payable_id
                )
            ids.add(account_dest.id)

        if not ids:
            return False
        if len(ids) > 1:
            _debug.logic(
                "destination_account_conflict", expenses=self, accounts=len(ids)
            )
            raise UserError(
                self.env._(
                    "The following expenses payment method leads to several accounts payable and this isn't supported:\n%(expenses)s",
                    expenses=self.browse(ids),
                )
            )
        return ids.pop()

    def _get_outstanding_account_id(self):
        account_ref = (
            "account_journal_payment_debit_account_id"
            if self.payment_channel_id.payment_type == "inbound"
            else "account_journal_payment_credit_account_id"
        )
        chart_template = self.with_context(
            allowed_company_ids=self.company_id.root_id.ids
        ).env["account.chart.template"]
        outstanding_account = chart_template.ref(account_ref, raise_if_not_found=False)
        if not outstanding_account:
            bank_prefix = self.company_id.bank_account_code_prefix
            first_account = self.env["account.account"].search(
                [("company_ids", "in", self.company_id.id)], limit=1
            )
            code_digits = len(first_account.code or "") or 6
            chart_template._create_outstanding_accounts(
                self.company_id, bank_prefix, code_digits
            )
            outstanding_account = chart_template.ref(
                account_ref, raise_if_not_found=False
            )
        if not outstanding_account.active:
            raise RedirectWarning(
                message=_(
                    "The account %(name)s (%(code)s) is archived. Activate it to continue",
                    name=outstanding_account.name,
                    code=outstanding_account.code,
                ),
                action=outstanding_account._get_records_action(),
                button_text=_("Go to Account"),
            )
        return outstanding_account

    def _creation_message(self):
        if self.env.context.get("from_split_wizard"):
            return _("Expense created from a split.")
        return super()._creation_message()
