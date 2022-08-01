# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectProjectStage(models.Model):
    _inherit = 'project.project.stage'

    sms_template_id = fields.Many2one('sms.template', string="SMS Template",
        domain=[('model', '=', 'project.project')], help="SMS sent when a task is moved to this stage.")
