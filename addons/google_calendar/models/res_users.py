# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from odoo.addons.google_calendar.models.google_sync import google_calendar_token
from datetime import timedelta


from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.loglevels import exception_to_unicode
from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService, InvalidSyncToken

_logger = logging.getLogger(__name__)

class User(models.Model):
    _inherit = 'res.users'

    google_calendar_rtoken = fields.Char('Refresh Token', copy=False, groups="base.group_system")
    google_calendar_token = fields.Char('User token', copy=False, groups="base.group_system")
    google_calendar_token_validity = fields.Datetime('Token Validity', copy=False)
    google_calendar_sync_token = fields.Char('Next Sync Token', copy=False)
    google_calendar_cal_id = fields.Char('Calendar ID', copy=False, help='Last Calendar ID who has been synchronized. If it is changed, we remove all links between GoogleID and Odoo Google Internal ID')

    def _set_auth_tokens(self, access_token, refresh_token, ttl):
        self.write({
            'google_calendar_rtoken': refresh_token,
            'google_calendar_token': access_token,
            'google_calendar_token_validity': fields.Datetime.now() + timedelta(seconds=ttl) if ttl else False,
        })

    def _google_calendar_authenticated(self):
        return bool(self.sudo().google_calendar_rtoken)

    def _get_google_calendar_token(self):
        self.ensure_one()
        if self._is_google_calendar_valid():
            self._refresh_google_calendar_token()
        return self.google_calendar_token

    def _is_google_calendar_valid(self):
        return self.google_calendar_token_validity and self.google_calendar_token_validity < (fields.Datetime.now() + timedelta(minutes=1))

    def _refresh_google_calendar_token(self):
        # LUL TODO similar code exists in google_drive. Should be factorized in google_account
        self.ensure_one()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('google_calendar_client_id')
        client_secret = get_param('google_calendar_client_secret')

        if not client_id or not client_secret:
            raise UserError(_("The account for the Google Calendar service is not configured."))

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': self.google_calendar_rtoken,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
        }

        try:
            dummy, response, dummy = self.env['google.service']._do_request(GOOGLE_TOKEN_ENDPOINT, params=data, headers=headers, method='POST', preuri='')
            ttl = response.get('expires_in')
            self.write({
                'google_calendar_token': response.get('access_token'),
                'google_calendar_token_validity': fields.Datetime.now() + timedelta(seconds=ttl),
            })
        except requests.HTTPError as error:
            if error.response.status_code == 400:  # invalid grant
                # Delete refresh token and make sure it's commited
                with self.pool.cursor() as cr:
                    self.env.user.with_env(self.env(cr=cr)).write({'google_calendar_rtoken': False})
            error_key = error.response.json().get("error", "nc")
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired [%s]", error_key)
            raise UserError(error_msg)

    def _sync_google_calendar(self, calendar_service: GoogleCalendarService):
        self.ensure_one()
        full_sync = not bool(self.google_calendar_sync_token)
        with google_calendar_token(self) as token:
            try:
                events, next_sync_token, default_reminders = calendar_service.get_events(self.google_calendar_sync_token, token=token)
            except InvalidSyncToken:
                events, next_sync_token, default_reminders = calendar_service.get_events(token=token)
                full_sync = True
        self.google_calendar_sync_token = next_sync_token

        # Google -> Odoo
        events.clear_type_ambiguity(self.env)
        recurrences = events.filter(lambda e: e.is_recurrence())
        synced_recurrences = self.env['calendar.recurrence']._sync_google2odoo(recurrences)
        synced_events = self.env['calendar.event']._sync_google2odoo(events - recurrences, default_reminders=default_reminders)

        # Odoo -> Google
        recurrences = self.env['calendar.recurrence']._get_records_to_sync(full_sync=full_sync)
        recurrences -= synced_recurrences
        recurrences._sync_odoo2google(calendar_service)
        synced_events |= recurrences.calendar_event_ids - recurrences._get_outliers()
        events = self.env['calendar.event']._get_records_to_sync(full_sync=full_sync)
        (events - synced_events)._sync_odoo2google(calendar_service)

        return bool(events | synced_events) or bool(recurrences | synced_recurrences)

    @api.model
    def _sync_all_google_calendar(self):
        """ Cron job """
        users = self.env['res.users'].search([('google_calendar_rtoken', '!=', False)])
        google = GoogleCalendarService(self.env['google.service'])
        for user in users:
            _logger.info("Calendar Synchro - Starting synchronization for %s", user)
            try:
                user.with_user(user).sudo()._sync_google_calendar(google)
            except Exception as e:
                _logger.exception("[%s] Calendar Synchro - Exception : %s !", user, exception_to_unicode(e))
