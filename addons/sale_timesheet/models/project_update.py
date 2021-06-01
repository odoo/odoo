# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import float_utils, format_amount
from odoo.tools.misc import formatLang

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        return {
            **super(ProjectUpdate, self)._get_template_values(project),
            'profitability': self._get_profitability_values(project),
        }

    @api.model
    def _get_profitability_values(self, project):
        if not (self.user_has_groups('project.group_project_manager') and (project.analytic_account_id and project.allow_billable or project.allow_timesheets)):
            return {}
        profitability = project.get_profitability_common()
        start_of_month = fields.Date.context_today(self) + relativedelta(day=1)
        timesheets_this_month = self.env['project.profitability.report'].read_group(
            [('project_id', '=', project.id),
             ('line_date', '>=', start_of_month)],
            ['project_id',
             'timesheet_unit_amount'],
            ['project_id'])
        timesheets_previous_month = self.env['project.profitability.report'].read_group(
            [('project_id', '=', project.id),
             ('line_date', '>=', start_of_month + relativedelta(months=-1, day=1)),
             ('line_date', '<', start_of_month)
             ],
            ['project_id',
             'timesheet_unit_amount'],
            ['project_id'])
        timesheet_unit_amount = timesheets_this_month and timesheets_this_month[0]['timesheet_unit_amount'] or 0.0
        previous_timesheet_unit_amount = timesheets_previous_month and timesheets_previous_month[0]['timesheet_unit_amount'] or 0.0
        return {
            'allow_timesheets': project.allow_timesheets,
            'analytic_account_id': project.analytic_account_id,
            'month': start_of_month.strftime('%B %Y'),
            'previous_month': (start_of_month + relativedelta(months=-1, day=1)).strftime('%B'),
            'is_timesheet_uom_hour': self.env.company._is_timesheet_hour_uom(),
            'timesheet_uom': self.env.company._timesheet_uom_text(),
            'timesheet_unit_amount': formatLang(self.env, project._convert_project_uom_to_timesheet_encode_uom(timesheet_unit_amount), digits=0),
            'previous_timesheet_unit_amount': formatLang(self.env, project._convert_project_uom_to_timesheet_encode_uom(previous_timesheet_unit_amount), digits=0),
            'timesheet_trend': formatLang(self.env,
                                          previous_timesheet_unit_amount > 0 and ((timesheet_unit_amount / previous_timesheet_unit_amount) - 1) * 100 or 0.0,
                                          digits=0),
            'costs': format_amount(self.env, -profitability['costs'], self.env.company.currency_id),
            'revenues': format_amount(self.env, profitability['revenues'], self.env.company.currency_id),
            'margin': profitability['margin'],
            'margin_formatted': format_amount(self.env, profitability['margin'], self.env.company.currency_id),
            'margin_percentage': formatLang(self.env,
                                            not float_utils.float_is_zero(profitability['costs'], precision_digits=2) and -(profitability['margin'] / profitability['costs']) * 100 or 0.0,
                                            digits=0),
            'billing_rate': formatLang(self.env,
                                       not float_utils.float_is_zero(profitability['costs'], precision_digits=2) and -(profitability['revenues'] / profitability['costs']) * 100 or 0.0,
                                       digits=0),
        }
