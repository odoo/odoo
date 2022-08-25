# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

ONBOARDING_STEP_STATES = [
    ('not_done', 'Not done'),
    ('just_done', 'Just done'),
    ('done', 'Done'),
]
ONBOARDING_STATES_ADDITIONAL_STEPS = [('closed', "Closed")]
ONBOARDING_STATES = ONBOARDING_STEP_STATES + ONBOARDING_STATES_ADDITIONAL_STEPS


class OnboardingStateMixin(models.AbstractModel):
    """Fields and methods common to onboarding and onboarding step states """
    _name = 'base.onboarding.state.mixin'
    _description = 'Onboarding State Mixin'

    company_id = fields.Many2one('res.company')
    state = fields.Selection(selection=ONBOARDING_STEP_STATES, string='Onboarding state', default='not_done')
    is_done = fields.Boolean('Is completed', compute='_compute_is_done')

    def _compute_is_done(self):
        for state in self:
            state.is_done = state.state in {'just_done', 'done'}

    @api.model
    def search_or_create(self, tracked_record):
        tracked_field = self.get_tracked_field()
        domain = self.get_search_domain(tracked_field, tracked_record)
        create_values = self.get_create_values(tracked_field, tracked_record)
        return self.search(domain) or self.create(create_values)

    def get_search_domain(self, tracked_field, tracked_record):
        return [(tracked_field, '=', tracked_record.id)] + (
            [('company_id', '=', self.env.company.id)] if tracked_record.is_per_company else []
        )

    def get_create_values(self, tracked_field, tracked_record):
        return {
            tracked_field: tracked_record.id,
            **({'company_id': self.env.company.id} if tracked_record.is_per_company else {})
        }

    @classmethod
    def get_tracked_field(cls):
        return 'onboarding_id'

    def set_done(self):
        self.set_state('done')

    def set_state(self, state):
        self.state = state


class OnboardingState(models.Model):
    _name = 'base.onboarding.state'
    _inherit = ['base.onboarding.state.mixin']

    _description = 'Onboarding Completion Tracker'

    onboarding_id = fields.Many2one('base.onboarding', 'Onboarding Tracked')
    state = fields.Selection(selection_add=ONBOARDING_STATES_ADDITIONAL_STEPS,
                             compute='_compute_state', store=True)

    _sql_constraints = [
        ('onboarding_company_uniq', 'unique (onboarding_id,company_id)',
         'There cannot be multiple records of the same onboarding completion for the same company.'),
    ]

    @api.depends_context('company')
    @api.depends('onboarding_id.step_ids')
    def _compute_state(self):
        for onboarding_state in self:
            if onboarding_state.state == 'closed':
                continue
            steps = onboarding_state.onboarding_id.step_ids
            for step in steps:
                step_state_record = step.get_state()
                if not step_state_record.is_done:
                    onboarding_state.state = 'not_done'
                    break
            else:
                onboarding_state.state = 'done'


class OnboardingStepState(models.Model):
    _name = 'base.onboarding.step.state'
    _inherit = ['base.onboarding.state.mixin']

    _description = 'Onboarding Step Completion Tracker'

    step_id = fields.Many2one('base.onboarding.step', 'Onboarding Step Tracked')
    state = fields.Selection(string='Onboarding Step State')

    _sql_constraints = [
        ('step_company_uniq', 'unique (step_id,company_id)',
         'There cannot be multiple records of the same onboarding step completion for the same company.'),
    ]

    @classmethod
    def get_tracked_field(cls):
        return 'step_id'

    def consolidate_just_done(self):
        was_just_done = self.filtered_domain([('state', '=', 'just_done')])
        was_just_done.state = 'done'
