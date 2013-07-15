import simplejson
import urllib
import openerp.addons.web.http as http
from openerp.addons.web.http import request
import openerp.addons.web.controllers.main as webmain

class crm_meetting_importstatus(http.Controller):

    @http.route('/meeting/meeting_invitation', type='http', auth="none")
    def meeting_invitation(self, db, token, action, view_type, id, status):
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in webmain.manifest_list('js', db=db))
        css = "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in webmain.manifest_list('css',db=db))

        return webmain.html_template % {
            'js': js,
            'css': css,
            'modules': simplejson.dumps(webmain.module_boot(db)),
            'init': 's.base_calendar.event("%s", "%s", "%s", "%s", "%s", "%s");'% (db, token, action, view_type, id, status),
        }


