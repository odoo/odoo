# -*- coding: utf-8 -*-
import glob, os
import pprint

import simplejson

import openerpweb
import openerpweb.ast
import openerpweb.nonliterals

import cherrypy


#----------------------------------------------------------
# OpenERP Web mobile Controllers
#----------------------------------------------------------

class MOBILE(openerpweb.Controller):
    _cp_path = "/web_mobile/mobile"

    @openerpweb.jsonrequest
    def sc_list(self, req):
        return req.session.model('ir.ui.view_sc').get_sc(req.session._uid, "ir.ui.menu", {})

    @openerpweb.jsonrequest
    def logout(self,req):
        req.session_id = False
        req.session._uid = False

