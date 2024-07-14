# -*- coding: utf-8 -*-

import base64
import requests

from datetime import datetime, timedelta
from http.client import BadStatusLine
from logging import getLogger
from psycopg2 import InternalError, OperationalError
from werkzeug.urls import url_encode, url_join

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import UserError

_logger = getLogger(__name__)


class WebsiteTwitterWall(models.Model):
    _name = 'website.twitter.wall'
    _inherit = ['website.published.mixin']
    _description = 'Website Twitter'
    _order = 'name'


    name = fields.Char(required=True, translate=True)
    description = fields.Html(translate=True, sanitize_attributes=False)
    is_live = fields.Boolean(help="Is live mode on/off", default=True)
    active = fields.Boolean(default=True)
    search_pattern = fields.Char('Search string',
        help='The search criteria to get the tweets you want. You can use the Twitter query operators.\n'
             'You can also use the special "favorites:screen_name" operator to get the favorited tweets of "screen_name".')
    mode = fields.Selection([('recent', 'Recent'), ('popular', 'Popular'), ('mixed', 'Mixed')], default='recent', string='Type of tweets', help="Most recent tweets, most popular tweets, or both")
    image = fields.Binary()
    tweet_ids = fields.Many2many('website.twitter.tweet', string='Tweets')
    total_tweets = fields.Integer(compute='_compute_count_total_tweets')
    api_key = fields.Char('Twitter API Key', groups='base.group_system')
    api_secret = fields.Char('Twitter API Secret', groups='base.group_system')
    access_token = fields.Char(groups='base.group_system')
    last_search = fields.Datetime(default=fields.Datetime.now)

    def _compute_website_url(self):
        super(WebsiteTwitterWall, self)._compute_website_url()
        for wall in self:
            if wall.id:
                wall.website_url = "%s/twitter_wall/view/%s" % (wall.get_base_url(), slug(wall))

    def toggle_live_mode(self):
        self.env.registry.clear_cache()  # not sure this is really useful
        self.is_live = not self.is_live

    def fetch_tweets(self):
        self.ensure_one()
        if not self.is_live:
            return
        try:
            if fields.Datetime.from_string(self.last_search) < datetime.now() - timedelta(minutes=1):
                self._cr.execute("SELECT value FROM ir_config_parameter WHERE key='twitter_wall_search' FOR UPDATE NOWAIT")
                for tweet in self.search_tweets():
                    self.process_tweet(tweet['id'], [self.id], author_id=tweet.get('user', {}).get('id_str'))
                self.last_search = fields.Datetime.now()
        except InternalError:
            pass
        except OperationalError:
            pass

    def search_tweets(self):
        self.ensure_one()
        website = self.env['website'].search([
            ('twitter_api_key', '!=', False),
            ('twitter_api_secret', '!=', False)], limit=1)
        consumer_key = website.sudo().twitter_api_key
        consumer_secret = website.sudo().twitter_api_secret
        bearer_token_64 = base64.b64encode(("%s:%s" % (consumer_key, consumer_secret)).encode('UTF-8')).decode('UTF-8')

        if not self.access_token:
            response = requests.post('https://api.twitter.com/oauth2/token', data={'grant_type':'client_credentials'}, headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'Authorization': ('Basic %s' % bearer_token_64)})
            try:
                response.raise_for_status()
                self.access_token = response.json().get('access_token')
            except requests.exceptions.HTTPError:
                raise UserError(_('The Twitter authentication failed. Please check your API key and secret.'))

        params = {'result_type': self.mode}
        if self.tweet_ids:
            params['since_id'] = self.tweet_ids[0].tweet_id

        is_favorite_search = 'favorites:' in self.search_pattern \
                              and len(self.search_pattern.split('favorites:')) > 0
        if is_favorite_search:
            endpoint = 'favorites/list.json'
            params['screen_name'] = self.search_pattern.split('favorites:')[1]
        else:
            endpoint = 'search/tweets.json'
            params['q'] = self.search_pattern

        response = requests.get(
            url_join('https://api.twitter.com/1.1/', endpoint),
            params=params,
            headers={'Authorization': 'Bearer %s' % self.access_token})

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise UserError(_('The tweets search failed. Check your credentials and access token'))

        if is_favorite_search:
            return response.json()
        else:
            return response.json().get('statuses')

    def process_tweet(self, tweet_id, wall_ids, author_id=False):
        Tweet = self.env['website.twitter.tweet']
        tweet = Tweet.search([('tweet_id', '=', tweet_id)])
        if tweet:
            tweet.write({'wall_ids': [(4, wall_id) for wall_id in wall_ids if wall_id not in tweet.wall_ids.ids]})
        else:
            try:
                if not author_id:
                    # kept for retro-compatibility with the old method signature but will be deprecated by Twitter
                    # https://twittercommunity.com/t/consolidating-the-oembed-functionality/154690
                    card_url = 'https://api.twitter.com/1/statuses/oembed.json?id=%s&omit_script=true' % (tweet_id)
                else:
                    card_url = 'https://publish.twitter.com/oembed?%s' % url_encode({
                        'url': 'https://twitter.com/%s/statuses/%s' % (author_id, tweet_id),
                        'omit_script': True
                    })
                response = requests.get(card_url, headers={'Content-Type': 'application/json'})
                card_tweet = response.json()
                if card_tweet:
                    self.env['website.twitter.tweet'].create({
                        'tweet_id': tweet_id,
                        'tweet_html': card_tweet.get('html', False),
                        'wall_ids': [(6, None, wall_ids)]
                    })
            except requests.exceptions.HTTPError as e:
                if e.code == 404:
                    _logger.warning("Tweet not found 404")
            except (BadStatusLine, ValueError) as e:
                _logger.warning(e)

    @api.depends('tweet_ids')
    def _compute_count_total_tweets(self):
        self.total_tweets = len(self.tweet_ids)

    @api.depends('name')
    def _website_url(self, name, arg):
        res = super(WebsiteTwitterWall, self)._website_url(name, arg)
        res.update({(wall.id, '%s/twitter_wall/view/%s' % (wall.get_base_url(), slug(wall))) for wall in self})
        return res

    def open_tweets(self):
        self.ensure_one()
        return {
            'name': _('Tweets'),
            'view_mode': 'tree,form',
            'res_model': 'website.twitter.tweet',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('wall_ids', 'in', [self.id])],
        }
