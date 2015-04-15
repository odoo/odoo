# -*- coding: utf-8 -*-
import logging
from json import loads
from urllib2 import Request, urlopen
from openerp import api, fields, models

_logger = logging.getLogger(__name__)


class TwitterTweet(models.Model):
    _name = 'twitter.tweet'

    tweet_id = fields.Char()
    tweet = fields.Html()
    comment = fields.Html(default='<br/>')
    agent_id = fields.Many2one('twitter.agent')

    _sql_constraints = [('website_twitter_wall_tweet_unique', 'UNIQUE(tweet_id, agent_id)', 'Duplicate tweet not allowed !')]

    @api.model
    def process_tweet(self, agent_id, tweet_id):
        try:
            card_url = 'https://api.twitter.com/1/statuses/oembed.json?id=%s&omit_script=true' % (tweet_id)
            cardtweet = loads(urlopen(Request(card_url, None, {'Content-Type': 'application/json'})).read())
            return self.create({
                'tweet_id': tweet_id,
                'tweet': cardtweet.get('html', False),
                'agent_id': agent_id
            })
        except Exception as e:
            _logger.error(e)
