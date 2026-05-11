# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime, timedelta
from itertools import chain, repeat
from unittest.mock import patch

from requests import HTTPError, Response

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarRateLimit, GoogleCalendarService
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


_TOKEN_PATCH = 'odoo.addons.google_calendar.models.res_users.ResUsers._get_google_calendar_token'


def _http_error(status, reason=None):
    """Capture a real HTTPError raised from a stub Response."""
    response = Response()
    response.status_code = status
    response._content = json.dumps({
        'error': {
            'code': status,
            'errors': [{'reason': reason}] if reason else [],
            'message': 'mocked',
        },
    }).encode()
    try:
        response.raise_for_status()
    except HTTPError as exc:
        return exc


class TestGoogleDeleteErrorHandling(TransactionCase):
    """Verify google.delete() classifies HTTP errors correctly per
    https://developers.google.com/workspace/calendar/api/guides/errors
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.google = GoogleCalendarService(cls.env['google.service'])

    def _patch_request(self, error):
        """Patch _do_request to raise the given HTTPError."""
        return patch.object(self.env.registry['google.service'], '_do_request', side_effect=error)

    def test_404_treated_as_already_gone(self):
        with self._patch_request(_http_error(404, reason='notFound')):
            self.google.delete('event-id', token='dummy')  # shouldn't raise an error

    def test_410_treated_as_already_gone(self):
        with self._patch_request(_http_error(410)):
            self.google.delete('event-id', token='dummy')

    def test_403_event_cancelled_treated_as_already_gone(self):
        with self._patch_request(_http_error(403, reason='eventCancelled')):
            self.google.delete('event-id', token='dummy')

    def test_429_raises_rate_limit(self):
        with self._patch_request(_http_error(429)):
            with self.assertRaises(GoogleCalendarRateLimit):
                self.google.delete('event-id', token='dummy')

    def test_403_rate_limit_reason_raises_rate_limit(self):
        for reason in ('rateLimitExceeded', 'userRateLimitExceeded', 'quotaExceeded'):
            with self._patch_request(_http_error(403, reason=reason)):
                with self.assertRaises(GoogleCalendarRateLimit):
                    self.google.delete('event-id', token='dummy')

    def test_403_forbidden_propagates(self):
        with self._patch_request(_http_error(403, reason='forbidden')):
            with self.assertRaises(HTTPError):
                self.google.delete('event-id', token='dummy')


class TestResetAccountAndCron(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'gcal-test-user',
            'login': 'gcal-test-user',
            'email': 'gcal-test-user@example.com',
        })
        cls.user_settings = cls.user.res_users_settings_id
        cls.user_settings.write({
            'google_calendar_rtoken': 'rtoken',
            'google_calendar_token': 'token',
        })
        cls.Pending = cls.env['google.calendar.pending.deletion']
        cls.PendingCls = cls.env.registry['google.calendar.pending.deletion']

    def _create_pending_events(self, *google_ids):
        return self.Pending.create([
            {'google_id': gid, 'user_id': self.user.id} for gid in google_ids
        ])

    def _create_recurrence_events(self, master_google_id, count, start):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule': f'FREQ=DAILY;COUNT={count}',
            'google_id': master_google_id,
        })
        events = self.env['calendar.event'].create([{
            'name': f'evt-{i}',
            'start': start + timedelta(days=i),
            'stop': start + timedelta(days=i, hours=1),
            'user_id': self.user.id,
            'recurrence_id': recurrence.id,
            'google_id': f'{master_google_id}_{i}',
        } for i in range(count)])
        recurrence.base_event_id = events[0]

    def _run_pending_deletions_cron(self):
        with self.enter_registry_test_mode():
            self.env.ref('google_calendar.ir_cron_process_google_pending_deletions').method_direct_trigger()

    def _reset_account(self, delete_policy, sync_policy='new'):
        wizard = self.env['google.calendar.account.reset'].create({
            'user_id': self.user.id,
            'delete_policy': delete_policy,
            'sync_policy': sync_policy,
        })
        wizard.reset_account()

    def _assert_finalized(self):
        """All credentials wiped and the pending-reset flag is false."""
        self.assertFalse(self.user_settings.google_calendar_reset_pending)
        self.assertFalse(self.user_settings.google_calendar_rtoken)
        self.assertFalse(self.user_settings.google_calendar_token)

    def test_wizard_queues_one_row_per_recurrence_master(self):
        self._create_recurrence_events('master', count=10, start=datetime(2030, 6, 1, 10, 0))
        self.env['calendar.event'].create({
            'name': 'standalone',
            'start': datetime(2030, 6, 1, 14, 0),
            'stop': datetime(2030, 6, 1, 15, 0),
            'user_id': self.user.id,
            'google_id': 'standalone',
        })
        self._reset_account('delete_google')

        pending = self.Pending.search([('user_id', '=', self.user.id)])
        self.assertEqual(
            set(pending.mapped('google_id')),
            {'master', 'standalone'}
        )

    @patch(_TOKEN_PATCH, lambda self: 'token')
    def test_pending_event_unlinked_after_successful_deletion(self):
        events = self._create_pending_events('a', 'b', 'c')
        with patch.object(GoogleCalendarService, 'delete') as mock_delete:
            self._run_pending_deletions_cron()
        self.assertEqual(mock_delete.call_count, 3)
        self.assertFalse(events.exists(), "Successful deletions should be unlinked")

    @patch(_TOKEN_PATCH, lambda self: 'token')
    @mute_logger(
        'odoo.addons.google_calendar.models.google_calendar_pending_deletion',
        'odoo.addons.base.models.ir_cron',
    )
    def test_pending_event_marked_failed_after_max_permanent_errors(self):
        event = self._create_pending_events('a')
        with patch.object(GoogleCalendarService, 'delete', side_effect=_http_error(500)):
            for _ in range(3):
                self._run_pending_deletions_cron()
        event = event.exists()
        self.assertEqual(event.state, 'failed')
        self.assertEqual(event.attempts, 3)
        self.assertIn('500', event.last_error or '')

    @patch(_TOKEN_PATCH, lambda self: 'token')
    def test_remaining_pending_events_deferred_on_rate_limit(self):
        events = self._create_pending_events('a', 'b', 'c')
        # First call succeeds, subsequent calls return False (rate-limit retries
        # exhausted).
        with patch.object(GoogleCalendarService, 'delete'), \
             patch.object(self.PendingCls, '_delete_with_backoff',
                          autospec=True, side_effect=chain([True], repeat(False))):
            self._run_pending_deletions_cron()
        remaining = events.exists()
        self.assertEqual(len(remaining), 2, "Only the first event should be processed")
        self.assertEqual(set(remaining.mapped('state')), {'pending'})

    @patch(_TOKEN_PATCH, lambda self: None)
    def test_pending_event_marked_failed_when_user_has_no_token(self):
        event = self._create_pending_events('a')
        self._run_pending_deletions_cron()
        event = event.exists()
        self.assertEqual(event.state, 'failed')
        self.assertIn('No Google Calendar token', event.last_error or '')

    def test_wizard_dont_delete_finalizes_immediately(self):
        self.user_settings.write({
            'google_calendar_sync_token': 'old_sync',
            'google_calendar_cal_id': 'old_cal',
        })
        self._reset_account('dont_delete')
        self._assert_finalized()
        self.assertFalse(self.user_settings.google_calendar_sync_token)
        self.assertFalse(self.user_settings.google_calendar_cal_id)

    def test_wizard_delete_google_defers_finalization(self):
        self.env['calendar.event'].create({
            'name': 'evt',
            'start': datetime(2030, 6, 1, 10, 0),
            'stop': datetime(2030, 6, 1, 11, 0),
            'user_id': self.user.id,
            'google_id': 'standalone',
        })
        self._reset_account('delete_google')
        # Credentials must still be valid so the cron can use them.
        self.assertTrue(self.user_settings.google_calendar_reset_pending)
        self.assertEqual(self.user_settings.google_calendar_token, 'token')

    @patch(_TOKEN_PATCH, lambda self: 'token')
    def test_cron_finalizes_after_queue_is_processed(self):
        self.user_settings.google_calendar_reset_pending = True
        self._create_pending_events('a', 'b')
        with patch.object(GoogleCalendarService, 'delete'):
            self._run_pending_deletions_cron()
        self._assert_finalized()

    @patch(_TOKEN_PATCH, lambda self: 'token')
    def test_cron_does_not_finalize_while_pending_rows_remain(self):
        self.user_settings.google_calendar_reset_pending = True
        self._create_pending_events('a', 'b', 'c')
        # One success then rate-limit forever. Rows 'b' and 'c' stay pending.
        with patch.object(GoogleCalendarService, 'delete'), \
             patch.object(self.PendingCls, '_delete_with_backoff',
                          autospec=True, side_effect=chain([True], repeat(False))):
            self._run_pending_deletions_cron()
        self.assertTrue(self.user_settings.google_calendar_reset_pending)
        self.assertEqual(self.user_settings.google_calendar_token, 'token')

    def test_relink_blocked_while_reset_pending(self):
        self.user_settings.google_calendar_reset_pending = True
        with self.assertRaises(UserError):
            self.user_settings._set_google_auth_tokens('new_token', 'new_rtoken', 3600)

    def test_sync_status_is_stopped_while_reset_pending(self):
        self.assertNotEqual(self.user._get_google_sync_status(), 'sync_stopped')
        self.user_settings.google_calendar_reset_pending = True
        self.assertEqual(self.user._get_google_sync_status(), 'sync_stopped')

    def test_cancel_pending_reset_drops_queue_and_finalizes(self):
        self.user_settings.google_calendar_reset_pending = True
        rows = self._create_pending_events('a', 'b', 'c')
        self.user.action_cancel_google_calendar_reset()
        self.assertFalse(rows.exists(), "Pending rows should be dropped on cancel")
        self._assert_finalized()
