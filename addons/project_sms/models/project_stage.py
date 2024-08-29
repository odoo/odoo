# -*- coding: utf-8 -*-
from odoo.addons import project
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectProjectStage(models.Model, project.ProjectProjectStage):

    sms_template_id = fields.Many2one('sms.template', string="SMS Template",
        domain=[('model', '=', 'project.project')],
        help="If set, an SMS Text Message will be automatically sent to the customer when the project reaches this stage.")
