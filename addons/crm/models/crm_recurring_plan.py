# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmRecurringPlan(models.Model):
    _name = 'crm.recurring.plan'
    _description = "CRM Recurring revenue plans"
    _order = "sequence"

    name = fields.Char('Plan Name', required=True, translate=True)
    number_of_months = fields.Integer('# Months', required=True)
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer('Sequence', default=10)

    _check_number_of_months = models.Constraint(
        'CHECK(number_of_months >= 0)',
        "The number of month can't be negative.",
    )
