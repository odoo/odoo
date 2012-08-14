#!/usr/bin/env python

import werkzeug

try:
    # embedded
    import openerp.addons.web.common.http as openerpweb
    from openerp.addons.web.controllers.main import View
except ImportError:
    # standalone
    import web.common.http as openerpweb
    from web.controllers.main import View

class Mobile(openerpweb.Controller):
    _cp_path = '/mobile'

    @openerpweb.httprequest
    def index(self, req):
        r = werkzeug.utils.redirect('/web_mobile/static/src/web_mobile.html', 301)
        r.autocorrect_location_header = False
        return r
