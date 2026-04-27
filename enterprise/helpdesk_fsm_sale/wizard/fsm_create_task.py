# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import models

class CreateTask(models.TransientModel):
    _inherit = 'helpdesk.create.fsm.task'

    def _generate_task_values(self):
        res = super()._generate_task_values()
        if self.helpdesk_ticket_id.sale_line_id:
            res['sale_line_id'] = self.helpdesk_ticket_id.sale_line_id.id
        return res
