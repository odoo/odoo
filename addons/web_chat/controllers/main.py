# -*- coding: utf-8 -*-
import sys, time

import simplejson

import openerpweb

#----------------------------------------------------------
# OpenERP Web ajaxim Controllers
#----------------------------------------------------------
class PollServerMessageQueue(object):
    def __init__(self):
        # message queue
        self.l = []
        # online users
        self.users = {}
        # should contains: {
        #   'user1234' : { s:1, m:"status message", timestamp: last_contact_timestamp }
        # }
    def userlist():
        # return user list
        pass

    def write(self, m_type,  m_sender, m_recipent, m_message, m_group):
        # appends messages to l
        # when status message uupdate users
        pass
    def read(self, recpient, timestamp):
        # return matching message
        pass
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
        mq = req.applicationsession.setdefault("web_chat",PollServerMessageQueue())
        print "chat login",kw
        # r = 'loggued in'
        #u = generate random.randint(0,2**32)
        #s = cherrypy cookie id
        #f = mq.userlist()
        return  """
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

    @openerpweb.httprequest
    def logout(self, req):
        """
        --> GET http://im.ajaxim.com/logout
            { "r":"logged out" }
        """

    @openerpweb.httprequest
    def poll(self, req, **kw):
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
            jsonp1302140191599([{"t":"m","s":"Guest130214008855.5","r":"Guest130214013134.26","m":"fuck"}]);

            ('t' => $msg->type, 's' => $msg->from, 'r' => $msg->to, 'm' => $msg->message )
            mag type s or m
            echo '<script type="text/javascript">parent.AjaxIM.incoming('. json_encode($this->_pollParseMessages($messages)) .  ');</script>'


        """
        # for i in range(60):
            #r = mq.read(username,timestamp)
            # if messages
                # return r
            # if no message sleep 2s and retry
                # sleep 2
        # else
            # return emptylist
        print "chat poll",kw
        time.sleep(2)
        # it's http://localhost:8002/web_chat/pollserver/poll?method=long?callback=jsonp1302147330483&_1302147330483=
        return '%s([{"t":"m","s":"Guest130214008855.5","r":"Guest130214013134.26","m":"fuck"}]);'%kw.get('callback','')
        return None

    @openerpweb.jsonrequest
    def send(self, req, **kw):
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
        print "chat send",kw
        # mq.write()
        return {"action": actions}

    @openerpweb.jsonrequest
    def status(self, req, **kw):
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
        print "chat status",kw
        # mq.write()
        return {"action": actions}


