import werkzeug

import odoo.http as http
from odoo.http import request


class CalendarController(http.Controller):

    @http.route('/calendar/meeting/accept', type='http', auth="calendar")
    def accept_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'accepted')])
        if not attendee:
            return request.not_found()
        return request.redirect(f'/calendar/meeting/accept/{token}/{attendee.id}?{werkzeug.urls.url_encode(kwargs)}')

    @http.route('/calendar/recurrence/accept', type='http', auth="calendar")
    def accept_recurrence(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'accepted')])
        if not attendee:
            return request.not_found()
        return request.redirect(f'/calendar/recurrence/accept/{token}/{attendee.id}?{werkzeug.urls.url_encode(kwargs)}')

    @http.route('/calendar/meeting/decline', type='http', auth="calendar")
    def decline_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'declined')])
        if not attendee:
            return request.not_found()
        return request.redirect(f'/calendar/meeting/decline/{token}/{attendee.id}?{werkzeug.urls.url_encode(kwargs)}')

    @http.route('/calendar/recurrence/decline', type='http', auth="calendar")
    def decline_recurrence(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('state', '!=', 'declined')])
        if not attendee:
            return request.not_found()
        return request.redirect(f'/calendar/recurrence/decline/{token}/{attendee.id}?{werkzeug.urls.url_encode(kwargs)}')

    @http.route('/calendar/meeting/view', type='http', auth="calendar")
    def view_meeting(self, token, id, **kwargs):
        attendee = request.env['calendar.attendee'].sudo().search([
            ('access_token', '=', token),
            ('event_id', '=', int(id))])
        if not attendee:
            return request.not_found()
        return request.redirect(f'/calendar/meeting/view/{token}/{attendee.event_id.id}/{attendee.id}?{werkzeug.urls.url_encode(kwargs)}')

    @http.route('/calendar/meeting/join', type='http', auth="user", website=True)
    def calendar_join_meeting(self, token, **kwargs):
        event = request.env['calendar.event'].sudo().search([
            ('access_token', '=', token)])
        if not event:
            return request.not_found()
        return request.redirect(f'/calendar/meeting/join/{token}/{event.id}?{werkzeug.urls.url_encode(kwargs)}')

    @http.route('/calendar/join_videocall/<string:access_token>', type='http', auth='public')
    def calendar_join_videocall(self, access_token):
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)])
        if not event:
            return request.not_found()
        return request.redirect(f'/calendar/join_videocall/{event.id}/{access_token}')
