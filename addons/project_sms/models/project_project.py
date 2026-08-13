# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    def _send_sms(self):
        for project in self:
            if project.partner_id and project.stage_id and project.stage_id.sms_template_id:
                project._message_sms_with_template(
                    template=project.stage_id.sms_template_id,
                    partner_ids=project.partner_id.ids,
                )

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        projects._send_sms()
        return projects

    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            self._send_sms()
        return res
