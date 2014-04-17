from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.translate import _

import json

class Twitter(http.Controller):
    @http.route(['/twitter_reload'], type='json', auth="user", website=True)
    def twitter_reload(self):
        return request.website.fetch_favorite_tweets()

    @http.route(['/get_favorites'], type='json', auth="public", website=True)
    def get_tweets(self, limit=20):
        key = request.website.twitter_api_key
        secret = request.website.twitter_api_secret
        screen_name = request.website.twitter_screen_name
        if not key or not secret:
            return {"error": _("Please set the Twitter API Key and Secret in the Website Settings.")}
        if not screen_name:
            return {"error": _("Please set a Twitter screen name to load favorites from, "
                               "in the Website Settings (it does not have to be yours)")}
        twitter_tweets = request.registry['website.twitter.tweet']
        tweets = twitter_tweets.search_read(
                request.cr, request.uid,
                [('website_id','=', request.website.id),
                 ('screen_name','=', screen_name)],
                ['tweet'], limit=int(limit), order="tweet_id desc", context=request.context)
        if len(tweets) < 12:
            return {"error": _("Twitter user @%(username)s has less than 12 favorite tweets. "
                               "Please add more or choose a different screen name.") % \
                                    {'username': screen_name}}
        return [json.loads(tweet['tweet']) for tweet in tweets]
