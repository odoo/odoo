# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import float_utils, format_amount, formatLang, format_date, DEFAULT_SERVER_DATE_FORMAT

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
        costs_revenues = project.analytic_account_id and project.allow_billable
        timesheets = project.allow_timesheets and self.user_has_groups('hr_timesheet.group_hr_timesheet_user')
        if not (self.user_has_groups('project.group_project_manager') and (costs_revenues or timesheets)):
            return {}
        this_month = fields.Date.context_today(self) + relativedelta(day=1)
        previous_month = this_month + relativedelta(months=-1, day=1)
        result = {
            'allow_timesheets': timesheets,
            'allow_costs_and_revenues': costs_revenues,
            'analytic_account_id': project.analytic_account_id,
            'month': format_date(self.env, this_month, date_format='LLLL y'),
            'previous_month': format_date(self.env, previous_month, date_format='LLLL'),
            'is_timesheet_uom_hour': self.env.company._is_timesheet_hour_uom(),
            'timesheet_uom': self.env.company._timesheet_uom_text(),
            'timesheet_unit_amount': '', 'previous_timesheet_unit_amount': '',
            'timesheet_trend': '', 'costs': '', 'revenues': '', 'margin': '',
            'margin_formatted': '', 'margin_percentage': '', 'billing_rate': '',
        }
        if timesheets:
            timesheets_per_month = self.env['account.analytic.line'].read_group(
                [('project_id', '=', project.id),
                 ('date', '>=', previous_month)],
                ['date', 'unit_amount'],
                ['date:month'])
            timesheet_unit_amount = {ts['__range']['date']['from']: ts['unit_amount'] for ts in timesheets_per_month}
            this_amount = timesheet_unit_amount.get(this_month.replace(day=1).strftime(DEFAULT_SERVER_DATE_FORMAT), 0.0)
            previous_amount = timesheet_unit_amount.get(previous_month.replace(day=1).strftime(DEFAULT_SERVER_DATE_FORMAT), 0.0)
            result.update({
                'timesheet_unit_amount': formatLang(self.env, project._convert_project_uom_to_timesheet_encode_uom(this_amount), digits=0),
                'previous_timesheet_unit_amount': formatLang(self.env, project._convert_project_uom_to_timesheet_encode_uom(previous_amount), digits=0),
                'timesheet_trend': formatLang(self.env, previous_amount > 0 and ((this_amount / previous_amount) - 1) * 100 or 0.0, digits=0),
            })
        if costs_revenues:
            profitability = project._get_profitability_common(costs_revenues=True, timesheets=False)
            result.update({
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
            })
        return result
