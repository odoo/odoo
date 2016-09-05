# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    timesheet_range = fields.Selection([('week', 'Week'), ('month', 'Month')],
            default='week', string='Timesheet range', help="Periodicity on which you validate your timesheets.")
