# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, fields, exceptions
from openerp.tools.translate import _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tasks_ids = fields.Many2many('project.task', compute='_compute_tasks_ids', string='Tasks associated to this sale')
    tasks_count = fields.Integer(string='Tasks', compute='_compute_tasks_ids')

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


class product_template(models.Model):
    _inherit = "product.template"
    project_id = fields.Many2one('project.project', string='Project', ondelete='set null')
    track_service = fields.Selection(selection_add=[('task', 'Create a task and track hours')])


class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _update_values(self, values):
        if values.get('task_id', False):
            task = self.env['project.task'].browse(values['task_id'])
            values['so_line'] = task.sale_line_id and task.sale_line_id.id or values.get('so_line', False)

    @api.model
    def create(self, values):
        self._update_values(values)
        result = super(account_analytic_line, self).create(values)
        return result

    @api.multi
    def write(self, values):
        self._update_values(values)
        result = super(account_analytic_line, self).write(values)
        return result
