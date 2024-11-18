# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class SlideSlidePartner(models.Model):
    _inherit = 'slide.slide.partner'

    user_input_ids = fields.One2many('survey.user_input', 'slide_partner_id', 'Certification attempts')
    survey_scoring_success = fields.Boolean('Certification Succeeded', compute='_compute_survey_scoring_success', store=True)

    @api.depends('partner_id', 'user_input_ids.scoring_success')
    def _compute_survey_scoring_success(self):
        succeeded_user_inputs = self.env['survey.user_input'].sudo().search([
            ('slide_partner_id', 'in', self.ids),
            ('scoring_success', '=', True)
        ])
        succeeded_slide_partners = succeeded_user_inputs.slide_partner_id
        for record in self:
            record.survey_scoring_success = record in succeeded_slide_partners

    def _compute_field_value(self, field):
        super()._compute_field_value(field)
        if field.name == 'survey_scoring_success':
            self.filtered('survey_scoring_success').write({
                'completed': True
            })

    def _recompute_completion(self):
        super()._recompute_completion()
        # Update certified partners
        certification_success_slides = self.filtered(lambda slide: slide.survey_scoring_success)
        if not certification_success_slides:
            return
        certified_channels_domain = expression.OR([
            [('partner_id', '=', slide.partner_id.id), ('channel_id', '=', slide.channel_id.id)]
            for slide in certification_success_slides
        ])
        self.env['slide.channel.partner'].search(expression.AND([
            [("survey_certification_success", "=", False)],
            certified_channels_domain]
        )).survey_certification_success = True


class SlideSlide(models.Model):
    _inherit = 'slide.slide'

    name = fields.Char(compute='_compute_name', readonly=False, store=True)
    slide_category = fields.Selection(selection_add=[
        ('certification', 'Certification')
    ], ondelete={'certification': 'set default'})
    slide_type = fields.Selection(selection_add=[
        ('certification', 'Certification')
    ], ondelete={'certification': 'set null'})
    survey_id = fields.Many2one('survey.survey', 'Certification')
    nbr_certification = fields.Integer("Number of Certifications", compute='_compute_slides_statistics', store=True)
    # small override of 'is_preview' to uncheck it automatically for slides of type 'certification'
    is_preview = fields.Boolean(compute='_compute_is_preview', readonly=False, store=True)

    _check_survey_id = models.Constraint(
        "CHECK(slide_category != 'certification' OR survey_id IS NOT NULL)",
        "A slide of type 'certification' requires a certification.",
    )
    _check_certification_preview = models.Constraint(
        "CHECK(slide_category != 'certification' OR is_preview = False)",
        'A slide of type certification cannot be previewed.',
    )

    @api.depends('survey_id')
    def _compute_name(self):
        for slide in self:
            if not slide.name and slide.survey_id:
                slide.name = slide.survey_id.title

    def _compute_mark_complete_actions(self):
        slides_certification = self.filtered(lambda slide: slide.slide_category == 'certification')
        slides_certification.can_self_mark_uncompleted = False
        slides_certification.can_self_mark_completed = False
        super(SlideSlide, self - slides_certification)._compute_mark_complete_actions()

    @api.depends('slide_category')
    def _compute_is_preview(self):
        for slide in self:
            if slide.slide_category == 'certification' or not slide.is_preview:
                slide.is_preview = False

    @api.depends('slide_type')
    def _compute_slide_icon_class(self):
        certification = self.filtered(lambda slide: slide.slide_type == 'certification')
        certification.slide_icon_class = 'fa-trophy'
        super(SlideSlide, self - certification)._compute_slide_icon_class()

    @api.depends('slide_category', 'source_type')
    def _compute_slide_type(self):
        super()._compute_slide_type()
        for slide in self:
            if slide.slide_category == 'certification':
                slide.slide_type = 'certification'

    @api.model_create_multi
    def create(self, vals_list):
        slides = super().create(vals_list)
        slides_with_survey = slides.filtered('survey_id')
        slides_with_survey.slide_category = 'certification'
        slides_with_survey._ensure_challenge_category()
        return slides

    def write(self, values):
        old_surveys = self.survey_id
        result = super().write(values)
        if 'survey_id' in values:
            self._ensure_challenge_category(old_surveys=old_surveys - self.survey_id)
        return result

    def unlink(self):
        old_surveys = self.survey_id
        result = super().unlink()
        self._ensure_challenge_category(old_surveys=old_surveys, unlink=True)
        return result

    def _ensure_challenge_category(self, old_surveys=None, unlink=False):
        """ If a slide is linked to a survey that gives a badge, the challenge category of this badge must be
        set to 'slides' in order to appear under the certification badge list on ranks_badges page.
        If the survey is unlinked from the slide, the challenge category must be reset to 'certification'"""
        if old_surveys:
            old_certification_challenges = old_surveys.certification_badge_id.challenge_ids
            old_certification_challenges.write({'challenge_category': 'certification'})
        if not unlink:
            certification_challenges = self.survey_id.certification_badge_id.challenge_ids
            certification_challenges.write({'challenge_category': 'slides'})

    def _generate_certification_url(self):
        """ get a map of certification url for certification slide from `self`. The url will come from the survey user input:
                1/ existing and not done user_input for member of the course
                2/ create a new user_input for member
                3/ for no member, a test user_input is created and the url is returned
            Note: the slide.slides.partner should already exist

            We have to generate a new invite_token to differentiate pools of attempts since the
            course can be enrolled multiple times.
        """
        certification_urls = {}
        for slide in self.filtered(lambda slide: slide.slide_category == 'certification' and slide.survey_id):
            if slide.channel_id.is_member:
                user_membership_id_sudo = slide.user_membership_id.sudo()
                if user_membership_id_sudo.user_input_ids:
                    last_user_input = next(user_input for user_input in user_membership_id_sudo.user_input_ids.sorted(
                        lambda user_input: user_input.create_date, reverse=True
                    ))
                    certification_urls[slide.id] = last_user_input.get_start_url()
                else:
                    user_input = slide.survey_id.sudo()._create_answer(
                        partner=self.env.user.partner_id,
                        check_attempts=False,
                        **{
                            'slide_id': slide.id,
                            'slide_partner_id': user_membership_id_sudo.id
                        },
                        invite_token=self.env['survey.user_input']._generate_invite_token()
                    )
                    certification_urls[slide.id] = user_input.get_start_url()
            else:
                user_input = slide.survey_id.sudo()._create_answer(
                    partner=self.env.user.partner_id,
                    check_attempts=False,
                    test_entry=True, **{
                        'slide_id': slide.id
                    }
                )
                certification_urls[slide.id] = user_input.get_start_url()
        return certification_urls
