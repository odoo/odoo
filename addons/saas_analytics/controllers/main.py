import json
import textwrap

import simplejson
import werkzeug.wrappers

import web.common.http as openerpweb
import web.controllers.main

class web_analytics(openerpweb.Controller):
    
    # This controllers redirects virtual urls of the form /web_analytics/MODEL/VIEW
    # as provided to google by the analytics modules to a real url that openerp can
    # understand of the form /web/webclient/home/#model=MODEL&view_type=VIEW
    # So that the user can click openerp urls inside google analytics.

    @openerpweb.httprequest
    def redirect(self,req):
        url = req.httprequest.base_url
        suburl = url.split('/')
        suburl = suburl[suburl.index('redirect')+1:]

        rurl = "/web/webclient/home/#"
        if len(suburl) >=1 and suburl[0]:
            rurl += "model="+str(suburl[0])
        if len(suburl) >=2 and suburl[1]:
            rurl += "&view_type="+str(suburl[1])

        redirect = werkzeug.utils.redirect(rurl, 303)

        return redirect

