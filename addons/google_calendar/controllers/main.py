# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class GoogleCalendarController(http.Controller):

    @http.route('/google_calendar/sync_data', type='json', auth='user')
    def sync_data(self, arch, fields, model, **kw):
        """ This route/function is called when we want to synchronize Odoo calendar with Google Calendar
            Function return a dictionary with the status :  need_config_from_admin, need_auth, need_refresh, success if not calendar_event
            The dictionary may contains an url, to allow Odoo Client to redirect user on this URL for authorization for example
        """
        if model == 'calendar.event':
            GoogleService = request.env['google.service']
            GoogleCal = request.env['google.calendar']

            # Checking that admin have already configured Google API for google synchronization !
            context = kw.get('local_context', {})
            client_id = GoogleService.with_context(context).get_client_id('calendar')

            if not client_id or client_id == '':
                action_id = ''
                if GoogleCal.can_authorize_google():
                    action_id = request.env.ref('google_calendar.action_config_settings_google_calendar').id
                return {
                    "status": "need_config_from_admin",
                    "url": '',
                    "action": action_id
                }

            # Checking that user have already accepted Odoo to access his calendar !
            if GoogleCal.need_authorize():
                url = GoogleCal.with_context(context).authorize_google_uri(from_url=kw.get('fromurl'))
                return {
                    "status": "need_auth",
                    "url": url
                }

            # If App authorized, and user access accepted, We launch the synchronization
            return GoogleCal.with_context(context).synchronize_events()

        return {"status": "success"}

    @http.route('/google_calendar/remove_references', type='json', auth='user')
    def remove_references(self, model, **kw):
        """ This route/function is called when we want to remove all the references between one calendar Odoo and one Google Calendar """
        status = "NOP"
        if model == 'calendar.event':
            GoogleCal = request.env['google.calendar']
            # Checking that user have already accepted Odoo to access his calendar !
            context = kw.get('local_context', {})
            if GoogleCal.with_context(context).remove_references():
                status = "OK"
            else:
                status = "KO"
        return {"status": status}
