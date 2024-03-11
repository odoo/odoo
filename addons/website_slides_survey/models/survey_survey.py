# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



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

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_course(self):
        # we consider it's ok to show certification names for people trying to delete courses
        # even if they don't have access to those surveys hence the sudo usage
        certifications = self.sudo().slide_ids.filtered(lambda slide: slide.slide_type == "certification").mapped('survey_id').exists()
        if certifications:
            certifications_course_mapping = [_('- %s (Courses - %s)', certi.title, '; '.join(certi.slide_channel_ids.mapped('name'))) for certi in certifications]
            raise ValidationError(_(
                'Any Survey listed below is currently used as a Course Certification and cannot be deleted:\n%s',
                '\n'.join(certifications_course_mapping)))

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------

    def action_survey_view_slide_channels(self):
        """ Redirect to the channels using the survey as a certification. Open
        in no-create as link between those two comes through a slide, hard to
        keep as default values. """
        action = self.env["ir.actions.actions"]._for_xml_id("website_slides.slide_channel_action_overview")
        action['display_name'] = _("Courses")
        if self.slide_channel_count == 1:
            action.update({'views': [(False, 'form')],
                           'res_id': self.slide_channel_ids[0].id})
        else:
            action.update({'views': [[False, 'tree'], [False, 'form']],
                           'domain': [('id', 'in', self.slide_channel_ids.ids)]})
        action['context'] = dict(
            ast.literal_eval(action.get('context') or '{}'),  # sufficient in most cases
            create=False
        )
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
