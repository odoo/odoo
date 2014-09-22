# -*- coding: utf-8 -*-
from json import loads
from thread import start_new_thread
from urllib2 import Request, urlopen
from openerp import api, fields, models, registry, SUPERUSER_ID, _
from openerp.addons.website.models.website import slug
from openerp.exceptions import UserError
from base_stream import Stream, StreamListener
from oauth import Oauth


class TwitterStream(models.Model, StreamListener):
    _name = 'twitter.stream'

    streams_objs = {}

    twitter_api_key = fields.Char()
    twitter_api_secret = fields.Char()
    model = fields.Char('Type of Model')
    agent_ids = fields.One2many('twitter.agent', 'stream_id')

    def _register_hook(self, cr):
        """ Start streaming on server start """
        super(TwitterStream, self)._register_hook(cr)
        self.start(cr)

    def start(self, cr):
        """ Start streaming """
        if not hasattr(self, '_id'):
            stream_id = self.search(cr, SUPERUSER_ID, [], limit=1)
            for stream in self.browse(cr, SUPERUSER_ID, stream_id):
                stream.start_streaming()

    @api.one
    def start_streaming(self):
        if self.agent_ids:
            def func(stream, user_ids):
                return stream.filter(follow=user_ids)
            auth = Oauth(self.twitter_api_key, self.twitter_api_secret)
            stream = None
            user_ids = []
            for agent in self.agent_ids:
                if agent['auth_user'] and agent['state'] != 'archive':
                    auth.set_access_token(agent['twitter_access_token'], agent['twitter_access_token_secret'])
                    stream = Stream(auth, self)
                    user_ids.append(agent['auth_user'])
            if user_ids:
                self.streams_objs[self.id] = stream
                start_new_thread(func, (stream, user_ids))
            return True

    def stop(self):
        """ Stop streaming """
        if self.streams_objs.get(self.id):
            self.streams_objs[self.id].disconnect()

    def restart(self):
        """ Restart streaming """
        self.stop()
        self.start()

    def on_data(self, tweet):
        """ Call when tweet is come and store in twitter.tweet Model """
        if 'delete' not in tweet:
            tweet = loads(tweet)
            with api.Environment.manage():
                with registry(self.env.cr.dbname).cursor() as new_cr:
                    self.env = api.Environment(new_cr, self.env.uid, self.env.context)
                    walls = self.agent_ids.filtered(lambda o: o.auth_user == tweet['user']['id_str'] and o.state != 'archive').sorted(lambda r: r.create_date, reverse=True)
                    if len(walls):
                        self.env['twitter.tweet'].process_tweet(walls[0].id, tweet)
        return True


class TwitterAgent(models.Model):
    _name = 'twitter.agent'
    _inherit = ['website.published.mixin']

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    total_views = fields.Integer()
    state = fields.Selection([('normal', 'Normal'), ('archive', 'Archive')], default='normal')
    tweetus_ids = fields.Many2many('twitter.hashtag', string='Tweet Us Hashtag')
    image = fields.Binary(required=True)
    twitter_access_token = fields.Char()
    twitter_access_token_secret = fields.Char()
    auth_user = fields.Char('Authenticated User Id')
    stream_id = fields.Many2one('twitter.stream', default=lambda self: self.env.ref('website_twitter_wall.twitter_stream_1').id)
    tweet_ids = fields.One2many('twitter.tweet', 'agent_id')

    @api.multi
    @api.depends('name')
    def _website_url(self, name, arg):
        res = super(TwitterAgent, self)._website_url(name, arg)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        res.update({(wall.id, '%s/twitter_wall/view/%s' % (base_url, slug(wall))) for wall in self})
        return res

    @api.multi
    def write(self, vals):
        """ Restart streaming when state is change from archive to normal """
        res = super(TwitterAgent, self).write(vals)
        if vals.get('state') == 'archive' and not self.auth_user:
            raise UserError(_("You can't archive wall without verify with twitter account"))
        if vals.get('state') == 'normal' and self.auth_user:
            self.stream_id.restart()
        return res

    @api.multi
    def unlink(self):
        """ Override unlink method to restart streaming when deletion perform """
        stream = None
        for wall in self:
            if wall.auth_user:
                stream = wall.stream_id
        super(TwitterAgent, self).unlink()
        if stream:
            stream.restart()


class TwitterTweet(models.Model):
    _name = 'twitter.tweet'

    tweet_id = fields.Char()
    html_description = fields.Html('Tweet')
    comment = fields.Html(default='<br/>')
    agent_id = fields.Many2one('twitter.agent')

    @api.model
    def process_tweet(self, wall_id, tweet):
        card_url = 'https://api.twitter.com/1/statuses/oembed.json?id=%s&omit_script=true' % (tweet.get('id'))
        cardtweet = loads(urlopen(Request(card_url, None, {'Content-Type': 'application/json'})).read())
        return self.create({
            'tweet_id': tweet.get('id'),
            'html_description': cardtweet.get('html', False),
            'agent_id': wall_id
        })


class TwitterHashtag(models.Model):
    _name = 'twitter.hashtag'

    name = fields.Char(required=True)

    _sql_constraints = [('website_twitter_wall_hashtag_unique', 'UNIQUE(name)', 'A hashtag must be unique!')]
