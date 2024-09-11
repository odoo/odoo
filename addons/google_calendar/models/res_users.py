# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging


from odoo import api, fields, models, Command
from odoo.tools import str2bool, exception_to_unicode
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService, InvalidSyncToken

_logger = logging.getLogger(__name__)


class User(models.Model):
    _inherit = 'res.users'

    google_calendar_rtoken = fields.Char(related='res_users_settings_id.google_calendar_rtoken', groups="base.group_system")
    google_calendar_token = fields.Char(related='res_users_settings_id.google_calendar_token', groups="base.group_system")
    google_calendar_token_validity = fields.Datetime(related='res_users_settings_id.google_calendar_token_validity', groups="base.group_system")
    google_synchronization_stopped = fields.Boolean(related='res_users_settings_id.google_synchronization_stopped', readonly=False, groups="base.group_system")

    def _get_google_calendar_token(self):
        self.ensure_one()
        if self.res_users_settings_id.sudo().google_calendar_rtoken and not self.res_users_settings_id._is_google_calendar_valid():
            self.sudo().res_users_settings_id._refresh_google_calendar_token()
        return self.res_users_settings_id.sudo().google_calendar_token

    def _get_google_sync_status(self):
        """ Returns the calendar synchronization status (active, paused or stopped). """
        status = "sync_active"
        if str2bool(self.env['ir.config_parameter'].sudo().get_param("google_calendar_sync_paused"), default=False):
            status = "sync_paused"
        elif self.sudo().google_calendar_rtoken and not self.sudo().google_synchronization_stopped:
            status = "sync_active"
        elif self.sudo().google_synchronization_stopped:
            status = "sync_stopped"
        return status

    def _check_pending_odoo_records(self):
        """ Returns True if sync is active and there are records to be synchronized to Google. """
        if self._get_google_sync_status() != "sync_active":
            return False
        pending_events = self.env['calendar.event']._check_any_records_to_sync()
        pending_recurrences = self.env['calendar.recurrence']._check_any_records_to_sync()
        return pending_events or pending_recurrences

    def _sync_google_calendar(self, calendar_service: GoogleCalendarService):
        self.ensure_one()
        res = False
        partner_ids = self.env['res.partner'].search(['|', ('id', 'in', self.partner_id.ids), ('parent_id', 'in', self.partner_id.ids),
                                                      '|', ('google_calendar_cal_id', '!=', False), ('parent_id', '=', False)])
        for partner in partner_ids:
            res = partner._sync_google_calendar(calendar_service=calendar_service) or res
        return res

    def _sync_single_event(self, calendar_service: GoogleCalendarService, odoo_event, event_id):
        self.ensure_one()
        results = self._sync_request(calendar_service, event_id)
        if not results or not results.get('events'):
            return False
        event, default_reminders, full_sync = results.values()
        # Google -> Odoo
        send_updates = not full_sync
        event.clear_type_ambiguity(self.env)
        synced_events = self.env['calendar.event']._sync_google2odoo(event, default_reminders=default_reminders)
        # Odoo -> Google
        odoo_event.with_context(send_updates=send_updates)._sync_odoo2google(calendar_service)
        return bool(odoo_event | synced_events)

    def _sync_request(self, calendar_service, event_id=None):
        if self._get_google_sync_status() != "sync_active":
            return False
        # don't attempt to sync when another sync is already in progress, as we wouldn't be
        # able to commit the transaction anyway (row is locked)
        self.env.cr.execute("""SELECT id FROM res_users WHERE id = %s FOR NO KEY UPDATE SKIP LOCKED""", [self.id])
        if not self.env.cr.rowcount:
            _logger.info("skipping calendar sync, locked user %s", self.login)
            return False

        full_sync = not bool(self.sudo().google_calendar_sync_token)
        with self._get_google_calendar_token() as token:
            try:
                if not event_id:
                    events, next_sync_token, default_reminders = calendar_service.get_events(self.res_users_settings_id.sudo().google_calendar_sync_token, token=token)
                else:
                    # We force the sync_token parameter to avoid doing a full sync.
                    # Other events are fetched when the calendar view is displayed.
                    events, next_sync_token, default_reminders = calendar_service.get_events(sync_token=token, token=token, event_id=event_id)
            except InvalidSyncToken:
                events, next_sync_token, default_reminders = calendar_service.get_events(token=token)
                full_sync = True
        if next_sync_token:
            self.res_users_settings_id.sudo().google_calendar_sync_token = next_sync_token
        return {
            'events': events,
            'default_reminders': default_reminders,
            'full_sync': full_sync,
        }

    @api.model
    def _sync_all_google_calendar(self):
        """ Cron job """
        users = self.env['res.users'].sudo().search([('google_calendar_rtoken', '!=', False), ('google_synchronization_stopped', '=', False)])
        google = GoogleCalendarService(self.env['google.service'])
        for user in users:
            _logger.info("Calendar Synchro - Starting synchronization for %s", user)
            try:
                user.with_user(user).sudo()._sync_google_calendar(google)
                self.env.cr.commit()
            except Exception as e:
                _logger.exception("[%s] Calendar Synchro - Exception : %s!", user, exception_to_unicode(e))
                self.env.cr.rollback()

    def is_google_calendar_synced(self):
        """ True if Google Calendar settings are filled (Client ID / Secret) and user calendar is synced
        meaning we can make API calls, false otherwise."""
        self.ensure_one()
        return self.sudo().google_calendar_token and self._get_google_sync_status() == 'sync_active'

    def stop_google_synchronization(self):
        self.ensure_one()
        self.sudo().google_synchronization_stopped = True

    def restart_google_synchronization(self):
        self.ensure_one()
        self.sudo().google_synchronization_stopped = False
        self.env['calendar.recurrence']._restart_google_sync()
        self.env['calendar.event']._restart_google_sync()

    def unpause_google_synchronization(self):
        self.env['ir.config_parameter'].sudo().set_param("google_calendar_sync_paused", False)

    def pause_google_synchronization(self):
        self.env['ir.config_parameter'].sudo().set_param("google_calendar_sync_paused", True)

    @api.model
    def check_calendar_credentials(self):
        res = super().check_calendar_credentials()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('google_calendar_client_id')
        client_secret = get_param('google_calendar_client_secret')
        res['google_calendar'] = bool(client_id and client_secret)
        return res

    def check_synchronization_status(self):
        res = super().check_synchronization_status()
        credentials_status = self.check_calendar_credentials()
        sync_status = 'missing_credentials'
        if credentials_status.get('google_calendar'):
            sync_status = self._get_google_sync_status()
            if sync_status == 'sync_active' and not self.sudo().google_calendar_rtoken:
                sync_status = 'sync_stopped'
        res['google_calendar'] = sync_status
        return res
