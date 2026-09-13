from itertools import zip_longest

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils, float_is_zero, float_round

_debug = DebugLog(__name__)


class AccountReportBudget(models.Model):
    _name = "account.report.budget"
    _description = "Accounting Report Budget"
    _order = "sequence, id"

    sequence = fields.Integer()
    name = fields.Char(required=True)
    item_ids = fields.One2many(
        comodel_name="account.report.budget.item",
        inverse_name="budget_id",
        string="Items",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda x: x.env.company,
        required=True,
    )

    @api.constrains("name")
    def _constrains_name(self):
        for budget in self:
            if not budget.name:
                raise ValidationError(_("Please enter a valid budget name."))

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
        for values in vals_list:
            if name := values.get("name"):
                values["name"] = name.strip()
        return super().create(vals_list)

    @_debug.perf.timed
    def _create_or_update_budget_items(
        self, value_to_set, account_id, rounding, date_from, date_to
    ):
        """Create or update one budget item per month between date_from and date_to, both included.

        :param value_to_set: The value written by the user in the report cell.
        :param account_id: The related account id.
        :param rounding: The rounding for the decimal precision.
        :param date_from: The start date for the budget item creation.
        :param date_to: The end date for the budget item creation.
        """
        self.check_singleton()

        date_from, date_to = (
            fields.Date.to_date(date_from),
            fields.Date.to_date(date_to),
        )
        if date_from != date_utils.start_of(date_from, "month"):
            date_from = date_from.replace(day=1) + relativedelta(months=1)
        existing_budget_items = self.env["account.report.budget.item"].search_fetch(
            [
                ("budget_id", "=", self.id),
                ("account_id", "=", account_id),
                ("date", "<=", date_to),
                ("date", ">=", date_from),
            ],
            ["id", "amount"],
        )
        existing_budget_items_by_date = {
            item.date: item for item in existing_budget_items
        }
        total_amount = sum(existing_budget_items.mapped("amount"))

        value_to_compute = value_to_set - total_amount
        _debug.logic(
            "budget_delta_computed",
            budget=self,
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            existing_items=len(existing_budget_items),
            delta=value_to_compute,
        )
        if float_is_zero(value_to_compute, precision_digits=rounding):
            # In case the computed amount equals 0, we do an early return as
            # it's not necessary to create new budget item
            return

        start_month_dates = [
            date_utils.start_of(date, "month")
            for date in date_utils.date_range(date_from, date_to)
        ]

        # Fill a list with the same amounts for each month
        amounts = [
            float_round(
                value_to_compute / len(start_month_dates),
                precision_digits=rounding,
                rounding_method="DOWN",
            )
        ] * len(start_month_dates)
        # Add the remainder in the last amount
        amounts[-1] += float_round(
            value_to_compute - sum(amounts), precision_digits=rounding
        )

        budget_items_commands = []
        for start_month_date, amount in zip_longest(start_month_dates, amounts):
            existing_budget_item = existing_budget_items_by_date.get(start_month_date)
            if existing_budget_item:
                budget_items_commands.append(
                    Command.update(
                        existing_budget_item.id,
                        {
                            "amount": existing_budget_item.amount + amount,
                        },
                    )
                )
            else:
                budget_items_commands.append(
                    Command.create(
                        {
                            "account_id": account_id,
                            "amount": amount,
                            "date": start_month_date,
                        }
                    )
                )

        _debug.pipeline(
            "budget_item_commands_built",
            budget=self,
            months=len(start_month_dates),
            existing_months=len(existing_budget_items_by_date),
            commands=len(budget_items_commands),
        )
        if budget_items_commands:
            self.item_ids = budget_items_commands
            # Make sure that the model is flushed before continuing the code and fetching these new items
            self.env["account.report.budget.item"].flush_model()

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", budget.name))
            for budget, vals in zip(self, vals_list, strict=False)
        ]

    @_debug.perf.timed
    def copy(self, default=None):
        _debug.lifecycle("copy", records=self)
        new_budgets = super().copy(default)
        for old_budget, new_budget in zip(self, new_budgets, strict=False):
            for item in old_budget.item_ids:
                item.copy(
                    {
                        "budget_id": new_budget.id,
                        "account_id": item.account_id.id,
                        "amount": item.amount,
                        "date": item.date,
                    }
                )

        return new_budgets


class AccountReportBudgetItem(models.Model):
    _name = "account.report.budget.item"
    _description = "Accounting Report Budget Item"

    budget_id = fields.Many2one(
        comodel_name="account.report.budget",
        index=True,
        required=True,
        ondelete="cascade",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        index=True,
        required=True,
        domain="[('account_type', 'in', ('income', 'income_other', 'expense', 'expense_other', 'expense_depreciation', 'expense_direct_cost'))]",
    )
    amount = fields.Float(default=0)
    date = fields.Date(required=True)
