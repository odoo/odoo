import logging
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.stock_account.models.constants import (
    COST_METHOD_SELECTION,
    VALUATION_SELECTION,
)

_logger = logging.getLogger(__name__)


_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    account_stock_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Stock Journal",
        check_company=True,
    )

    account_stock_valuation_id = fields.Many2one(
        comodel_name="account.account",
        string="Stock Valuation Account",
        check_company=True,
    )

    account_production_wip_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production WIP Account",
        check_company=True,
    )
    account_production_wip_overhead_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production WIP Overhead Account",
        check_company=True,
    )

    inventory_period = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("daily", "Daily"),
            ("monthly", "Monthly"),
        ],
        default="manual",
        required=True,
    )

    inventory_valuation = fields.Selection(
        selection=VALUATION_SELECTION,
        string="Valuation",
        default="periodic",
    )

    cost_method = fields.Selection(
        selection=COST_METHOD_SELECTION,
        default="standard",
        required=True,
    )

    def action_close_stock_valuation(self, at_date=None, auto_post=False):
        self.check_singleton()
        account_move = self._close_stock_valuation(at_date=at_date, auto_post=auto_post)
        if not account_move:
            raise UserError(_("Everything is correctly closed"))
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Items"),
            "res_model": "account.move",
            "res_id": account_move.id,
            "views": [(False, "form")],
        }

    def _close_stock_valuation(self, at_date=None, auto_post=False):
        _debug.pipeline(
            "valuation_closing_enter",
            company=self.id,
            at_date=at_date,
            auto_post=auto_post,
        )
        self.check_singleton()
        if not self.try_lock_for_update(allow_referencing=True):
            raise UserError(
                _(
                    "An inventory valuation closing is already running for %s.",
                    self.display_name,
                ),
            )
        if at_date and isinstance(at_date, str):
            at_date = fields.Date.from_string(at_date)
        pending = self.env["account.move"].search(
            [
                ("is_stock_valuation_closing", "=", True),
                ("company_id", "=", self.id),
                ("state", "=", "draft"),
            ],
            order="date desc, id desc",
        )
        if reset := pending.filtered("posted_before"):
            _debug.logic(
                "valuation_closing_refused",
                reason="posted_entry_in_draft",
                company=self.id,
                entry=reset[0].id,
            )
            _logger.info(
                "Stock valuation closing for company %s has a previously-posted entry"
                " %s back in draft; not computing another.",
                self.display_name,
                reset[0].name or reset[0].id,
            )
            return reset[0]
        (pending - pending.filtered("posted_before")).unlink()
        last_closing_date = self._get_last_closing_date()
        if (
            at_date
            and last_closing_date
            and at_date < fields.Date.to_date(last_closing_date)
        ):
            raise UserError(
                self.env._(
                    "It exists closing entries after the selected date. Cancel them before generate an entry prior to them"
                )
            )
        with _debug.perf(
            "valuation_closing_build",
            cr=self.env.cr,
            company=self.id,
            at_date=at_date,
        ) as span:
            aml_vals_list = self.with_context(
                allowed_company_ids=self.ids
            )._action_close_stock_valuation(at_date=at_date)
            span.set(aml_lines=len(aml_vals_list))

        if not aml_vals_list:
            return self.env["account.move"]
        if not self.account_stock_journal_id:
            raise UserError(
                self.env._(
                    "Please set the Journal for Inventory Valuation in the settings."
                )
            )
        if not self.account_stock_valuation_id:
            raise UserError(
                self.env._(
                    "Please set the Valuation Account for Inventory Valuation in the settings."
                )
            )

        moves_vals = {
            "journal_id": self.account_stock_journal_id.id,
            "date": at_date or fields.Date.today(),
            "ref": _("Stock Closing"),
            "is_stock_valuation_closing": True,
            "stock_valuation_closing_cutoff": (
                fields.Datetime.to_datetime(at_date)
                if at_date
                else fields.Datetime.now()
            ),
            "line_ids": [Command.create(aml_vals) for aml_vals in aml_vals_list],
        }
        account_move = (
            self.with_context(allowed_company_ids=self.ids)
            .env["account.move"]
            .create(moves_vals)
        )
        if auto_post:
            account_move._post()
        return account_move

    def _get_stock_value(self, accounts_by_product=None, at_date=None):
        self.check_singleton()
        value_by_account: dict = defaultdict(float)
        if not accounts_by_product:
            accounts_by_product = self.with_context(
                prefetch_fields=False
            )._get_accounts_by_product()
        for product, accounts in accounts_by_product.items():
            account = accounts["valuation"]
            product_value = product.with_context(to_date=at_date).total_value
            value_by_account[account] += product_value
        return value_by_account

    def _get_stock_accounting_value(self, accounts_by_product=None, at_date=None):
        self.check_singleton()
        if not accounts_by_product:
            accounts_by_product = self._get_accounts_by_product()
        account_data = defaultdict(float)
        stock_valuation_accounts_ids = {
            accounts["valuation"].id for accounts in accounts_by_product.values()
        }
        stock_valuation_accounts = self.env["account.account"].browse(
            stock_valuation_accounts_ids
        )
        domain = Domain(
            [
                ("account_id", "in", stock_valuation_accounts.ids),
                ("company_id", "=", self.id),
                ("parent_state", "=", "posted"),
            ]
        )
        if at_date:
            domain &= Domain([("date", "<=", at_date)])
        amls_group = self.env["account.move.line"]._read_group(
            domain, ["account_id"], ["balance:sum"]
        )
        for account, balance in amls_group:
            account_data[account] += balance
        return account_data

    def _action_close_stock_valuation(self, at_date=None):
        _debug.pipeline("valuation_closing_build", company=self.id, at_date=at_date)
        aml_vals_list = []
        accounts_by_product = self._get_accounts_by_product()

        vals_list = self._prepare_location_valuation_vals(at_date)
        if vals_list:
            aml_vals_list += vals_list

        vals_list = self._prepare_stock_valuation_account_vals(
            accounts_by_product, at_date, aml_vals_list
        )
        if vals_list:
            aml_vals_list += vals_list

        vals_list = self._prepare_continental_realtime_variation_vals(
            accounts_by_product, at_date, aml_vals_list
        )
        if vals_list:
            aml_vals_list += vals_list
        return aml_vals_list

    @api.model
    def _cron_post_stock_valuation(self):
        _debug.lifecycle("cron_enter", cron="post_stock_valuation")
        today = fields.Date.today()
        periods = ["daily"]
        if today == today + relativedelta(day=31):
            periods.append("monthly")
        domain = Domain(
            [
                ("inventory_period", "in", periods),
                ("inventory_valuation", "!=", "real_time"),
            ]
        )
        companies = self.env["res.company"].search(domain)
        _debug.logic("cron_scope", periods=periods, companies=companies)
        for company in companies:
            try:
                with self.env.cr.savepoint():
                    company._close_stock_valuation(auto_post=True)
            except UserError:
                _logger.warning(
                    "Stock valuation closing skipped for company %s",
                    company.display_name,
                    exc_info=True,
                )

    def _get_domain_valuation_product(self):
        return [("is_storable", "=", True)]

    def _get_accounts_by_product(self, products=None):
        if not products:
            products = (
                self.env["product.product"]
                .with_company(self)
                .search_fetch(
                    self._get_domain_valuation_product(),
                    ["categ_id"],
                )
            )

        accounts_by_product = {}
        for product in products:
            accounts = product._get_product_accounts()
            accounts_by_product[product] = {
                "valuation": accounts["stock_valuation"],
                "variation": accounts["stock_variation"],
                "expense": accounts["expense"],
            }
        return accounts_by_product

    @api.model
    def _get_extra_balance(self, vals_list=None):
        extra_balance = defaultdict(float)
        if not vals_list:
            return extra_balance
        for vals in vals_list:
            extra_balance[vals["account_id"]] += vals["debit"] - vals["credit"]
        return extra_balance

    def _prepare_location_valuation_vals(self, at_date=None, location_domain=False):
        _debug.perf.count("location_valuation_vals", company=self.id, at_date=at_date)
        location_domain = Domain.AND(
            [
                location_domain or [],
                [("valuation_account_id", "!=", False)],
                [("company_id", "=", self.id)],
            ]
        )
        amls_vals_list = []
        valued_location = self.env["stock.location"].search(location_domain)
        last_closing_date = self._get_last_closing_date()
        moves_base_domain = Domain(
            [
                ("product_id.is_storable", "=", True),
                ("product_id.valuation", "=", "periodic"),
            ]
        )
        if last_closing_date:
            moves_base_domain &= Domain([("date", ">", last_closing_date)])
        if at_date:
            moves_base_domain &= Domain([("date", "<=", at_date)])
        into_location_domain = (
            Domain(
                [
                    ("is_out", "=", True),
                    ("company_id", "=", self.id),
                    ("location_dest_id", "in", valued_location.ids),
                ]
            )
            & moves_base_domain
        )
        value_into_location = self.env["stock.move"]._read_group(
            into_location_domain,
            ["location_dest_id", "product_category_id"],
            ["value:sum"],
        )
        out_of_location_domain = (
            Domain(
                [
                    ("is_in", "=", True),
                    ("company_id", "=", self.id),
                    ("location_id", "in", valued_location.ids),
                ]
            )
            & moves_base_domain
        )
        value_out_of_location = self.env["stock.move"]._read_group(
            out_of_location_domain,
            ["location_id", "product_category_id"],
            ["value:sum"],
        )
        account_balance = defaultdict(float)
        for location, category, value in value_into_location:
            stock_valuation_acc = (
                category.property_stock_valuation_account_id
                or self.account_stock_valuation_id
            )
            account_balance[location.valuation_account_id, stock_valuation_acc] += value

        for location, category, value in value_out_of_location:
            stock_valuation_acc = (
                category.property_stock_valuation_account_id
                or self.account_stock_valuation_id
            )
            account_balance[location.valuation_account_id, stock_valuation_acc] -= value

        for (location_account, stock_account), balance in account_balance.items():
            if self.currency_id.is_zero(balance):
                continue
            amls_vals = self._prepare_inventory_aml_vals(
                location_account,
                stock_account,
                balance,
                _(
                    "Closing: Location Reclassification - [%(account)s]",
                    account=location_account.display_name,
                ),
            )
            amls_vals_list += amls_vals
        return amls_vals_list

    def _prepare_stock_valuation_account_vals(
        self, accounts_by_product, at_date=None, extra_aml_vals_list=None
    ):
        amls_vals_list = []
        if not accounts_by_product:
            return amls_vals_list

        extra_balance = self._get_extra_balance(extra_aml_vals_list)

        if "inventory_data" in self.env.context:
            inventory_data = self.env.context.get("inventory_data")
        else:
            inventory_data = self._get_stock_value(accounts_by_product, at_date)
        accounting_data = self._get_stock_accounting_value(accounts_by_product, at_date)

        accounts = inventory_data.keys() | accounting_data.keys()
        for account in accounts:
            account_variation = account.account_stock_variation_id
            if not account_variation:
                account_variation = self.expense_account_id
            if not account_variation:
                continue
            balance = inventory_data.get(account, 0) - accounting_data.get(account, 0)
            balance -= extra_balance.get(account.id, 0)

            if self.currency_id.is_zero(balance):
                continue

            amls_vals = self._prepare_inventory_aml_vals(
                account,
                account_variation,
                balance,
                _(
                    "Closing: Stock Variation Global for company [%(company)s]",
                    company=self.display_name,
                ),
            )
            amls_vals_list += amls_vals

        return amls_vals_list

    def _prepare_continental_realtime_variation_vals(
        self, accounts_by_product, at_date=None, extra_aml_vals_list=None
    ):
        extra_balance = self._get_extra_balance(extra_aml_vals_list)

        reference_date = at_date or fields.Date.today()
        fiscal_year_date_from = self.compute_fiscalyear_dates(reference_date)[
            "date_from"
        ]

        amls_vals_list = []
        accounting_data_today = self._get_stock_accounting_value(
            accounts_by_product, at_date=at_date
        )
        accounting_data_last_period = self._get_stock_accounting_value(
            accounts_by_product, at_date=fiscal_year_date_from
        )

        accounts = accounting_data_today.keys() | accounting_data_last_period.keys()

        for account in accounts:
            variation_acc = account.account_stock_variation_id
            expense_acc = account.account_stock_expense_id

            if not variation_acc or not expense_acc:
                continue

            balance_today = accounting_data_today.get(account, 0) - extra_balance.get(
                account.id, 0
            )
            balance_last_period = accounting_data_last_period.get(account, 0)
            balance_over_period = balance_today - balance_last_period

            current_balance_domain = Domain(
                [
                    ("account_id", "=", variation_acc.id),
                    ("company_id", "=", self.id),
                    ("parent_state", "=", "posted"),
                ]
            )
            if at_date:
                current_balance_domain &= Domain([("date", "<=", at_date)])
            [(existing_balance,)] = self.env["account.move.line"]._read_group(  # noqa: E8507 - one aggregate per company, on its own accounts
                current_balance_domain, aggregates=["balance:sum"]
            )
            balance_over_period += existing_balance

            if self.currency_id.is_zero(balance_over_period):
                continue

            amls_vals = self._prepare_inventory_aml_vals(
                expense_acc,
                variation_acc,
                balance_over_period,
                _("Closing: Stock Variation Over Period"),
            )
            amls_vals_list += amls_vals

        return amls_vals_list

    def _prepare_inventory_aml_vals(
        self, debit_acc, credit_acc, balance, ref, product_id=False
    ):
        if balance < 0:
            credit_acc, debit_acc = debit_acc, credit_acc
            balance = abs(balance)
        return [
            {
                "account_id": credit_acc.id,
                "name": ref,
                "debit": 0,
                "credit": balance,
                "product_id": product_id,
            },
            {
                "account_id": debit_acc.id,
                "name": ref,
                "debit": balance,
                "credit": 0,
                "product_id": product_id,
            },
        ]

    def _get_last_closing_date(self):
        self.check_singleton()
        closing = self.env["account.move"].search(
            [
                ("is_stock_valuation_closing", "=", True),
                ("company_id", "=", self.id),
                ("state", "!=", "cancel"),
            ],
            order="date desc, id desc",
            limit=1,
        )
        if not closing:
            return False
        if closing.stock_valuation_closing_cutoff:
            return closing.stock_valuation_closing_cutoff
        am_state_field = (
            self.env["ir.model.fields"]
            .sudo()
            .search([("model", "=", "account.move"), ("name", "=", "state")], limit=1)
        )
        state_tracking = (
            closing.message_ids.sudo()
            .tracking_value_ids.filtered(lambda t: t.field_id == am_state_field)
            .sorted("id")
        )
        create_date = state_tracking[-1:].create_date
        if create_date and create_date.date() == closing.date:
            return create_date
        return fields.Datetime.to_datetime(closing.date)

    def _set_category_defaults(self, changed_fields=None):
        super()._set_category_defaults(changed_fields)
        IrDefault = self.env["ir.default"].sudo()
        for company in self:
            if changed_fields is None or "inventory_valuation" in changed_fields:
                IrDefault.set(
                    "product.category",
                    "property_valuation",
                    company.inventory_valuation,
                    company_id=company.id,
                )
            if changed_fields is None or "cost_method" in changed_fields:
                IrDefault.set(
                    "product.category",
                    "property_cost_method",
                    company.cost_method,
                    company_id=company.id,
                )
            if changed_fields is None or "account_stock_journal_id" in changed_fields:
                IrDefault.set(
                    "product.category",
                    "property_stock_journal",
                    company.account_stock_journal_id.id,
                    company_id=company.id,
                )
            if changed_fields is None or "account_stock_valuation_id" in changed_fields:
                IrDefault.set(
                    "product.category",
                    "property_stock_valuation_account_id",
                    company.account_stock_valuation_id.id,
                    company_id=company.id,
                )
