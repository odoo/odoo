# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval
import babel
from dateutil.relativedelta import relativedelta
import itertools
import json

from odoo import http, fields, _
from odoo.http import request
from odoo.tools import float_round

from odoo.addons.web.controllers.main import clean_action

DEFAULT_MONTH_RANGE = 3


class SaleTimesheetController(http.Controller):

    @http.route('/timesheet/plan', type='json', auth="user")
    def plan(self, domain):
        """ Get the HTML of the project plan for projects matching the given domain
            :param domain: a domain for project.project
        """
        projects = request.env['project.project'].search(domain)
        values = self._plan_prepare_values(projects)
        view = request.env.ref('sale_timesheet.timesheet_plan')
        return {
            'html_content': view.render(values),
            'project_ids': projects.ids,
            'actions': self._plan_prepare_actions(projects, values),
        }

    def _plan_prepare_values(self, projects):

        currency = request.env.user.company_id.currency_id
        uom_hour = request.env.ref('uom.product_uom_hour')
        hour_rounding = uom_hour.rounding
        billable_types = ['non_billable', 'non_billable_project', 'billable_time', 'billable_fixed']

        values = {
            'projects': projects,
            'currency': currency,
            'timesheet_domain': [('project_id', 'in', projects.ids)],
            'stat_buttons': self._plan_get_stat_button(projects),
        }

        #
        # Hours, Rates and Profitability
        #
        dashboard_values = {
            'hours': dict.fromkeys(billable_types + ['total'], 0.0),
            'rates': dict.fromkeys(billable_types + ['total'], 0.0),
            'profit': {
                'invoiced': 0.0,
                'to_invoice': 0.0,
                'cost': 0.0,
                'total': 0.0,
            }
        }

        # hours (from timesheet) and rates (by billable type)
        dashboard_domain = [('project_id', 'in', projects.ids), ('timesheet_invoice_type', '!=', False)]  # force billable type
        dashboard_data = request.env['account.analytic.line'].read_group(dashboard_domain, ['unit_amount', 'timesheet_invoice_type'], ['timesheet_invoice_type'])
        dashboard_total_hours = sum([data['unit_amount'] for data in dashboard_data])
        for data in dashboard_data:
            billable_type = data['timesheet_invoice_type']
            dashboard_values['hours'][billable_type] = float_round(data.get('unit_amount'), precision_rounding=hour_rounding)
            dashboard_values['hours']['total'] += float_round(data.get('unit_amount'), precision_rounding=hour_rounding)
            # rates
            rate = round(data.get('unit_amount') / dashboard_total_hours * 100, 2) if dashboard_total_hours else 0.0
            dashboard_values['rates'][billable_type] = rate
            dashboard_values['rates']['total'] += rate

        # profitability, using profitability SQL report
        profit = dict.fromkeys(['invoiced', 'to_invoice', 'cost', 'expense_cost', 'expense_amount_untaxed_invoiced', 'total'], 0.0)
        profitability_raw_data = request.env['project.profitability.report'].read_group([('project_id', 'in', projects.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_invoiced'], ['project_id'])
        for data in profitability_raw_data:
            profit['invoiced'] += data.get('amount_untaxed_invoiced', 0.0)
            profit['to_invoice'] += data.get('amount_untaxed_to_invoice', 0.0)
            profit['cost'] += data.get('timesheet_cost', 0.0)
            profit['expense_cost'] += data.get('expense_cost', 0.0)
            profit['expense_amount_untaxed_invoiced'] += data.get('expense_amount_untaxed_invoiced', 0.0)
        profit['total'] = sum([profit[item] for item in profit.keys()])
        dashboard_values['profit'] = profit

        values['dashboard'] = dashboard_values

        #
        # Time Repartition (per employee per billable types)
        #
        user_ids = request.env['project.task'].sudo().search_read([('project_id', 'in', projects.ids), ('user_id', '!=', False)], ['user_id'])
        user_ids = [user_id['user_id'][0] for user_id in user_ids]
        employee_ids = request.env['res.users'].sudo().search_read([('id', 'in', user_ids)], ['employee_ids'])
        # flatten the list of list
        employee_ids = list(itertools.chain.from_iterable([employee_id['employee_ids'] for employee_id in employee_ids]))
        employees = request.env['hr.employee'].sudo().browse(employee_ids) | request.env['account.analytic.line'].search([('project_id', 'in', projects.ids)]).mapped('employee_id')
        repartition_domain = [('project_id', 'in', projects.ids), ('employee_id', '!=', False), ('timesheet_invoice_type', '!=', False)]  # force billable type
        repartition_data = request.env['account.analytic.line'].read_group(repartition_domain, ['employee_id', 'timesheet_invoice_type', 'unit_amount'], ['employee_id', 'timesheet_invoice_type'], lazy=False)

        # set repartition per type per employee
        repartition_employee = {}
        for employee in employees:
            repartition_employee[employee.id] = dict(
                employee_id=employee.id,
                employee_name=employee.name,
                non_billable_project=0.0,
                non_billable=0.0,
                billable_time=0.0,
                billable_fixed=0.0,
                total=0.0,
            )
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
            repartition_employee[employee_id]['__domain_' + data['timesheet_invoice_type']] = data['__domain']

        # compute total
        for employee_id, vals in repartition_employee.items():
            repartition_employee[employee_id]['total'] = sum([vals[inv_type] for inv_type in billable_types])

        hours_per_employee = [repartition_employee[employee_id]['total'] for employee_id in repartition_employee]
        values['repartition_employee_max'] = (max(hours_per_employee) if hours_per_employee else 1) or 1
        values['repartition_employee'] = repartition_employee

        #
        # Table grouped by SO / SOL / Employees
        #
        timesheet_forecast_table_rows = self._table_get_line_values(projects)
        if timesheet_forecast_table_rows:
            values['timesheet_forecast_table'] = timesheet_forecast_table_rows
        return values

    def _table_get_line_values(self, projects):
        """ return the header and the rows informations of the table """
        if not projects:
            return False

        uom_hour = request.env.ref('uom.product_uom_hour')

        # build SQL query and fetch raw data
        query, query_params = self._table_rows_sql_query(projects)
        request.env.cr.execute(query, query_params)
        raw_data = request.env.cr.dictfetchall()
        rows_employee = self._table_rows_get_employee_lines(projects, raw_data)
        default_row_vals = self._table_row_default(projects)

        empty_line_ids, empty_order_ids = self._table_get_empty_so_lines(projects)

        # extract row labels
        sale_line_ids = set()
        sale_order_ids = set()
        for key_tuple, row in rows_employee.items():
            if row[0]['sale_line_id']:
                sale_line_ids.add(row[0]['sale_line_id'])
            if row[0]['sale_order_id']:
                sale_order_ids.add(row[0]['sale_order_id'])

        sale_order_lines = request.env['sale.order.line'].sudo().browse(sale_line_ids | empty_line_ids)
        map_so_names = {so.id: so.name for so in request.env['sale.order'].sudo().browse(sale_order_ids | empty_order_ids)}
        map_sol = {sol.id: sol for sol in sale_order_lines}
        map_sol_names = {sol.id: sol.name.split('\n')[0] if sol.name else _('No Sales Order Line') for sol in sale_order_lines}
        map_sol_so = {sol.id: sol.order_id.id for sol in sale_order_lines}

        rows_sale_line = {}  # (so, sol) -> [INFO, before, M1, M2, M3, Done, M3, M4, M5, After, Forecasted]
        for sale_line_id in empty_line_ids:  # add service SO line having no timesheet
            sale_line_row_key = (map_sol_so.get(sale_line_id), sale_line_id)
            sale_line = map_sol.get(sale_line_id)
            is_milestone = sale_line.product_id.invoice_policy == 'delivery' and sale_line.product_id.service_type == 'manual' if sale_line else False
            rows_sale_line[sale_line_row_key] = [{'label': map_sol_names.get(sale_line_id, _('No Sales Order Line')), 'res_id': sale_line_id, 'res_model': 'sale.order.line', 'type': 'sale_order_line', 'is_milestone': is_milestone}] + default_row_vals[:]
            if not is_milestone:
                rows_sale_line[sale_line_row_key][-2] = sale_line.product_uom._compute_quantity(sale_line.product_uom_qty, uom_hour, raise_if_failure=False) if sale_line else 0.0

        for row_key, row_employee in rows_employee.items():
            sale_line_id = row_key[1]
            sale_order_id = row_key[0]
            # sale line row
            sale_line_row_key = (sale_order_id, sale_line_id)
            if sale_line_row_key not in rows_sale_line:
                sale_line = map_sol.get(sale_line_id, request.env['sale.order.line'])
                is_milestone = sale_line.product_id.invoice_policy == 'delivery' and sale_line.product_id.service_type == 'manual' if sale_line else False
                rows_sale_line[sale_line_row_key] = [{'label': map_sol_names.get(sale_line.id) if sale_line else _('No Sales Order Line'), 'res_id': sale_line_id, 'res_model': 'sale.order.line', 'type': 'sale_order_line', 'is_milestone': is_milestone}] + default_row_vals[:]  # INFO, before, M1, M2, M3, Done, M3, M4, M5, After, Forecasted
                if not is_milestone:
                    rows_sale_line[sale_line_row_key][-2] = sale_line.product_uom._compute_quantity(sale_line.product_uom_qty, uom_hour, raise_if_failure=False) if sale_line else 0.0

            for index in range(len(rows_employee[row_key])):
                if index != 0:
                    rows_sale_line[sale_line_row_key][index] += rows_employee[row_key][index]
                    if not rows_sale_line[sale_line_row_key][0].get('is_milestone'):
                        rows_sale_line[sale_line_row_key][-1] = rows_sale_line[sale_line_row_key][-2] - rows_sale_line[sale_line_row_key][5]
                    else:
                        rows_sale_line[sale_line_row_key][-1] = 0

        rows_sale_order = {}  # so -> [INFO, before, M1, M2, M3, Done, M3, M4, M5, After, Forecasted]
        rows_sale_order_done_sold = dict.fromkeys(set(map_sol_so.values()) | set([None]), dict(sold=0.0, done=0.0))  # SO id -> {'sold':0.0, 'done': 0.0}
        for row_key, row_sale_line in rows_sale_line.items():
            sale_order_id = row_key[0]
            # sale order row
            if sale_order_id not in rows_sale_order:
                rows_sale_order[sale_order_id] = [{'label': map_so_names.get(sale_order_id, _('No Sales Order')), 'res_id': sale_order_id, 'res_model': 'sale.order', 'type': 'sale_order'}] + default_row_vals[:]  # INFO, before, M1, M2, M3, Done, M3, M4, M5, After, Forecasted

            for index in range(len(rows_sale_line[row_key])):
                if index != 0:
                    rows_sale_order[sale_order_id][index] += rows_sale_line[row_key][index]

            # do not sum the milestone SO line for sold and done (for remaining computation)
            if not rows_sale_line[row_key][0].get('is_milestone'):
                rows_sale_order_done_sold[sale_order_id]['sold'] += rows_sale_line[row_key][-2]
                rows_sale_order_done_sold[sale_order_id]['done'] += rows_sale_line[row_key][5]

        # remaining computation of SO row, as Sold - Done (timesheet total)
        for sale_order_id, done_sold_vals in rows_sale_order_done_sold.items():
            if sale_order_id in rows_sale_order:
                rows_sale_order[sale_order_id][-1] = done_sold_vals['sold'] - done_sold_vals['done']

        # group rows SO, SOL and their related employee rows.
        timesheet_forecast_table_rows = []
        for sale_order_id, sale_order_row in rows_sale_order.items():
            timesheet_forecast_table_rows.append(sale_order_row)
            for sale_line_row_key, sale_line_row in rows_sale_line.items():
                if sale_order_id == sale_line_row_key[0]:
                    timesheet_forecast_table_rows.append(sale_line_row)
                    for employee_row_key, employee_row in rows_employee.items():
                        if sale_order_id == employee_row_key[0] and sale_line_row_key[1] == employee_row_key[1]:
                            timesheet_forecast_table_rows.append(employee_row)

        # complete table data
        return {
            'header': self._table_header(projects),
            'rows': timesheet_forecast_table_rows
        }

    def _table_header(self, projects):
        initial_date = fields.Date.from_string(fields.Date.today())
        ts_months = sorted([fields.Date.to_string(initial_date - relativedelta(months=i, day=1)) for i in range(0, DEFAULT_MONTH_RANGE)])  # M1, M2, M3

        def _to_short_month_name(date):
            month_index = fields.Date.from_string(date).month
            return babel.dates.get_month_names('abbreviated', locale=request.env.context.get('lang', 'en_US'))[month_index]

        header_names = [_('Name'), _('Before')] + [_to_short_month_name(date) for date in ts_months] + [_('Done'), _('Sold'), _('Remaining')]

        result = []
        for name in header_names:
            result.append({
                'label': name,
                'tooltip': '',
            })
        # add tooltip for reminaing
        result[-1]['tooltip'] = _('What is still to deliver based on sold hours and hours already done. Equals to sold hours - done hours.')
        return result

    def _table_row_default(self, projects):
        lenght = len(self._table_header(projects))
        return [0.0] * (lenght - 1)  # before, M1, M2, M3, Done, Sold, Remaining

    def _table_rows_sql_query(self, projects):
        initial_date = fields.Date.from_string(fields.Date.today())
        ts_months = sorted([fields.Date.to_string(initial_date - relativedelta(months=i, day=1)) for i in range(0, DEFAULT_MONTH_RANGE)])  # M1, M2, M3
        # build query
        query = """
            SELECT
                'timesheet' AS type,
                date_trunc('month', date)::date AS month_date,
                E.id AS employee_id,
                S.order_id AS sale_order_id,
                A.so_line AS sale_line_id,
                SUM(A.unit_amount) AS number_hours
            FROM account_analytic_line A
                JOIN hr_employee E ON E.id = A.employee_id
                LEFT JOIN sale_order_line S ON S.id = A.so_line
            WHERE A.project_id IS NOT NULL
                AND A.project_id IN %s
                AND A.date < %s
            GROUP BY date_trunc('month', date)::date, S.order_id, A.so_line, E.id
        """

        last_ts_month = fields.Date.to_string(fields.Date.from_string(ts_months[-1]) + relativedelta(months=1))
        query_params = (tuple(projects.ids), last_ts_month)
        return query, query_params

    def _table_rows_get_employee_lines(self, projects, data_from_db):
        initial_date = fields.Date.today()
        ts_months = sorted([initial_date - relativedelta(months=i, day=1) for i in range(0, DEFAULT_MONTH_RANGE)])  # M1, M2, M3
        default_row_vals = self._table_row_default(projects)

        # extract employee names
        employee_ids = set()
        for data in data_from_db:
            employee_ids.add(data['employee_id'])
        map_empl_names = {empl.id: empl.name for empl in request.env['hr.employee'].sudo().browse(employee_ids)}

        # extract rows data for employee, sol and so rows
        rows_employee = {}  # (so, sol, employee) -> [INFO, before, M1, M2, M3, Done, M3, M4, M5, After, Forecasted]
        for data in data_from_db:
            sale_line_id = data['sale_line_id']
            sale_order_id = data['sale_order_id']
            # employee row
            row_key = (data['sale_order_id'], sale_line_id, data['employee_id'])
            if row_key not in rows_employee:
                meta_vals = {
                    'label': map_empl_names.get(row_key[2]),
                    'sale_line_id': sale_line_id,
                    'sale_order_id': sale_order_id,
                    'res_id': row_key[2],
                    'res_model': 'hr.employee',
                    'type': 'hr_employee'
                }
                rows_employee[row_key] = [meta_vals] + default_row_vals[:]  # INFO, before, M1, M2, M3, Done, M3, M4, M5, After, Forecasted

            index = False
            if data['type'] == 'timesheet':
                if data['month_date'] in ts_months:
                    index = ts_months.index(data['month_date']) + 2
                elif data['month_date'] < ts_months[0]:
                    index = 1
                rows_employee[row_key][index] += data['number_hours']
                rows_employee[row_key][5] += data['number_hours']
        return rows_employee

    def _table_get_empty_so_lines(self, projects):
        """ get the Sale Order Lines having no timesheet but having generated a task or a project """
        so_lines = projects.sudo().mapped('sale_line_id.order_id.order_line').filtered(lambda sol: sol.is_service and not sol.is_expense)
        return set(so_lines.ids), set(so_lines.mapped('order_id').ids)

    # --------------------------------------------------
    # Actions: Stat buttons, ...
    # --------------------------------------------------

    def _plan_prepare_actions(self, projects, values):
        actions = []
        if len(projects) == 1:
            if request.env.user.has_group('sales_team.group_sale_salesman'):
                if not projects.sale_line_id and not projects.tasks.mapped('sale_line_id'):
                    actions.append({
                        'label': _("Create a Sales Order"),
                        'type': 'action',
                        'action_id': 'sale_timesheet.project_project_action_multi_create_sale_order',
                        'context': json.dumps({'active_id': projects.id, 'active_model': 'project.project'}),
                    })
            if request.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
                to_invoice_amount = values['dashboard']['profit'].get('to_invoice', False)  # plan project only takes services SO line with timesheet into account
                sale_orders = projects.tasks.mapped('sale_line_id.order_id').filtered(lambda so: so.invoice_status == 'to invoice')
                if to_invoice_amount and sale_orders:
                    if len(sale_orders) == 1:
                        actions.append({
                            'label': _("Create Invoice"),
                            'type': 'action',
                            'action_id': 'sale.action_view_sale_advance_payment_inv',
                            'context': json.dumps({'active_ids': sale_orders.ids, 'active_model': 'project.project'}),
                        })
                    else:
                        actions.append({
                            'label': _("Create Invoice"),
                            'type': 'action',
                            'action_id': 'sale_timesheet.project_project_action_multi_create_invoice',
                            'context': json.dumps({'active_id': projects.id, 'active_model': 'project.project'}),
                        })
        return actions

    def _plan_get_stat_button(self, projects):
        stat_buttons = []
        if len(projects) == 1:
            stat_buttons.append({
                'name': _('Project'),
                'res_model': 'project.project',
                'res_id': projects.id,
                'icon': 'fa fa-puzzle-piece',
            })
        stat_buttons.append({
            'name': _('Timesheets'),
            'res_model': 'account.analytic.line',
            'domain': [('project_id', 'in', projects.ids)],
            'icon': 'fa fa-calendar',
        })
        stat_buttons.append({
            'name': _('Tasks'),
            'count': sum(projects.mapped('task_count')),
            'res_model': 'project.task',
            'domain': [('project_id', 'in', projects.ids)],
            'icon': 'fa fa-tasks',
        })
        if request.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            sale_orders = projects.mapped('sale_line_id.order_id') | projects.mapped('tasks.sale_order_id')
            if sale_orders:
                stat_buttons.append({
                    'name': _('Sales Orders'),
                    'count': len(sale_orders),
                    'res_model': 'sale.order',
                    'domain': [('id', 'in', sale_orders.ids)],
                    'icon': 'fa fa-dollar',
                })
                invoices = sale_orders.mapped('invoice_ids').filtered(lambda inv: inv.type == 'out_invoice')
                if invoices:
                    stat_buttons.append({
                        'name': _('Invoices'),
                        'count': len(invoices),
                        'res_model': 'account.invoice',
                        'domain': [('id', 'in', invoices.ids), ('type', '=', 'out_invoice')],
                        'icon': 'fa fa-pencil-square-o',
                    })
        return stat_buttons

    @http.route('/timesheet/plan/action', type='json', auth="user")
    def plan_stat_button(self, domain=[], res_model='account.analytic.line', res_id=False):
        action = {
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'list',
            'domain': domain,
        }
        if res_model == 'project.project':
            view_form_id = request.env.ref('project.edit_project').id
            action = {
                'name': _('Project'),
                'type': 'ir.actions.act_window',
                'res_model': res_model,
                'view_mode': 'form',
                'view_type': 'form',
                'views': [[view_form_id, 'form']],
                'res_id': res_id,
            }
        elif res_model == 'account.analytic.line':
            ts_view_tree_id = request.env.ref('hr_timesheet.hr_timesheet_line_tree').id
            ts_view_form_id = request.env.ref('hr_timesheet.hr_timesheet_line_form').id
            action = {
                'name': _('Timesheets'),
                'type': 'ir.actions.act_window',
                'res_model': res_model,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'views': [[ts_view_tree_id, 'list'], [ts_view_form_id, 'form']],
                'domain': domain,
            }
        elif res_model == 'project.task':
            action = request.env.ref('project.action_view_task').read()[0]
            action.update({
                'name': _('Tasks'),
                'domain': domain,
                'context': dict(request.env.context),  # erase original context to avoid default filter
            })
            # if only one project, add it in the context as default value
            tasks = request.env['project.task'].sudo().search(literal_eval(domain))
            if len(tasks.mapped('project_id')) == 1:
                action['context']['default_project_id'] = tasks.mapped('project_id')[0].id
        elif res_model == 'sale.order':
            action = clean_action(request.env.ref('sale.action_orders').read()[0])
            action['domain'] = domain
            action['context'] = {'create': False, 'edit': False, 'delete': False}  # No CRUD operation when coming from overview
        elif res_model == 'account.invoice':
            action = clean_action(request.env.ref('account.action_invoice_tree1').read()[0])
            action['domain'] = domain
            action['context'] = {'create': False, 'delete': False}  # only edition of invoice from overview
        return action
