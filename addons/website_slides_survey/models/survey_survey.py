# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Survey(models.Model):
    _inherit = 'survey.survey'

    slide_ids = fields.One2many(
        'slide.slide', 'survey_id', string="Certification Slides",
        help="The slides this survey is linked to through the e-learning application")
    slide_channel_ids = fields.One2many(
        'slide.channel', string="Certification Courses", compute='_compute_slide_channel_data',
        help="The courses this survey is linked to through the e-learning application",
        groups='website_slides.group_website_slides_officer')
    slide_channel_count = fields.Integer("Courses Count", compute='_compute_slide_channel_data', groups='website_slides.group_website_slides_officer')

    @api.depends('slide_ids.channel_id')
    def _compute_slide_channel_data(self):
        for survey in self:
            survey.slide_channel_ids = survey.slide_ids.mapped('channel_id')
            survey.slide_channel_count = len(survey.slide_channel_ids)

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------

    def action_survey_view_slide_channels(self):
        action = self.env["ir.actions.actions"]._for_xml_id("website_slides.slide_channel_action_overview")
        action['display_name'] = _("Courses")
        if self.slide_channel_count == 1:
            action.update({'views': [(False, 'form')],
                           'res_id': self.slide_channel_ids[0].id})
        else:
            action.update({'views': [[False, 'tree'], [False, 'form']],
                           'domain': [('id', 'in', self.slide_channel_ids.ids)]})
        return action

    # ---------------------------------------------------------
    # Business
    # ---------------------------------------------------------

    def _check_answer_creation(self, user, partner, email, test_entry=False, check_attempts=True, invite_token=False):
        """ Overridden to allow website_slides_officer to test certifications. """
        self.ensure_one()
        if test_entry and user.has_group('website_slides.group_website_slides_officer'):
            return True

        return super(Survey, self)._check_answer_creation(user, partner, email, test_entry=test_entry, check_attempts=check_attempts, invite_token=invite_token)

    def _prepare_challenge_category(self):
        slide_survey = self.env['slide.slide'].search([('survey_id', '=', self.id)])
        return 'slides' if slide_survey else 'certification'
