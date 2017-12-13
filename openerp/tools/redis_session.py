# -*- coding: utf-8 -*-
"""
Created on 09/11/2011
@author: Carlo Pires <carlopires@gmail.com>
"""
import tnetstring
from werkzeug.contrib.sessions import SessionStore

SESSION_TIMEOUT = 60*60*24*7 # 7 weeks in seconds

class RedisSessionStore(SessionStore):
    """
    SessionStore that saves session to redis
    """
    def __init__(self, redis, key_template='session:%s', generate_salt=None):

        if not generate_salt:
            generate_salt = 'RFHXSYf_A@!d!2@g'  # default salt

        SessionStore.__init__(self)
        self.redis = redis
        self.key_template = key_template
        self.generate_salt = generate_salt

    def new(self):
        """Generate a new session."""
        return self.session_class({}, self.generate_key(self.generate_salt), True)

    def get_session_key(self, sid):
        if isinstance(sid, unicode):
            sid = sid.encode('utf-8')
        return self.key_template % sid

    def save(self, session):
        key = self.get_session_key(session.sid)
        if self.redis.set(key, tnetstring.dumps(dict(session))):
            return self.redis.expire(key, SESSION_TIMEOUT)

    def delete(self, session):
        key = self.get_session_key(session.sid)
        return self.redis.delete(key)

    def get(self, sid):
        if not self.is_valid_key(sid):
            return self.new()
        
        key = self.get_session_key(sid)
        saved = self.redis.get(key)
        if saved:
            data = tnetstring.loads(saved)
            return self.session_class(data, sid, False)

    def list(self):
        """
        Lists all sessions in the store.
        """
        session_keys = self.redis.keys(self.key_template[:-2] + '*')
        return [s[len(self.key_template)-2:] for s in session_keys]

# vim:et:ts=4:sw=4:
