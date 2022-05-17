# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

from odoo.addons.microsoft_account.models.microsoft_service import MicrosoftService

class MicrosoftCalendarSyncController(http.Controller):

    @http.route('/calendar_microsoft/enable_sync', type='json', auth='user')
    def enable_sync(self, from_url, **kw):
        """
        This route tries to enable the Microsoft Calendar sync.
        """
        service = request.env['microsoft.service']

        # First, be sure that Microsoft API credentials are correctly configured and, if not,
        # redirect the user to the settings page.
        if not service.has_credentials_configured():
            if service.can_set_credentials(request.env.user):
                action_id = request.env.ref('base_setup.action_general_configuration').id
                return {
                    "status": "need_config_from_admin",
                    "url": '',
                    "action": action_id
                }

        # Then, be sure that the user is already authenticated
        if not service.is_user_authenticated(request.env.user):
            return {
                "status": "need_auth",
                "url": service.get_calendar_auth_url(from_url=from_url)
            }

        # Everything is fine, so enable calendar sync
        request.env.user.enable_microsoft_calendar_sync()

        return {"status": "enabled"}

    @http.route('/calendar_microsoft/disable_sync', type='json', auth='user')
    def disable_sync(self):
        """
        TODO
        """
        request.env.user.disable_microsoft_calendar_sync()
        return {"status": "disabled"}

    @http.route('/calendar_microsoft/sync_status', type='json', auth='user')
    def sync_status(self):
        """
        TODO
        """
        return {
            "isEnabled": request.env.user.is_microsoft_calendar_sync_enabled()
        }
