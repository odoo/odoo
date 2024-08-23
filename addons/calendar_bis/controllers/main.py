# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.http as http

from odoo.http import request
from odoo.tools.misc import get_lang


class CalendarController(http.Controller):

    # YTI Note: Keep id and kwargs only for retrocompatibility purpose
    @http.route('/calendar/meeting/accept', type='http', auth="calendar")
    def accept_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee_bis'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'yes')])
        attendee.do_accept()
        return self.view_meeting(token, id)

    @http.route('/calendar/recurrence/accept', type='http', auth="calendar")
    def accept_recurrence(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee_bis'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'yes')])
        if attendee:
            attendees = request.env['calendar.attendee_bis'].sudo().search([
                ('timeslot_ids', 'in', attendee.timeslot_id.event_id.timeslot_ids.ids),
                ('partner_id', '=', attendee.partner_id.id),
                ('state', '!=', 'yes'),
            ])
            attendees.do_accept()
        return self.view_meeting(token, id)

    @http.route('/calendar/meeting/decline', type='http', auth="calendar")
    def decline_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee_bis'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'no')])
        attendee.do_decline()
        return self.view_meeting(token, id)

    @http.route('/calendar/recurrence/decline', type='http', auth="calendar")
    def decline_recurrence(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee_bis'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'no')])
        if attendee:
            attendees = request.env['calendar.attendee_bis'].sudo().search([
                ('timeslot_ids', 'in', attendee.timeslot_id.event_id.timeslot_ids.ids),
                ('partner_id', '=', attendee.partner_id.id),
                ('state', '!=', 'no'),
            ])
            attendees.do_decline()
        return self.view_meeting(token, id)

    @http.route('/calendar/meeting/view', type='http', auth="calendar")
    def view_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee_bis'].sudo().search([
            ('access_token', '=', token),
            ('event_id', '=', int(id))])
        if not attendee:
            return request.not_found()
        timezone = attendee.partner_id.tz
        lang = attendee.partner_id.lang or get_lang(request.env).code
        timeslot = request.env['calendar.timeslot'].with_context(tz=timezone, lang=lang).sudo().browse(int(id))
        company = timeslot.user_id and timeslot.user_id.company_id or timeslot.create_uid.company_id

        # If user is internal and logged, redirect to form view of event
        # otherwise, display the simplified web page with event information
        if request.env.user._is_internal():
            return request.redirect('/web?db=%s#id=%s&view_type=form&model=calendar.event' % (request.env.cr.dbname, id))

        # NOTE : we don't use request.render() since:
        # - we need a template rendering which is not lazy, to render before cursor closing
        # - we need to display the template in the language of the user (not possible with
        #   request.render())
        response_content = request.env['ir.ui.view'].with_context(lang=lang)._render_template(
            'calendar.invitation_page_anonymous', {
                'company': company,
                'timeslot': timeslot,
                'attendee': attendee,
            })
        return request.make_response(response_content, headers=[('Content-Type', 'text/html')])

    # @http.route('/calendar/meeting/join', type='http', auth="user", website=True)
    # def calendar_join_meeting(self, token, **kwargs):
    #     event = request.env['calendar.timeslot'].sudo().search([
    #         ('access_token', '=', token)])
    #     if not event:
    #         return request.not_found()
    #     event.action_join_meeting(request.env.user.partner_id.id)
    #     attendee = request.env['calendar.attendee'].sudo().search([('partner_id', '=', request.env.user.partner_id.id), ('event_id', '=', event.id)])
    #     return request.redirect('/calendar/meeting/view?token=%s&id=%s' % (attendee.access_token, event.id))
    #
    # # Function used, in RPC to check every 5 minutes, if notification to do for an event or not
    # @http.route('/calendar/notify', type='json', auth="user")
    # def notify(self):
    #     return request.env['calendar.alarm_manager'].get_next_notif()
    #
    # @http.route('/calendar/notify_ack', type='json', auth="user")
    # def notify_ack(self):
    #     return request.env['res.partner'].sudo()._set_calendar_last_notif_ack()
    #
    # @http.route('/calendar/join_videocall/<string:access_token>', type='http', auth='public')
    # def calendar_join_videocall(self, access_token):
    #     event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)])
    #     if not event:
    #         return request.not_found()
    #
    #     # if channel doesn't exist
    #     if not event.videocall_channel_id:
    #         event._create_videocall_channel()
    #
    #     return request.redirect(event.videocall_channel_id.invitation_url)
    #
    # @http.route('/calendar/check_credentials', type='json', auth='user')
    # def check_calendar_credentials(self):
    #     # method should be overwritten by sync providers
    #     return request.env['res.users'].check_calendar_credentials()
