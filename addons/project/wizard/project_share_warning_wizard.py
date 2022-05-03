# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectShareWarning(models.TransientModel):
    _name = 'project.share.warning.wizard'
    _description = 'Project Share Warning Wizard'

    project_share_id = fields.Many2one('project.share.wizard')
    non_portal_partner_ids = fields.Many2many('res.partner')

    def confirmed_action_send_mail(self):

        self.project_share_id.action_send_mail_post_warning()

        return {'type': 'ir.actions.act_window_close'}
