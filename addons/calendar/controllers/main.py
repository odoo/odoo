import json
import openerp
import openerp.http as http
from openerp.http import request
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
        partner_pool = registry.get('res.partner')
        with registry.cursor() as cr:
            attendee = attendee_pool.search_read(cr, openerp.SUPERUSER_ID, [('access_token', '=', token)], [])

            if attendee and attendee[0] and attendee[0].get('partner_id'):
                partner_id = int(attendee[0].get('partner_id')[0])
                tz = partner_pool.read(cr, openerp.SUPERUSER_ID, partner_id, ['tz'])['tz']
            else:
                tz = False

            attendee_data = meeting_pool.get_attendee(cr, openerp.SUPERUSER_ID, id, dict(tz=tz))

        if attendee:
            attendee_data['current_attendee'] = attendee[0]

        values = dict(
            init = """
                odoo.define('calendar.invitation_page', function (require) {
                    require('base_calendar.base_calendar').showCalendarInvitation('%s', '%s', '%s', '%s', '%s');
                });
            """ % (db, action, id, 'form', json.dumps(attendee_data))
        )
        return request.render('web.webclient_bootstrap', values)

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
            res = registry.get("res.partner")._set_calendar_last_notif_ack(cr, uid, context=context)
            return res
