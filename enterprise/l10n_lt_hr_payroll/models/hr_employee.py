# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_lt_working_capacity = fields.Selection([
        ('0_25', 'Between 0-25%'),
        ('30_55', 'Between 30-55%'),
        ('60_100', 'Between 60-100%'),
    ], default='60_100', string="Working Capacity", groups="hr.group_hr_user")
