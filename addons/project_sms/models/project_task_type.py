# -*- coding: utf-8 -*-
from odoo.addons import project
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectTaskType(models.Model, project.ProjectTaskType):

    sms_template_id = fields.Many2one('sms.template', string="SMS Template",
        domain=[('model', '=', 'project.task')],
        help="If set, an SMS Text Message will be automatically sent to the customer when the task reaches this stage.")
