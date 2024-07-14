# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools.misc import unique

class HelpdeskStage(models.Model):
    _name = 'helpdesk.stage'
    _description = 'Helpdesk Stage'
    _order = 'sequence, id'

    def _default_team_ids(self):
        team_id = self.env.context.get('default_team_id')
        if team_id:
            return [(4, team_id, 0)]

    active = fields.Boolean(default=True)
    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer('Sequence', default=10)
    fold = fields.Boolean(
        'Folded in Kanban',
        help='Tickets in a folded stage are considered as closed.')
    team_ids = fields.Many2many(
        'helpdesk.team', relation='team_stage_rel', string='Helpdesk Teams',
        default=_default_team_ids, required=True)
    template_id = fields.Many2one(
        'mail.template', 'Email Template',
        domain="[('model', '=', 'helpdesk.ticket')]",
        help="Email automatically sent to the customer when the ticket reaches this stage.\n"
             "By default, the email will be sent from the email alias of the helpdesk team.\n"
             "Otherwise it will be sent from the company's email address, or from the catchall (as defined in the System Parameters).")
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda s: _('Blocked'), translate=True, required=True)
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda s: _('Ready'), translate=True, required=True)
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda s: _('In Progress'), translate=True, required=True)
    ticket_count = fields.Integer(compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        res = self.env['helpdesk.ticket']._read_group(
            [('stage_id', 'in', self.ids)],
            ['stage_id'], ['__count'])
        stage_data = {stage.id: count for stage, count in res}
        for stage in self:
            stage.ticket_count = stage_data.get(stage.id, 0)

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self.env['helpdesk.ticket'].search([('stage_id', 'in', self.ids)]).write({'active': False})
        return super(HelpdeskStage, self).write(vals)

    def toggle_active(self):
        res = super().toggle_active()
        stage_active = self.filtered('active')
        if stage_active and sum(stage_active.with_context(active_test=False).mapped('ticket_count')) > 0:
            wizard = self.env['helpdesk.stage.delete.wizard'].create({
                'stage_ids': stage_active.ids,
            })

            return {
                'name': _('Unarchive Tickets'),
                'view_mode': 'form',
                'res_model': 'helpdesk.stage.delete.wizard',
                'views': [(self.env.ref('helpdesk.view_helpdesk_stage_unarchive_wizard').id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': wizard.id,
                'target': 'new',
            }
        return res

    def action_unlink_wizard(self, stage_view=False):
        self = self.with_context(active_test=False)
        # retrieves all the teams with a least 1 ticket in that stage
        # a ticket can be in a stage even if the team is not assigned to the stage
        readgroup = self.with_context(active_test=False).env['helpdesk.ticket']._read_group(
            [('stage_id', 'in', self.ids), ('team_id', '!=', False)],
            ['team_id'])
        team_ids = list(unique([team.id for [team] in readgroup] + self.team_ids.ids))

        wizard = self.env['helpdesk.stage.delete.wizard'].create({
            'team_ids': team_ids,
            'stage_ids': self.ids
        })

        context = dict(self.env.context)
        context['stage_view'] = stage_view
        return {
            'name': _('Delete Stage'),
            'view_mode': 'form',
            'res_model': 'helpdesk.stage.delete.wizard',
            'views': [(self.env.ref('helpdesk.view_helpdesk_stage_delete_wizard').id, 'form')],
            'type': 'ir.actions.act_window',
            'res_id': wizard.id,
            'target': 'new',
            'context': context,
        }

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action.update({
            'domain': [('stage_id', 'in', self.ids)],
            'context': {
                'default_stage_id': self.id,
            },
        })
        return action
