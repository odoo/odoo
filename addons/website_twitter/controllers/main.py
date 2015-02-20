# -*- coding: utf-8 -*-

import json

from openerp import _
from openerp.addons.web import http
from openerp.addons.web.http import request

class Twitter(http.Controller):
    @http.route(['/twitter_reload'], type='json', auth="user", website=True)
    def twitter_reload(self):
        return request.website.fetch_favorite_tweets()

    @http.route(['/get_favorites'], type='json', auth="public", website=True)
    def get_tweets(self, limit=20):
        key = request.website.twitter_api_key
        secret = request.website.twitter_api_secret
        screen_name = request.website.twitter_screen_name
        Debug = request.env['res.users'].has_group('base.group_website_publisher')
        if not key or not secret:
            if Debug:
                return {"error": _("Please set the Twitter API Key and Secret in the Website Settings.")}
            return []
        if not screen_name:
            if Debug:
                return {"error": _("Please set a Twitter screen name to load favorites from, "
                                   "in the Website Settings (it does not have to be yours)")}
            return []
        TwitterTweets = request.env['website.twitter.tweet']
        tweets = TwitterTweets.search(
                [('website_id','=', request.website.id),
                 ('screen_name','=', screen_name)],
                limit=int(limit), order="tweet_id desc")
        if len(tweets) < 12:
            if Debug:
                return {"error": _("Twitter user @%(username)s has less than 12 favorite tweets. "
                                   "Please add more or choose a different screen name.") % \
                                      {'username': screen_name}}
            else:
                return []
        return [json.loads(tweet['tweet']) for tweet in tweets]
