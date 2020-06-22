# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SlidePartnerRelation(models.Model):
    _inherit = 'slide.slide.partner'

    user_input_ids = fields.One2many('survey.user_input', 'slide_partner_id', 'Certification attempts')
    survey_scoring_success = fields.Boolean('Certification Succeeded', compute='_compute_survey_scoring_success', store=True)

    @api.depends('partner_id', 'user_input_ids.scoring_success')
    def _compute_survey_scoring_success(self):
        succeeded_user_inputs = self.env['survey.user_input'].sudo().search([
            ('slide_partner_id', 'in', self.ids),
            ('scoring_success', '=', True)
        ])
        succeeded_slide_partners = succeeded_user_inputs.mapped('slide_partner_id')
        for record in self:
            record.survey_scoring_success = record in succeeded_slide_partners

    def _compute_field_value(self, field):
        super()._compute_field_value(field)
        if field.name == 'survey_scoring_success':
            self.filtered('survey_scoring_success').write({
                'completed': True
            })

class Slide(models.Model):
    _inherit = 'slide.slide'

    slide_type = fields.Selection(selection_add=[
        ('certification', 'Certification')
    ], ondelete={'certification': 'set default'})
    survey_id = fields.Many2one('survey.survey', 'Certification')
    nbr_certification = fields.Integer("Number of Certifications", compute='_compute_slides_statistics', store=True)

    _sql_constraints = [
        ('check_survey_id', "CHECK(slide_type != 'certification' OR survey_id IS NOT NULL)", "A slide of type 'certification' requires a certification."),
        ('check_certification_preview', "CHECK(slide_type != 'certification' OR is_preview = False)", "A slide of type certification cannot be previewed."),
    ]

    @api.onchange('survey_id')
    def _on_change_survey_id(self):
        if self.survey_id:
            self.slide_type = 'certification'

    @api.model
    def create(self, values):
        rec = super(Slide, self).create(values)
        if rec.survey_id:
            rec.slide_type = 'certification'
        if 'survey_id' in values:
            rec._ensure_challenge_category()
        return rec

    def write(self, values):
        old_surveys = self.mapped('survey_id')
        result = super(Slide, self).write(values)
        if 'survey_id' in values:
            self._ensure_challenge_category(old_surveys=old_surveys - self.mapped('survey_id'))
        return result

    def unlink(self):
        old_surveys = self.mapped('survey_id')
        result = super(Slide, self).unlink()
        self._ensure_challenge_category(old_surveys=old_surveys, unlink=True)
        return result

    def _ensure_challenge_category(self, old_surveys=None, unlink=False):
        """ If a slide is linked to a survey that gives a badge, the challenge category of this badge must be
        set to 'slides' in order to appear under the certification badge list on ranks_badges page.
        If the survey is unlinked from the slide, the challenge category must be reset to 'certification'"""
        if old_surveys:
            old_certification_challenges = old_surveys.mapped('certification_badge_id').challenge_ids
            old_certification_challenges.write({'challenge_category': 'certification'})
        if not unlink:
            certification_challenges = self.mapped('survey_id').mapped('certification_badge_id').challenge_ids
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
        for slide in self.filtered(lambda slide: slide.slide_type == 'certification' and slide.survey_id):
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
