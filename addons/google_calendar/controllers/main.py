# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request


class GoogleCalendarController(http.Controller):

    @http.route('/google_calendar/sync_data', type='json', auth='user')
    def sync_data(self, arch, fields, model, **kw):
        """
            This route/function is called when we want to synchronize Odoo calendar with Google Calendar
            Function return a dictionary with the status :  need_config_from_admin, need_auth, need_refresh, success if not calendar_event
            The dictionary may contains an url, to allow Odoo Client to redirect user on this URL for authorization for example
        """

        if model == 'calendar.event':
            GoogleCalendar = request.env['google.calendar'].with_context(kw.get('local_context'))

            # Checking that admin have already configured Google API for google synchronization !
            client_id = request.env['google.service'].with_context(kw.get('local_context')).get_client_id('calendar')

            if not client_id or client_id == '':

                result = {
                    "status": "need_config_from_admin",
                    "url": '',
                }
                if GoogleCalendar.can_authorize_google():
                    action = request.env.ref('google_calendar.action_config_settings_google_calendar')
                    result['action'] = action.id

                return result

            # Checking that user have already accepted Odoo to access his calendar !
            if GoogleCalendar.need_authorize():
                url = GoogleCalendar.authorize_google_uri(from_url=kw.get('fromurl'))
                return {
                    "status": "need_auth",
                    "url": url
                }

            # If App authorized, and user access accepted, We launch the synchronization
            return GoogleCalendar.synchronize_events()

        return {"status": "success"}

    @http.route('/google_calendar/remove_references', type='json', auth='user')
    def remove_references(self, model, **kw):
        """
            This route/function is called when we want to remove all the references between one Odoo Calendar and one Google Calendar
        """
        status = "NOP"
        if model == 'calendar.event':
            # Checking that user have already accepted Odoo to access his calendar !
            if request.env['google.calendar'].with_context(kw.get('local_context')).remove_references():
                status = "OK"
            else:
                status = "KO"
        return {"status": status}
