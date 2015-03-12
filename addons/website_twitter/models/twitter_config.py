# -*- coding: utf-8 -*-

import logging
from urllib2 import URLError, HTTPError

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)


class twitter_config_settings(osv.TransientModel):
    _inherit = 'website.config.settings'

    _columns = {
        'twitter_api_key': fields.related(
            'website_id', 'twitter_api_key', type="char",
            string='Twitter API Key',
            help="Twitter API key you can get it from https://apps.twitter.com/app/new"),
        'twitter_api_secret': fields.related(
            'website_id', 'twitter_api_secret', type="char",
            string='Twitter API secret',
            help="Twitter API secret you can get it from https://apps.twitter.com/app/new"),
        'twitter_tutorial': fields.dummy(
            type="boolean", string="Show me how to obtain the Twitter API Key and Secret"),
        'twitter_screen_name': fields.related(
            'website_id', 'twitter_screen_name',
            type="char", string='Get favorites from this screen name',
            help="Screen Name of the Twitter Account from which you want to load favorites."
                 "It does not have to match the API Key/Secret."),
    }

    def _get_twitter_exception_message(self, error_code, context=None):
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
        if error_code in TWITTER_EXCEPTION:
            return TWITTER_EXCEPTION[error_code]
        else:
            return _('HTTP Error: Something is misconfigured')

    def _check_twitter_authorization(self, cr, uid, config_id, context=None):
        website_obj = self.pool['website']
        website_config = self.browse(cr, uid, config_id, context=context)
        try:
            website_obj.fetch_favorite_tweets(cr, uid, [website_config.website_id.id], context=context)

        except HTTPError, e:
            _logger.info("%s - %s" % (e.code, e.reason), exc_info=True)
            raise UserError("%s - %s" % (e.code, e.reason) + ':' + self._get_twitter_exception_message(e.code, context))
        except URLError, e:
            _logger.info(_('We failed to reach a twitter server.'), exc_info=True)
            raise UserError(_('Internet connection refused') + ' ' + _('We failed to reach a twitter server.'))
        except Exception, e:
            _logger.info(_('Please double-check your Twitter API Key and Secret!'), exc_info=True)
            raise UserError(_('Twitter authorization error!') + ' ' + _('Please double-check your Twitter API Key and Secret!'))

    def create(self, cr, uid, vals, context=None):
        res_id = super(twitter_config_settings, self).create(cr, uid, vals, context=context)
        if vals.get('twitter_api_key') or vals.get('twitter_api_secret') or vals.get('twitter_screen_name'):
            self._check_twitter_authorization(cr, uid, res_id, context=context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        res_id = super(twitter_config_settings, self).write(cr, uid, ids, vals, context=context)
        if vals.get('twitter_api_key') or vals.get('twitter_api_secret') or vals.get('twitter_screen_name'):
            self._check_twitter_authorization(cr, uid, ids, context=context)
        return res_id
