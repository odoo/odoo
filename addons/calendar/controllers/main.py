# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.http as http

from odoo.http import request
from odoo.tools.misc import get_lang
from odoo.tools import consteq


class CalendarController(http.Controller):

    @http.route('/calendar/meeting/accept/<string:token>/<int:attendee_id>', type='http', auth="calendar")
    def accept_meeting(self, token, attendee_id):
        """
            :param token: access token to authenticate the attendee
            :param attendee_id: ID of the attendee
        """
        attendee = request.env['calendar.attendee'].sudo().search([
            ('id', '=', attendee_id),
            ('state', '!=', 'accepted')
        ], limit=1)
        if not attendee or not consteq(attendee.access_token, token):
            return request.not_found()

        attendee.do_accept()
        return self.view_meeting(token, attendee.event_id.id, attendee_id=attendee.id)

    @http.route('/calendar/recurrence/accept/<string:token>/<int:attendee_id>', type='http', auth="calendar")
    def accept_recurrence(self, token, attendee_id):
        """
            :param token: access token to authenticate the attendee
            :param attendee_id: ID of the attendee
        """
        attendee = request.env['calendar.attendee'].sudo().search([
            ('id', '=', attendee_id),
            ('state', '!=', 'accepted')
        ], limit=1)

        if not attendee or not consteq(attendee.access_token, token):
            return request.not_found()

        attendees = request.env['calendar.attendee'].sudo().search([
            ('event_id', 'in', attendee.event_id.recurrence_id.calendar_event_ids.ids),
            ('partner_id', '=', attendee.partner_id.id),
            ('state', '!=', 'accepted'),
        ])
        attendees.do_accept()
        return self.view_meeting(token, attendee.event_id.id, attendee.id)

    @http.route('/calendar/meeting/decline/<string:token>/<int:attendee_id>', type='http', auth="calendar")
    def decline_meeting(self, token, attendee_id):
        """
            :param token: access token to authenticate the attendee
            :param attendee_id: ID of the attendee
        """
        attendee = request.env['calendar.attendee'].sudo().search([
            ('id', '=', attendee_id),
            ('state', '!=', 'declined')
        ], limit=1)

        if not attendee or not consteq(attendee.access_token, token):
            return request.not_found()
        attendee.do_decline()
        return self.view_meeting(token, attendee.event_id.id, attendee.id)

    @http.route('/calendar/recurrence/decline/<string:token>/<int:attendee_id>', type='http', auth="calendar")
    def decline_recurrence(self, token, attendee_id):
        """
            :param token: access token to authenticate the attendee
            :param attendee_id: ID of the attendee
        """
        attendee = request.env['calendar.attendee'].sudo().search([
            ('id', '=', attendee_id),
            ('state', '!=', 'declined')
        ], limit=1)

        if not attendee or not consteq(attendee.access_token, token):
            return request.not_found()
        attendees = request.env['calendar.attendee'].sudo().search([
            ('event_id', 'in', attendee.event_id.recurrence_id.calendar_event_ids.ids),
            ('partner_id', '=', attendee.partner_id.id),
            ('state', '!=', 'declined'),
        ])
        attendees.do_decline()
        return self.view_meeting(token, attendee.event_id.id, attendee.id)

    @http.route('/calendar/meeting/view/<string:token>/<int:event_id>/<int:attendee_id>', type='http', auth="calendar")
    def view_meeting(self, token, event_id, attendee_id):
        """
            :param token: access token to authenticate the attendee
            :param event_id: ID of the event
            :param attendee_id: ID of the attendee
        """
        attendee = request.env['calendar.attendee'].browse(attendee_id)
        if not (consteq(attendee.access_token, token) and attendee.event_id.id == event_id):
            return request.not_found()

        timezone = attendee.partner_id.tz
        lang = attendee.partner_id.lang or get_lang(request.env).code
        event = request.env['calendar.event'].with_context(tz=timezone, lang=lang).sudo().browse(int(event_id))
        company = event.user_id and event.user_id.company_id or event.create_uid.company_id

        # If user is internal and logged, redirect to form view of event
        # otherwise, display the simplifyed web page with event informations
        if request.env.user._is_internal():
            return request.redirect('/odoo/calendar.event/%s?db=%s' % (event_id, request.env.cr.dbname))

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

    @http.route('/calendar/meeting/join/<string:token>/<int:event_id>', type='http', auth="user", website=True)
    def calendar_join_meeting(self, token, event_id):
        event = request.env['calendar.event'].sudo().browse(event_id).exists()
        if not event or not consteq(event.access_token, token):
            return request.not_found()
        event.action_join_meeting(request.env.user.partner_id.id)
        attendee = request.env['calendar.attendee'].sudo().search([('partner_id', '=', request.env.user.partner_id.id), ('event_id', '=', event.id)])
        return request.redirect(f'/calendar/meeting/view/{attendee.access_token}/{event.id}/{attendee.id}')

    # Function used, in RPC to check every 5 minutes, if notification to do for an event or not
    @http.route('/calendar/notify', type='jsonrpc', auth="user")
    def notify(self):
        return request.env['calendar.alarm_manager'].get_next_notif()

    @http.route('/calendar/notify_ack', type='jsonrpc', auth="user")
    def notify_ack(self):
        return request.env['res.partner'].sudo()._set_calendar_last_notif_ack()

    @http.route(['/calendar/join_videocall/<int:event_id>/<string:access_token>'], type='http', auth='public')
    def calendar_join_videocall(self, access_token, event_id):
        event = request.env['calendar.event'].sudo().browse(event_id).exists()
        if not event or not consteq(event.access_token, access_token):
            return request.not_found()

        # if channel doesn't exist
        if not event.videocall_channel_id:
            event._create_videocall_channel()

        return request.redirect(event.videocall_channel_id.invitation_url)

    @http.route('/calendar/check_credentials', type='jsonrpc', auth='user')
    def check_calendar_credentials(self):
        # method should be overwritten by sync providers
        return request.env['res.users'].check_calendar_credentials()
