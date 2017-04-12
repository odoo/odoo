# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, fields
from openerp.tools.translate import _

from openerp.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _get_uom_hours(self):
        try:
            return self.env.ref("product.product_uom_hour")
        except ValueError:
            return False
    project_time_mode_id = fields.Many2one('product.uom', string='Timesheet UoM', default=_get_uom_hours)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    # FIXME: this field should be in module hr_timesheet, not sale_timesheet
    timesheet_cost = fields.Float(string='Timesheet Cost', default=0.0)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    track_service = fields.Selection(selection_add=[('timesheet', 'Timesheets on project'), ('task', 'Create a task and track hours')])
    project_id = fields.Many2one('project.project', string='Project', help='Create a task under this project on sale order validation.',
                             ondelete='set null')

    @api.onchange('type', 'invoice_policy')
    def onchange_type_timesheet(self):
        if self.type == 'service' and self.invoice_policy != 'cost':
            self.track_service = 'timesheet'
        else:
            self.track_service = 'manual'
        return {}


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _get_sale_order_line(self, vals=None):
        result = dict(vals or {})
        if self.project_id:
            if result.get('so_line'):
                sol = self.env['sale.order.line'].browse([result['so_line']])
            else:
                sol = self.so_line
            if not sol:
                sol = self.env['sale.order.line'].search([
                    ('order_id.project_id', '=', self.account_id.id),
                    ('state', '=', 'sale'),
                    ('product_id.track_service', '=', 'timesheet'),
                    ('product_id.type', '=', 'service')],
                    limit=1)
            if sol:
                result.update({
                    'so_line': sol.id,
                    'product_id': sol.product_id.id,
                })
                result = self._get_timesheet_cost(result)

        result = super(AccountAnalyticLine, self)._get_sale_order_line(vals=result)
        return result

    def _get_timesheet_cost(self, vals=None):
        result = dict(vals or {})
        if result.get('project_id') or self.project_id:
            if result.get('amount'):
                return result
            unit_amount = result.get('unit_amount', 0.0) or self.unit_amount
            user_id = result.get('user_id') or self.user_id.id or self._default_user()
            user = self.env['res.users'].browse([user_id])
            emp = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
            cost = emp and emp.timesheet_cost or 0.0
            uom = (emp or user).company_id.project_time_mode_id
            # Nominal employee cost = 1 * company project UoM (project_time_mode_id)
            result.update(
                amount=(-unit_amount * cost),
                product_uom_id=uom.id
            )
        return result

    @api.model
    def _update_values(self, values):
        if values.get('task_id', False):
            task = self.env['project.task'].browse(values['task_id'])
            values['so_line'] = task.sale_line_id and task.sale_line_id.id or values.get('so_line', False)

    @api.multi
    def write(self, values):
        so_lines = self.mapped('so_line')
        self._update_values(values)
        for line in self:
            values = line._get_timesheet_cost(vals=values)
            super(AccountAnalyticLine, line).write(values)

        # Update delivered quantity on SO lines which are not linked to the analytic lines anymore
        so_lines -= self.mapped('so_line')
        if so_lines:
            so_lines.with_context(force_so_lines=so_lines).sudo()._compute_analytic()

        return True

    @api.model
    def create(self, values):
        self._update_values(values)
        values = self._get_timesheet_cost(vals=values)
        return super(AccountAnalyticLine, self).create(values)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', string='Timesheet activities associated to this sale')
    timesheet_count = fields.Float(string='Timesheet activities', compute='_compute_timesheet_ids')

    tasks_ids = fields.Many2many('project.task', compute='_compute_tasks_ids', string='Tasks associated to this sale')
    tasks_count = fields.Integer(string='Tasks', compute='_compute_tasks_ids')

    project_project_id = fields.Many2one('project.project', compute='_compute_project_project_id', string='Project associated to this sale')

    @api.multi
    @api.depends('project_id.line_ids')
    def _compute_timesheet_ids(self):
        for order in self:
            if order.project_id:
                order.timesheet_ids = self.env['account.analytic.line'].search(
                    [('so_line', 'in', order.order_line.ids),
                        ('amount', '<=', 0.0),
                        ('project_id', '!=', False)])
            else:
                order.timesheet_ids = []
            order.timesheet_count = len(order.timesheet_ids)

    @api.multi
    @api.constrains('order_line')
    def _check_multi_timesheet(self):
        for order in self:
            count = 0
            for line in order.order_line:
                if line.product_id.track_service == 'timesheet':
                    count += 1
                if count > 1:
                    raise ValidationError(_("You can use only one product on timesheet within the same sale order. You should split your order to include only one contract based on time and material."))
        return {}

    @api.multi
    @api.depends('order_line.product_id.project_id')
    def _compute_tasks_ids(self):
        for order in self:
            order.tasks_ids = self.env['project.task'].search([('sale_line_id', 'in', order.order_line.ids)])
            order.tasks_count = len(order.tasks_ids)

    @api.multi
    def action_view_task(self):
        self.ensure_one()
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('project.action_view_task')
        list_view_id = imd.xmlid_to_res_id('project.view_task_tree2')
        form_view_id = imd.xmlid_to_res_id('project.view_task_form2')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [False, 'kanban'], [form_view_id, 'form'], [False, 'graph'], [False, 'calendar'], [False, 'pivot'], [False, 'graph']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(self.tasks_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % self.tasks_ids.ids
        elif len(self.tasks_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = self.tasks_ids.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.multi
    @api.depends('project_id.project_ids')
    def _compute_project_project_id(self):
        for order in self:
            order.project_project_id = self.env['project.project'].search([('analytic_account_id', '=', order.project_id.id)])

    @api.multi
    def action_view_project_project(self):
        self.ensure_one()
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('project.open_view_project_all')
        form_view_id = imd.xmlid_to_res_id('project.edit_project')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [(form_view_id, 'form')],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
            'res_id': self.project_project_id.id,
        }
        return result

    @api.multi
    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        for order in self:
            if not order.project_project_id:
                for line in order.order_line:
                    if line.product_id.track_service == 'timesheet':
                        if not order.project_id:
                            order._create_analytic_account(prefix=line.product_id.default_code or None)
                        order.project_id.project_create({'name': order.project_id.name, 'use_tasks': True})
                        break
        return result

    @api.multi
    def action_view_timesheet(self):
        self.ensure_one()
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('hr_timesheet.act_hr_timesheet_line')
        list_view_id = imd.xmlid_to_res_id('hr_timesheet.hr_timesheet_line_tree')
        form_view_id = imd.xmlid_to_res_id('hr_timesheet.hr_timesheet_line_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if self.timesheet_count > 0:
            result['domain'] = "[('id','in',%s)]" % self.timesheet_ids.ids
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _compute_analytic(self, domain=None):
        if not domain:
            # To filter on analyic lines linked to an expense
            expense_type_id = self.env.ref('account.data_account_type_expenses', raise_if_not_found=False)
            expense_type_id = expense_type_id and expense_type_id.id
            domain = [
                ('so_line', 'in', self.ids),
                    '|',
                        '|',
                            ('amount', '<', 0.0),
                            ('project_id', '!=', False),
                        '&',
                            ('amount', '=', 0),
                            '|',
                                ('move_id', '=', False),
                                ('move_id.account_id.user_type_id', '=', expense_type_id)
            ]
        return super(SaleOrderLine, self)._compute_analytic(domain=domain)

    @api.model
    def _get_analytic_track_service(self):
        return super(SaleOrderLine, self)._get_analytic_track_service() + ['timesheet', 'task']
