# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AnalyticPack(models.Model):
    _inherit = 'analytic.pack'

    analytic_line_ids = fields.One2many('account.analytic.line', 'pack_id', string="Analytic Lines", domain=[('is_timesheet', '=', False)])
    timesheet_ids = fields.One2many('account.analytic.line', 'pack_id', string="Timesheets", domain=[('is_timesheet', '=', True)])
