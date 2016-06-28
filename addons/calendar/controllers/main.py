import json
import openerp
import openerp.http as http
from openerp.http import request
import openerp.addons.web.controllers.main as webmain
import json
import werkzeug

from odoo.api import Environment


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
        with registry.cursor() as cr:
            # Since we are in auth=none, create an env with SUPERUSER_ID
            env = Environment(cr, openerp.SUPERUSER_ID, {})
            attendee = env['calendar.attendee'].search([('access_token', '=', token)])
            timezone = attendee.partner_id.tz
            event = env['calendar.event'].with_context(tz=timezone).browse(int(id))

            # If user is logged, redirect to form view of event
            # otherwise, display the simplifyed web page with event informations
            if request.session.uid:
                return werkzeug.utils.redirect('/web?db=%s#id=%s&view_type=form&model=calendar.event' % (db, id))

            # NOTE : calling render return a lazy response. The rendering result will be done when the
            # cursor will be closed. So it is requried to call `flatten` to make the redering before
            # existing the `with` clause
            response = request.render('calendar.invitation_page_anonymous', {
                'event': event,
                'attendee': attendee,
            })
            response.flatten()
            return response

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
