# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    sms_template_id = fields.Many2one('sms.template', string="SMS Template",
        domain=[('model', '=', 'project.task')], help="SMS sent when a task is moved to this stage.")
