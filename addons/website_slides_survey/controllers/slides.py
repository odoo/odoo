# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.controllers.main import WebsiteSlides

from odoo.http import request


class WebsiteSlides(WebsiteSlides):
    def _get_valid_slide_post_values(self):
        result = super(WebsiteSlides, self)._get_valid_slide_post_values()
        result.append('survey_id')
        return result

    def _get_slide_detail(self, slide):
        """ If the slide is a certification, we pass to the template additional information:
        - The certification url, built with the latest attempt (survey.user_input) token
        - A 'quizz_passed' boolean to know if we have to show the 'download certification' button
        - The 'survey_id' to be able to download the certification

        If the user is not a member of the channel, we give the opportunity to test the certification.
        The user still has to have the necessary rights, please check survey.survey._check_answer_creation
        for more info.
        This is used in the context of a website_publisher designing a course."""
        result = super(WebsiteSlides, self)._get_slide_detail(slide)
        if not request.env.user._is_public() and slide.slide_type == 'certification' and slide.survey_id:
            if slide.channel_id.is_member:
                user_membership_id_sudo = slide.user_membership_id.sudo()
                quizz_passed = user_membership_id_sudo.survey_quizz_passed
                result['quizz_passed'] = quizz_passed
                result['survey_id'] = slide.survey_id.id
                if not quizz_passed:
                    last_user_input = next(user_input for user_input in user_membership_id_sudo.user_input_ids.sorted(
                        lambda user_input: user_input.create_date, reverse=True
                    ))
                    result['certification_url'] = last_user_input._get_survey_url()
            else:
                result['quizz_passed'] = False
                result['test_entry'] = True
                user_input = slide.survey_id._create_answer(
                    partner=request.env.user.partner_id,
                    check_attempts=False,
                    test_entry=True, **{
                        'slide_id': slide.id
                    }
                )
                result['certification_url'] = user_input._get_survey_url()

        return result

    # Profile
    # ---------------------------------------------------
    def _prepare_user_slides_profile(self, user):
        values = super(WebsiteSlides, self)._prepare_user_slides_profile(user)
        values.update({
            'certificates': self._get_user_certificates(user),
        })
        return values

    # All Users Page
    # ---------------------------------------------------
    def _prepare_all_users_values(self, user, position):
        result = super(WebsiteSlides, self)._prepare_all_users_values(user, position)
        result.update({
            'certification_count': len(self._get_user_certificates(user))
        })
        return result

    def _get_user_certificates(self, user):
        domain = [
            ('partner_id', '=', user.partner_id.id),
            ('quizz_passed', '=', True),
            ('slide_partner_id.survey_quizz_passed', '=', True)
        ]
        certifications = request.env['survey.user_input'].sudo().search(domain)
        return certifications
