# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from odoo.addons.microsoft_calendar.models.microsoft_sync import microsoft_calendar_token
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.loglevels import exception_to_unicode
from odoo.addons.microsoft_account.models.microsoft_service import MICROSOFT_TOKEN_ENDPOINT
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService, InvalidSyncToken

_logger = logging.getLogger(__name__)


class User(models.Model):
    _inherit = 'res.users'

    microsoft_calendar_sync_token = fields.Char('Microsoft Next Sync Token', copy=False)

    def _microsoft_calendar_authenticated(self):
        return bool(self.sudo().microsoft_calendar_rtoken)

    def _get_microsoft_calendar_token(self):
        self.ensure_one()
        if self._is_microsoft_calendar_valid():
            self._refresh_microsoft_calendar_token()
        return self.microsoft_calendar_token

    def _is_microsoft_calendar_valid(self):
        return self.microsoft_calendar_token_validity and self.microsoft_calendar_token_validity < (fields.Datetime.now() + timedelta(minutes=1))

    def _refresh_microsoft_calendar_token(self):
        self.ensure_one()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('microsoft_calendar_client_id')
        client_secret = get_param('microsoft_calendar_client_secret')

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
            dummy, response, dummy = self.env['microsoft.service']._do_request(MICROSOFT_TOKEN_ENDPOINT, params=data, headers=headers, method='POST', preuri='')
            ttl = response.get('expires_in')
            self.write({
                'microsoft_calendar_token': response.get('access_token'),
                'microsoft_calendar_token_validity': fields.Datetime.now() + timedelta(seconds=ttl),
            })
        except requests.HTTPError as error:
            if error.response.status_code == 400:  # invalid grant
                # Delete refresh token and make sure it's commited
                with self.pool.cursor() as cr:
                    self.env.user.with_env(self.env(cr=cr)).write({'microsoft_calendar_rtoken': False})
            error_key = error.response.json().get("error", "nc")
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired [%s]", error_key)
            raise UserError(error_msg)

    def _sync_microsoft_calendar(self, calendar_service: MicrosoftCalendarService):
        self.ensure_one()
        full_sync = not bool(self.microsoft_calendar_sync_token)
        with microsoft_calendar_token(self) as token:
            try:
                events, next_sync_token, default_reminders = calendar_service.get_events(self.microsoft_calendar_sync_token, token=token)
            except InvalidSyncToken:
                events, next_sync_token, default_reminders = calendar_service.get_events(token=token)
                full_sync = True
        self.microsoft_calendar_sync_token = next_sync_token

        # Microsoft -> Odoo
        recurrences = events.filter(lambda e: e.is_recurrent())
        synced_events, synced_recurrences = self.env['calendar.event']._sync_microsoft2odoo(events, default_reminders=default_reminders) if events else (self.env['calendar.event'], self.env['calendar.recurrence'])

        # Odoo -> Microsoft
        recurrences = self.env['calendar.recurrence']._get_microsoft_records_to_sync(full_sync=full_sync)
        recurrences -= synced_recurrences
        recurrences._sync_odoo2microsoft(calendar_service)
        synced_events |= recurrences.calendar_event_ids

        events = self.env['calendar.event']._get_microsoft_records_to_sync(full_sync=full_sync)
        (events - synced_events)._sync_odoo2microsoft(calendar_service)

        return bool(events | synced_events) or bool(recurrences | synced_recurrences)

    @api.model
    def _sync_all_microsoft_calendar(self):
        """ Cron job """
        users = self.env['res.users'].search([('microsoft_calendar_rtoken', '!=', False)])
        microsoft = MicrosoftCalendarService(self.env['microsoft.service'])
        for user in users:
            _logger.info("Calendar Synchro - Starting synchronization for %s", user)
            try:
                user.with_user(user).sudo()._sync_microsoft_calendar(microsoft)
            except Exception as e:
                _logger.exception("[%s] Calendar Synchro - Exception : %s !", user, exception_to_unicode(e))
