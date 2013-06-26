import simplejson
import openerp.addons.web.http as oeweb
import openerp.addons.web.controllers.main as webmain

class crm_meetting_importstatus(oeweb.Controller):
    _cp_path = '/meeting'
    @oeweb.httprequest
    def meeting_invitation(self, req, db='may_29'):
        return webmain.html_template % {
            'js': "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in webmain.manifest_list(req, 'js',db= db)),
            'css': "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in webmain.manifest_list(req, 'css', db=db)),
            'modules': simplejson.dumps(webmain.module_boot(req, db)),
            'init': 'var wc = new s.web.WebClient();wc.appendTo($(document.body)); s.base_calendar.meeting_invitation();'
        }
