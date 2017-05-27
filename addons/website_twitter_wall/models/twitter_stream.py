# -*- coding: utf-8 -*-
from json import loads
from thread import start_new_thread
from openerp import api, fields, models, registry, SUPERUSER_ID
from base_stream import Stream, StreamListener
from oauth import Oauth


class TwitterStream(models.Model, StreamListener):
    _name = 'twitter.stream'

    streams_objs = {}

    twitter_api_key = fields.Char()
    twitter_api_secret = fields.Char()
    model = fields.Char('Type of Model')
    agent_ids = fields.One2many('twitter.agent', 'stream_id')
    state = fields.Selection([('start', 'Start'), ('stop', 'Stop')], default='stop')

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
            user_ids, last_agent = [], None
            for agent in self.agent_ids:
                if agent['auth_user'] and agent['state'] != 'archive':
                    last_agent = agent
                    user_ids.append(agent['auth_user'])
            if user_ids:
                auth = Oauth(self.twitter_api_key, self.twitter_api_secret)
                auth.set_access_token(last_agent['twitter_access_token'], last_agent['twitter_access_token_secret'])
                stream = Stream(auth, self)
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

    def on_connect(self):
        super(TwitterStream, self).on_connect()
        with api.Environment.manage():
            with registry(self.env.cr.dbname).cursor() as new_cr:
                self.env = api.Environment(new_cr, self.env.uid, self.env.context)
                self.state = 'start'
        pass

    def on_data(self, tweet):
        """ Call when tweet is come and store in twitter.tweet Model """
        if 'delete' not in tweet:
            tweet = loads(tweet)
            with api.Environment.manage():
                with registry(self.env.cr.dbname).cursor() as new_cr:
                    self.env = api.Environment(new_cr, self.env.uid, self.env.context)
                    agents = self.agent_ids.filtered(lambda o: o.auth_user == tweet['user']['id_str'] and o.state != 'archive').sorted(lambda r: r.create_date, reverse=True)
                    if len(agents):
                        self.env['twitter.tweet'].process_tweet(agents[0].id, tweet['retweeted_status']['id'] if tweet.get('retweeted_status') else tweet.get('id'))
        return True

    def on_error(self, status_code):
        super(TwitterStream, self).on_error(status_code)
        with api.Environment.manage():
            with registry(self.env.cr.dbname).cursor() as new_cr:
                self.env = api.Environment(new_cr, self.env.uid, self.env.context)
                self.state = 'stop'
        return False

    def on_disconnect(self, notice):
        super(TwitterStream, self).on_disconnect(notice)
        with api.Environment.manage():
            with registry(self.env.cr.dbname).cursor() as new_cr:
                self.env = api.Environment(new_cr, self.env.uid, self.env.context)
                self.state = 'stop'
        return False
