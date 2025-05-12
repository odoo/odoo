# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.http import request
from odoo.addons.website_profile.controllers.main import WebsiteProfile


class WebsiteSlidesSurvey(WebsiteProfile):
    def _prepare_user_profile_values(self, user, **kwargs):
        """Loads all data required to display the certification attempts of the given user"""
        values = super(WebsiteSlidesSurvey, self)._prepare_user_profile_values(user, **kwargs)
        values['show_certification_tab'] = ('user' in values) and (
            values['user'].id == request.env.user.id or \
            request.env.user.has_group('survey.group_survey_manager')
        )

        if not values['show_certification_tab']:
            return values

        domain = (
            Domain('survey_id.certification', '=', True)
            & Domain('state', '=', 'done')
            & (
                (Domain('email', '=', values['user'].email) if values['user'].email else Domain.FALSE)
                | Domain('partner_id', '=', values['user'].partner_id.id)
            )
        )

        if 'certification_search' in kwargs:
            values['active_tab'] = 'certification'
            values['certification_search_terms'] = kwargs['certification_search']
            domain &= Domain('survey_id.title', 'ilike', kwargs['certification_search'])

        UserInputSudo = request.env['survey.user_input'].sudo()
        values['user_inputs'] = UserInputSudo.search(domain, order='create_date desc')

        return values
