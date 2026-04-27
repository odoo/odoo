# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_mx_schedule_pay = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('10_days', '10 Days'),
        ('bi_weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], string="MX: Schedule Pay", default="monthly", index=True)
    l10n_mx_risk_bonus_rate = fields.Float(string="Risk Bonus Rate")
    l10n_mx_christmas_bonus = fields.Float(string="Christmas Bonus")
    l10n_mx_holidays_count = fields.Float(string="Holidays Count", default=12)
    l10n_mx_holiday_bonus_rate = fields.Float(string="Holiday Bonus Rate")
