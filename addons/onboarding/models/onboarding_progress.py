# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


ONBOARDING_PROGRESS_STATES = [
    ('not_done', 'Not done'),
    ('just_done', 'Just done'),
    ('done', 'Done'),
]


class OnboardingProgress(models.Model):
    _name = 'onboarding.progress'
    _description = 'Onboarding Progress Tracker'
    _rec_name = 'onboarding_id'

    onboarding_state = fields.Selection(
        ONBOARDING_PROGRESS_STATES, string='Onboarding progress', compute='_compute_onboarding_state', store=True)
    is_onboarding_closed = fields.Boolean('Was panel closed?')
    company_id = fields.Many2one('res.company', ondelete='cascade')
    onboarding_id = fields.Many2one(
        'onboarding.onboarding', 'Related onboarding tracked', required=True, index=True, ondelete='cascade')
    progress_step_ids = fields.Many2many('onboarding.progress.step', string='Progress Steps Trackers')

    # not in _sql_constraint because COALESCE is not supported for PostgreSQL constraint
    _onboarding_company_uniq = models.UniqueIndex("(onboarding_id, COALESCE(company_id, 0))")

    @api.depends('onboarding_id.step_ids', 'progress_step_ids', 'progress_step_ids.step_state')
    def _compute_onboarding_state(self):
        for progress in self:
            progress.onboarding_state = (
                'not_done' if (
                    len(progress.progress_step_ids.filtered(lambda p: p.step_state in {'just_done', 'done'}))
                    != len(progress.onboarding_id.step_ids)
                )
                else 'done'
            )

    def _recompute_progress_step_ids(self):
        """Update progress steps when a step (with existing progress) is added to an onboarding."""
        for progress in self:
            progress.progress_step_ids = progress.onboarding_id.step_ids.current_progress_step_id

    def action_close(self):
        self.is_onboarding_closed = True

    def action_toggle_visibility(self):
        for progress in self:
            progress.is_onboarding_closed = not progress.is_onboarding_closed

    def _get_and_update_onboarding_state(self):
        """Fetch the progress of an onboarding for rendering its panel.

        This method is expected to only be called by the onboarding controller.
        It also has the responsibility of updating the 'just_done' state into
        'done' so that the 'just_done' states are only rendered once.
        """
        self.ensure_one()
        onboarding_states_values = {}
        progress_steps_to_consolidate = self.env['onboarding.progress.step']

        # Iterate over onboarding step_ids and not self.progress_step_ids because 'not_done' steps
        # may not have a progress_step record.
        for step in self.onboarding_id.step_ids:
            step_state = step.current_step_state
            if step_state == 'just_done':
                progress_steps_to_consolidate |= step.current_progress_step_id
            onboarding_states_values[step.id] = step_state

        progress_steps_to_consolidate.action_consolidate_just_done()

        if self.is_onboarding_closed:
            onboarding_states_values['onboarding_state'] = 'closed'
        elif self.onboarding_state == 'done':
            onboarding_states_values['onboarding_state'] = 'just_done' if progress_steps_to_consolidate else 'done'
        return onboarding_states_values
