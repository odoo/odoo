# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


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
    @api.depends('order_line.product_id.project_id')
    def _compute_tasks_ids(self):
        for order in self:
            order.tasks_ids = self.env['project.task'].search([('sale_line_id', 'in', order.order_line.ids)])
            order.tasks_count = len(order.tasks_ids)

    @api.multi
    @api.depends('project_id.project_ids')
    def _compute_project_project_id(self):
        for order in self:
            order.project_project_id = self.env['project.project'].search([('analytic_account_id', '=', order.project_id.id)])

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
    def action_view_task(self):
        self.ensure_one()
        action = self.env.ref('project.action_view_task')
        list_view_id = self.env.ref('project.view_task_tree2').id
        form_view_id = self.env.ref('project.view_task_form2').id

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[False, 'kanban'], [list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'calendar'], [False, 'pivot'], [False, 'graph']],
            'target': action.target,
            'context': "{'group_by':'stage_id'}",
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
    def action_view_project_project(self):
        self.ensure_one()
        action = self.env.ref('project.open_view_project_all').read()[0]
        form_view_id = self.env.ref('project.edit_project').id

        action['views'] = [(form_view_id, 'form')]
        action['res_id'] = self.project_project_id.id
        action.pop('target', None)

        return action

    @api.multi
    def action_view_timesheet(self):
        self.ensure_one()
        action = self.env.ref('hr_timesheet.act_hr_timesheet_line')
        list_view_id = self.env.ref('hr_timesheet.hr_timesheet_line_tree').id
        form_view_id = self.env.ref('hr_timesheet.hr_timesheet_line_form').id

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

    @api.model
    def create(self, values):
        line = super(SaleOrderLine, self).create(values)
        if line.state == 'sale' and not line.order_id.project_id and line.product_id.track_service in ['timesheet', 'task']:
            line.order_id._create_analytic_account()
        return line

    @api.multi
    def _compute_analytic(self, domain=None):
        if not domain:
            # To filter on analyic lines linked to an expense
            domain = [('so_line', 'in', self.ids), '|', ('amount', '<=', 0.0), ('project_id', '!=', False)]
        return super(SaleOrderLine, self)._compute_analytic(domain=domain)
