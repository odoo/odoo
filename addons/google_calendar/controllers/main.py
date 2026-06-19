# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from requests import HTTPError

from odoo import http
from odoo.http import request
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService
from odoo.addons.calendar.controllers.main import CalendarController

_logger = logging.getLogger(__name__)


class GoogleCalendarController(CalendarController):

    @http.route('/google_calendar/sync_data', type='jsonrpc', auth='user')
    def google_calendar_sync_data(self, model, **kw):
        """ This route/function is called when we want to synchronize Odoo
            calendar with Google Calendar.
            Function return a dictionary with the status :  need_config_from_admin, need_auth,
            need_refresh, sync_stopped, success if not calendar_event
            The dictionary may contains an url, to allow Odoo Client to redirect user on
            this URL for authorization for example
        """
        if model == 'calendar.event':
            base_url = request.httprequest.url_root.strip('/')
            GoogleCal = GoogleCalendarService(request.env['google.service'].with_context(base_url=base_url))

            # Checking that admin have already configured Google API for google synchronization !
            client_id = request.env['google.service']._get_client_id('calendar')

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
                _logger.info("User %s: Google Calendar synchronization needs user authorization. Redirecting to %s", self.env.user.login, url)
                return {
                    "status": "need_auth",
                    "url": url
                }
            # If App authorized, and user access accepted, We launch the synchronization
            try:
                _logger.info("User %s: Google Calendar synchronization started", self.env.user.login)
                request.env.user.sudo()._sync_google_calendars(GoogleCal)
                # Commit calendar changes so that the @after_commit calls to the Google API are performed before
                # continuing with event sync.
                request.env.cr.commit()
                _logger.info("User %s: Commited calendar changes, starting event synchronization", self.env.user.login)
                need_refresh = request.env.user.sudo()._sync_google_calendar(GoogleCal)
            except HTTPError as e:
                _logger.error("User %s: Google Calendar synchronization failed. %s", self.env.user, e)
                return {"status": "sync_failed"}

            # If synchronization has been stopped or paused
            sync_status = request.env.user._get_google_sync_status()
            if not need_refresh and sync_status != "sync_active":
                return {
                    "status": sync_status,
                    "url": ''
                }
            return {
                "status": "need_refresh" if need_refresh else "no_new_event_from_google",
                "url": ''
            }

        return {"status": "success"}
