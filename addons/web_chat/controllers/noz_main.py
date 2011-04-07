# -*- coding: utf-8 -*-

import simplejson
import openerpweb

from web_chat.controllers import im

__all__ = ['Webchat_IM']

chat_config_options = {'IM_LIBRARY': 'main',               # The IM server library.
                       'COOKIE_NAME': 'ajaxim_session',    # Session cookie used by Ajax IM
                       'COOKIE_PERIOD': 365                # Cookie period, in days                       
                       }

nodejs_memcache_server = ['localhost:11211']

class Webchat_IM(im.IM):
    
    _cp_path = "/webchat/webchatim"
    
    def __init__(self):
        super(Webchat_IM, self).__init__()
        
        return;
    
    @openerpweb.jsonrequest
    def index(self, req, username="admin", password="admin"):
                
        if req._login:
            self.username = req._login
            self.uid = req._uid
            self.db = req._db
            
        return;
    
    @openerpweb.jsonrequest
    def chat_login(self, req, username="admin", password="admin"):
        # TODO: use db and uid for unique identification.
        
        self.auth = [['admin', 'a'], ['demo', 'demo']]
        
        self.user_pass = []
        self.user_session = None
        
        if username and password:
            self.user_pass = [username, password]
        
        if self.user_pass in self.auth:
            self.user_session = username + '_' + str(req.session_id)
        
        data = {'username': username, 'user_id': username, 'user_session': self.user_session,
                'friends': {'u': 'demo', 'g': 'Friends', 's': '1'}    # {'u': 'username', 'g': 'group', 's': 'status'}
                }
        
        # Get the list of friends from memcache.            
        
        return dict(r='logged in', s=self.user_session, f=data['friends'])
    
    @openerpweb.jsonrequest
    def chat_logout(self):
        return dict(r='Logged out')