from itertools import zip_longest
from dateutil.relativedelta import relativedelta

from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils, float_is_zero, float_round


class AccountReportBudget(models.Model):
    _name = 'account.report.budget'
    _description = "Accounting Report Budget"
    _order = 'sequence, id'

    sequence = fields.Integer(string="Sequence")
    name = fields.Char(string="Name", required=True)
    item_ids = fields.One2many(string="Items", comodel_name='account.report.budget.item', inverse_name='budget_id')
    company_id = fields.Many2one(string="Company", comodel_name='res.company', required=True, default=lambda x: x.env.company)

    @api.constrains('name')
    def _contrains_name(self):
        for budget in self:
            if not budget.name:
                raise ValidationError(_("Please enter a valid budget name."))

    @api.model_create_multi
    def create(self, create_values):
        for values in create_values:
            if name := values.get('name'):
                values['name'] = name.strip()
        return super().create(create_values)

    def _create_or_update_budget_items(self, value_to_set, account_id, rounding, date_from, date_to):
        """ This method will create / update several budget items following the number
            of months between date_from(include) and date_to(include).

            :param value_to_set: The value written by the user in the report cell.
            :param account_id: The related account id.
            :param rounding: The rounding for the decimal precision.
            :param date_from: The start date for the budget item creation.
            :param date_to: The end date for the budget item creation.
        """
        self.ensure_one()

        date_from, date_to = fields.Date.to_date(date_from), fields.Date.to_date(date_to)
        if date_from != date_utils.start_of(date_from, 'month'):
            date_from = (date_from.replace(day=1) + relativedelta(months=1))
        existing_budget_items = self.env['account.report.budget.item'].search_fetch([
            ('budget_id', '=', self.id),
            ('account_id', '=', account_id),
            ('date', '<=', date_to),
            ('date', '>=', date_from),
        ], ['id', 'amount'])
        existing_budget_items_by_date = {item.date: item for item in existing_budget_items}
        total_amount = sum(existing_budget_items.mapped('amount'))

        value_to_compute = value_to_set - total_amount
        if float_is_zero(value_to_compute, precision_digits=rounding):
            # In case the computed amount equals 0, we do an early return as
            # it's not necessary to create new budget item
            return

        start_month_dates = [
            date_utils.start_of(date, 'month')
            for date in date_utils.date_range(date_from, date_to)
        ]

        # Fill a list with the same amounts for each month
        amounts = [float_round(value_to_compute / len(start_month_dates), precision_digits=rounding, rounding_method='DOWN')] * len(start_month_dates)
        # Add the remainder in the last amount
        amounts[-1] += float_round(value_to_compute - sum(amounts), precision_digits=rounding)

        budget_items_commands = []
        for start_month_date, amount in zip_longest(start_month_dates, amounts):
            existing_budget_item = existing_budget_items_by_date.get(start_month_date)
            if existing_budget_item:
                budget_items_commands.append(Command.update(existing_budget_item.id, {
                    'amount': existing_budget_item.amount + amount,
                }))
            else:
                budget_items_commands.append(Command.create({
                    'account_id': account_id,
                    'amount': amount,
                    'date': start_month_date,
                }))

        if budget_items_commands:
            self.item_ids = budget_items_commands
            # Make sure that the model is flushed before continuing the code and fetching these new items
            self.env['account.report.budget.item'].flush_model()

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", budget.name)) for budget, vals in zip(self, vals_list)]

    def copy(self, default=None):
        new_budgets = super().copy(default)
        for old_budget, new_budget in zip(self, new_budgets):
            for item in old_budget.item_ids:
                item.copy({
                    'budget_id': new_budget.id,
                    'account_id': item.account_id.id,
                    'amount': item.amount,
                    'date': item.date,
                })

        return new_budgets


class AccountReportBudgetItem(models.Model):
    _name = 'account.report.budget.item'
    _description = "Accounting Report Budget Item"

    budget_id = fields.Many2one(string="Budget", comodel_name='account.report.budget', required=True, ondelete='cascade')
    account_id = fields.Many2one(string="Account", comodel_name='account.account', required=True)
    amount = fields.Float(string="Amount", default=0)
    date = fields.Date(required=True)
