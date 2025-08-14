# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools
import itertools

from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

import odoo

from odoo import Command
from odoo.addons.test_http.utils import (
    USER_AGENT_linux_chrome,
    USER_AGENT_linux_firefox,
    TEST_IPv4_locations,
    TEST_IPv6_locations,
)
from .test_common import TestHttpBase


class TestDevice(TestHttpBase):

    def setUp(self):
        super().setUp()

        self.Device = self.env['res.device']
        self.DeviceLine = self.env['res.device.line']
        self.DeviceLog = self.env['res.device.log']

        self.user_admin = self.env.ref('base.user_admin')
        self.user_internal = self.env['res.users'].create({
            'login': 'internal',
            'password': 'internal',
            'name': 'Internal',
            'email': 'internal@example.com',
            'group_ids': [Command.set([self.env.ref('base.group_user').id])],
        })
        self.user_portal = self.env['res.users'].create({
            'login': 'portal',
            'password': 'portal',
            'name': 'Portal',
            'email': 'portal@example.com',
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
        })

        self.url_public_readonly = '/test_http/greeting-public'
        self.url_public_noreadonly = '/test_http/greeting-public?readonly=0'
        self.url_auth_readonly = '/test_http/greeting-user'
        self.url_auth_noreadonly = '/test_http/greeting-user?readonly=0'

        self.geoip_resolver.add_locations(TEST_IPv4_locations)
        self.geoip_resolver.add_locations(TEST_IPv6_locations)

        self._clean_env()

    def _clean_env(self):
        self.DeviceLog.search([]).unlink()

    # --------------------
    # HELPERS
    # --------------------

    def hit(self, session_sid, time, endpoint, headers=None, ip=None):
        # By default: Belgium (Brussels) | Linux Chrome
        headers = headers or {}
        ip = ip or TEST_IPv4_locations.Belgium.Brussels

        headers = {
            **headers,
            'Host': '',
            'X-Forwarded-For': ip,
            'X-Forwarded-Host': 'odoo.com',
            'X-Forwarded-Proto': 'https',
        }

        if 'User-Agent' not in headers:
            headers['User-Agent'] = USER_AGENT_linux_chrome

        with freeze_time(time), \
            patch.dict(odoo.tools.config.options, {'proxy_mode': bool(ip)}):
            return self.url_open(url=endpoint, headers=headers, cookies={'session_id': session_sid})

    def get_trace_info(self, trace):
        (user_agent, ip_address, _), (first_activity, last_activity) = trace
        return {
            'user_agent': user_agent,
            'ip_address': ip_address,
            'elapsed_time': last_activity - first_activity,
        }

    def get_devices(self, user=None, _with=False):
        self.DeviceLog.flush_model()
        self.DeviceLine.invalidate_model()
        self.Device.invalidate_model()

        if _with:
            device_ids = self.Device.with_user(user).search([])
            device_line_ids = device_ids.device_line_ids
            device_log_ids = self.DeviceLog.with_user(user).search([])
        else:
            domain = [('user_id', '=', user.id)] if user else []
            device_ids = self.Device.search(domain)
            device_line_ids = device_ids.device_line_ids  # To have the order `last_activity desc`
            device_log_ids = self.DeviceLog.search(domain)
        return device_ids, device_line_ids, device_log_ids

    def fuzz_user_url(func_test):

        @functools.wraps(func_test)
        def wrapper(self, *args, **kwars):
            users = (self.user_admin, self.user_internal, self.user_portal)
            urls = (self.url_public_readonly, self.url_public_noreadonly, self.url_auth_noreadonly)
            for user, url in itertools.product(users, urls):
                self._clean_env()
                with self.subTest(user=user, url=url):
                    func_test(self, user, url)

        return wrapper

    # --------------------
    # DETECTION
    # --------------------

    @fuzz_user_url
    def test_detection_session_auth(self, user, url):
        session1 = self.authenticate(user.login, user.login)
        time1 = datetime(2025, 1, 1, 8, 0, 0)

        self.hit(session1.sid, time1, url)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (1, 1, 1))
        self.assertEqual(len(session1['_trace']), 1)
        self.assertEqual(self.get_trace_info(next(iter(session1['_trace'].values())))['elapsed_time'], 0)

        self.hit(session1.sid, time1 + timedelta(minutes=30), url)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (1, 1, 1), 'Below the activity update frequency')
        self.assertEqual(len(session1['_trace']), 1)
        self.assertEqual(self.get_trace_info(next(iter(session1['_trace'].values())))['elapsed_time'], 0)

        self.hit(session1.sid, time1 + timedelta(hours=1), url)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (2, 1, 1))
        self.assertEqual(len(session1['_trace']), 1)
        self.assertEqual(self.get_trace_info(next(iter(session1['_trace'].values())))['elapsed_time'], timedelta(hours=1).seconds)

        self.hit(session1.sid, time1 + timedelta(hours=2), url)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (3, 1, 1))
        self.assertEqual(len(session1['_trace']), 1)
        self.assertEqual(self.get_trace_info(next(iter(session1['_trace'].values())))['elapsed_time'], timedelta(hours=2).seconds)

        session2 = self.authenticate(user.login, user.login)
        time2 = datetime(2025, 1, 1, 10, 0, 0)

        self.hit(session2.sid, time2, url)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (4, 2, 2))
        self.assertEqual(len(session2['_trace']), 1)
        self.assertEqual(self.get_trace_info(next(iter(session2['_trace'].values())))['elapsed_time'], 0)

        self.hit(session1.sid, time2 + timedelta(hours=1), url)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (5, 2, 2))
        self.assertEqual(len(session2['_trace']), 1)
        self.assertEqual(self.get_trace_info(next(iter(session2['_trace'].values())))['elapsed_time'], timedelta(hours=1).seconds)

    def test_detection_session_public(self):
        session = self.authenticate(None, None)

        time = datetime(2025, 1, 1, 8, 0, 0)
        self.hit(session.sid, time, self.url_public_readonly)

        # As we don't have a uid in the session, we shouldn't go through
        # the session check and therefore we won't go through the device update.
        # `authenticate` method in the test is not the real method.
        # To check that we are not creating a session (by making it dirty),
        # we can check that there is no `_trace`.
        # This means that the device logic will not create a session file
        # (because we are not passing in the `_update_device` logic).
        self.assertEqual(len(session['_trace']), 0)
        self.assertFalse(session.is_dirty)

    @fuzz_user_url
    def test_detection_device_auth(self, user, url):
        # Different devices for a session is suspicious
        session = self.authenticate(user.login, user.login)
        time = datetime(2025, 1, 1, 8, 0, 0)

        self.hit(session.sid, time + timedelta(minutes=1), url,
            headers={'User-Agent': USER_AGENT_linux_chrome}, ip=TEST_IPv4_locations.Belgium.Brussels)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (1, 1, 1))
        self.assertEqual(len(session['_trace']), 1)
        self.assertFalse(devices[0].suspicious)
        self.assertFalse(device_lines[0].suspicious)
        self.assertFalse(device_lines[0].suspicious_device)

        self.hit(session.sid, time + timedelta(minutes=2), url,
            headers={'User-Agent': USER_AGENT_linux_firefox}, ip=TEST_IPv4_locations.Belgium.Brussels)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (2, 2, 1))
        self.assertEqual(len(session['_trace']), 2)
        self.assertTrue(devices[0].suspicious, 'A User Agent is suspicious')
        self.assertTrue(device_lines[0].suspicious)
        self.assertTrue(device_lines[0].suspicious_device)

        self.hit(session.sid, time + timedelta(minutes=3), url,
            headers={'User-Agent': USER_AGENT_linux_chrome}, ip=TEST_IPv4_locations.France.Paris)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (3, 3, 1))
        self.assertEqual(len(session['_trace']), 3)
        self.assertTrue(devices[0].suspicious, 'An IP address is suspicious')
        self.assertTrue(device_lines[0].suspicious)
        self.assertTrue(device_lines[0].suspicious_device)

    @fuzz_user_url
    def test_detection_device_validity_period_auth(self, user, url):
        session = self.authenticate(user.login, user.login)
        time = datetime(2025, 1, 1, 8, 0, 0)

        self.hit(session.sid, time + timedelta(minutes=1), url,
            headers={'User-Agent': USER_AGENT_linux_chrome}, ip=TEST_IPv4_locations.Belgium.Brussels)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (1, 1, 1))

        self.hit(session.sid, time + timedelta(minutes=1), url,
            headers={'User-Agent': USER_AGENT_linux_chrome}, ip=TEST_IPv4_locations.France.Paris)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (2, 2, 1))

        # Mark it as no suspicious
        self.assertTrue(devices[0].suspicious)

        suspicious_device = device_lines.filtered('suspicious')
        suspicious_device._mark_as_not_suspicious()
        self.DeviceLog.flush_model()
        self.DeviceLine.invalidate_model()
        self.Device.invalidate_model()

        self.assertFalse(devices[0].suspicious)

        time2 = time + timedelta(days=15)

        self.hit(session.sid, time2, url,
            headers={'User-Agent': USER_AGENT_linux_chrome}, ip=TEST_IPv4_locations.Belgium.Brussels)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (3, 2, 1))

        self.hit(session.sid, time2, url,
            headers={'User-Agent': USER_AGENT_linux_chrome}, ip=TEST_IPv4_locations.France.Paris)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (4, 2, 1))

        self.assertFalse(devices[0].suspicious)

        time3 = time2 + timedelta(days=31)

        self.hit(session.sid, time3, url,
            headers={'User-Agent': USER_AGENT_linux_chrome}, ip=TEST_IPv4_locations.France.Paris)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (5, 2, 1))

        self.assertTrue(devices[0].suspicious, 'The device is suspicious because the validity is 30 days.')

    @fuzz_user_url
    def test_detection_no_trace_mechanism(self, user, url):
        session = self.authenticate(user.login, user.login)
        session['_trace_disable'] = True
        odoo.http.root.session_store.save(session)

        time = datetime(2025, 1, 1, 8, 0, 0)
        for hour in range(1, 5):
            self.hit(session.sid, time + timedelta(hours=hour), url, ip=TEST_IPv4_locations.Belgium.Brussels)

        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (0, 0, 0), 'No log should be inserted.')

        self.hit(session.sid, time + timedelta(hours=hour + 1), url, ip=TEST_IPv4_locations.France.Paris)

        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (1, 1, 1), 'A log should be inserted because is suspicious.')

        self.hit(session.sid, time + timedelta(hours=hour + 2), url, ip=TEST_IPv4_locations.France.Paris)
        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (1, 1, 1), 'No log should be inserted because we match a trace history.')

    def test_detection_devices_according_to_user_or_admin(self):
        time = datetime(2025, 1, 1, 8, 0, 0)

        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        for hour in range(1, 6):
            self.hit(session.sid, time + timedelta(hours=hour), self.url_public_noreadonly)

        session = self.authenticate(self.user_internal.login, self.user_internal.login)
        for hour in range(1, 6):
            self.hit(session.sid, time + timedelta(hours=hour), self.url_public_noreadonly)

        devices, device_lines, logs = self.get_devices()
        self.assertEqual((len(logs), len(device_lines), len(devices)), (10, 2, 2))

        devices, device_lines, logs = self.get_devices(self.user_admin, _with=True)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (10, 2, 2))

        devices, device_lines, logs = self.get_devices(self.user_internal, _with=True)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (5, 1, 1))

    # --------------------
    # GARBAGE COLLECTOR
    # --------------------

    @fuzz_user_url
    def test_garbage_collector_log(self, user, url):
        session = self.authenticate(user.login, user.login)
        time = datetime(2025, 1, 1, 8, 0, 0)

        self.hit(session.sid, time, url)
        for hour in range(1, 10):
            self.hit(session.sid, time + timedelta(hours=hour), url)

        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (10, 1, 1))
        first_activity = devices[0].first_activity
        last_activity = devices[0].last_activity

        self.DeviceLog._gc_device_log()
        self.DeviceLog.flush_model()
        self.DeviceLine.invalidate_model()
        self.Device.invalidate_model()

        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (1, 1, 1))
        # Check we conserve session information after GC
        self.assertEqual(devices[0].first_activity, first_activity)
        self.assertEqual(devices[0].last_activity, last_activity)

    @fuzz_user_url
    def test_garbage_collector_conserve_suspicious_log(self, user, url):
        session = self.authenticate(user.login, user.login)
        time = datetime(2025, 1, 1, 8, 0, 0)

        self.hit(session.sid, time, url, ip=TEST_IPv4_locations.Belgium.Brussels)
        for hour in range(1, 5):
            self.hit(session.sid, time + timedelta(hours=hour), url, ip=TEST_IPv4_locations.Belgium.Brussels)
        self.hit(session.sid, time + timedelta(hours=hour), url, ip=TEST_IPv4_locations.France.Paris)
        for hour in range(5, 9):
            self.hit(session.sid, time + timedelta(hours=hour), url, ip=TEST_IPv4_locations.Belgium.Brussels)

        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (10, 2, 1))
        self.assertTrue(devices[0].suspicious)
        first_activity = devices[0].first_activity
        last_activity = devices[0].last_activity

        self.DeviceLog._gc_device_log()
        self.DeviceLog.flush_model()
        self.DeviceLine.invalidate_model()
        self.Device.invalidate_model()

        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (2, 2, 1))
        # Check we conserve session information after GC
        self.assertTrue(devices[0].suspicious)
        self.assertEqual(devices[0].first_activity, first_activity)
        self.assertEqual(devices[0].last_activity, last_activity)

    # --------------------
    # DELETION
    # --------------------

    def test_deletion_session(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        time = datetime(2025, 1, 1, 8, 0, 0)

        res = self.hit(session.sid, time, self.url_auth_noreadonly)
        self.assertNotIn('/web/login', res.url)

        self.user_admin.device_ids._revoke()

        res = self.hit(session.sid, time, self.url_auth_noreadonly)
        self.assertIn('/web/login', res.url, 'We must be redirected to the login page because the session has been deleted.')

    # --------------------
    # FILESYSTEM REFLEXION
    # --------------------

    def _create_device_log_for_user(self, session, count):
        now = int(datetime.now().timestamp())
        for _ in range(count):
            self.DeviceLog.create({
                'session_identifier': odoo.http.root.session_store.generate_key(),
                'user_id': session.uid,
                'user_agent': '',
                'ip_address': '',
                'fingerprint': '',
                'first_activity': datetime.fromtimestamp(now),
                'last_activity': datetime.fromtimestamp(now),
                'revoked': False,
            })

    @fuzz_user_url
    def test_filesystem_reflexion(self, user, url):
        session = self.authenticate(user.login, user.login)
        self._create_device_log_for_user(session, 10)

        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (10, 10, 10))

        self.DeviceLog._ResDeviceLog__update_revoked()

        devices, device_lines, logs = self.get_devices(user)
        self.assertEqual((len(logs), len(device_lines), len(devices)), (10, 0, 0), 'Logs still exist but are no longer used')

    # --------------------
    # UNTRUSTED LOCATIONS
    # --------------------

    @fuzz_user_url
    def test_untrusted_location_device_ipv4(self, user, url):
        session = self.authenticate(user.login, user.login)

        time = datetime(2025, 1, 1, 8, 0, 0)

        self.hit(session.sid, time, url, ip=TEST_IPv4_locations.Belgium.Bruges)
        self.hit(session.sid, time, url, ip=TEST_IPv4_locations.France.Paris)  # suspicious

        _, _, logs = self.get_devices(user)
        self.assertEqual(len(logs.filtered('suspicious')), 1)

        self.hit(session.sid, time, url, ip=TEST_IPv4_locations.United_Kingdom.London)  # suspicious

        _, _, logs = self.get_devices(user)
        self.assertEqual(len(logs.filtered('suspicious')), 2)

        self.hit(session.sid, time + timedelta(days=15), url, ip=TEST_IPv4_locations.Belgium.Bruges)
        self.hit(session.sid, time + timedelta(days=15), url, ip=TEST_IPv4_locations.United_Kingdom.London)

        _, _, logs = self.get_devices(user)
        self.assertEqual(len(logs.filtered('suspicious')), 2)

        self.hit(session.sid, time + timedelta(days=15 + 31), url, ip=TEST_IPv4_locations.United_Kingdom.London)  # suspicious

        _, _, logs = self.get_devices(user)
        self.assertEqual(len(logs.filtered('suspicious')), 3)

        self.hit(session.sid, time + timedelta(days=30), url, ip=TEST_IPv4_locations.Italy.Rome)  # suspicious

        _, _, logs = self.get_devices(user)
        self.assertEqual(len(logs.filtered('suspicious')), 4)

    @fuzz_user_url
    def test_untrusted_location_device_ipv6(self, user, url):
        session = self.authenticate(user.login, user.login)

        time = datetime(2025, 1, 1, 8, 0, 0)

        self.hit(session.sid, time, url, ip=TEST_IPv6_locations.Belgium.Bruges)
        self.hit(session.sid, time, url, ip=TEST_IPv6_locations.France.Paris)  # suspicious

        _, _, logs = self.get_devices(user)
        self.assertEqual(len(logs.filtered('suspicious')), 1)

        self.hit(session.sid, time, url, ip=TEST_IPv6_locations.United_Kingdom.London)  # suspicious

        _, _, logs = self.get_devices(user)
        self.assertEqual(len(logs.filtered('suspicious')), 2)

        self.hit(session.sid, time + timedelta(days=15), url, ip=TEST_IPv6_locations.Belgium.Bruges)
        self.hit(session.sid, time + timedelta(days=15), url, ip=TEST_IPv6_locations.United_Kingdom.London)

        # Trust ipv6 on the same network
        self.hit(session.sid, time + timedelta(days=30), url, ip=TEST_IPv6_locations.Netherlands.Rotterdam)

        _, _, logs = self.get_devices(user)
        self.assertEqual(len(logs.filtered('suspicious')), 2)
