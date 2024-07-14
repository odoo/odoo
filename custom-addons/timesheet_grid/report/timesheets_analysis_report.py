# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    validated = fields.Boolean("Validated line", group_operator="bool_and", readonly=True)
    is_timesheet = fields.Boolean(string="Timesheet Line", readonly=True)
    is_timer_running = fields.Boolean(compute='_compute_is_timer_running', search='_search_is_timer_running')

    def _compute_is_timer_running(self):
        timer_timesheet_ids = set(self.env['account.analytic.line']._search([('id', 'in', self.ids), ('is_timer_running', '=', True)]))
        for timesheet_analysis in self:
            timesheet_analysis.is_timer_running = timesheet_analysis.id in timer_timesheet_ids

    def _search_is_timer_running(self, operator, value):
        return self.env['account.analytic.line']._search_is_timer_running(operator, value)

    @api.model
    def _select(self):
        return super()._select() + """,
            A.validated AS validated,
            A.project_id IS NOT NULL AS is_timesheet
        """
