from collections import defaultdict

from odoo import fields, models
from odoo.fields import Domain
from odoo.tools.cache import TransactionMemo
from odoo.tools.safe_eval import safe_eval

VALUATION_DATA = TransactionMemo(
    "stock_account.stock_valuation_report.data",
    invalidated_by=(
        "account.move",
        "account.move.line",
        "product.product",
        "stock.location",
        "stock.move",
        "stock.move.line",
        "stock.quant",
    ),
)


class StockValuationReport(models.AbstractModel):
    _name = "stock_account.stock.valuation.report"
    _description = "Stock Valuation"

    def _get_report_data(self, date=False, product_category=False):
        company = self.env.company
        if isinstance(date, str):
            date = fields.Date.from_string(date)
        if date == fields.Date.context_today(self):
            date = False
        valued_product_context = (
            self.env["product.product"]
            .sudo()
            .with_company(company)
            ._with_valuation_context()
        )
        if date:
            valued_product_context = valued_product_context.with_context(
                at_date=date, to_date=date
            )
        valued_products = valued_product_context.search(
            [
                ("is_storable", "=", True),
                "|",
                ("qty_available", "!=", 0),
                ("lot_valuated", "=", True),
            ]
        )
        accounts_by_product = company._get_accounts_by_product(products=valued_products)
        if not date:
            inventory_data = company._get_stock_value(accounts_by_product)
            accounting_data = company._get_stock_accounting_value(accounts_by_product)
        else:
            inventory_data = company._get_stock_value(accounts_by_product, at_date=date)
            accounting_data = company._get_stock_accounting_value(
                accounts_by_product, at_date=date
            )

        accounts = inventory_data.keys() | accounting_data.keys()
        account_ids = {acc.id for acc in accounts}

        initial_balance = {
            "label": self.env._("Initial Balance"),
            "value": 0,
            "lines_by_account_id": defaultdict(
                lambda: {
                    "value": 0,
                }
            ),
        }
        ending_stock = {
            "label": self.env._("Ending Stock"),
            "value": 0,
            "lines_by_account_id": defaultdict(
                lambda: {
                    "value": 0,
                }
            ),
        }

        for account in accounts:
            opening_balance = accounting_data.get(account, 0)
            ending_balance = inventory_data.get(account, 0)
            account_ids.add(account.id)
            if opening_balance:
                initial_balance["value"] += opening_balance
                initial_balance["lines_by_account_id"][account.id]["value"] += (
                    opening_balance
                )
            if ending_balance:
                ending_stock["value"] += ending_balance
                ending_stock["lines_by_account_id"][account.id]["value"] += (
                    ending_balance
                )

        stock_valuation_account_vals = company.with_context(
            inventory_data=inventory_data
        )._prepare_stock_valuation_account_vals(
            accounts_by_product, date, company._prepare_location_valuation_vals(date)
        )

        report_data = {
            "company_id": company.id,
            "currency_id": company.currency_id.id,
            "ending_stock": ending_stock,
            "initial_balance": initial_balance,
        }

        if self._is_inventory_loss_included():
            location_valuation_vals = company._prepare_location_valuation_vals(
                date,
                location_domain=[("usage", "=", "inventory")],
            )
            inventory_loss = {
                "label": self.env._("Inventory Loss"),
                "value": 0,
            }
            lines_by_account_id = defaultdict(
                lambda: {
                    "debit": 0,
                    "credit": 0,
                }
            )
            for vals in location_valuation_vals:
                account_ids.add(vals["account_id"])
                inventory_loss["value"] -= vals["debit"]
                lines_by_account_id[vals["account_id"]]["debit"] += vals["debit"]
                lines_by_account_id[vals["account_id"]]["credit"] += vals["credit"]
            inventory_loss["lines"] = [
                {
                    "account_id": account_id,
                    "debit": vals["debit"],
                    "credit": vals["credit"],
                }
                for (account_id, vals) in lines_by_account_id.items()
            ]
            report_data["inventory_loss"] = inventory_loss

        stock_variation = {
            "label": self.env._("Stock Variation"),
            "value": 0,
        }
        lines_by_account_id = defaultdict(
            lambda: {
                "debit": 0,
                "credit": 0,
                "lines": [],
            }
        )
        for vals in stock_valuation_account_vals:
            account_ids.add(vals["account_id"])
            stock_variation["value"] += vals["debit"]
            lines_by_account_id[vals["account_id"]]["debit"] += vals["debit"]
            lines_by_account_id[vals["account_id"]]["credit"] += vals["credit"]
        stock_variation["lines"] = [
            {
                "account_id": account_id,
                "debit": vals["debit"],
                "credit": vals["credit"],
            }
            for (account_id, vals) in lines_by_account_id.items()
        ]

        accounts_read_data = self.env["account.account"].search_read(
            [("id", "in", account_ids)], ["id", "name", "code", "display_name"]
        )
        report_data.update(
            accounts_by_id={
                acc_data["id"]: acc_data for acc_data in accounts_read_data
            },
            stock_variation=stock_variation,
        )
        return report_data

    def _is_inventory_loss_included(self):
        return bool(
            self.env["stock.location"].search_count(
                [
                    ("usage", "=", "inventory"),
                    ("valuation_account_id", "!=", False),
                ],
                limit=1,
            )
        )


class StockValuationReportHandler(models.AbstractModel):
    _name = "stock_account.stock.valuation.report.handler"
    _inherit = ["report.formula.custom.handler"]
    _description = "Stock Valuation Report Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        options["buttons"].append(
            {
                "name": self.env._("Generate Entry"),
                "sequence": 5,
                "action": "action_generate_entry",
                "always_show": True,
            }
        )

    def _valuation_date(self, options):
        date = fields.Date.from_string(options["date"]["date_to"])
        return False if date >= fields.Date.context_today(self) else date

    def _valuation_data(self, options):
        date = self._valuation_date(options)
        memo = VALUATION_DATA(self.env)
        key = (self.env.company.id, date)
        if key not in memo:
            memo[key] = (
                self.env["stock_account.stock.valuation.report"]
                .with_context(allowed_company_ids=self.env.company.ids)
                ._get_report_data(date=date)
            )
        return memo[key]

    def _section_result(self, section, options, current_groupby):
        if current_groupby not in (None, "account_id", "account_code"):
            raise NotImplementedError(
                f"the stock valuation report groups by account only, not {current_groupby}"
            )
        data = self._valuation_data(options).get(section)
        if not data:
            return [] if current_groupby else {"value": 0, "debit": 0, "credit": 0}
        if "lines_by_account_id" in data:
            by_account = {
                int(account_id): {"value": line["value"], "debit": 0, "credit": 0}
                for account_id, line in data["lines_by_account_id"].items()
            }
        else:
            by_account = {
                line["account_id"]: {
                    "value": 0,
                    "debit": line["debit"],
                    "credit": line["credit"],
                }
                for line in data["lines"]
            }
        if current_groupby == "account_code":
            by_code = defaultdict(lambda: {"value": 0, "debit": 0, "credit": 0})
            accounts = self.env["account.account"].browse(by_account)
            for account in accounts:
                totals = by_code[account.code]
                for key, amount in by_account[account.id].items():
                    totals[key] += amount
            return list(by_code.items())
        if current_groupby:
            return list(by_account.items())
        return {"value": data["value"], "debit": 0, "credit": 0}

    def _report_custom_engine_stock_valuation_initial_balance(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._section_result("initial_balance", options, current_groupby)

    def _report_custom_engine_stock_valuation_inventory_loss(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._section_result("inventory_loss", options, current_groupby)

    def _report_custom_engine_stock_valuation_stock_variation(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._section_result("stock_variation", options, current_groupby)

    def _report_custom_engine_stock_valuation_ending_stock(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        return self._section_result("ending_stock", options, current_groupby)

    def action_generate_entry(self, options):
        date = self._valuation_date(options)
        company = self.env.company
        company.check_singleton()
        account_move = company._close_stock_valuation(at_date=date or None)
        if not account_move:
            # the button answers "nothing to close" as a notice, not an error:
            # a report's actions run on any company, a closed one included
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": self.env._("Everything is correctly closed"),
                    "type": "info",
                    "sticky": False,
                },
            }
        return company._stock_valuation_move_action(account_move)

    def execute_action(self, options, params=None):
        report = self.env["report.formula"].browse(options["report_id"])
        action = report.execute_action(options, params)
        line = self._clicked_report_line(report, params)
        if not line:
            return action
        return self._scope_section_action(action, line.code, options)

    def _clicked_report_line(self, report, params):
        line_id = (params or {}).get("id")
        if not isinstance(line_id, str):
            return self.env["report.formula.line"]
        model, record_id = report._get_model_info_from_id(line_id)
        if model != "report.formula.line":
            return self.env["report.formula.line"]
        return self.env["report.formula.line"].browse(record_id)

    def _scope_section_action(self, action, code, options):
        date = self._valuation_date(options)
        if code == "SV_INITIAL":
            data = self._valuation_data(options)["initial_balance"]
            domain = Domain(self._action_domain(action))
            account_ids = [int(a) for a in data["lines_by_account_id"]]
            if account_ids:
                domain &= Domain("account_id", "in", account_ids)
            if date:
                domain &= Domain("date", "<=", fields.Date.to_string(date))
            action["domain"] = list(domain)
            action["context"] = {
                **self._action_context(action),
                "search_default_group_by_account": 1,
                "search_default_groupby_date": "month",
            }
        elif code == "SV_ENDING":
            if date:
                action["context"] = {
                    **self._action_context(action),
                    "to_date": fields.Date.to_string(date),
                }
        elif code in self._section_move_usages():
            usage, name = self._section_move_usages()[code]
            domain = [
                "|",
                ("location_id.usage", "=", usage),
                ("location_dest_id.usage", "=", usage),
            ]
            if date:
                domain = ["&", ("date", "<=", fields.Date.to_string(date)), *domain]
            action.update(name=name, domain=domain)
        return action

    def _action_domain(self, action):
        domain = action.get("domain") or []
        if isinstance(domain, str):
            domain = safe_eval(domain, {"uid": self.env.uid})
        return domain

    def _action_context(self, action):
        context = action.get("context") or {}
        if isinstance(context, str):
            context = self.env["ir.actions.actions"]._eval_action_context(context)
        return context

    def _section_move_usages(self):
        return {"SV_LOSS": ("inventory", self.env._("Inventory Loss"))}
