# -*- coding: utf-8 -*-

from urllib2 import urlopen, Request, HTTPError

import base64
import json
import logging
import werkzeug

from openerp import models, fields, api

API_ENDPOINT = 'https://api.twitter.com'
API_VERSION = '1.1'
REQUEST_TOKEN_URL = '%s/oauth2/token' % API_ENDPOINT
REQUEST_FAVORITE_LIST_URL = '%s/%s/favorites/list.json' % (API_ENDPOINT, API_VERSION)
URLOPEN_TIMEOUT = 10

_logger = logging.getLogger(__name__)

class TwitterClient(models.Model):
    _inherit = "website"

    twitter_api_key = fields.Char('Twitter API key', help="Twitter API Key")
    twitter_api_secret = fields.Char('Twitter API secret', help="Twitter API Secret")
    twitter_screen_name = fields.Char('Get favorites from this screen name')

    @api.model
    def _request(self, website, url, params=None):
        """Send an authenticated request to the Twitter API."""
        access_token = self._get_access_token(website)
        if params:
            params = werkzeug.url_encode(params)
            url = url + '?' + params
        try:
            request = Request(url)
            request.add_header('Authorization', 'Bearer %s' % access_token)
            return json.load(urlopen(request, timeout=URLOPEN_TIMEOUT))
        except HTTPError, e:
            _logger.debug("Twitter API request failed with code: %r, msg: %r, content: %r",
                          e.code, e.msg, e.fp.read())
            raise

    @api.model
    def _refresh_favorite_tweets(self):
        ''' called by cron job '''
        Website = self.env['website'].search([('twitter_api_key', '!=', False),
                                          ('twitter_api_secret', '!=', False),
                                          ('twitter_screen_name', '!=', False)])
        _logger.debug("Refreshing tweets for website IDs: %r", Website.ids)
        Website.fetch_favorite_tweets()

    @api.multi
    def fetch_favorite_tweets(self):
        WebsiteTweets = self.env['website.twitter.tweet']
        tweet_ids = []
        for website in self:
            if not all((website.twitter_api_key, website.twitter_api_secret,
                       website.twitter_screen_name)):
                _logger.debug("Skip fetching favorite tweets for unconfigured website %s",
                              website) 
                continue
            params = {'screen_name': website.twitter_screen_name}
            last_tweet = WebsiteTweets.search([('website_id', '=', website.id),
                                                     ('screen_name', '=', website.twitter_screen_name)],
                                                     limit=1, order='tweet_id desc')
            if last_tweet:
                params['since_id'] = int(last_tweet[0]['tweet_id'])
            _logger.debug("Fetching favorite tweets using params %r", params)
            response = self._request(website, REQUEST_FAVORITE_LIST_URL, params=params)
            for tweet_dict in response:
                tweet_id = tweet_dict['id'] # unsigned 64-bit snowflake ID
                tweet_ids = WebsiteTweets.search([('tweet_id', '=', tweet_id)]).ids
                if not tweet_ids:
                    new_tweet = WebsiteTweets.create(
                            {
                              'website_id': website.id,
                              'tweet': json.dumps(tweet_dict),
                              'tweet_id': tweet_id, # stored in NUMERIC PG field 
                              'screen_name': website.twitter_screen_name,
                            })
                    _logger.debug("Found new favorite: %r, %r", tweet_id, tweet_dict)
                    tweet_ids.append(new_tweet.id)
        return tweet_ids

    def _get_access_token(self, website):
        """Obtain a bearer token."""
        bearer_token_cred = '%s:%s' % (website.twitter_api_key, website.twitter_api_secret)
        encoded_cred = base64.b64encode(bearer_token_cred)
        request = Request(REQUEST_TOKEN_URL)
        request.add_header('Content-Type',
                           'application/x-www-form-urlencoded;charset=UTF-8')
        request.add_header('Authorization',
                           'Basic %s' % encoded_cred)
        request.add_data('grant_type=client_credentials')
        data = json.load(urlopen(request, timeout=URLOPEN_TIMEOUT))
        access_token = data['access_token']
        return access_token

class WebsiteTwitterTweet(models.Model):
    _name = "website.twitter.tweet"
    _description = "Twitter Tweets"
    website_id = fields.Many2one('website', string="Website")
    screen_name = fields.Char("Screen Name")
    tweet = fields.Text('Tweets')

    # Twitter IDs are 64-bit unsigned ints, so we need to store them in
    # unlimited precision NUMERIC columns, which can be done with a
    # float field. Used digits=(0,0) to indicate unlimited.
    # Using VARCHAR would work too but would have sorting problems.  
    tweet_id = fields.Float("Tweet ID", digits=(0,0)) # Twitter
