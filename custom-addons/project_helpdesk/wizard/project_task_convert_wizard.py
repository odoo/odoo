# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class ProjectTaskConvertWizard(models.TransientModel):
    _name = 'project.task.convert.wizard'
    _description = 'Convert Project Tasks to Tickets'

    @api.model
    def default_get(self, field_list):
        result = super().default_get(field_list)
        if 'team_id' in field_list and not result.get('team_id'):
            result['team_id'] = self._default_team_id() or self.env['helpdesk.team'].search([], limit=1).id
        return result

    def _default_team_id(self):
        # This method is meant to be overridden.
        return False

    team_id = fields.Many2one('helpdesk.team', string='Team')
    stage_id = fields.Many2one('helpdesk.stage', string='Stage', domain="[('team_ids', 'in', team_id)]",
        compute='_compute_default_stage', readonly=False, store=True, required=True)

    @api.depends('team_id')
    def _compute_default_stage(self):
        self.stage_id = self.team_id.stage_ids[0].id if self.team_id.stage_ids else False

    def action_convert(self):
        tasks_to_convert = self._get_tasks_to_convert()

        created_tickets = self.env['helpdesk.ticket'].with_context(mail_create_nolog=True).create(
            [self._get_ticket_values(task) for task in tasks_to_convert]
        )

        for task, ticket in zip(tasks_to_convert, created_tickets):
            task.active = False

            task_sudo, ticket_sudo = task.sudo(), ticket.sudo()
            task_sudo.message_post(body=_("Task converted into ticket %s", ticket_sudo._get_html_link()))
            ticket_sudo.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': ticket_sudo, 'origin': task_sudo},
                subtype_xmlid='mail.mt_note',
            )

        if len(created_tickets) == 1:
            return {
                'view_mode': 'form',
                'res_model': 'helpdesk.ticket',
                'res_id': created_tickets[0].id,
                'views': [(False, 'form')],
                'type': 'ir.actions.act_window',
            }
        return {
            'name': _('Converted Tickets'),
            'view_mode': 'tree,form',
            'res_model': 'helpdesk.ticket',
            'views': [(False, 'tree'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', created_tickets.ids)],
        }

    def _get_tasks_to_convert(self):
        to_convert_ids = self.env.context.get('to_convert', [])
        return self.env['project.task'].browse(to_convert_ids)

    def _get_ticket_values(self, task):
        return {
            'name': task.name,
            'description': task.description,
            'team_id': self.team_id.id,
            'stage_id': self.stage_id.id,
            'partner_id': task.partner_id.id,
        }
