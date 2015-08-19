import simplejson
import openerp
import openerp.http as http
from openerp.http import request
import openerp.addons.web.controllers.main as webmain
import json

class Controller(openerp.addons.bus.bus.Controller):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            ## For performance issue, the real time status notification is disabled. This means a change of status are still braoadcasted
            ## but not received by anyone. Otherwise, all listening user restart their longpolling at the same time and cause a 'ConnectionPool Full Error'
            ## since there is not enought cursors for everyone. Now, when a user open his list of users, an RPC call is made to update his user status list.
            # channel to receive message
            channels.append((request.db, 'calendar.alarm'))
        return super(Controller, self)._poll(dbname, channels, last, options)

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

        values = dict(init="s.calendar.event('%s', '%s', '%s', '%s' , '%s');" % (db, action, id, 'form', json.dumps(attendee_data)))
        return request.render('web.webclient_bootstrap', values)
