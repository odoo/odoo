# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'
    _description = 'Salary Structure Type'

    l10n_mx_default_schedule_pay = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('10_days', '10 Days'),
        ('14_days', '14 Days'),
        ('bi_weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('bi_monthly', 'Bi-monthly'),
    ], string='MX: Default Scheduled Pay', default='monthly',
        help="Defines the frequency of the wage payment.")
