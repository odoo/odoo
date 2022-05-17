# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.calendar_microsoft.models.calendar_provider import PROVIDER_NAME

_logger = logging.getLogger(__name__)


class User(models.Model):
    _inherit = 'res.users'

    calendar_provider_name = fields.Selection(
        selection_add=[(PROVIDER_NAME, "Microsoft")],
        ondelete={PROVIDER_NAME: 'set default'}
    )
    microsoft_calendar_sync_token = fields.Char(
        'Last Microsoft sync point',
        copy=False
    )

    def _microsoft_calendar_authenticated(self):
        return bool(self.sudo().microsoft_calendar_rtoken)

    def _get_microsoft_calendar_token(self):
        self.ensure_one()
        if self.microsoft_calendar_rtoken and not self._is_microsoft_calendar_valid():
            self._refresh_microsoft_calendar_token()
        return self.microsoft_calendar_token

    def _is_microsoft_calendar_valid(self):
        return self.microsoft_calendar_token_validity and self.microsoft_calendar_token_validity >= (fields.Datetime.now() + timedelta(minutes=1))

    def _refresh_microsoft_calendar_token(self):
        self.ensure_one()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('microsoft_api_client_id')
        client_secret = get_param('microsoft_api_client_secret')

        if not client_id or not client_secret:
            raise UserError(_("The account for the Outlook Calendar service is not configured."))

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': self.microsoft_calendar_rtoken,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
        }

        try:
            endpoint = self.env['microsoft.service']._get_token_endpoint()
            dummy, response, dummy = self.env['microsoft.service']._do_request(
                endpoint, params=data, headers=headers, method='POST', preuri=''
            )
            ttl = response.get('expires_in')
            self.write({
                'microsoft_calendar_token': response.get('access_token'),
                'microsoft_calendar_token_validity': fields.Datetime.now() + timedelta(seconds=ttl),
            })
        except requests.HTTPError as error:
            if error.response.status_code in (400, 401):  # invalid grant or invalid client
                # Delete refresh token and make sure it's commited
                self.env.cr.rollback()
                self.write({
                    'microsoft_calendar_rtoken': False,
                    'microsoft_calendar_token': False,
                    'microsoft_calendar_token_validity': False,
                    'microsoft_calendar_sync_token': False,
                })
                self.env.cr.commit()
            error_key = error.response.json().get("error", "nc")
            error_msg = _(
                "An error occurred while generating the token. Your authorization code may be invalid or has already expired [%s]. "
                "You should check your Client ID and secret on the Microsoft Azure portal or try to stop and restart your calendar synchronisation.",
                error_key)
            raise UserError(error_msg)

    def is_microsoft_calendar_sync_enabled(self):
        self.ensure_one()
        return self.calendar_provider_name == PROVIDER_NAME

    def disable_microsoft_calendar_sync(self):
        self.ensure_one()
        self.calendar_provider_name = "none"

    def enable_microsoft_calendar_sync(self):
        self.ensure_one()
        self.calendar_provider_name = PROVIDER_NAME

        # self.env['calendar.recurrence']._restart_microsoft_sync()
        # self.env['calendar.event']._restart_microsoft_sync()
