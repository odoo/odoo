# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug
import werkzeug.utils
import werkzeug.exceptions

from odoo import _
from odoo import http
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.osv import expression

from odoo.addons.website_slides.controllers.main import WebsiteSlides


class WebsiteSlidesSurvey(WebsiteSlides):

    @http.route(['/slides_survey/slide/get_certification_url'], type='http', auth='user', website=True)
    def slide_get_certification_url(self, slide_id, **kw):
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            raise werkzeug.exceptions.NotFound()
        slide = fetch_res['slide']
        if slide.channel_id.is_member:
            slide.action_set_viewed()
        certification_url = slide._generate_certification_url().get(slide.id)
        if not certification_url:
            raise werkzeug.exceptions.NotFound()
        return request.redirect(certification_url)

    @http.route(['/slides_survey/certification/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slides_certification_search_read(self, fields):
        can_create = request.env['survey.survey'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['survey.survey'].search_read([('certification', '=', True)], fields),
            'can_create': can_create,
        }

    # ------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------

    @http.route(['/slides/add_slide'], type='json', auth='user', methods=['POST'], website=True)
    def create_slide(self, *args, **post):
        create_new_survey = post['slide_category'] == "certification" and post.get('survey') and not post['survey']['id']
        linked_survey_id = int(post.get('survey', {}).get('id') or 0)

        if create_new_survey:
            # If user cannot create a new survey, no need to create the slide either.
            if not request.env['survey.survey'].check_access_rights('create', raise_exception=False):
                return {'error': _('You are not allowed to create a survey.')}

            # Create survey first as certification slide needs a survey_id (constraint)
            post['survey_id'] = request.env['survey.survey'].create({
                'title': post['survey']['title'],
                'questions_layout': 'page_per_question',
                'is_attempts_limited': True,
                'attempts_limit': 1,
                'is_time_limited': False,
                'scoring_type': 'scoring_without_answers',
                'certification': True,
                'scoring_success_min': 70.0,
                'certification_mail_template_id': request.env.ref('survey.mail_template_certification').id,
            }).id
        elif linked_survey_id:
            try:
                request.env['survey.survey'].browse([linked_survey_id]).read(['title'])
            except AccessError:
                return {'error': _('You are not allowed to link a certification.')}

            post['survey_id'] = post['survey']['id']

        # Then create the slide
        result = super(WebsiteSlidesSurvey, self).create_slide(*args, **post)

        if post['slide_category'] == "certification":
            # Set the url to redirect the user to the survey
            result['url'] = '/slides/slide/%s?fullscreen=1' % (slug(request.env['slide.slide'].browse(result['slide_id']))),

        return result

    # Utils
    # ---------------------------------------------------
    def _slide_mark_completed(self, slide):
        if slide.slide_category == 'certification':
            raise werkzeug.exceptions.Forbidden(_("Certification slides are completed when the survey is succeeded."))
        return super(WebsiteSlidesSurvey, self)._slide_mark_completed(slide)

    def _get_valid_slide_post_values(self):
        result = super(WebsiteSlidesSurvey, self)._get_valid_slide_post_values()
        result.append('survey_id')
        return result

    # Profile
    # ---------------------------------------------------
    def _prepare_user_slides_profile(self, user):
        values = super(WebsiteSlidesSurvey, self)._prepare_user_slides_profile(user)
        values.update({
            'certificates': self._get_users_certificates(user)[user.id]
        })
        return values

    # All Users Page
    # ---------------------------------------------------
    def _prepare_all_users_values(self, users):
        result = super(WebsiteSlidesSurvey, self)._prepare_all_users_values(users)
        certificates_per_user = self._get_users_certificates(users)
        for index, user in enumerate(users):
            result[index].update({
                'certification_count': len(certificates_per_user.get(user.id, []))
            })
        return result

    def _get_users_certificates(self, users):
        partner_ids = [user.partner_id.id for user in users]
        domain = [
            ('slide_partner_id.partner_id', 'in', partner_ids),
            ('scoring_success', '=', True),
            ('slide_partner_id.survey_scoring_success', '=', True)
        ]
        certificates = request.env['survey.user_input'].sudo().search(domain)
        users_certificates = {
            user.id: [
                certificate for certificate in certificates if certificate.partner_id == user.partner_id
            ] for user in users
        }
        return users_certificates

    # Badges & Ranks Page
    # ---------------------------------------------------
    def _prepare_ranks_badges_values(self, **kwargs):
        """ Extract certification badges, to render them in ranks/badges page in another section.
        Order them by number of granted users desc and show only badges linked to opened certifications."""
        values = super(WebsiteSlidesSurvey, self)._prepare_ranks_badges_values(**kwargs)

        # 1. Getting all certification badges, sorted by granted user desc
        domain = expression.AND([[('survey_id', '!=', False)], self._prepare_badges_domain(**kwargs)])
        certification_badges = request.env['gamification.badge'].sudo().search(domain)
        # keep only the badge with challenge category = slides (the rest will be displayed under 'normal badges' section
        certification_badges = certification_badges.filtered(
            lambda b: 'slides' in b.challenge_ids.mapped('challenge_category'))

        if not certification_badges:
            return values

        # 2. sort by granted users (done here, and not in search directly, because non stored field)
        certification_badges = certification_badges.sorted("granted_users_count", reverse=True)

        # 3. Remove certification badge from badges
        badges = values['badges'] - certification_badges

        # 4. Getting all course url for each badge
        certification_slides = request.env['slide.slide'].sudo().search([('survey_id', 'in', certification_badges.mapped('survey_id').ids)])
        certification_badge_urls = {slide.survey_id.certification_badge_id.id: slide.channel_id.website_url for slide in certification_slides}

        # 5. Applying changes
        values.update({
            'badges': badges,
            'certification_badges': certification_badges,
            'certification_badge_urls': certification_badge_urls
        })
        return values
