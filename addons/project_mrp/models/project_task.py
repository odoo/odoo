# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    mrp_order_count = fields.Integer('# Manufacturing Order Count', compute='_compute_mrp_order_count',
        groups='mrp.group_mrp_user', export_string_translation=False)

    def _compute_mrp_order_count(self):
        mrp_orders_per_task = {mrp_order.id: count
            for mrp_order, count in self.env['mrp.production']._read_group([
                ('task_id', 'in', self.ids),
            ], ['task_id'], ['__count'])}
        for task in self:
            task.mrp_order_count = mrp_orders_per_task.get(task.id, 0)

    @api.model
    def action_create_mrp_order_from_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'form',
            'context': {
                'default_company_id': self.company_id.id or self.env.company.id,
                'default_task_id': self.id,
                'task_id': self.id,
            },
        }

    def action_open_task_mrp_orders(self):
        """ Return the action for the views of the mrp_orders linked to the task."""
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('mrp.mrp_production_action')
        action['domain'] = [('task_id', '=', self.id)]
        action['context'] = {
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_task_id': self.id,
            'task_id': self.id,
        },
        if self.mrp_order_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.env['mrp.production'].search([('task_id', '=', self.id)]).id
            if 'views' in action:
                action['views'] = [
                    (view_id, view_type)
                    for view_id, view_type in action['views']
                    if view_type == 'form'
                ] or [False, 'form']

        return action
