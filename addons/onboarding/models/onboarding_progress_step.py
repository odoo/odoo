# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.onboarding.models.onboarding_progress import ONBOARDING_PROGRESS_STATES


class OnboardingProgressStep(models.Model):
    _name = 'onboarding.progress.step'
    _description = 'Onboarding Progress Step Tracker'
    _rec_name = 'step_id'

    progress_id = fields.Many2one(
        'onboarding.progress', 'Related Onboarding Progress Tracker', required=True, ondelete='cascade')
    step_state = fields.Selection(
        ONBOARDING_PROGRESS_STATES, string='Onboarding Step Progress', default='not_done')
    onboarding_id = fields.Many2one(related='progress_id.onboarding_id', string='Onboarding')
    step_id = fields.Many2one(
        'onboarding.onboarding.step', string='Onboarding Step', required=True, ondelete='cascade')

    _sql_constraints = [
        ('progress_step_uniq', 'unique (progress_id, step_id)',
         'There cannot be multiple records of the same onboarding step completion for the same Progress record.'),
    ]

    def action_consolidate_just_done(self):
        was_just_done = self.filtered(lambda progress: progress.step_state == 'just_done')
        was_just_done.step_state = 'done'
        return was_just_done

    def action_set_just_done(self):
        not_done = self.filtered_domain([('step_state', '=', 'not_done')])
        not_done.step_state = 'just_done'
        return not_done
