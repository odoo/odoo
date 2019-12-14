# -*- coding: utf-8 -*-
import babel
from dateutil.relativedelta import relativedelta
import itertools
import json

from odoo import fields, _, models
from odoo.tools import float_round
from odoo.tools.misc import get_lang

from odoo.addons.web.controllers.main import clean_action

DEFAULT_MONTH_RANGE = 3


class Project(models.Model):
    _inherit = 'project.project'


    def _qweb_prepare_qcontext(self, view_id, domain):
        values = super()._qweb_prepare_qcontext(view_id, domain)

        projects = self.search(domain)
        values.update(projects._plan_prepare_values())
        values['actions'] = projects._plan_prepare_actions(values)

        return values

    def _plan_prepare_values(self):
        currency = self.env.company.currency_id
        uom_hour = self.env.ref('uom.product_uom_hour')
        hour_rounding = uom_hour.rounding
        billable_types = ['non_billable', 'non_billable_project', 'billable_time', 'billable_fixed']

        values = {
            'projects': self,
            'currency': currency,
            'timesheet_domain': [('project_id', 'in', self.ids)],
            'profitability_domain': [('project_id', 'in', self.ids)],
            'stat_buttons': self._plan_get_stat_button(),
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

        # hours from non-invoiced timesheets that are linked to canceled so
        canceled_hours_domain = [('project_id', 'in', self.ids), ('timesheet_invoice_type', '!=', False), ('so_line.state', '=', 'cancel')]
        total_canceled_hours = sum(self.env['account.analytic.line'].search(canceled_hours_domain).mapped('unit_amount'))
        dashboard_values['hours']['canceled'] = float_round(total_canceled_hours, precision_rounding=hour_rounding)
        dashboard_values['hours']['total'] += float_round(total_canceled_hours, precision_rounding=hour_rounding)

        # hours (from timesheet) and rates (by billable type)
        dashboard_domain = [('project_id', 'in', self.ids), ('timesheet_invoice_type', '!=', False), '|', ('so_line', '=', False), ('so_line.state', '!=', 'cancel')]  # force billable type
        dashboard_data = self.env['account.analytic.line'].read_group(dashboard_domain, ['unit_amount', 'timesheet_invoice_type'], ['timesheet_invoice_type'])
        dashboard_total_hours = sum([data['unit_amount'] for data in dashboard_data]) + total_canceled_hours
        for data in dashboard_data:
            billable_type = data['timesheet_invoice_type']
            dashboard_values['hours'][billable_type] = float_round(data.get('unit_amount'), precision_rounding=hour_rounding)
            dashboard_values['hours']['total'] += float_round(data.get('unit_amount'), precision_rounding=hour_rounding)
            # rates
            rate = round(data.get('unit_amount') / dashboard_total_hours * 100, 2) if dashboard_total_hours else 0.0
            dashboard_values['rates'][billable_type] = rate
            dashboard_values['rates']['total'] += rate

        # rates from non-invoiced timesheets that are linked to canceled so
        dashboard_values['rates']['canceled'] = float_round(100 * total_canceled_hours / (dashboard_total_hours or 1), precision_rounding=hour_rounding)

        # profitability, using profitability SQL report
        profit = dict.fromkeys(['invoiced', 'to_invoice', 'cost', 'expense_cost', 'expense_amount_untaxed_invoiced', 'total'], 0.0)
        profitability_raw_data = self.env['project.profitability.report'].read_group([('project_id', 'in', self.ids)], ['project_id', 'amount_untaxed_to_invoice', 'amount_untaxed_invoiced', 'timesheet_cost', 'expense_cost', 'expense_amount_untaxed_invoiced'], ['project_id'])
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
        user_ids = self.env['project.task'].sudo().read_group([('project_id', 'in', self.ids), ('user_id', '!=', False)], ['user_id'], ['user_id'])
        user_ids = [user_id['user_id'][0] for user_id in user_ids]
        employee_ids = self.env['res.users'].sudo().search_read([('id', 'in', user_ids)], ['employee_ids'])
        # flatten the list of list
        employee_ids = list(itertools.chain.from_iterable([employee_id['employee_ids'] for employee_id in employee_ids]))

        aal_employee_ids = self.env['account.analytic.line'].read_group([('project_id', 'in', self.ids), ('employee_id', '!=', False)], ['employee_id'], ['employee_id'])
        employee_ids.extend(list(map(lambda x: x['employee_id'][0], aal_employee_ids)))

        employees = self.env['hr.employee'].sudo().browse(employee_ids)
        repartition_domain = [('project_id', 'in', self.ids), ('employee_id', '!=', False), ('timesheet_invoice_type', '!=', False)]  # force billable type
        # repartition data, without timesheet on cancelled so
        repartition_data = self.env['account.analytic.line'].read_group(repartition_domain + ['|', ('so_line', '=', False), ('so_line.state', '!=', 'cancel')], ['employee_id', 'timesheet_invoice_type', 'unit_amount'], ['employee_id', 'timesheet_invoice_type'], lazy=False)
        # read timesheet on cancelled so
        cancelled_so_timesheet = self.env['account.analytic.line'].read_group(repartition_domain + [('so_line.state', '=', 'cancel')], ['employee_id', 'unit_amount'], ['employee_id'], lazy=False)
        repartition_data += [{**canceled, 'timesheet_invoice_type': 'canceled'} for canceled in cancelled_so_timesheet]

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
                canceled=0.0,
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
                canceled=0.0,
                total=0.0,
            ))[data['timesheet_invoice_type']] = float_round(data.get('unit_amount', 0.0), precision_rounding=hour_rounding)
            repartition_employee[employee_id]['__domain_' + data['timesheet_invoice_type']] = data['__domain']
        # compute total
        for employee_id, vals in repartition_employee.items():
            repartition_employee[employee_id]['total'] = sum([vals[inv_type] for inv_type in [*billable_types, 'canceled']])
        hours_per_employee = [repartition_employee[employee_id]['total'] for employee_id in repartition_employee]
        values['repartition_employee_max'] = (max(hours_per_employee) if hours_per_employee else 1) or 1
        values['repartition_employee'] = repartition_employee

        #
        # Table grouped by SO / SOL / Employees
        #
        timesheet_forecast_table_rows = self._table_get_line_values()
        if timesheet_forecast_table_rows:
            values['timesheet_forecast_table'] = timesheet_forecast_table_rows
        return values

    def _table_get_line_values(self):
        """ return the header and the rows informations of the table """
        if not self:
            return False

        uom_hour = self.env.ref('uom.product_uom_hour')

        # build SQL query and fetch raw data
        query, query_params = self._table_rows_sql_query()
        self.env.cr.execute(query, query_params)
        raw_data = self.env.cr.dictfetchall()
        rows_employee = self._table_rows_get_employee_lines(raw_data)
        default_row_vals = self._table_row_default()

        empty_line_ids, empty_order_ids = self._table_get_empty_so_lines()

        # extract row labels
        sale_line_ids = set()
        sale_order_ids = set()
        for key_tuple, row in rows_employee.items():
            if row[0]['sale_line_id']:
                sale_line_ids.add(row[0]['sale_line_id'])
            if row[0]['sale_order_id']:
                sale_order_ids.add(row[0]['sale_order_id'])

        sale_orders = self.env['sale.order'].sudo().browse(sale_order_ids | empty_order_ids)
        sale_order_lines = self.env['sale.order.line'].sudo().browse(sale_line_ids | empty_line_ids)
        map_so_names = {so.id: so.name for so in sale_orders}
        map_so_cancel = {so.id: so.state == 'cancel' for so in sale_orders}
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
                sale_line = map_sol.get(sale_line_id, self.env['sale.order.line'])
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
        rows_sale_order_done_sold = {key : dict(sold=0.0, done=0.0) for key in set(map_sol_so.values()) | set([None])}  # SO id -> {'sold':0.0, 'done': 0.0}
        for row_key, row_sale_line in rows_sale_line.items():
            sale_order_id = row_key[0]
            # sale order row
            if sale_order_id not in rows_sale_order:
                rows_sale_order[sale_order_id] = [{'label': map_so_names.get(sale_order_id, _('No Sales Order')), 'canceled': map_so_cancel.get(sale_order_id, False), 'res_id': sale_order_id, 'res_model': 'sale.order', 'type': 'sale_order'}] + default_row_vals[:]  # INFO, before, M1, M2, M3, Done, M3, M4, M5, After, Forecasted

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
            'header': self._table_header(),
            'rows': timesheet_forecast_table_rows
        }
    def _table_header(self):
        initial_date = fields.Date.from_string(fields.Date.today())
        ts_months = sorted([fields.Date.to_string(initial_date - relativedelta(months=i, day=1)) for i in range(0, DEFAULT_MONTH_RANGE)])  # M1, M2, M3

        def _to_short_month_name(date):
            month_index = fields.Date.from_string(date).month
            return babel.dates.get_month_names('abbreviated', locale=get_lang(self.env).code)[month_index]

        header_names = [_('Name'), _('Before')] + [_to_short_month_name(date) for date in ts_months] + [_('Total'), _('Sold'), _('Remaining')]

        result = []
        for name in header_names:
            result.append({
                'label': name,
                'tooltip': '',
            })
        # add tooltip for reminaing
        result[-1]['tooltip'] = _('What is still to deliver based on sold hours and hours already done. Equals to sold hours - done hours.')
        return result

    def _table_row_default(self):
        lenght = len(self._table_header())
        return [0.0] * (lenght - 1)  # before, M1, M2, M3, Done, Sold, Remaining

    def _table_rows_sql_query(self):
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
        query_params = (tuple(self.ids), last_ts_month)
        return query, query_params

    def _table_rows_get_employee_lines(self, data_from_db):
        initial_date = fields.Date.today()
        ts_months = sorted([initial_date - relativedelta(months=i, day=1) for i in range(0, DEFAULT_MONTH_RANGE)])  # M1, M2, M3
        default_row_vals = self._table_row_default()

        # extract employee names
        employee_ids = set()
        for data in data_from_db:
            employee_ids.add(data['employee_id'])
        map_empl_names = {empl.id: empl.name for empl in self.env['hr.employee'].sudo().browse(employee_ids)}

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

    def _table_get_empty_so_lines(self):
        """ get the Sale Order Lines having no timesheet but having generated a task or a project """
        so_lines = self.sudo().mapped('sale_line_id.order_id.order_line').filtered(lambda sol: sol.is_service and not sol.is_expense and not sol.is_downpayment)
        # include the service SO line of SO sharing the same project
        sale_order = self.env['sale.order'].search([('project_id', 'in', self.ids)])
        return set(so_lines.ids) | set(sale_order.mapped('order_line').filtered(lambda sol: sol.is_service and not sol.is_expense).ids), set(so_lines.mapped('order_id').ids) | set(sale_order.ids)

    # --------------------------------------------------
    # Actions: Stat buttons, ...
    # --------------------------------------------------

    def _plan_prepare_actions(self, values):
        actions = []
        if len(self) == 1:
            task_order_line_ids = []
            # retrieve all the sale order line that we will need later below
            if self.env.user.has_group('sales_team.group_sale_salesman') or self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
                task_order_line_ids = self.env['project.task'].read_group([('project_id', '=', self.id), ('sale_line_id', '!=', False)], ['sale_line_id'], ['sale_line_id'])
                task_order_line_ids = [ol['sale_line_id'][0] for ol in task_order_line_ids]

            if self.env.user.has_group('sales_team.group_sale_salesman'):
                if not self.sale_line_id and not task_order_line_ids:
                    actions.append({
                        'label': _("Create a Sales Order"),
                        'type': 'action',
                        'action_id': 'sale_timesheet.project_project_action_multi_create_sale_order',
                        'context': json.dumps({'active_id': self.id, 'active_model': 'project.project'}),
                    })
            if self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
                to_invoice_amount = values['dashboard']['profit'].get('to_invoice', False)  # plan project only takes services SO line with timesheet into account

                sale_order_ids = self.env['sale.order.line'].read_group([('id', 'in', task_order_line_ids)], ['order_id'], ['order_id'])
                sale_order_ids = [s['order_id'][0] for s in sale_order_ids]
                sale_order_ids = self.env['sale.order'].search_read([('id', 'in', sale_order_ids), ('invoice_status', '=', 'to invoice')], ['id'])
                sale_order_ids = list(map(lambda x: x['id'], sale_order_ids))

                if to_invoice_amount and sale_order_ids:
                    if len(sale_order_ids) == 1:
                        actions.append({
                            'label': _("Create Invoice"),
                            'type': 'action',
                            'action_id': 'sale.action_view_sale_advance_payment_inv',
                            'context': json.dumps({'active_ids': sale_order_ids, 'active_model': 'project.project'}),
                        })
                    else:
                        actions.append({
                            'label': _("Create Invoice"),
                            'type': 'action',
                            'action_id': 'sale_timesheet.project_project_action_multi_create_invoice',
                            'context': json.dumps({'active_id': self.id, 'active_model': 'project.project'}),
                        })
        return actions

    def _plan_get_stat_button(self):
        stat_buttons = []
        if len(self) == 1:
            edit_project = self.env.ref('project.edit_project')
            stat_buttons.append({
                'name': _('Project'),
                'icon': 'fa fa-puzzle-piece',
                'action': _to_action_data('project.project', res_id=self.id,
                    views=[[edit_project.id, 'form']])
            })
        ts_tree = self.env.ref('hr_timesheet.hr_timesheet_line_tree')
        ts_form = self.env.ref('hr_timesheet.hr_timesheet_line_form')
        stat_buttons.append({
            'name': _('Timesheets'),
            'icon': 'fa fa-calendar',
            'action': _to_action_data(
                'account.analytic.line',
                domain=[('project_id', 'in', self.ids)],
                views=[(ts_tree.id, 'list'), (ts_form.id, 'form')],
            )
        })

        # if only one project, add it in the context as default value
        tasks_domain = [('project_id', 'in', self.ids)]
        tasks_context = self.env.context

        # filter out all the projects that have no tasks
        task_projects_ids = self.env['project.task'].read_group([('project_id', 'in', self.ids)], ['project_id'], ['project_id'])
        task_projects_ids = [p['project_id'][0] for p in task_projects_ids]

        if len(task_projects_ids) == 1:
            tasks_context = {**tasks_context, 'default_project_id': task_projects_ids[0]}
        stat_buttons.append({
            'name': _('Tasks'),
            'count': sum(self.mapped('task_count')),
            'icon': 'fa fa-tasks',
            'action': _to_action_data(
                action=self.env.ref('project.action_view_task'),
                domain=tasks_domain,
                context=tasks_context
            )
        })

        if self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            # read all the sale orders linked to the projects' tasks
            task_so_ids = self.env['project.task'].search_read([
                ('project_id', 'in', self.ids), ('sale_order_id', '!=', False)
            ], ['sale_order_id'])
            task_so_ids = [o['sale_order_id'][0] for o in task_so_ids]

            sale_orders = self.mapped('sale_line_id.order_id') | self.env['sale.order'].browse(task_so_ids)
            if sale_orders:
                stat_buttons.append({
                    'name': _('Sales Orders'),
                    'count': len(sale_orders),
                    'icon': 'fa fa-dollar',
                    'action': _to_action_data(
                        action=self.env.ref('sale.action_orders'),
                        domain=[('id', 'in', sale_orders.ids)],
                        context={'create': False, 'edit': False, 'delete': False}
                    )
                })

                invoice_ids = self.env['sale.order'].search_read([('id', 'in', sale_orders.ids)], ['invoice_ids'])
                invoice_ids = list(itertools.chain(*[i['invoice_ids'] for i in invoice_ids]))
                invoice_ids = self.env['account.move'].search_read([('id', 'in', invoice_ids), ('type', '=', 'out_invoice')], ['id'])
                invoice_ids = list(map(lambda x: x['id'], invoice_ids))

                if invoice_ids:
                    stat_buttons.append({
                        'name': _('Invoices'),
                        'count': len(invoice_ids),
                        'icon': 'fa fa-pencil-square-o',
                        'action': _to_action_data(
                            action=self.env.ref('account.action_move_out_invoice_type'),
                            domain=[('id', 'in', invoice_ids), ('type', '=', 'out_invoice')],
                            context={'create': False, 'delete': False}
                        )
                    })
        return stat_buttons


def _to_action_data(model=None, *, action=None, views=None, res_id=None, domain=None, context=None):
    # pass in either action or (model, views)
    if action:
        assert model is None and views is None
        act = clean_action(action.read()[0])
        model = act['res_model']
        views = act['views']
    # FIXME: search-view-id, possibly help?
    descr = {
        'data-model': model,
        'data-views': json.dumps(views),
    }
    if context is not None: # otherwise copy action's?
        descr['data-context'] = json.dumps(context)
    if res_id:
        descr['data-res-id'] = res_id
    elif domain:
        descr['data-domain'] = json.dumps(domain)
    return descr
