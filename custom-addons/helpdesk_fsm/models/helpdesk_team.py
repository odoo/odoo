# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import models, api, fields

class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    @api.model
    def _default_fsm_project_id(self):
        project = self.env['project.project'].search([('is_fsm', '=', True)], limit=1)
        return project

    fsm_project_id = fields.Many2one('project.project', string='FSM Project', domain=[('is_fsm', '=', True)],
                                     default=_default_fsm_project_id)

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _mail_get_message_subtypes(self):
        res = super()._mail_get_message_subtypes()
        if len(self) == 1:
            task_done_subtype = self.env.ref('helpdesk_fsm.mt_team_ticket_task_done')
            if not self.use_fsm and task_done_subtype in res:
                res -= task_done_subtype
        return res
