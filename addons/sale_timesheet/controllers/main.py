# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

from odoo.tools import float_round


class SaleTimesheetController(http.Controller):

    @http.route('/timesheet/plan', type='json', auth="user")
    def plan(self, domain):
        values = self._prepare_plan_values(domain)
        view = request.env['ir.model.data'].get_object('sale_timesheet', 'timesheet_plan')
        return {
            'html_content': view.render(values)
        }

    def _prepare_plan_values(self, domain):
        values = {
            'currency': request.env.user.company_id.currency_id,
            'timesheet_lines': request.env['account.analytic.line'].search(domain),
            'domain': domain,
        }
        hour_rounding = request.env.ref('product.product_uom_hour').rounding
        billable_types = ['non_billable', 'billable_time', 'billable_fixed']

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
            dashboard_values['rates'][billable_type] = float_round(data.get('unit_amount') / dashboard_total_hours * 100, precision_rounding=hour_rounding)
            dashboard_values['rates']['total'] += float_round(data.get('unit_amount') / dashboard_total_hours * 100, precision_rounding=hour_rounding)

        # money_amount
        dashboard_values['money_amount']['invoiced'] = sum(values['timesheet_lines'].filtered(lambda l: l.timesheet_invoice_id).mapped('timesheet_revenue'))
        dashboard_values['money_amount']['to_invoice'] = sum(values['timesheet_lines'].filtered(lambda l: not l.timesheet_invoice_id).mapped('timesheet_revenue'))
        dashboard_values['money_amount']['cost'] = sum(values['timesheet_lines'].mapped('amount'))
        dashboard_values['money_amount']['total'] = sum([dashboard_values['money_amount'][item] for item in dashboard_values['money_amount'].keys()])

        values['dashboard'] = dashboard_values

        # -- Time Repartition (per employee)
        repartition_domain = domain + [('timesheet_invoice_type', '!=', False)]  # force billable type
        repartition_data = request.env['account.analytic.line'].read_group(repartition_domain, ['employee_id', 'timesheet_invoice_type', 'unit_amount'], ['employee_id', 'timesheet_invoice_type'], lazy=False)

        # set repartition per type per employee
        repartition_employee = {}
        for data in repartition_data:
            employee_id = data['employee_id'][0]
            repartition_employee.setdefault(employee_id, dict(
                employee_id=data['employee_id'][0],
                employee_name=data['employee_id'][1],
                non_billable=0.0,
                billable_time=0.0,
                billable_fixed=0.0,
                total=0.0
            ))[data['timesheet_invoice_type']] = float_round(data.get('unit_amount', 0.0), precision_rounding=hour_rounding)

        # compute total
        for employee_id, vals in repartition_employee.items():
            repartition_employee[employee_id]['total'] = sum([vals[inv_type] for inv_type in billable_types])

        hours_per_employee = [repartition_employee[employee_id]['total'] for employee_id in repartition_employee]
        values['repartition_employee_max'] = max(hours_per_employee) if hours_per_employee else 1
        values['repartition_employee'] = repartition_employee

        return values
