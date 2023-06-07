# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _send_sms(self):
        for task in self:
            if task.partner_id and task.stage_id and task.stage_id.sms_template_id:
                task._message_sms_with_template(
                    template=task.stage_id.sms_template_id,
                    partner_ids=task.partner_id.ids,
                )

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        tasks._send_sms()
        return tasks

    def write(self, vals):
        res = super().write(vals)

        if 'stage_id' in vals:
            if self.env.user.has_group('base.group_portal') and not self.env.su:
                # sudo as sms template model is protected
                self.sudo()._send_sms()
            else:
                self._send_sms()
        return res
