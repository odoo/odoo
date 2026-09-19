import json
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils, format_date
from odoo.tools.misc import formatLang

_debug = DebugLog(__name__)


def _ellipsis(string, size):
    if len(string) > size:
        return string[0 : size - 3] + "..."
    return string


class AccountAccruedOrdersWizard(models.TransientModel):
    _name = "account.accrued.orders.wizard"
    _description = "Accrued Orders Wizard"
    _check_company_auto = True

    def _default_date(self):
        return date_utils.get_month(fields.Date.context_today(self))[0] - relativedelta(
            days=1
        )

    res_model = fields.Char(
        compute="_compute_selection",
        precompute=True,
        store=True,
        readonly=True,
    )
    res_ids = fields.Json(
        compute="_compute_selection",
        precompute=True,
        store=True,
        readonly=True,
    )
    is_purchase = fields.Boolean(
        compute="_compute_is_purchase",
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        precompute=True,
        store=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('type', '=', 'general')]",
        check_company=True,
    )
    date = fields.Date(
        default=_default_date,
        required=True,
    )
    reversal_date = fields.Date(
        compute="_compute_reversal_date",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    amount = fields.Monetary(
        help="Specify an arbitrary value that will be accrued on a \
        default account for the entire order, regardless of the products on the different lines."
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
        help="Utility field to express amount currency",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Accrual Account",
        required=True,
        domain="[('account_type', '=', 'liability_current' if is_purchase else 'asset_current')]",
        check_company=True,
    )
    preview_data = fields.Text(compute="_compute_preview_data")
    display_amount = fields.Boolean(compute="_compute_display_amount")

    def _compute_selection(self):
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        for record in self:
            record.res_model = active_model
            record.res_ids = list(active_ids)

    @api.depends("res_model")
    def _compute_is_purchase(self):
        for record in self:
            record.is_purchase = (record.res_model or "").startswith("purchase.order")

    @api.depends("res_model", "res_ids")
    def _compute_company_id(self):
        for record in self:
            orders = record._get_selected_records()
            record.company_id = orders[:1].company_id if orders else self.env.company

    def _get_selected_records(self):
        self.check_singleton()
        if not self.res_model or not self.res_ids:
            return None
        return self.env[self.res_model].browse(self.res_ids)

    @api.depends("date", "amount", "preview_data", "res_ids")
    def _compute_display_amount(self):
        for record in self:
            single_order = len(record.res_ids or []) == 1
            groups_vals = json.loads(record.preview_data).get("groups_vals") or [{}]
            lines = groups_vals[0].get("items_vals", [])
            record.display_amount = record.amount or (single_order and not lines)

    @api.depends("date")
    def _compute_reversal_date(self):
        for record in self:
            if record.date and (
                not record.reversal_date or record.reversal_date <= record.date
            ):
                record.reversal_date = record.date + relativedelta(days=1)
            else:
                record.reversal_date = record.reversal_date

    @api.depends("company_id")
    def _compute_journal_id(self):
        Journal = self.env["account.journal"]
        journals = Journal.search(
            [*Journal._check_company_domain(self.company_id), ("type", "=", "general")]
        )
        for record in self:
            record.journal_id = journals.filtered_domain(
                Journal._check_company_domain(record.company_id)
            )[:1]

    @api.depends("date", "journal_id", "account_id", "amount", "res_model", "res_ids")
    @_debug.perf.timed
    def _compute_preview_data(self):
        for record in self:
            preview_vals = [
                self.env["account.move"]._move_dict_to_preview_vals(
                    record._prepare_accrual_move_data()[0],
                    record.company_id.currency_id,
                )
            ]
            preview_columns = [
                {"field": "account_id", "label": _("Account")},
                {"field": "name", "label": _("Label")},
                {
                    "field": "debit",
                    "label": _("Debit"),
                    "class": "text-end text-nowrap",
                },
                {
                    "field": "credit",
                    "label": _("Credit"),
                    "class": "text-end text-nowrap",
                },
            ]
            record.preview_data = json.dumps(
                {
                    "groups_vals": preview_vals,
                    "options": {
                        "columns": preview_columns,
                    },
                }
            )

    def _get_computed_account(self, order, product, is_purchase):
        accounts = product.with_company(
            order.company_id
        ).product_tmpl_id._get_product_accounts(fiscal_pos=order.fiscal_position_id)
        if is_purchase:
            return accounts["expense"]
        else:
            return accounts["income"]

    def _prepare_aml_vals(
        self,
        order,
        balance,
        amount_currency,
        account_id,
        is_purchase,
        label="",
        analytic_distribution=None,
    ):
        if not is_purchase:
            balance *= -1
            amount_currency *= -1
        values = {
            "name": label,
            "debit": balance if balance > 0 else 0.0,
            "credit": balance * -1 if balance < 0 else 0.0,
            "account_id": account_id,
        }
        if analytic_distribution:
            values["analytic_distribution"] = analytic_distribution
        if len(order) == 1 and self.company_id.currency_id != order.currency_id:
            values["amount_currency"] = amount_currency
            values["currency_id"] = order.currency_id.id
        return values

    def _get_accrual_orders_and_lines(self):
        selected = self._get_selected_records()
        if selected is None:
            _debug.logic("accrual_orders_rejected", accrual=self, reason="no_selection")
            raise UserError(_("Select the orders to accrue first."))
        selected = selected.with_company(self.company_id)
        if self.res_model in ("purchase.order.line", "sale.order.line"):
            lines = selected
            orders = lines.order_id
        else:
            orders = selected
            lines = orders.line_ids.filtered(lambda x: x.product_id)
        is_purchase = orders._name == "purchase.order"

        if orders.filtered(lambda o: o.company_id != self.company_id):
            _debug.logic(
                "accrual_orders_rejected", accrual=self, reason="multi_company"
            )
            raise UserError(
                _("Entries can only be created for a single company at a time.")
            )
        if len(orders.currency_id) > 1:
            _debug.logic(
                "accrual_orders_rejected", accrual=self, reason="multi_currency"
            )
            raise UserError(
                _("Cannot create an accrual entry with orders in different currencies.")
            )
        return orders, lines, is_purchase

    def _prepare_manual_accrual_aml_vals(self, order, order_line, is_purchase):
        account = self._get_computed_account(order, order_line.product_id, is_purchase)
        return self._prepare_aml_vals(
            order,
            self.amount,
            0,
            account.id,
            is_purchase,
            label=_("Manual entry"),
            analytic_distribution=order_line.analytic_distribution or {},
        )

    def _get_accrual_order_lines(self, order, lines):
        accrual_entry_date = self.env.context.get("accrual_entry_date")
        accrual_entry_date = (
            fields.Date.from_string(accrual_entry_date)
            if accrual_entry_date
            else self.date
        )
        return lines.with_context(
            accrual_entry_date=accrual_entry_date,
            uom_reconcile_strict=True,
        ).filtered(
            lambda l, order=order: (
                not l.display_type
                and not l.is_downpayment
                and l.id in order.line_ids.ids
                and fields.Float.compare(
                    l.amount_to_invoice_at_date,
                    0,
                    precision_rounding=l.product_uom_id.rounding,
                )
                != 0
            )
        )

    @_debug.perf.timed
    def _get_purchase_accrual_line_amounts(self, order, order_line):
        product = order_line.product_id
        _expense_account, stock_variation_account = (
            self._get_product_expense_and_stock_var_accounts(product)
        )
        account = stock_variation_account or self._get_computed_account(
            order, product, True
        )
        if any(tax.price_include for tax in order_line.tax_ids):
            qty_to_invoice = (
                order_line.qty_transferred_at_date - order_line.qty_invoiced_at_date
            )
            price_subtotal = order_line.tax_ids.compute_all(
                order_line.price_unit,
                currency=order_line.order_id.currency_id,
                quantity=qty_to_invoice,
                product=order_line.product_id,
                partner=order_line.order_id.partner_id,
            )["total_excluded"]
        else:
            price_subtotal = order_line.amount_to_invoice_at_date
        amount_currency = order_line.currency_id.round(price_subtotal)
        amount = order.currency_id._convert(
            amount_currency,
            self.company_id.currency_id,
            self.company_id,
        )
        label = _(
            "%(order)s - %(order_line)s; %(quantity_billed)s Billed, %(quantity_received)s Received at %(unit_price)s each",
            order=order.name,
            order_line=_ellipsis(order_line.name, 20),
            quantity_billed=order_line.qty_invoiced_at_date,
            quantity_received=order_line.qty_transferred_at_date,
            unit_price=formatLang(
                self.env,
                order_line.price_unit,
                currency_obj=order.currency_id,
            ),
        )
        return amount, amount_currency, account, label

    @_debug.perf.timed
    def _get_sale_accrual_line_amounts(
        self, order, order_line, amounts_by_perpetual_account
    ):
        product = order_line.product_id
        expense_account, stock_variation_account = (
            self._get_product_expense_and_stock_var_accounts(product)
        )
        account = self._get_computed_account(order, product, False)
        amount_currency = order_line.amount_to_invoice_at_date
        amount = order.currency_id._convert(
            amount_currency,
            self.company_id.currency_id,
            self.company_id,
        )
        label = _(
            "%(order)s - %(order_line)s; %(quantity_invoiced)s Invoiced, %(quantity_delivered)s Delivered at %(unit_price)s each",
            order=order.name,
            order_line=_ellipsis(order_line.name, 20),
            quantity_invoiced=order_line.qty_invoiced_at_date,
            quantity_delivered=order_line.qty_transferred_at_date,
            unit_price=formatLang(
                self.env,
                order_line.price_unit,
                currency_obj=order.currency_id,
            ),
        )
        if expense_account and stock_variation_account:
            label += " (*)"
            amounts_by_perpetual_account[expense_account, stock_variation_account] += (
                amount
            )
        return amount, amount_currency, account, label

    def _prepare_order_accrual_aml_vals(
        self, order, lines, is_purchase, amounts_by_perpetual_account
    ):
        values = []
        total = 0.0
        for order_line in self._get_accrual_order_lines(order, lines):
            if is_purchase:
                amount, amount_currency, account, label = (
                    self._get_purchase_accrual_line_amounts(order, order_line)
                )
            else:
                amount, amount_currency, account, label = (
                    self._get_sale_accrual_line_amounts(
                        order, order_line, amounts_by_perpetual_account
                    )
                )
            values.append(
                self._prepare_aml_vals(
                    order,
                    amount,
                    amount_currency,
                    account.id,
                    is_purchase,
                    label=label,
                    analytic_distribution=order_line.analytic_distribution or {},
                )
            )
            total += amount
        return values, total

    def _get_accrual_analytic_distribution(self, orders):
        analytic_distribution = {}
        total = sum(order.amount_total for order in orders)
        for line in orders.line_ids if total else ():
            if not line.analytic_distribution:
                continue
            ratio = line.price_total / total
            for account_id, distribution in line.analytic_distribution.items():
                analytic_distribution[account_id] = (
                    analytic_distribution.get(account_id, 0) + distribution * ratio
                )
        return analytic_distribution

    def _prepare_perpetual_valuation_aml_vals(
        self, orders, is_purchase, amounts_by_perpetual_account
    ):
        values = []
        for (
            expense_account,
            stock_variation_account,
        ), amount in amounts_by_perpetual_account.items():
            if amount == 0:
                continue
            if amount > 0:
                label = _("(*) Goods Delivered not Invoiced (perpetual valuation)")
            else:
                label = _("(*) Goods Invoiced not Delivered (perpetual valuation)")
            values.append(
                self._prepare_aml_vals(
                    orders,
                    amount,
                    0.0,
                    stock_variation_account.id,
                    is_purchase,
                    label=label,
                )
            )
            values.append(
                self._prepare_aml_vals(
                    orders, -amount, 0.0, expense_account.id, is_purchase, label=label
                )
            )
        _debug.pipeline(
            "perpetual_valuation_lines_built",
            accrual=self,
            account_pairs=len(amounts_by_perpetual_account),
            lines=len(values),
        )
        return values

    @_debug.perf.timed
    def _prepare_accrual_move_data(self):
        self.check_singleton()
        orders, lines, is_purchase = self._get_accrual_orders_and_lines()
        move_lines = []
        orders_with_entries = orders.browse()
        total_balance = 0.0
        amounts_by_perpetual_account = defaultdict(float)

        if _debug.logic.enabled:
            _debug.logic(
                "accrual_mode_chosen",
                accrual=self,
                is_purchase=is_purchase,
                orders=len(orders),
                lines=len(lines),
                manual_amount=len(orders) == 1 and bool(self.amount),
            )
        for order, product_lines in lines.grouped("order_id").items():
            if len(orders) == 1 and product_lines and self.amount and order.line_ids:
                total_balance = self.amount
                move_lines.append(
                    Command.create(
                        self._prepare_manual_accrual_aml_vals(
                            order, product_lines[0], is_purchase
                        )
                    )
                )
                orders_with_entries |= order
            else:
                order_vals, order_balance = self._prepare_order_accrual_aml_vals(
                    order, lines, is_purchase, amounts_by_perpetual_account
                )
                if order_vals:
                    move_lines += [Command.create(vals) for vals in order_vals]
                    total_balance += order_balance
                    orders_with_entries |= order

        _debug.pipeline(
            "accrual_order_lines_built",
            accrual=self,
            orders_with_entries=orders_with_entries,
            move_lines=len(move_lines),
            total_balance=total_balance,
            perpetual_account_pairs=len(amounts_by_perpetual_account),
        )
        if not self.company_id.currency_id.is_zero(total_balance):
            move_lines.append(
                Command.create(
                    self._prepare_aml_vals(
                        orders,
                        -total_balance,
                        0.0,
                        self.account_id.id,
                        is_purchase,
                        label=_("Accrued total"),
                        analytic_distribution=self._get_accrual_analytic_distribution(
                            orders
                        ),
                    )
                )
            )

        move_lines += [
            Command.create(vals)
            for vals in self._prepare_perpetual_valuation_aml_vals(
                orders, is_purchase, amounts_by_perpetual_account
            )
        ]

        _debug.pipeline(
            "accrual_move_lines_completed",
            accrual=self,
            move_lines=len(move_lines),
        )
        move_type = _("Expense") if is_purchase else _("Revenue")
        move_vals = {
            "ref": _(
                "Accrued %(entry_type)s entry as of %(date)s",
                entry_type=move_type,
                date=format_date(self.env, self.date),
            ),
            "name": "/",
            "journal_id": self.journal_id.id,
            "date": self.date,
            "line_ids": move_lines,
            "currency_id": orders.currency_id.id or self.company_id.currency_id.id,
        }
        return move_vals, orders_with_entries

    def _get_accrual_message_body(self, move, reverse_move):
        self.check_singleton()
        return _(
            "Accrual entry created on %(date)s: %(accrual_entry)s.\
                And its reverse entry: %(reverse_entry)s.",
            date=self.date,
            accrual_entry=move._get_html_link(),
            reverse_entry=reverse_move._get_html_link(),
        )

    def create_entries(self):
        self.check_singleton()

        if self.reversal_date <= self.date:
            raise UserError(_("Reversal date must be posterior to date."))
        move_vals, orders_with_entries = self._prepare_accrual_move_data()
        _debug.pipeline(
            "reversal",
            accrual=self,
            count=len(move_vals.get("line_ids", [])),
            orders_with_entries=orders_with_entries,
            reversal_date=self.reversal_date,
        )
        move = self.env["account.move"].create(move_vals)
        move._post()
        reverse_move = move._reverse_moves(
            default_values_list=[
                {
                    "ref": _("Reversal of: %s", move.ref),
                    "name": "/",
                    "date": self.reversal_date,
                }
            ]
        )
        reverse_move._post()
        for order in orders_with_entries:
            order.message_post(body=self._get_accrual_message_body(move, reverse_move))
        return {
            "name": _("Accrual Moves"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", (move | reverse_move).ids)],
        }

    @api.model
    def _get_product_expense_and_stock_var_accounts(self, product):
        return (False, False)
