import simplejson
import openerp
import openerp.addons.web.http as http
from openerp.addons.web.http import request
import openerp.addons.web.controllers.main as webmain
import json


class meeting_invitation(http.Controller):

    @http.route('/calendar/meeting/accept', type='http', auth="calendar")
    def accept(self, db, token, action, id, **kwargs):
        registry = openerp.modules.registry.RegistryManager.get(db)
        attendee_pool = registry.get('calendar.attendee')
        with registry.cursor() as cr:
            attendee_id = attendee_pool.search(cr, openerp.SUPERUSER_ID, [('access_token', '=', token), ('state', '!=', 'accepted')])
            if attendee_id:
                attendee_pool.do_accept(cr, openerp.SUPERUSER_ID, attendee_id)
        return self.view(db, token, action, id, view='form')

    @http.route('/calendar/meeting/decline', type='http', auth="calendar")
    def declined(self, db, token, action, id):
        registry = openerp.modules.registry.RegistryManager.get(db)
        attendee_pool = registry.get('calendar.attendee')
        with registry.cursor() as cr:
            attendee_id = attendee_pool.search(cr, openerp.SUPERUSER_ID, [('access_token', '=', token), ('state', '!=', 'declined')])
            if attendee_id:
                attendee_pool.do_decline(cr, openerp.SUPERUSER_ID, attendee_id)
        return self.view(db, token, action, id, view='form')

    @http.route('/calendar/meeting/view', type='http', auth="calendar")
    def view(self, db, token, action, id, view='calendar'):
        registry = openerp.modules.registry.RegistryManager.get(db)
        meeting_pool = registry.get('calendar.event')
        attendee_pool = registry.get('calendar.attendee')
        with registry.cursor() as cr:
            attendee_data = meeting_pool.get_attendee(cr, openerp.SUPERUSER_ID, id)
            attendee = attendee_pool.search_read(cr, openerp.SUPERUSER_ID, [('access_token', '=', token)], [])

        if attendee:
            attendee_data['current_attendee'] = attendee[0]
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in webmain.manifest_list('js', db=db))
        css = "\n       ".join('<link rel="stylesheet" href="%s">' % i for i in webmain.manifest_list('css', db=db))

        return webmain.html_template % {
            'js': js,
            'css': css,
            'modules': simplejson.dumps(webmain.module_boot(db)),
            'init': "s.calendar.event('%s', '%s', '%s', '%s' , '%s');" % (db, action, id, 'form', json.dumps(attendee_data)),
        }

    # Function used, in RPC to check every 5 minutes, if notification to do for an event or not
    @http.route('/calendar/notify', type='json', auth="none")
    def notify(self):
        registry = request.registry
        uid = request.session.uid
        context = request.session.context
        with registry.cursor() as cr:
            res = registry.get("calendar.alarm_manager").get_next_notif(cr, uid, context=context)
            return res

    @http.route('/calendar/notify_ack', type='json', auth="none")
    def notify_ack(self, type=''):
        registry = request.registry
        uid = request.session.uid
        context = request.session.context
        with registry.cursor() as cr:
            res = registry.get("res.partner").calendar_last_notif_ack(cr, uid, context=context)
            return res
