# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import random
import time

from requests import HTTPError

from odoo import api, fields, models

from odoo.addons.google_calendar.models.google_sync import google_calendar_token
from odoo.addons.google_calendar.utils.google_calendar import (
    GoogleCalendarRateLimit,
    GoogleCalendarService,
)


_logger = logging.getLogger(__name__)

# Truncated exponential backoff per
# https://developers.google.com/workspace/calendar/api/guides/quota
# Wait time = min(2^n + random_ms, _BACKOFF_MAX_S).
_BACKOFF_MAX_S = 64
_MAX_BACKOFF_ROUNDS = 8

# Stop retrying an event after N permanent (non-rate-limit) failures so a
# poison event never blocks the queue.
_MAX_ATTEMPTS = 3


class GoogleCalendarPendingDeletion(models.Model):
    _name = 'google.calendar.pending.deletion'
    _description = 'Google Calendar Pending Deletion'

    google_id = fields.Char(required=True, index=True)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    state = fields.Selection(
        [('pending', 'Pending'), ('failed', 'Failed')],
        required=True, default='pending', index=True,
    )
    attempts = fields.Integer(default=0)
    last_error = fields.Char()

    @api.model
    def _cron_process_pending_deletions(self):
        """Process queued Google Calendar deletions with rate-limit-aware backoff."""
        commit_progress = self.env['ir.cron']._commit_progress
        events = self.search([('state', '=', 'pending')])
        commit_progress(remaining=len(events))
        if not events:
            return

        for user in events.user_id:
            user_events = events.filtered(lambda e: e.user_id == user)
            try:
                with google_calendar_token(user.sudo()) as token:
                    if not token:
                        user_events.write({
                            'state': 'failed',
                            'last_error': "No Google Calendar token for user %s" % user.id,
                        })
                        self._finalize_reset(user)
                        if not commit_progress(len(user_events)):
                            return
                        continue
                    keep_going = user_events._process(token)
                    self._finalize_reset(user)  # Always check finalize, even on terminate (keep_going = 0)
                    if not keep_going:
                        return
            except Exception as e:  # noqa: BLE001
                self.env['ir.cron']._rollback_progress()
                _logger.exception("Unexpected error processing pending deletions for user %s", user.id)
                user_events.write({'state': 'failed', 'last_error': str(e)[:255]})
                self._finalize_reset(user)
                if not commit_progress(len(user_events)):
                    return

    def _finalize_reset(self, user):
        """Finalize the account reset the user's queue is empty."""
        if not user.res_users_settings_id.sudo().google_calendar_reset_pending:
            return
        if self.search_count([('user_id', '=', user.id), ('state', '=', 'pending')], limit=1):
            return
        user.res_users_settings_id._finalize_google_calendar_reset()

    def _process(self, token):
        """Process the pending-deletion events. Returns False to abort the cron tick."""
        commit_progress = self.env['ir.cron']._commit_progress
        for event in self:
            event = event.try_lock_for_update().filtered(lambda e: e.state == 'pending')
            if not event:
                continue  # claimed by another concurrent worker

            try:
                if not event._delete_with_backoff(token):
                    # Rate limit persisted across all retries; leave the event
                    # pending and let the next cron tick try again.
                    return False
            except HTTPError as e:
                self.env['ir.cron']._rollback_progress()
                event.attempts += 1
                event.last_error = ("HTTP %s: %s" % (e.response.status_code, e))[:255]
                if event.attempts >= _MAX_ATTEMPTS:
                    event.state = 'failed'
                    _logger.error(
                        "Giving up on Google deletion of %s after %d attempts: %s",
                        event.google_id, event.attempts, e,
                    )
                    advance = 1  # the unit of work is done
                else:
                    advance = 0  # event stays pending. Will be retried next tick

                if not commit_progress(advance):
                    return False

                continue

            event.unlink()
            if not commit_progress(1):
                return False
        return True

    def _delete_with_backoff(self, token):
        """Call google.delete with truncated exponential backoff on rate-limit.

        Returns True on success, False if rate-limit retries were exhausted.
        Re-raises HTTPError for non-rate-limit failures.
        """
        self.ensure_one()
        google = GoogleCalendarService(self.env['google.service'])
        for backoff_round in range(_MAX_BACKOFF_ROUNDS + 1):
            try:
                google.delete(self.google_id, token=token)
                return True
            except GoogleCalendarRateLimit as e:
                self.env['ir.cron']._rollback_progress()
                if backoff_round == _MAX_BACKOFF_ROUNDS:
                    _logger.warning(
                        "Google rate-limit persisted after %d retries (%s); deferring to next tick",
                        backoff_round, e,
                    )
                    return False
                wait = min((2 ** backoff_round) + random.random(), _BACKOFF_MAX_S)
                _logger.warning("Google rate-limited (%s); sleeping %.2fs", e, wait)
                time.sleep(wait)
                # The user might have cancelled the reset while this process was sleeping.
                if not self.exists():
                    return False
