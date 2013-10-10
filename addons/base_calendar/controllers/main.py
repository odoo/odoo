import simplejson
import urllib
import openerp
import openerp.addons.web.http as http
from openerp.addons.web.http import request
import openerp.addons.web.controllers.main as webmain
import json

class meetting_invitation(http.Controller):

    @http.route('/meeting_invitation/accept', type='http', auth="none")
    def accept(self, db, token, action, id):
        # http://hostname:8069/meeting_invitation/accept?db=#token=&action=&id=
        registry = openerp.modules.registry.RegistryManager.get(db)
        attendee_pool = registry.get('calendar.attendee')
        with registry.cursor() as cr:
            attendee_id = attendee_pool.search(cr, openerp.SUPERUSER_ID, [('access_token','=',token),('state','!=', 'accepted')])
            if attendee_id:
                attendee_pool.do_accept(cr, openerp.SUPERUSER_ID, attendee_id)
        return self.view(db, token, action, id, view='form')

    @http.route('/meeting_invitation/decline', type='http', auth="none")
    def declined(self, db, token, action, id):
        # http://hostname:8069/meeting_invitation/decline?db=#token=&action=&id=
        registry = openerp.modules.registry.RegistryManager.get(db)
        attendee_pool = registry.get('calendar.attendee')
        with registry.cursor() as cr:
            attendee_id = attendee_pool.search(cr, openerp.SUPERUSER_ID, [('access_token','=',token),('state','!=', 'declined')])
            if attendee_id:
                attendee_pool.do_decline(cr, openerp.SUPERUSER_ID, attendee_id)
        return self.view(db, token, action, id, view='form')

    @http.route('/meeting_invitation/view', type='http', auth="none")
    def view(self, db, token, action, id, view='calendar'):
        # http://hostname:8069/meeting_invitation/view?db=#token=&action=&id=
        registry = openerp.modules.registry.RegistryManager.get(db)
        meeting_pool = registry.get('crm.meeting')
        attendee_pool = registry.get('calendar.attendee')
        with registry.cursor() as cr:
            attendee_data = meeting_pool.get_attendee(cr, openerp.SUPERUSER_ID, id);
            attendee = attendee_pool.search_read(cr, openerp.SUPERUSER_ID, [('access_token','=',token)],[])
        if attendee:
            attendee_data['current_attendee'] = attendee[0]
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in webmain.manifest_list('js', db=db))
        css = "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in webmain.manifest_list('css',db=db))
        return webmain.html_template % {
            'js': js,
            'css': css,
            'modules': simplejson.dumps(webmain.module_boot(db)),
            'init': "s.base_calendar.event('%s', '%s', '%s', '%s' , '%s');" % (db, action, id, view, json.dumps(attendee_data)),
        }


