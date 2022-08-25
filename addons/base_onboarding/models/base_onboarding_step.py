# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.base_onboarding.models.base_onboarding_state import ONBOARDING_STEP_STATES
from odoo.tools.json import scriptsafe as json_safe


class OnboardingStep(models.Model):
    _name = 'base.onboarding.step'
    _description = 'Onboarding Step'

    name = fields.Char('Name of the onboarding step')
    onboarding_id = fields.Many2one('base.onboarding', required=True)
    is_per_company = fields.Boolean('Is this step to be completed per company?', default=True)

    panel_step_title = fields.Char('Title')
    panel_step_description = fields.Char('Description')
    panel_step_button_text = fields.Char('Button text')
    panel_step_done_icon = fields.Char('Font Awesome Icon when completed', default='fa-star')
    panel_step_done_text = fields.Char(
        'Text to show when step is completed', default='Step Completed! - Click to review')
    panel_step_open_action_name = fields.Char('Action to execute when opening the step')
    panel_step_properties = fields.Text(
        'Panel template properties', compute='_compute_panel_step_properties', store=False, default='')

    step_state = fields.Selection(
        ONBOARDING_STEP_STATES, compute='_compute_step_state', store=False)

    def set_done(self):
        step_state_model = self.env['base.onboarding.step.state']
        for step in self:
            step_state = step_state_model.search_or_create(step)
            if step_state.state == 'not_done':
                step_state.state = 'just_done'

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', 'Onboarding step name must be unique.'),
        ('name_onboarding_company_uniq',
         'unique (name,onboarding_id)',
         'There cannot be multiple records of the same onboarding step for the same company.')
    ]

    @api.depends('panel_step_title', 'panel_step_description', 'panel_step_button_text',
                 'panel_step_done_icon')
    def _compute_panel_step_properties(self):
        for step in self:
            step.panel_step_properties = json_safe.dumps({
                'title': step.panel_step_title,
                'description': step.panel_step_description,
                'btn_text': step.panel_step_button_text,
                'done_icon': step.panel_step_done_icon,
                'done_text': step.panel_step_done_text,
                'method': step.panel_step_open_action_name,
                'model': 'base.onboarding',
                'state': step.step_state,
            })

    @api.depends_context('company')
    def _compute_step_state(self):
        step_state_model = self.env['base.onboarding.step.state']
        for step in self:
            step.step_state = step_state_model.search_or_create(step).state

    def is_done(self):
        self.ensure_one()
        return self.get_state().is_done

    def get_state(self):
        self.ensure_one()
        return self.env['base.onboarding.step.state'].search_or_create(self)

    def consolidate_just_done(self):
        self.ensure_one()
        self.get_state().consolidate_just_done()
