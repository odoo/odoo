# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests

from odoo import api, fields, models, _, _lt
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TWITTER_EXCEPTION = {
    304: _lt('There was no new data to return.'),
    400: _lt('The request was invalid or cannot be otherwise served. Requests without authentication are considered invalid and will yield this response.'),
    401: _lt('Authentication credentials were missing or incorrect. Maybe screen name tweets are protected.'),
    403: _lt('The request is understood, but it has been refused or access is not allowed. Please check your Twitter API Key and Secret.'),
    429: _lt('Request cannot be served due to the applications rate limit having been exhausted for the resource.'),
    500: _lt('Twitter seems broken. Please retry later. You may consider posting an issue on Twitter forums to get help.'),
    502: _lt('Twitter is down or being upgraded.'),
    503: _lt('The Twitter servers are up, but overloaded with requests. Try again later.'),
    504: _lt('The Twitter servers are up, but the request could not be serviced due to some failure within our stack. Try again later.')
}


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    twitter_api_key = fields.Char(
        related='website_id.twitter_api_key', readonly=False,
        string='API Key',
        help='Twitter API key you can get it from https://apps.twitter.com/')
    twitter_api_secret = fields.Char(
        related='website_id.twitter_api_secret', readonly=False,
        string='API secret',
        help='Twitter API secret you can get it from https://apps.twitter.com/')
    twitter_screen_name = fields.Char(
        related='website_id.twitter_screen_name', readonly=False,
        string='Favorites From',
        help='Screen Name of the Twitter Account from which you want to load favorites.'
             'It does not have to match the API Key/Secret.')
    twitter_server_uri = fields.Char(string='Twitter server uri', readonly=True)

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
            _logger.info('We failed to reach a twitter server.', exc_info=True)
            raise UserError(_('Internet connection refused: We failed to reach a twitter server.'))
        except Exception:
            _logger.info('Please double-check your Twitter API Key and Secret!', exc_info=True)
            raise UserError(_('Twitter authorization error! Please double-check your Twitter API Key and Secret!'))

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        for config in configs:
            if config.twitter_api_key or config.twitter_api_secret or config.twitter_screen_name:
                config._check_twitter_authorization()
        return configs

    def write(self, vals):
        TwitterConfig = super(ResConfigSettings, self).write(vals)
        if vals.get('twitter_api_key') or vals.get('twitter_api_secret') or vals.get('twitter_screen_name'):
            self._check_twitter_authorization()
        return TwitterConfig

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        Params = self.env['ir.config_parameter'].sudo()
        res.update({
            'twitter_server_uri': '%s/' % Params.get_param('web.base.url', default='http://yourcompany.odoo.com'),
        })
        return res
