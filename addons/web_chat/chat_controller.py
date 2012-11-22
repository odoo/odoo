# -*- coding: utf-8 -*-

import openerp
import openerp.tools.config
import chat

class ImportController(openerp.addons.web.http.Controller):
    _cp_path = '/chat'

    @openerp.addons.web.http.jsonrequest
    def poll(self, req, last=None):
        if not openerp.tools.config.options["gevent"]:
            raise Exception("Not usable in a server not running gevent")
        num = 0
        while True:
            res = req.session.model('chat.message').get_messages(last, req.session.eval_context(req.context))
            if num >= 1 or len(res["res"]) > 0:
                return res
            last = res["last"]
            num += 1
            print "waiting"
            chat.Watcher.get_watcher(res["dbname"]).stop(30)
