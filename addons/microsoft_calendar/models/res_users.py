# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from odoo.addons.microsoft_calendar.models.microsoft_sync import microsoft_calendar_token
from datetime import timedelta

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.loglevels import exception_to_unicode
from odoo.addons.microsoft_account.models.microsoft_service import DEFAULT_MICROSOFT_TOKEN_ENDPOINT
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import InvalidSyncToken
from odoo.tools import str2bool

_logger = logging.getLogger(__name__)


class User(models.Model):
    _inherit = 'res.users'

    microsoft_calendar_account_id = fields.Many2one('microsoft.calendar.credentials')
    microsoft_calendar_sync_token = fields.Char(related='microsoft_calendar_account_id.calendar_sync_token')
    microsoft_synchronization_stopped = fields.Boolean(related='microsoft_calendar_account_id.synchronization_stopped', readonly=False)
    microsoft_last_sync_date = fields.Datetime(related='microsoft_calendar_account_id.last_sync_date', readonly=False)

    _sql_constraints = [
        ('microsoft_token_uniq', 'unique (microsoft_calendar_account_id)', "The user has already a microsoft account"),
    ]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['microsoft_synchronization_stopped', 'microsoft_calendar_account_id', 'microsoft_last_sync_date']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['microsoft_synchronization_stopped', 'microsoft_calendar_account_id', 'microsoft_last_sync_date']

    def _microsoft_calendar_authenticated(self):
        return bool(self.sudo().microsoft_calendar_rtoken)

    def _get_microsoft_calendar_token(self):
        if not self:
            return None

        self.ensure_one()
        if self.microsoft_calendar_rtoken and not self._is_microsoft_calendar_valid():
            self._refresh_microsoft_calendar_token()
        return self.microsoft_calendar_token

    def _is_microsoft_calendar_valid(self):
        return self.microsoft_calendar_token_validity and self.microsoft_calendar_token_validity >= (fields.Datetime.now() + timedelta(minutes=1))

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
            dummy, response, dummy = self.env['microsoft.service']._do_request(
                DEFAULT_MICROSOFT_TOKEN_ENDPOINT, params=data, headers=headers, method='POST', preuri=''
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
                })
                self.microsoft_calendar_account_id.write({
                    'calendar_sync_token': False
                })
                self.env.cr.commit()
            error_key = error.response.json().get("error", "nc")
            error_msg = _(
                "An error occurred while generating the token. Your authorization code may be invalid or has already expired [%s]. "
                "You should check your Client ID and secret on the Microsoft Azure portal or try to stop and restart your calendar synchronisation.",
                error_key)
            raise UserError(error_msg)

    def _get_microsoft_sync_status(self):
        """ Returns the calendar synchronization status (active, paused or stopped). """
        status = "sync_active"
        if str2bool(self.env['ir.config_parameter'].sudo().get_param("microsoft_calendar_sync_paused"), default=False):
            status = "sync_paused"
        elif self.microsoft_synchronization_stopped:
            status = "sync_stopped"
        return status

    def _sync_microsoft_calendar(self):
        self.ensure_one()
        # Create the Calendar Credentials if it is not defined yet and define the last sync date after creation.
        if not self.microsoft_calendar_account_id and self._check_microsoft_calendar_credentials():
            self.microsoft_last_sync_date = fields.datetime.now()

        if self._get_microsoft_sync_status() != "sync_active":
            return False
        calendar_service = self.env["calendar.event"]._get_microsoft_service()
        full_sync = not bool(self.microsoft_calendar_sync_token)
        with microsoft_calendar_token(self) as token:
            try:
                events, next_sync_token = calendar_service.get_events(self.microsoft_calendar_sync_token, token=token)
            except InvalidSyncToken:
                events, next_sync_token = calendar_service.get_events(token=token)
                full_sync = True
        self.microsoft_calendar_account_id.calendar_sync_token = next_sync_token

        # Microsoft -> Odoo
        synced_events, synced_recurrences = self.env['calendar.event']._sync_microsoft2odoo(events) if events else (self.env['calendar.event'], self.env['calendar.recurrence'])

        # Odoo -> Microsoft
        recurrences = self.env['calendar.recurrence']._get_microsoft_records_to_sync(full_sync=full_sync)
        recurrences -= synced_recurrences
        recurrences._sync_odoo2microsoft()
        synced_events |= recurrences.calendar_event_ids

        events = self.env['calendar.event']._get_microsoft_records_to_sync(full_sync=full_sync)
        (events - synced_events)._sync_odoo2microsoft()
        self.microsoft_last_sync_date = fields.datetime.now()

        return bool(events | synced_events) or bool(recurrences | synced_recurrences)

    @api.model
    def _sync_all_microsoft_calendar(self):
        """ Cron job """
        users = self.env['res.users'].search([('microsoft_calendar_rtoken', '!=', False), ('microsoft_synchronization_stopped', '=', False)])
        for user in users:
            _logger.info("Calendar Synchro - Starting synchronization for %s", user)
            try:
                user.with_user(user).sudo()._sync_microsoft_calendar()
                self.env.cr.commit()
            except Exception as e:
                _logger.exception("[%s] Calendar Synchro - Exception : %s!", user, exception_to_unicode(e))
                self.env.cr.rollback()

    def _check_microsoft_calendar_credentials(self):
        # Create the Calendar Credentials for the current user if not already created.
        self.ensure_one()
        if not self.microsoft_calendar_account_id:
            self.microsoft_calendar_account_id = self.env['microsoft.calendar.credentials'].sudo().create([{'user_ids': [Command.set(self.ids)]}])
        return True

    def stop_microsoft_synchronization(self):
        self.ensure_one()
        self._check_microsoft_calendar_credentials()
        self.microsoft_synchronization_stopped = True
        self.microsoft_last_sync_date = None

    def restart_microsoft_synchronization(self):
        self.ensure_one()
        self._check_microsoft_calendar_credentials()
        self.microsoft_last_sync_date = fields.datetime.now()
        self.microsoft_synchronization_stopped = False
        self.env['calendar.recurrence']._restart_microsoft_sync()
        self.env['calendar.event']._restart_microsoft_sync()

    def unpause_microsoft_synchronization(self):
        self.env['ir.config_parameter'].sudo().set_param("microsoft_calendar_sync_paused", False)

    def pause_microsoft_synchronization(self):
        self.env['ir.config_parameter'].sudo().set_param("microsoft_calendar_sync_paused", True)

    @api.model
    def check_calendar_credentials(self):
        res = super().check_calendar_credentials()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('microsoft_calendar_client_id')
        client_secret = get_param('microsoft_calendar_client_secret')
        res['microsoft_calendar'] = bool(client_id and client_secret)
        return res
