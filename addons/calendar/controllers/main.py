# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

import odoo
from odoo import http, registry
from odoo.http import request


class MeetingInvitation(http.Controller):

    @http.route('/calendar/meeting/accept', type='http', auth="calendar")
    def accept(self, db, token, action, id, **kwargs):
        with registry(db).cursor() as cr:
            env = request.env(cr, odoo.SUPERUSER_ID)
            attendee = env['calendar.attendee'].search([('access_token', '=', token), ('state', '!=', 'accepted')])
            if attendee:
                attendee.do_accept()
        return self.view(db, token, action, id, view='form')

    @http.route('/calendar/meeting/decline', type='http', auth="calendar")
    def declined(self, db, token, action, id):
        with registry(db).cursor() as cr:
            env = request.env(cr, odoo.SUPERUSER_ID)
            attendee = env['calendar.attendee'].search([('access_token', '=', token), ('state', '!=', 'declined')])
            if attendee:
                attendee.do_decline()
        return self.view(db, token, action, id, view='form')

    @http.route('/calendar/meeting/view', type='http', auth="calendar")
    def view(self, db, token, action, id, view='calendar'):
        with registry(db).cursor() as cr:
            env = request.env(cr, odoo.SUPERUSER_ID)
            ResPartner = env['res.partner']
            attendee = env['calendar.attendee'].search_read([('access_token', '=', token)], [], limit=1)

            if attendee and attendee[0] and attendee[0].get('partner_id'):
                partner_id = int(attendee[0].get('partner_id')[0])
                tz = ResPartner.browse(partner_id).tz
                lang = ResPartner.browse(partner_id).lang
            else:
                tz = False
                lang = False

            attendee_data = env['calendar.event'].browse(id).with_context({tz: tz, lang: lang}).get_attendee()

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
    @http.route('/calendar/notify', type='json', auth="user")
    def notify(self):
        env = request.env(user=request.session.uid, context=request.session.context)
        return env["calendar.alarm_manager"].get_next_notif()

    @http.route('/calendar/notify_ack', type='json', auth="user")
    def notify_ack(self):
        env = request.env(user=request.session.uid, context=request.session.context)
        return env['res.partner']._set_calendar_last_notif_ack()
