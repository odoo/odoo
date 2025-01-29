# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hourly_cost = fields.Float(string='Hourly Cost', digits='Hourly Cost',
        groups="hr.group_hr_user", default=0.0, tracking=True)
