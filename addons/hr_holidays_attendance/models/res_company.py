# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    attendance_based = fields.Boolean(default=False, required=True, groups="hr.group_hr_user")
