# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from werkzeug.urls import url_parse

from odoo import api, models

SURVEY_START_RE = re.compile(r'^/survey/start/(?P<token>[^/?#]+)')


class LinkTracker(models.Model):
    _inherit = 'link.tracker'

    @api.model
    def _get_survey_from_url(self, url):
        parsed = url_parse(url)
        match = SURVEY_START_RE.match(parsed.path)
        if not match or parsed.netloc not in ('', url_parse(self.get_base_url()).netloc):
            return self.env['survey.survey']
        return self.env['survey.survey'].sudo().search(
            [('access_token', '=', match['token'])], limit=1,
        )

    @api.model
    def _get_title_from_url(self, url):
        survey = self._get_survey_from_url(url)
        return survey.title if survey else super()._get_title_from_url(url)
