# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.http as http

from odoo.http import request
from odoo.tools.misc import get_lang
from odoo.tools import consteq


class CalendarController(http.Controller):

    def fetch_attendee(self, id=False, attendee_id=False, token=False, filter_state='accepted'):
        if id and token:
            # Old logic with event ID
            attendee = request.env['calendar.attendee'].sudo().search([
                ('access_token', '=', token),
                ('state', '!=', filter_state)
            ], limit=1)
            return attendee
        elif attendee_id:
            # New logic with attendee ID
            attendee = request.env['calendar.attendee'].sudo().search([
                ('id', '=', attendee_id),
                ('state', '!=', filter_state)
            ], limit=1)
            return attendee
        else:
            return request.env['calendar.attendee']

    @http.route('/calendar/meeting/accept', type='http', auth="calendar")
    def accept_meeting(self, token, id=False, attendee_id=False):
        """
            :param token: access token to authenticate the attendee
            :param id: optional, ID of the event
            :param attendee_id: optional, ID of the attendee
        """
        attendee = self.fetch_attendee(id, attendee_id, token)
        if not attendee or not consteq(attendee.access_token, token):
            return request.not_found()

        attendee.do_accept()
        return self.view_meeting(token, attendee.event_id.id, attendee_id=attendee.id)

    @http.route('/calendar/recurrence/accept', type='http', auth="calendar")
    def accept_recurrence(self, token, id=False, attendee_id=False):
        """
            :param token: access token to authenticate the attendee
            :param id: optional, ID of the event
            :param attendee_id: optional, ID of the attendee
        """

        attendee = self.fetch_attendee(id, attendee_id, token)
        if not attendee or not consteq(attendee.access_token, token):
            return request.not_found()

        attendees = request.env['calendar.attendee'].sudo().search([
            ('event_id', 'in', attendee.event_id.recurrence_id.calendar_event_ids.ids),
            ('partner_id', '=', attendee.partner_id.id),
            ('state', '!=', 'accepted'),
        ])
        attendees.do_accept()
        return self.view_meeting(token, id, attendee.id)

    @http.route('/calendar/meeting/decline', type='http', auth="calendar")
    def decline_meeting(self, token, id=False, attendee_id=False):
        """
            :param token: access token to authenticate the attendee
            :param id: optional, ID of the event
            :param attendee_id: optional, ID of the attendee
        """

        attendee = self.fetch_attendee(id, attendee_id, token, 'declined')
        if not attendee or not consteq(attendee.access_token, token):
            return request.not_found()
        attendee.do_decline()
        return self.view_meeting(token, id, attendee.id)

    @http.route('/calendar/recurrence/decline', type='http', auth="calendar")
    def decline_recurrence(self, token, id=False, attendee_id=False):
        """
            :param token: access token to authenticate the attendee
            :param id: optional, ID of the event
            :param attendee_id: optional, ID of the attendee
        """

        attendee = self.fetch_attendee(id, attendee_id, token, 'declined')
        if not attendee or not consteq(attendee.access_token, token):
            return request.not_found()
        attendees = request.env['calendar.attendee'].sudo().search([
            ('event_id', 'in', attendee.event_id.recurrence_id.calendar_event_ids.ids),
            ('partner_id', '=', attendee.partner_id.id),
            ('state', '!=', 'declined'),
        ])
        attendees.do_decline()
        return self.view_meeting(token, id, attendee.id)

    @http.route('/calendar/meeting/view', type='http', auth="calendar")
    def view_meeting(self, token, id=False, attendee_id=False):
        """
            :param token: access token to authenticate the attendee
            :param id: optional, ID of the event
            :param attendee_id: optional, ID of the attendee
        """
        attendee = request.env['calendar.attendee'].browse(attendee_id)
        if not (consteq(attendee.access_token, token) and attendee.event_id.id == id):
            return request.not_found()
        timezone = attendee.partner_id.tz
        lang = attendee.partner_id.lang or get_lang(request.env).code
        event = request.env['calendar.event'].with_context(tz=timezone, lang=lang).sudo().browse(int(id))
        company = event.user_id and event.user_id.company_id or event.create_uid.company_id

        # If user is internal and logged, redirect to form view of event
        # otherwise, display the simplifyed web page with event informations
        if request.env.user._is_internal():
            return request.redirect('/odoo/calendar.event/%s?db=%s' % (id, request.env.cr.dbname))

        # NOTE : we don't use request.render() since:
        # - we need a template rendering which is not lazy, to render before cursor closing
        # - we need to display the template in the language of the user (not possible with
        #   request.render())
        response_content = request.env['ir.ui.view'].with_context(lang=lang)._render_template(
            'calendar.invitation_page_anonymous', {
                'company': company,
                'event': event,
                'attendee': attendee,
            })
        return request.make_response(response_content, headers=[('Content-Type', 'text/html')])

    @http.route('/calendar/meeting/join', type='http', auth="user", website=True)
    def calendar_join_meeting(self, token):
        event = request.env['calendar.event'].sudo().search([
            ('access_token', '=', token)])
        if not event or not consteq(event.access_token, token):
            return request.not_found()
        event.action_join_meeting(request.env.user.partner_id.id)
        attendee = request.env['calendar.attendee'].sudo().search([('partner_id', '=', request.env.user.partner_id.id), ('event_id', '=', event.id)])
        return request.redirect('/calendar/meeting/view?token=%s&id=%s&attendee_id=%s' % (attendee.access_token, event.id, attendee.id))

    # Function used, in RPC to check every 5 minutes, if notification to do for an event or not
    @http.route('/calendar/notify', type='json', auth="user")
    def notify(self):
        return request.env['calendar.alarm_manager'].get_next_notif()

    @http.route('/calendar/notify_ack', type='json', auth="user")
    def notify_ack(self):
        return request.env['res.partner'].sudo()._set_calendar_last_notif_ack()

    # DANE: remove old routes in v19/v20
    @http.route(['/calendar/join_videocall/<int:event_id>/<string:access_token>',
                 '/calendar/join_videocall/<string:access_token>'], type='http', auth='public')
    def calendar_join_videocall(self, access_token=False, event_id=False):
        if not event_id:
            event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)])
        else:
            event = request.env['calendar.event'].sudo().browse(event_id).exists()

        if not event or not consteq(event.access_token, access_token):
            return request.not_found()

        # if channel doesn't exist
        if not event.videocall_channel_id:
            event._create_videocall_channel()

        return request.redirect(event.videocall_channel_id.invitation_url)

    @http.route('/calendar/check_credentials', type='json', auth='user')
    def check_calendar_credentials(self):
        # method should be overwritten by sync providers
        return request.env['res.users'].check_calendar_credentials()
