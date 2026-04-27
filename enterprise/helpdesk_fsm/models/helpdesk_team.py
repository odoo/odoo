# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import models, api, fields

class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    fsm_project_id = fields.Many2one('project.project', string='FSM Project', domain=[('is_fsm', '=', True)],
        readonly=False, store=True, compute='_compute_fsm_project_id')

    @api.depends('use_fsm', 'company_id')
    def _compute_fsm_project_id(self):
        '''
        Compute the default fsm project from the same company
        as the helpdesk team when 'use_fsm' is enabled.
        '''
        fsm_teams_without_project = self.filtered(lambda t: t.use_fsm and not t.fsm_project_id)
        if fsm_teams_without_project:
            project_read_group = self.env['project.project'].read_group(
                domain=[
                    ('is_fsm', '=', True),
                    ('company_id', 'in', fsm_teams_without_project.company_id.ids),
                ],
                fields=['ids:array_agg(id)'],
                groupby=['company_id'],
            )
            mapped_project_per_company = {res['company_id'][0]: self.env['project.project'].browse(min(res['ids'])) for res in project_read_group}
        for team in fsm_teams_without_project:
            team.fsm_project_id = mapped_project_per_company.get(team.company_id.id, False)
        (self - fsm_teams_without_project).fsm_project_id = False

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
