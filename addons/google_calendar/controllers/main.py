# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService


class GoogleCalendarController(http.Controller):

    @http.route('/google_calendar/sync_data', type='json', auth='user')
    def sync_data(self, model, **kw):
        """ This route/function is called when we want to synchronize Odoo
            calendar with Google Calendar.
            Function return a dictionary with the status :  need_config_from_admin, need_auth,
            need_refresh, sync_stopped, success if not calendar_event
            The dictionary may contains an url, to allow Odoo Client to redirect user on
            this URL for authorization for example
        """
        if model == 'calendar.event':
            GoogleCal = GoogleCalendarService(request.env['google.service'])

            # Checking that admin have already configured Google API for google synchronization !
            client_id = request.env['ir.config_parameter'].sudo().get_param('google_calendar_client_id')

            if not client_id or client_id == '':
                action_id = ''
                if GoogleCal._can_authorize_google(request.env.user):
                    action_id = request.env.ref('base_setup.action_general_configuration').id
                return {
                    "status": "need_config_from_admin",
                    "url": '',
                    "action": action_id
                }

            # Checking that user have already accepted Odoo to access his calendar !
            if not GoogleCal.is_authorized(request.env.user):
                url = GoogleCal._google_authentication_url(from_url=kw.get('fromurl'))
                return {
                    "status": "need_auth",
                    "url": url
                }
            # If App authorized, and user access accepted, We launch the synchronization
            need_refresh = request.env.user.sudo()._sync_google_calendar(GoogleCal)

            # If synchronization has been stopped
            if not need_refresh and request.env.user.google_synchronization_stopped:
                return {
                    "status": "sync_stopped",
                    "url": ''
                }
            return {
                "status": "need_refresh" if need_refresh else "no_new_event_from_google",
                "url": ''
            }

        return {"status": "success"}
