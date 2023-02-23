# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.addons.onboarding.models.onboarding_progress import ONBOARDING_PROGRESS_STATES


class OnboardingStep(models.Model):
    _name = 'onboarding.onboarding.step'
    _description = 'Onboarding Step'
    _order = 'sequence asc, id asc'
    _rec_name = 'title'

    onboarding_id = fields.Many2one(
        'onboarding.onboarding', string='Onboarding', readonly=True, required=True, ondelete='cascade')

    title = fields.Char('Title', translate=True)
    description = fields.Char('Description', translate=True)
    button_text = fields.Char(
        'Button text', required=True, default=_("Let's do it"), translate=True,
        help="Text on the panel's button to start this step")
    done_icon = fields.Char('Font Awesome Icon when completed', default='fa-star')
    done_text = fields.Char(
        'Text to show when step is completed', default=_('Step Completed! - Click to review'), translate=True)
    panel_step_open_action_name = fields.Char(
        string='Opening action', required=True,
        help='Name of the onboarding step model action to execute when opening the step, '
             'e.g. action_open_onboarding_1_step_1')

    current_progress_step_id = fields.Many2one(
        'onboarding.progress.step', string='Step Progress',
        compute='_compute_current_progress', help='Onboarding Progress Step for the current context (company).')
    current_step_state = fields.Selection(
        ONBOARDING_PROGRESS_STATES, string='Completion State', compute='_compute_current_progress')
    progress_ids = fields.One2many(
        'onboarding.progress.step', 'step_id', string='Onboarding Progress Step Records', readonly=True,
        help='All related Onboarding Progress Step Records (across companies)')

    sequence = fields.Integer(default=10)

    @api.depends_context('company')
    @api.depends('progress_ids', 'progress_ids.step_state')
    def _compute_current_progress(self):
        existing_progress_steps = self.progress_ids.filtered_domain([
            ('step_id', 'in', self.ids),
            ('progress_id.company_id', 'in', [False, self.env.company.id]),
        ])
        for step in self:
            if step in existing_progress_steps.step_id:
                current_progress_step_id = existing_progress_steps.filtered(
                    lambda progress_step: progress_step.step_id == step)
                if len(current_progress_step_id) > 1:
                    current_progress_step_id = current_progress_step_id.sorted('create_date', reverse=True)[0]
                step.current_progress_step_id = current_progress_step_id
                step.current_step_state = current_progress_step_id.step_state
            else:
                step.current_progress_step_id = False
                step.current_step_state = 'not_done'

    def action_set_just_done(self):
        # Make sure progress records exist for the current context (company)
        steps_without_progress = self.filtered(lambda step: not step.current_progress_step_id)
        steps_without_progress._create_progress_steps()
        return self.current_progress_step_id.action_set_just_done()

    def _create_progress_steps(self):
        onboarding_progress_records = self.env['onboarding.progress'].search([
            ('onboarding_id', 'in', self.onboarding_id.ids),
            ('company_id', 'in', [False, self.env.company.id])
        ])
        progress_step_values = []
        for onboarding_progress_record in onboarding_progress_records:
            progress_step_values += [
                {
                    'onboarding_id': onboarding_progress_record.onboarding_id.id,
                    'progress_id': onboarding_progress_record.id,
                    'step_id': step_id.id,
                }
                for step_id
                in self.filtered(lambda step: self.onboarding_id == onboarding_progress_record.onboarding_id)
                if step_id not in onboarding_progress_record.progress_step_ids.step_id
            ]

        return self.env['onboarding.progress.step'].create(progress_step_values)
