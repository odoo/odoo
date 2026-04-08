# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hourly_cost = fields.Monetary(readonly=False, related='version_id.hourly_cost', inherited=True, groups="hr.group_hr_user")
