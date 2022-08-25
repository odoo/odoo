# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from .base_onboarding_state import ONBOARDING_STATES
from odoo.tools.json import scriptsafe as json_safe


class Onboarding(models.Model):
    _name = 'base.onboarding'
    _description = 'Onboarding'

    name = fields.Char('Name of the onboarding')
    route_name = fields.Char(
        'Short name to use in route', default=lambda s: s.name.replace(' ', '') if s.name else 'route')
    step_ids = fields.One2many('base.onboarding.step', 'onboarding_id', 'Onboarding steps')

    panel_background_color = fields.Selection(
        [('orange', 'Orange'), ('blue', 'Blue')], default='orange')
    panel_background_image_url = fields.Char("URL for the panel's background image")
    panel_properties = fields.Text(
        'Panel template properties', compute='_compute_panel_properties', store=False, default='')
    panel_close_action_name = fields.Char('Action to execute when closing the panel')

    is_per_company = fields.Boolean(
        'Should any of the onboarding steps be done for each company', compute='_compute_is_per_company',
        readonly=True)

    is_done = fields.Boolean('Is completed', compute='_compute_is_done')
    is_closed = fields.Boolean('Is completed', compute='_compute_is_closed')

    onboarding_state = fields.Selection(
        ONBOARDING_STATES, string='Onboarding Completion state', compute='_compute_onboarding_state',
        store=False)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', 'Onboarding name must be unique.')
    ]

    @api.depends_context('company')
    @api.depends('panel_background_color', 'panel_background_image_url')
    def _compute_panel_properties(self):
        for onboarding in self:
            onboarding.panel_properties = json_safe.dumps({
                'classes': f'o_onboarding_{onboarding.panel_background_color}',
                'bg_image': onboarding.panel_background_image_url,
                'close_method': onboarding.panel_close_action_name,
                'close_model': 'base.onboarding',
                'state': onboarding.get_and_update_onboarding_states(),
            })

    @api.depends_context('company')
    def _compute_is_closed(self):
        for onboarding in self:
            onboarding.is_done = onboarding.onboarding_state == 'closed'

    @api.depends_context('company')
    def _compute_is_done(self):
        for onboarding in self:
            onboarding.is_done = onboarding.onboarding_state in {'just_done', 'done'}

    @api.depends('step_ids.is_per_company')
    def _compute_is_per_company(self):
        for onboarding in self:
            onboarding.is_per_company = any(step.is_per_company for step in onboarding.step_ids)

    @api.depends_context('company')
    def _compute_onboarding_state(self):
        for onboarding in self:
            state_record = onboarding._get_onboarding_state()
            onboarding.onboarding_state = state_record.state

    def close(self):
        """Close the onboarding panel."""
        self.set_state('closed')

    def get_and_update_onboarding_states(self):
        self.ensure_one()
        old_values = {}
        if not self.step_ids:
            return {}
        all_done = True
        for step in self.step_ids:
            old_values[step.name] = step.step_state
            step.consolidate_just_done()
            if not step.is_done():
                all_done = False

        if all_done:
            old_values['onboarding_state'] = ('just_done' if self.onboarding_state == 'not_done'
                                              else 'done')
            if self.onboarding_state != 'closed':
                self.set_state('done')
        else:
            old_values['onboarding_state'] = self.onboarding_state

        return old_values

    def set_state(self, state):
        for onboarding in self:
            state_record = self.env['base.onboarding.state'].search_or_create(onboarding)
            state_record.set_state(state)

    def _get_onboarding_state(self):
        self.ensure_one()
        return self.env['base.onboarding.state'].search_or_create(self)
