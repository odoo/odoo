# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SlidePartnerRelation(models.Model):
    _inherit = 'slide.slide.partner'

    user_input_ids = fields.One2many('survey.user_input', 'slide_partner_id', 'Certification attempts')
    survey_quizz_passed = fields.Boolean('Certification Quizz Passed', compute='_compute_survey_quizz_passed', store=True)

    @api.depends('partner_id', 'user_input_ids.quizz_passed')
    def _compute_survey_quizz_passed(self):
        passed_user_inputs = self.env['survey.user_input'].sudo().search([
            ('slide_partner_id', 'in', self.ids),
            ('quizz_passed', '=', True)
        ])
        passed_slide_partners = passed_user_inputs.mapped('slide_partner_id')
        for record in self:
            record.survey_quizz_passed = record in passed_slide_partners

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SlidePartnerRelation, self).create(vals_list)
        completed = res.filtered('survey_quizz_passed')
        if completed:
            completed.write({'completed': True})
        return res

    def _write(self, vals):
        res = super(SlidePartnerRelation, self)._write(vals)
        if vals.get('survey_quizz_passed'):
            self.sudo().write({'completed': True})
        return res


class Slide(models.Model):
    _inherit = 'slide.slide'

    slide_type = fields.Selection(selection_add=[('certification', 'Certification')])
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
        return rec

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
                    certification_urls[slide.id] = last_user_input._get_survey_url()
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
                    certification_urls[slide.id] = user_input._get_survey_url()
            else:
                user_input = slide.survey_id.sudo()._create_answer(
                    partner=self.env.user.partner_id,
                    check_attempts=False,
                    test_entry=True, **{
                        'slide_id': slide.id
                    }
                )
                certification_urls[slide.id] = user_input._get_survey_url()
        return certification_urls
