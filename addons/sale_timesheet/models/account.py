# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError

from odoo import api, fields, models, _
from odoo.osv import expression


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _default_sale_line_domain(self):
        domain = super(AccountAnalyticLine, self)._default_sale_line_domain()
        return expression.OR([domain, [('qty_delivered_method', '=', 'timesheet')]])

    exclude_from_sale_order = fields.Boolean(
        string='Exclude from Sale Order',
        help='Checking this would exclude this timesheet entry from Sale Order',
    )
    timesheet_invoice_type = fields.Selection([
        ('billable_time', 'Billable Time'),
        ('billable_fixed', 'Billable Fixed'),
        ('non_billable', 'Non Billable'),
        ('non_billable_project', 'No task found')], string="Billable Type", compute='_compute_timesheet_invoice_type', compute_sudo=True, store=True, readonly=True)
    timesheet_invoice_id = fields.Many2one('account.invoice', string="Invoice", readonly=True, copy=False, help="Invoice created from the timesheet")

    @api.multi
    @api.depends('so_line.product_id', 'project_id', 'task_id', 'exclude_from_sale_order')
    def _compute_timesheet_invoice_type(self):
        for timesheet in self:
            if timesheet.project_id:  # AAL will be set to False
                invoice_type = 'non_billable_project' if not timesheet.task_id else 'non_billable'
                if timesheet.task_id and timesheet.so_line.product_id.type == 'service' and not timesheet.exclude_from_sale_order:
                    if timesheet.so_line.product_id.invoice_policy == 'delivery':
                        if timesheet.so_line.product_id.service_type == 'timesheet':
                            invoice_type = 'billable_time'
                        else:
                            invoice_type = 'billable_fixed'
                    elif timesheet.so_line.product_id.invoice_policy == 'order':
                        invoice_type = 'billable_fixed'
                timesheet.timesheet_invoice_type = invoice_type

    @api.onchange('task_id', 'employee_id')
    def _onchange_task_id_employee_id(self):
        if self.project_id:  # timesheet only
            self.so_line = self._timesheet_get_sale_line()

    @api.onchange('exclude_from_sale_order')
    def _onchange_exclude_from_sale_order(self):
        if self.project_id:  # timesheet only
            self.so_line = self._timesheet_get_sale_line()

    @api.constrains('so_line', 'project_id')
    def _check_so_line_valid_for_project(self):
        for timesheet in self:
            if not timesheet.project_id or not timesheet.so_line:
                continue

            if timesheet.so_line not in timesheet._get_valid_so_line_ids():
                raise ValidationError(_(
                    'This timesheet line cannot be billed: there is no Sale'
                    ' Order Item defined on the task, nor on the project.'
                    ' Please define one to save your timesheet line.'
                ))

    @api.multi
    def _get_valid_so_line_ids(self):
        self.ensure_one()

        return (
            self.project_id.mapped(
                'sale_line_employee_ids.sale_line_id'
            )
            | self.task_id.sale_line_id
            | self.project_id.sale_line_id
        )

    @api.multi
    def write(self, values):
        # prevent to update invoiced timesheets if one line is of type delivery
        if self.sudo().filtered(lambda aal: aal.so_line.product_id.invoice_policy == "delivery" and aal.timesheet_invoice_id):
            if not self._timesheet_check_invoiced_write(values):
                raise UserError(_(
                    'You can not modify timesheets in a way that would affect'
                    ' invoices since these timesheets were already invoiced.'
                ))
        result = super(AccountAnalyticLine, self).write(values)
        return result

    @api.model
    def _timesheet_check_invoiced_write(self, values):
        return all([field_name not in values for field_name in ['unit_amount', 'employee_id', 'project_id', 'task_id', 'so_line', 'amount', 'date', 'exclude_from_sale_order']])

    @api.model
    def _timesheet_preprocess(self, values):
        values = super(AccountAnalyticLine, self)._timesheet_preprocess(values)
        # task implies so line (at create)
        if not values.get('so_line') and self._timesheet_should_evaluate_so_line(values, all):
            so_line = self._timesheet_determine_sale_line(
                **self._timesheet_determine_sale_line_arguments(values)
            ) if not values.get('exclude_from_sale_order') else False
            values['so_line'] = so_line.id if so_line else False
        return values

    @api.multi
    def _timesheet_postprocess_values(self, values):
        result = super(AccountAnalyticLine, self)._timesheet_postprocess_values(values)
        # (re)compute the sale line
        if self._timesheet_should_evaluate_so_line(values, any):
            for timesheet in self:
                so_line = timesheet._timesheet_get_sale_line()
                result[timesheet.id].update({
                    'so_line': so_line.id if so_line else False,
                })
        return result

    @api.multi
    def _timesheet_get_sale_line(self):
        self.ensure_one()
        return self._timesheet_determine_sale_line(
            **self._timesheet_determine_sale_line_arguments()
        ) if not self.exclude_from_sale_order else False

    @api.model
    def _timesheet_get_sale_line_dependencies(self):
        return [
            'task_id',
            'employee_id',
            'exclude_from_sale_order',
        ]

    @api.model
    def _timesheet_should_evaluate_so_line(self, values, check):
        return check([field_name in values for field_name in
                      self._timesheet_get_sale_line_dependencies()])

    @api.multi
    def _timesheet_determine_sale_line_arguments(self, values=None):
        return {
            'task': (
                self.env['project.task'].sudo().browse(values['task_id'])
            ) if values and 'task_id' in values else self.task_id,
            'employee': (
                self.env['hr.employee'].sudo().browse(values['employee_id'])
            ) if values and 'employee_id' in values else self.employee_id,
        }

    @api.model
    def _timesheet_determine_sale_line(self, task, employee, **kwargs):
        """ Deduce the SO line associated to the timesheet line:
            1/ timesheet on task rate: the so line will be the one from the task
            2/ timesheet on employee rate task: find the SO line in the map of the project (even for subtask), or fallback on the SO line of the task, or fallback
                on the one on the project
            NOTE: this have to be consistent with `_compute_billable_type` on project.task.
        """
        if task.billable_type != 'no':
            if task.billable_type == 'employee_rate':
                map_entry = self.env['project.sale.line.employee.map'].search([('project_id', '=', task.project_id.id), ('employee_id', '=', employee.id)])
                if map_entry:
                    return map_entry.sale_line_id
                if task.sale_line_id:
                    return task.sale_line_id
                return task.project_id.sale_line_id
            elif task.billable_type == 'task_rate':
                return task.sale_line_id
        return self.env['sale.order.line']
