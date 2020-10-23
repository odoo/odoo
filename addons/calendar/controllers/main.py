# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

import odoo.http as http

from odoo.http import request
from odoo.tools.misc import get_lang


class CalendarController(http.Controller):

    # YTI Note: Keep id and kwargs only for retrocompatibility purpose
    @http.route('/calendar/meeting/accept', type='http', auth="calendar")
    def accept_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'accepted')])
        attendee.do_accept()
        return self.view_meeting(token, id)

    @http.route('/calendar/recurrence/accept', type='http', auth="calendar")
    def accept_recurrence(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'accepted')])
        if attendee:
            attendees = request.env['calendar.attendee'].sudo().search([
                ('event_id', 'in', attendee.event_id.recurrence_id.calendar_event_ids.ids),
                ('partner_id', '=', attendee.partner_id.id),
                ('state', '!=', 'accepted'),
            ])
            attendees.do_accept()
        return self.view_meeting(token, id)

    @http.route('/calendar/meeting/decline', type='http', auth="calendar")
    def decline_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'declined')])
        attendee.do_decline()
        return self.view_meeting(token, id)

    @http.route('/calendar/recurrence/decline', type='http', auth="calendar")
    def decline_recurrence(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'declined')])
        if attendee:
            attendees = request.env['calendar.attendee'].sudo().search([
                ('event_id', 'in', attendee.event_id.recurrence_id.calendar_event_ids.ids),
                ('partner_id', '=', attendee.partner_id.id),
                ('state', '!=', 'declined'),
            ])
            attendees.do_decline()
        return self.view_meeting(token, id)

    @http.route('/calendar/meeting/view', type='http', auth="calendar")
    def view_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('event_id', '=', int(id))])
        if not attendee:
            return request.not_found()
        timezone = attendee.partner_id.tz
        lang = attendee.partner_id.lang or get_lang(request.env).code
        event = request.env['calendar.event'].with_context(tz=timezone, lang=lang).sudo().browse(int(id))

        # If user is internal and logged, redirect to form view of event
        # otherwise, display the simplifyed web page with event informations
        if request.session.uid and request.env['res.users'].browse(request.session.uid).user_has_groups('base.group_user'):
            return werkzeug.utils.redirect('/web?db=%s#id=%s&view_type=form&model=calendar.event' % (request.env.cr.dbname, id))

        # NOTE : we don't use request.render() since:
        # - we need a template rendering which is not lazy, to render before cursor closing
        # - we need to display the template in the language of the user (not possible with
        #   request.render())
        response_content = request.env['ir.ui.view'].with_context(lang=lang)._render_template(
            'calendar.invitation_page_anonymous', {
                'event': event,
                'attendee': attendee,
            })
        return request.make_response(response_content, headers=[('Content-Type', 'text/html')])

    # Function used, in RPC to check every 5 minutes, if notification to do for an event or not
    @http.route('/calendar/notify', type='json', auth="user")
    def notify(self):
        return request.env['calendar.alarm_manager'].get_next_notif()

    @http.route('/calendar/notify_ack', type='json', auth="user")
    def notify_ack(self):
        return request.env['res.partner'].sudo()._set_calendar_last_notif_ack()
