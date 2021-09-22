# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging


from odoo import api, fields, models, Command
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService, InvalidSyncToken
from odoo.addons.google_calendar.models.google_sync import google_calendar_token
from odoo.loglevels import exception_to_unicode

_logger = logging.getLogger(__name__)

class User(models.Model):
    _inherit = 'res.users'

    google_cal_account_id = fields.Many2one('google.calendar.credentials')
    google_calendar_rtoken = fields.Char(related='google_cal_account_id.calendar_rtoken', groups="base.group_system")
    google_calendar_token = fields.Char(related='google_cal_account_id.calendar_token')
    google_calendar_token_validity = fields.Datetime(related='google_cal_account_id.calendar_token_validity')
    google_calendar_sync_token = fields.Char(related='google_cal_account_id.calendar_sync_token')
    google_calendar_cal_id = fields.Char(related='google_cal_account_id.calendar_cal_id')
    google_synchronization_stopped = fields.Boolean(related='google_cal_account_id.synchronization_stopped', readonly=False)

    _sql_constraints = [
        ('google_token_uniq', 'unique (google_cal_account_id)', "The user has already a google account"),
    ]


    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['google_synchronization_stopped', 'google_cal_account_id']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['google_synchronization_stopped', 'google_cal_account_id']

    def _get_google_calendar_token(self):
        self.ensure_one()
        if self.google_cal_account_id.calendar_rtoken and not self.google_cal_account_id._is_google_calendar_valid():
            self.sudo().google_cal_account_id._refresh_google_calendar_token()
        return self.google_cal_account_id.calendar_token

    def _sync_google_calendar(self, calendar_service: GoogleCalendarService):
        self.ensure_one()
        if self.google_synchronization_stopped:
            return False

        # don't attempt to sync when another sync is already in progress, as we wouldn't be
        # able to commit the transaction anyway (row is locked)
        self.env.cr.execute("""SELECT id FROM res_users WHERE id = %s FOR NO KEY UPDATE SKIP LOCKED""", [self.id])
        if not self.env.cr.rowcount:
            _logger.info("skipping calendar sync, locked user %s", self.login)
            return False

        full_sync = not bool(self.google_calendar_sync_token)
        with google_calendar_token(self) as token:
            try:
                events, next_sync_token, default_reminders = calendar_service.get_events(self.google_cal_account_id.calendar_sync_token, token=token)
            except InvalidSyncToken:
                events, next_sync_token, default_reminders = calendar_service.get_events(token=token)
                full_sync = True
        self.google_cal_account_id.calendar_sync_token = next_sync_token

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
        users = self.env['res.users'].search([('google_calendar_rtoken', '!=', False), ('google_synchronization_stopped', '=', False)])
        google = GoogleCalendarService(self.env['google.service'])
        for user in users:
            _logger.info("Calendar Synchro - Starting synchronization for %s", user)
            try:
                user.with_user(user).sudo()._sync_google_calendar(google)
                self.env.cr.commit()
            except Exception as e:
                _logger.exception("[%s] Calendar Synchro - Exception : %s !", user, exception_to_unicode(e))
                self.env.cr.rollback()

    def stop_google_synchronization(self):
        self.ensure_one()
        self.google_synchronization_stopped = True

    def restart_google_synchronization(self):
        self.ensure_one()
        if not self.google_cal_account_id:
            self.google_cal_account_id = self.env['google.calendar.credentials'].sudo().create([{'user_ids': [Command.set(self.ids)]}])
        self.google_synchronization_stopped = False
        self.env['calendar.recurrence']._restart_google_sync()
        self.env['calendar.event']._restart_google_sync()
