# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProjectTask(models.Model):
    _inherit = "project.task"

    mrp_order_count = fields.Integer('# Manufacturing Order Count', compute='_compute_mrp_order_count', groups='mrp.group_mrp_user')

    def _compute_mrp_order_count(self):
        mrp_orders_per_task = {order['task_id'][0]: order['task_id_count']
            for order in self.env['mrp.production']._read_group([
                ('task_id', 'in', self.ids),
            ], ['task_id'], ['task_id'])}
        for task in self:
            task.mrp_order_count = mrp_orders_per_task.get(task.id, 0)

    @api.model
    def action_create_mrp_order_from_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'form',
            'context': {'default_task_id': self.id, 'default_analytic_account_id': self.analytic_account_id.id},
        }

    def action_open_task_mrp_orders(self):
        """ Return the action for the views of the mrp_orders linked to the task."""
        self.ensure_one()
        mrp_order_ids = self.env['mrp.production'].search([('task_id', '=', self.id)])
        action = {
            'name': _('Manufacturing Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
            'context': {'default_task_id': self.id},
        }
        if len(mrp_order_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = mrp_order_ids.id

        return action
