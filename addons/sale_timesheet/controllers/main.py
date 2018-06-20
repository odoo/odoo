# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.osv import expression

from odoo.tools import float_round


class SaleTimesheetController(http.Controller):

    @http.route('/timesheet/plan', type='json', auth="user")
    def plan(self, domain):
        domain = expression.AND([domain, [('project_id', '!=', False)]])  # force timesheet and not AAL
        values = self._prepare_plan_values(domain)
        view = request.env.ref('sale_timesheet.timesheet_plan')
        return {
            'html_content': view.render(values)
        }

    def _prepare_plan_values(self, domain):

        timesheet_lines = request.env['account.analytic.line'].search(domain)
        currency = request.env.user.company_id.currency_id

        values = {
            'currency': currency,
            'timesheet_lines': timesheet_lines,
            'domain': domain,
        }
        hour_rounding = request.env.ref('product.product_uom_hour').rounding
        billable_types = ['non_billable', 'non_billable_project', 'billable_time', 'billable_fixed']

        # -- Stat Buttons
        values['stat_buttons'] = self._plan_get_stat_button(timesheet_lines)

        # -- Dashboard (per billable type)
        dashboard_values = {
            'hours': dict.fromkeys(billable_types + ['total'], 0.0),
            'rates': dict.fromkeys(billable_types + ['total'], 0.0),
            'money_amount': {
                'invoiced': 0.0,
                'to_invoiced': 0.0,
                'cost': 0.0,
                'total': 0.0,
            }
        }
        dashboard_domain = domain + [('timesheet_invoice_type', '!=', False)]  # force billable type
        dashboard_data = request.env['account.analytic.line'].read_group(dashboard_domain, ['unit_amount', 'timesheet_revenue', 'timesheet_invoice_type'], ['timesheet_invoice_type'])

        dashboard_total_hours = sum([data['unit_amount'] for data in dashboard_data])
        for data in dashboard_data:
            billable_type = data['timesheet_invoice_type']
            # hours
            dashboard_values['hours'][billable_type] = float_round(data.get('unit_amount'), precision_rounding=hour_rounding)
            dashboard_values['hours']['total'] += float_round(data.get('unit_amount'), precision_rounding=hour_rounding)
            # rates
            dashboard_values['rates'][billable_type] = dashboard_total_hours and round(data.get('unit_amount') / dashboard_total_hours * 100, 2) or 0
            dashboard_values['rates']['total'] += dashboard_total_hours  and round(data.get('unit_amount') / dashboard_total_hours * 100, 2) or 0

        # money_amount
        so_lines = values['timesheet_lines'].mapped('so_line')
        invoice_lines = so_lines.mapped('invoice_lines')
        dashboard_values['money_amount']['invoiced'] = sum([inv_line.currency_id.with_context(date=inv_line.invoice_id.date_invoice).compute(inv_line.price_unit * inv_line.quantity, currency) for inv_line in invoice_lines.filtered(lambda line: line.invoice_id.state in ['open', 'paid'])])
        dashboard_values['money_amount']['to_invoice'] = sum([sol.currency_id.compute(sol.price_unit * (1 - (sol.discount or 0.0) / 100.0) * sol.qty_to_invoice, currency) for sol in so_lines]) + sum([i.currency_id.with_context(date=i.invoice_id.date_invoice).compute(i.price_unit * i.quantity, currency) for i in invoice_lines.filtered(lambda line: line.invoice_id.state == 'draft')])
        dashboard_values['money_amount']['cost'] = sum(values['timesheet_lines'].mapped('amount'))
        dashboard_values['money_amount']['total'] = sum([dashboard_values['money_amount'][item] for item in dashboard_values['money_amount'].keys()])

        values['dashboard'] = dashboard_values

        # -- Time Repartition (per employee)
        repartition_domain = domain + [('employee_id', '!=', False), ('timesheet_invoice_type', '!=', False)]  # force billable type
        repartition_data = request.env['account.analytic.line'].read_group(repartition_domain, ['employee_id', 'timesheet_invoice_type', 'unit_amount'], ['employee_id', 'timesheet_invoice_type'], lazy=False)

        # set repartition per type per employee
        repartition_employee = {}
        for data in repartition_data:
            employee_id = data['employee_id'][0]
            repartition_employee.setdefault(employee_id, dict(
                employee_id=data['employee_id'][0],
                employee_name=data['employee_id'][1],
                non_billable_project=0.0,
                non_billable=0.0,
                billable_time=0.0,
                billable_fixed=0.0,
                total=0.0,
            ))[data['timesheet_invoice_type']] = float_round(data.get('unit_amount', 0.0), precision_rounding=hour_rounding)
            repartition_employee[employee_id]['__domain_'+data['timesheet_invoice_type']] = data['__domain']

        # compute total
        for employee_id, vals in repartition_employee.items():
            repartition_employee[employee_id]['total'] = sum([vals[inv_type] for inv_type in billable_types])

        hours_per_employee = [repartition_employee[employee_id]['total'] for employee_id in repartition_employee]
        values['repartition_employee_max'] = max(hours_per_employee) if hours_per_employee else 1
        values['repartition_employee'] = repartition_employee

        return values

    def _plan_get_stat_button(self, timesheet_lines):
        stat_buttons = []
        stat_buttons.append({
            'name': _('Timesheets'),
            'res_model': 'account.analytic.line',
            'domain': [('id', 'in', timesheet_lines.ids)],
            'icon': 'fa fa-calendar',
        })
        stat_project_ids = timesheet_lines.mapped('project_id').ids
        stat_task_domain = [('project_id', 'in', stat_project_ids), '|', ('stage_id', '=', False), ('stage_id.fold', '=', False)]
        stat_buttons.append({
            'name': _('Tasks'),
            'count': request.env['project.task'].search_count(stat_task_domain),
            'res_model': 'project.task',
            'domain': stat_task_domain,
            'icon': 'fa fa-tasks',
        })
        return stat_buttons

    @http.route('/timesheet/plan/action', type='json', auth="user")
    def plan_stat_button(self, domain, res_model='account.analytic.line'):
        action = {
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'list',
            'domain': domain,
        }
        if res_model == 'account.analytic.line':
            ts_view_tree_id = request.env.ref('hr_timesheet.hr_timesheet_line_tree').id
            ts_view_form_id = request.env.ref('hr_timesheet.hr_timesheet_line_form').id
            action = {
                'name': _('Timesheets'),
                'type': 'ir.actions.act_window',
                'res_model': res_model,
                'view_mode': 'tree,form',
                'view_type': 'tree',
                'views': [[ts_view_tree_id, 'list'], [ts_view_form_id, 'form']],
                'domain': domain,
            }
        elif res_model == 'project.task':
            action = request.env.ref('project.action_view_task').read()[0]
            action.update({
                'name': _('Tasks'),
                'domain': domain,
                'context': request.env.context,  # erase original context to avoid default filter
            })
        return action
