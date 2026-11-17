# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.controllers.main import MassMailController
from odoo.http import request

from werkzeug.urls import url_encode


class SurveyMassMailController(MassMailController):

    def _add_url_params(self, url, params=None):
        """Add parameters to the given URL.
           Eg, given:
            - 'http://example.com'
            - params: {'colour': 'blue', 'sort': 'newest'}
            returns: http://example.com?colour=blue&sort=newest
        """
        separator = '&' if '?' in url else '?'
        return f"{url}{separator}{url_encode(params)}"

    # Override
    def _preprocess_url(self, url, mailing_trace_id, code=None):
        """Extend the URL with the mailing information linked to the survey,
        if any, and with the recipient's email if not logged in."""
        url = super()._preprocess_url(url, mailing_trace_id, code=code)
        survey = request.env['link.tracker']._get_survey_from_url(url)
        if not survey:
            return url
        trace = request.env['mailing.trace'].sudo().browse(mailing_trace_id).exists()
        link = request.env['link.tracker.code'].sudo().search([('code', '=', code)], limit=1).link_id
        if not trace.email or trace.mass_mailing_id != link.mass_mailing_id:
            return url
        url = self._add_url_params(url, {'mass_mailing_id': trace.mass_mailing_id.id})
        if request.env.user._is_public():
            url = self._add_url_params(url, {'email': trace.email})
        return url
