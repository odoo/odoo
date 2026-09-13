from odoo import fields, models


class CrmRecurringPlan(models.Model):
    _name = "crm.recurring.plan"
    _description = "CRM Recurring revenue plans"
    _order = "sequence"

    name = fields.Char(
        string="Plan Name",
        translate=True,
        required=True,
    )
    number_of_months = fields.Integer(
        string="# Months",
        required=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _check_number_of_months = models.Constraint(
        "CHECK(number_of_months >= 0)",
        "The number of month can't be negative.",
    )
