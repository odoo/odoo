# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TWITTER_EXCEPTION = {
    304: _('There was no new data to return.'),
    400: _('The request was invalid or cannot be otherwise served. Requests without authentication are considered invalid and will yield this response.'),
    401: _('Authentication credentials were missing or incorrect. Maybe screen name tweets are protected.'),
    403: _('The request is understood, but it has been refused or access is not allowed. Please check your Twitter API Key and Secret.'),
    429: _('Request cannot be served due to the applications rate limit having been exhausted for the resource.'),
    500: _('Twitter seems broken. Please retry later. You may consider posting an issue on Twitter forums to get help.'),
    502: _('Twitter is down or being upgraded.'),
    503: _('The Twitter servers are up, but overloaded with requests. Try again later.'),
    504: _('The Twitter servers are up, but the request could not be serviced due to some failure within our stack. Try again later.')
}


class WebsiteTwitterConfig(models.TransientModel):
    _inherit = 'website.config.settings'

    twitter_api_key = fields.Char(
        related='website_id.twitter_api_key',
        string='API Key',
        help='Twitter API key you can get it from https://apps.twitter.com/')
    twitter_api_secret = fields.Char(
        related='website_id.twitter_api_secret',
        string='API secret',
        help='Twitter API secret you can get it from https://apps.twitter.com/')
    twitter_tutorial = fields.Boolean(string='Show me how to obtain the Twitter API Key and Secret')
    twitter_screen_name = fields.Char(
        related='website_id.twitter_screen_name',
        string='Favorites From',
        help='Screen Name of the Twitter Account from which you want to load favorites.'
             'It does not have to match the API Key/Secret.')

    def _get_twitter_exception_message(self, error_code):
        if error_code in TWITTER_EXCEPTION:
            return TWITTER_EXCEPTION[error_code]
        else:
            return _('HTTP Error: Something is misconfigured')

    def _check_twitter_authorization(self):
        try:
            self.website_id.fetch_favorite_tweets()

        except requests.HTTPError as e:
            _logger.info("%s - %s" % (e.response.status_code, e.response.reason), exc_info=True)
            raise UserError("%s - %s" % (e.response.status_code, e.response.reason) + ':' + self._get_twitter_exception_message(e.response.status_code))
        except IOError:
            _logger.info(_('We failed to reach a twitter server.'), exc_info=True)
            raise UserError(_('Internet connection refused') + ' ' + _('We failed to reach a twitter server.'))
        except Exception:
            _logger.info(_('Please double-check your Twitter API Key and Secret!'), exc_info=True)
            raise UserError(_('Twitter authorization error!') + ' ' + _('Please double-check your Twitter API Key and Secret!'))

    @api.model
    def create(self, vals):
        TwitterConfig = super(WebsiteTwitterConfig, self).create(vals)
        if vals.get('twitter_api_key') or vals.get('twitter_api_secret') or vals.get('twitter_screen_name'):
            TwitterConfig._check_twitter_authorization()
        return TwitterConfig

    @api.multi
    def write(self, vals):
        TwitterConfig = super(WebsiteTwitterConfig, self).write(vals)
        if vals.get('twitter_api_key') or vals.get('twitter_api_secret') or vals.get('twitter_screen_name'):
            self._check_twitter_authorization()
        return TwitterConfig
