import simplejson
import urllib
import openerp
import openerp.addons.web.http as http
from openerp.addons.web.http import request
import openerp.addons.web.controllers.main as webmain
SUPERUSER_ID = 1

class meetting_invitation(http.Controller):
    
    @http.route('/meeting_invitation/accept', type='http', auth="none")
    def accept(self, db, token, action, id):
        # http://hostname:8069/meeting_invitation/accept/id=1&token=&db=
        registry = openerp.modules.registry.RegistryManager.get(db)
        attendee_pool = registry.get('calendar.attendee')
        with registry.cursor() as cr:
            attendee_ids = attendee_pool.search(cr, SUPERUSER_ID, [('access_token','=',token)])
            attendee_pool.do_accept(cr, SUPERUSER_ID, attendee_ids)
        return self.view(db, action, id, view='form')
    
        
    @http.route('/meeting_invitation/decline', type='http', auth="none")
    def declined(self, db, token, action, id):
        # http://hostname:8069/meeting_invitation/accept/id=1&token=&db=
        registry = openerp.modules.registry.RegistryManager.get(db)
        attendee_pool = registry.get('calendar.attendee')
        with registry.cursor() as cr:
            attendee_ids = attendee_pool.search(cr, SUPERUSER_ID, [('access_token','=',token)])
            attendee_pool.do_decline(cr, SUPERUSER_ID, attendee_ids)
        return self.view(db, action, id, view='form')
        
    @http.route('/meeting_invitation/view', type='http', auth="none")
    def view(self, db, action, id, view='calendar'):
        # http://hostname:8069/meeting_invitation/view/id=1&token=&db=&view=
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in webmain.manifest_list('js', db=db))
        css = "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in webmain.manifest_list('css',db=db))
        return webmain.html_template % {
            'js': js,
            'css': css,
            'modules': simplejson.dumps(webmain.module_boot(db)),
            'init': 's.base_calendar.event("%s", "%s", "%s", "%s");' % (db, action, id, view),
        }


