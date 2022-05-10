# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ProjectMilestoneReachWizard(models.TransientModel):
    _name = 'project.milestone.reach.wizard'
    _description = 'Mark one or more milestones as reached'

    milestone_id = fields.Many2one(related='line_ids.milestone_id')
    line_ids = fields.One2many('project.milestone.reach.line.wizard', 'wizard_id')
    line_count = fields.Integer(compute='_compute_line_count')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for wizard in self:
            wizard.line_count = len(wizard.line_ids)

    def action_mark_milestone_as_reach(self):
        milestones = self.line_ids.filtered('mark_as_reached').milestone_id if self.line_count > 1 else self.milestone_id
        if not milestones:
            return {'type': 'ir.actions.act_window_close'}
        milestones.is_reached = True
        if len(milestones) == 1:
            message = _('The %s milestone has successfully been marked as reached.', milestones.display_name)
        else:
            message = _('The selected milestones have successfully been marked as reached.')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class ProjectMilestoneReachLineWizard(models.TransientModel):
    _name = 'project.milestone.reach.line.wizard'
    _description = 'Mark a milestone as reached'

    wizard_id = fields.Many2one('project.milestone.reach.wizard', readonly=True)
    milestone_id = fields.Many2one('project.milestone', readonly=True)
    mark_as_reached = fields.Boolean(default=True)
