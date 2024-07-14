# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

class Task(models.Model):
    _inherit = 'project.task'

    def action_convert_to_ticket(self):
        if any(task.recurring_task for task in self):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('Recurring tasks cannot be converted into tickets.'),
                }
            }
        return {
            'name': _('Convert to Ticket'),
            'view_mode': 'form',
            'res_model': 'project.task.convert.wizard',
            'views': [(False, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                **self.env.context,
                'to_convert': self.ids,
                'dialog_size': 'medium',
            },
        }
