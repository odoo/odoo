# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Project(models.Model):
    _inherit = "project.task"

    purchase_order_count = fields.Integer('# Purchase Orders', compute='_compute_purchase_order_count', groups='purchase.group_purchase_user')

    def _compute_purchase_order_count(self):
        purchase_orders_per_task = {purchase_order['task_id'][0]: purchase_order['task_id_count']
        for purchase_order in self.env['purchase.order']._read_group([
            ('task_id', 'in', self.ids),
        ], ['task_id'], ['task_id'])}
        for task in self:
            task.purchase_order_count = purchase_orders_per_task.get(task.id, 0)

    # ----------------------------
    #  Actions
    # ----------------------------

    @api.model
    def action_create_purchase_order_from_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'context': {'default_task_id': self.id, 'task_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_open_task_purchase_orders(self):
        """ Return the action for the views of the purchase order linked to the task.

        Note: self.ensure_one()

        :return: The action
        :rtype: dict
        """
        self.ensure_one()
        purchase_order_ids = self.env['purchase.order'].search([('task_id', '=', self.id)])
        action = {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
            'context': {'default_task_id': self.id, 'task_id': self.id,},
        }
        if len(purchase_order_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = purchase_order_ids.id

        return action
