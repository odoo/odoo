# -*- coding: utf-8 -*-
import sys, time

import simplejson
import random
import openerpweb

#----------------------------------------------------------
# OpenERP Web ajaxim Controllers
#----------------------------------------------------------
class PollServerMessageQueue(object):
    def __init__(self):
        # message queue
        self.messages = []
        # online users
        self.users = {}
        # should contains: {
        #   'user1234' : { s:1, m:"status message", timestamp: last_contact_timestamp }
        # }
    def userlist(self, req):
        userlist = [users for users in req.applicationsession['users']]
        
#        userlist = [
#                    {"u": "Guest130205108745.47", "s": {"s": 1, "m": ""}, "g": "Users"},
#                    {"u": "Guest130209838956.76", "s": {"s": 1, "m": ""}, "g": "Users"},
#                ]

        return userlist

    def write(self, m_type,  m_from, m_to, m_message, m_group):
        self.messages.append({'type': m_type, 'from': m_from, 'to': m_to, 'message': m_message, 'group': m_group})
        # when status message update users
        pass
    
    def read(self, recipient, timestamp):
        for msg in self.messages:
            if msg['to'] == recipient:
                return self.messages
            
    def gc():
        # remove message older than 300s from self.l
        # remove dead users from self.users
        pass

class PollServer(openerpweb.Controller):
    _cp_path = "/web_chat/pollserver"

    @openerpweb.httprequest
    def login(self, req, **kw):
                
        """
        --> POST http://ajaxim.com/wp-content/plugins/im/ajaxim.php/login
            Form Data
                username:""
                password:"d41d8cd98f00b204e9800998ecf8427e"
        <-- 200 OK
            Content-Type:text/html

            {
                "r":"logged in",
                "u":"Guest130213866190.85",
                "s":"f9e1811536f19ad5b9e00376f9ff1532",
                "f":[
                    {"u":"Guest130205108745.47","s":{"s":1,"m":""},"g":"Users"},
                    {"u":"Guest130209838956.76","s":{"s":1,"m":""},"g":"Users"},
                ]
            }
        """
        mq = req.applicationsession.setdefault("web_chat", PollServerMessageQueue())
        mq.messages = []
        
        #r = 'logged in'
        #u = generate random.randint(0,2**32)
        #s = cherrypy cookie id
        #f = mq.userlist()
        
#        username = 'Guest'+ str(random.randint(0, 2**32))
#        
#        if not req.applicationsession.get('users'):
#            req.applicationsession['users'] = [{'u': username, 's':{'s':1, 'm':''}, 'g':'Users'}]
#        else:
#            req.applicationsession['users'].append({'u': username, 's':{'s':1, 'm':''}, 'g':'Users'})
        req.applicationsession['users'] = [{'u': 'Guest1', 's':{'s':1, 'm':'111'}, 'g':'Users'},
                                           {'u': 'Guest2', 's':{'s':1, 'm':'222'}, 'g':'Users'},
                                           {'u': 'Guest3', 's':{'s':1, 'm':'333'}, 'g':'Users'}]
        
        # Temporary Guest1 is my current user
        req.applicationsession['current_user'] = 'Guest1'
        
        return """
            {
                "r":"logged in",
                "u":'Guest1',
                "s":"f9e1811536f19ad5b9e00376f9ff1532",
                "f":""" + str(mq.userlist(req)) + """
            }
        """

    @openerpweb.httprequest
    def logout(self, req):
        """
        --> GET http://im.ajaxim.com/logout
            { "r":"logged out" }
        """

    @openerpweb.httprequest
    def poll(self, req, **kw):
        
        mq = req.applicationsession.setdefault("web_chat", PollServerMessageQueue())
        
        # Method: Long Poll
        
        """
        --> GET http://im.ajaxim.com/poll?callback=jsonp1302138663582&_1302138663582=
        <-- 200 OK
            Content-Type:text/html

            noop:
            jsonp1302138663582([]);

            roster user online:
            jsonp1302140366243([{"t":"s","s":"Guest130214038974.31","r":"all","m":"1:","g":"Users"}]);

            roster user left:
            jsonp1302140441577([{"t":"s","s":"Guest130214038974.31","r":"","m":"0:"}]);

            receive message:
            jsonp1302140191599([{"t":"m","s":"Guest130214008855.5","r":"Guest130214013134.26","m":"xxxxxx"}]);

            ('t' => $msg->type, 's' => $msg->from, 'r' => $msg->to, 'm' => $msg->message )
            mag type s or m
            echo '<script type="text/javascript">parent.AjaxIM.incoming('. json_encode($this->_pollParseMessages($messages)) .  ');</script>'

        """
        
        msg = '[]'
        
        for i in range(5):
            received_msg = mq.read('Guest1', i);
            if received_msg:
                msg = self._pollParseMessages(received_msg)
                time.sleep(1)
            else:
                msg = '[]'
                time.sleep(1)

        return '%s'%kw.get('callback', '') + '(' + str(msg) + ');'
        
    @openerpweb.httprequest
    def send(self, req, **kw):
        
        to = kw.get('to')
        message = kw.get('message')
        
        mq = req.applicationsession.setdefault("web_chat", PollServerMessageQueue())
        
        """
        --> GET http://im.ajaxim.com/send?callback=jsonp1302139980022&to=Guest130205108745.47&message=test&_1302139980022=
            callback: jsonp1302139980022
            to: Guest130205108745.47
            message: test
            _1302139980022:

        <-- 200 OK
            Content-Type:text/html

            return array('r' => 'sent');
            return array('r' => 'error', 'e' => 'no session found');
            return array('r' => 'error', 'e' => 'no_recipient');
            return array('r' => 'error', 'e' => 'send error');

        """
        
        if not req.applicationsession['current_user']:
            return dict(r='error', e='no session found')
        
        if not to:
            return dict(r='error', e='no_recipient')
        
        if message:
            mq.write(m_type="m",  m_from=req.applicationsession['current_user'], m_to=to, m_message=message, m_group="Users")        
            return '%s'%kw.get('callback', '') + '(' + simplejson.dumps({'r': 'sent'}) + ')'
        else:
            return {'r': 'error', 'e': 'send error'}

    @openerpweb.httprequest
    def status(self, req, **kw):
        mq = req.applicationsession.setdefault("web_chat", PollServerMessageQueue())
        
        """
        --> GET status call
           const Offline = 0;
           const Available = 1;
           const Away = 2;
           const Invisible = 3;

        <-- 200 OK
            Content-Type:text/html

            return array('r' => 'status set');
            return array('r' => 'error', 'e' => 'no session found');
            return array('r' => 'error', 'e' => 'status error');
        """
        print "======== chat status ========",kw
        # mq.write()
        return {"action": ""}
    
    def _pollParseMessages(self, messages):
        msg_arr = []
        for msg in messages:
            msg_arr.append({"t": str(msg['type']), "s": str(msg['from']), "r": str(msg['to']), "m": str(msg['message'])})
        
        return msg_arr
    
    def _sanitize(self, message):
        return message.replace('>', '&gt;').replace('<', '&lt;').replace('&', '&amp;');


