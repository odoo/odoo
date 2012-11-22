# -*- coding: utf-8 -*-

import openerp

class ImportController(openerp.addons.web.http.Controller):
    _cp_path = '/chat'

    @openerp.addons.web.http.jsonrequest
    def poll(self, req, last=None):
        res = req.session.model('chat.message').poll(last, req.session.eval_context(req.context))

        return res
