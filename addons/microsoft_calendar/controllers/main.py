# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService


class MicrosoftCalendarController(http.Controller):

    @http.route('/microsoft_calendar/sync_data', type='json', auth='user')
    def sync_data(self, model, **kw):
        """ This route/function is called when we want to synchronize Odoo
            calendar with Microsoft Calendar.
            Function return a dictionary with the status :  need_config_from_admin, need_auth,
            need_refresh, success if not calendar_event
            The dictionary may contains an url, to allow Odoo Client to redirect user on
            this URL for authorization for example
        """
        if model == 'calendar.event':
            MicrosoftCal = MicrosoftCalendarService(request.env['microsoft.service'])

            # Checking that admin have already configured Microsoft API for microsoft synchronization !
            client_id = request.env['ir.config_parameter'].sudo().get_param('microsoft_calendar_client_id')

            if not client_id or client_id == '':
                action_id = ''
                if MicrosoftCal._can_authorize_microsoft(request.env.user):
                    action_id = request.env.ref('base_setup.action_general_configuration').id
                return {
                    "status": "need_config_from_admin",
                    "url": '',
                    "action": action_id
                }

            # Checking that user have already accepted Odoo to access his calendar !
            if not MicrosoftCal.is_authorized(request.env.user):
                url = MicrosoftCal._microsoft_authentication_url(from_url=kw.get('fromurl'))
                return {
                    "status": "need_auth",
                    "url": url
                }
            # If App authorized, and user access accepted, We launch the synchronization
            need_refresh = request.env.user.sudo()._sync_microsoft_calendar(MicrosoftCal)
            return {
                "status": "need_refresh" if need_refresh else "no_new_event_from_microsoft",
                "url": ''
            }

        return {"status": "success"}
