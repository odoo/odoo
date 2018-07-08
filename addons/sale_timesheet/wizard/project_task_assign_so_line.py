# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectTaskAssignSOLine(models.TransientModel):
    _name = 'project.task.assign.sale'
    _description = "Assign Sale Order line to tasks"

    @api.model
    def default_get(self, fields):
        result = super(ProjectTaskAssignSOLine, self).default_get(fields)
        if self._context.get('active_model') == 'project.task' and 'task_ids' in fields:
            result['task_ids'] = self._context.get('active_ids', [])
        return result

    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Item', domain=[('is_service', '=', True)], help="Sale order line to link to selected tasks")
    partner_id = fields.Many2one('res.partner', related='sale_line_id.order_partner_id', readonly=True)
    task_ids = fields.Many2many('project.task', 'project_task_assign_so_line_rel', 'task_id', 'wizard_id', string='Tasks', domain=[('parent_id', '=', False)], help="Select the tasks to assign to the Sale Order Items. You can only choose task (no sub tasks).")

    @api.multi
    def action_assign_sale_line(self):
        for wizard in self:
            wizard.task_ids.write({
                'sale_line_id': wizard.sale_line_id.id,
                'partner_id': wizard.partner_id.id,
            })
        return {'type': 'ir.actions.act_window_close'}
