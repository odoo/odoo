# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlsplit, urlencode, parse_qsl

from odoo.addons.mass_mailing.controllers.main import MassMailController
from odoo.exceptions import UserError
from odoo.http import request


class MassMailSurveyController(MassMailController):

    # Override
    def _preprocess_url(self, url, mailing_trace_id, code=None):
        """Link the survey answer to the mailing recipient's email for public visitors:
        pass the token of an unstarted answer (reused or created), or only the email
        if one was already started, so its token is never leaked to whoever holds the
        link. Otherwise, return the url unchanged for the survey controller to handle."""
        url = super()._preprocess_url(url, mailing_trace_id, code=code)
        if not mailing_trace_id or not request.env.user._is_public():
            return url
        survey = request.env['link.tracker']._get_survey_from_url(url)
        if not survey:
            return url
        trace = request.env['mailing.trace'].sudo().browse(mailing_trace_id).exists()
        link = request.env['link.tracker.code'].sudo().search([('code', '=', code)], limit=1).link_id
        if not trace.email or trace.mass_mailing_id != link.mass_mailing_id:
            return url
        # Latest unfinished answer of this recipient
        answer = request.env['survey.user_input'].sudo().search([
            ('survey_id', '=', survey.id),
            ('email', '=', trace.email),
            ('partner_id', '=', False),
            ('test_entry', '=', False),
            ('state', '!=', 'done'),
        ], limit=1)
        if answer.state == 'in_progress':
            # Already started: never hand its token to whoever holds the link.
            extra_query = {'email': trace.email}
        else:
            if not answer:
                try:
                    answer = survey._create_answer(email=trace.email)
                except UserError:
                    # Let the survey controller handle it.
                    return url
            extra_query = {'answer_token': answer.access_token}
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query), **extra_query)
        return parts._replace(query=urlencode(query)).geturl()
