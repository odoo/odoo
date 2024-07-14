# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, _lt

class Project(models.Model):
    _inherit = 'project.project'

    ticket_ids = fields.One2many('helpdesk.ticket', 'project_id', string='Tickets')
    ticket_count = fields.Integer('# Tickets', compute='_compute_ticket_count')

    helpdesk_team = fields.One2many('helpdesk.team', 'project_id')
    has_helpdesk_team = fields.Boolean('Has Helpdesk Teams', compute='_compute_has_helpdesk_team', search='_search_has_helpdesk_team', compute_sudo=True)

    @api.depends('ticket_ids.project_id')
    def _compute_ticket_count(self):
        if not self.user_has_groups('helpdesk.group_helpdesk_user'):
            self.ticket_count = 0
            return
        result = self.env['helpdesk.ticket']._read_group([
            ('project_id', 'in', self.ids)
        ], ['project_id'], ['__count'])
        data = {project.id: count for project, count in result}
        for project in self:
            project.ticket_count = data.get(project.id, 0)

    @api.depends('helpdesk_team.project_id')
    def _compute_has_helpdesk_team(self):
        result = self.env['helpdesk.team']._read_group([
            ('project_id', 'in', self.ids)
        ], ['project_id'], ['__count'])
        data = {project.id: count for project, count in result}
        for project in self:
            project.has_helpdesk_team = data.get(project.id, False)

    def _search_has_helpdesk_team(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))

        helpdesk_team_ids = self.env['helpdesk.team']._read_group(
            [('use_helpdesk_timesheet', '=', True), ('project_id', '!=', False)],
            [], ['project_id:recordset']
        )[0][0].ids
        operator_new = "in" if (operator == "=") == bool(value) else "not in"
        return [('id', operator_new, helpdesk_team_ids)]

    def action_open_project_tickets(self):
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk_timesheet.project_project_action_view_helpdesk_tickets")
        action.update({
            'display_name': _('Tickets'),
            'domain': [('id', 'in', self.ticket_ids.ids)],
            'context': {'active_id': self.id},
        })
        if len(self.ticket_ids.ids) == 1:
            action["view_mode"] = 'form'
            action["views"] = [[False, 'form']]
            action["res_id"] = self.ticket_ids.id
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        buttons.append({
            'icon': 'life-ring',
            'text': _lt('Tickets'),
            'number': self.sudo().ticket_count,
            'action_type': 'object',
            'action': 'action_open_project_tickets',
            'show': self.sudo().ticket_count > 0,
            'sequence': 25,
        })
        return buttons
