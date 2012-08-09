#!/usr/bin/env python

from openerp.addons.web.common import http as oeweb
import werkzeug

class Mobile(oeweb.Controller):
    _cp_path = '/mobile'

    @oeweb.httprequest
    def index(self, req):
        return werkzeug.utils.redirect('/web_mobile/static/src/web_mobile.html', 301)
