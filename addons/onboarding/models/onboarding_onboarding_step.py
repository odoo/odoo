# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.addons.onboarding.models.onboarding_progress import ONBOARDING_PROGRESS_STATES
from odoo.exceptions import ValidationError


class OnboardingStep(models.Model):
    _name = 'onboarding.onboarding.step'
    _description = 'Onboarding Step'
    _order = 'sequence asc, id asc'
    _rec_name = 'title'

    onboarding_ids = fields.Many2many('onboarding.onboarding', string='Onboardings')

    title = fields.Char('Title', translate=True)
    description = fields.Char('Description', translate=True)
    button_text = fields.Char(
        'Button text', required=True, default=lambda s: s.env._("Let's do it"), translate=True,
        help="Text on the panel's button to start this step")
    done_icon = fields.Char('Font Awesome Icon when completed', default='fa-star')
    done_text = fields.Char(
        'Text to show when step is completed', default=lambda s: s.env._('Step Completed!'), translate=True)
    step_image = fields.Binary("Step Image")
    step_image_filename = fields.Char("Step Image Filename")
    step_image_alt = fields.Char(
        'Alt Text for the Step Image', default='Onboarding Step Image', translate=True,
        help='Show when impossible to load the image')
    panel_step_open_action_name = fields.Char(
        string='Opening action', required=False,
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

    is_per_company = fields.Boolean('Is per company', default=True)
    sequence = fields.Integer(default=10)

    @api.depends_context('company')
    @api.depends('progress_ids', 'progress_ids.step_state')
    def _compute_current_progress(self):
        # When `is_per_company` is changed, `progress_ids` is updated (see `write`) which triggers this `_compute`.
        existing_progress_steps = self.progress_ids.filtered_domain([
            ('step_id', 'in', self.ids),
            ('company_id', 'in', [False, self.env.company.id]),
        ])
        for step in self:
            if step in existing_progress_steps.step_id:
                current_progress_step_id = existing_progress_steps.filtered(
                    lambda progress_step: progress_step.step_id == step)
                step.current_progress_step_id = current_progress_step_id
                step.current_step_state = current_progress_step_id.step_state
            else:
                step.current_progress_step_id = False
                step.current_step_state = 'not_done'

    @api.constrains('onboarding_ids')
    def check_step_on_onboarding_has_action(self):
        if steps_without_action := self.filtered(lambda step: step.onboarding_ids and not step.panel_step_open_action_name):
            raise ValidationError(_(
                'An "Opening Action" is required for the following steps to be '
                'linked to an onboarding panel: %(step_titles)s',
                step_titles=steps_without_action.mapped('title'),
            ))

    def write(self, vals):
        new_is_per_company = vals.get('is_per_company')
        steps_changing_is_per_company = (
            self.browse() if new_is_per_company is None
            else self.filtered(lambda step: step.is_per_company != new_is_per_company)
        )
        already_linked_onboardings = self.onboarding_ids

        res = super().write(vals)

        # Progress is reset (to be done per-company or, for steps, to have a single record)
        if steps_changing_is_per_company:
            steps_changing_is_per_company.progress_ids.unlink()
        self.onboarding_ids.action_refresh_progress_ids()

        if self.onboarding_ids - already_linked_onboardings:
            self.onboarding_ids.progress_ids._recompute_progress_step_ids()

        return res

    def action_set_just_done(self):
        # Make sure progress records exist for the current context (company)
        steps_without_progress = self.filtered(lambda step: not step.current_progress_step_id)
        steps_without_progress._create_progress_steps()
        return self.current_progress_step_id.action_set_just_done().step_id

    @api.model
    def action_validate_step(self, xml_id):
        step = self.env.ref(xml_id, raise_if_not_found=False)
        if not step:
            return "NOT_FOUND"
        return "JUST_DONE" if step.action_set_just_done() else "WAS_DONE"

    @api.model
    def _get_placeholder_filename(self, field):
        if field == "step_image":
            return 'base/static/img/onboarding_default.png'
        return super()._get_placeholder_filename(field)

    def _create_progress_steps(self):
        """Create progress step records as necessary to validate steps.

        Only considers existing `onboarding.progress` records for the current
        company or without company (depending on `is_per_company`).
        """
        onboarding_progress_records = self.env['onboarding.progress'].search([
            ('onboarding_id', 'in', self.onboarding_ids.ids),
            ('company_id', 'in', [False, self.env.company.id])
        ])
        progress_step_values = [
            {
                'step_id': step_id.id,
                'progress_ids': [
                    Command.link(onboarding_progress_record.id)
                    for onboarding_progress_record
                    in onboarding_progress_records.filtered(lambda p: step_id in p.onboarding_id.step_ids)],
                'company_id': self.env.company.id if step_id.is_per_company else False,
            } for step_id in self
        ]
        return self.env['onboarding.progress.step'].create(progress_step_values)
