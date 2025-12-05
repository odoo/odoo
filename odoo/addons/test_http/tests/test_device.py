# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

import odoo

from odoo import Command
from odoo.addons.test_http.utils import (
    TEST_IP,
    USER_AGENT_android_chrome,
    USER_AGENT_linux_chrome,
    USER_AGENT_linux_firefox
)
from odoo.tests import tagged

from .test_common import TestHttpBase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestDevice(TestHttpBase):

    def setUp(self):
        super().setUp()

        self.Session = self.env['res.session']
        self.DeviceLine = self.env['res.device']
        self.DeviceLog = self.env['res.device.log']

        self.DeviceLog.search([]).unlink()

        self.user_admin = self.env.ref('base.user_admin')
        self.user_internal = self.env['res.users'].create({
            'login': 'internal',
            'password': 'internal',
            'name': 'Internal',
            'email': 'internal@example.com',
            'group_ids': [Command.set([self.env.ref('base.group_user').id])],
        })

    def hit(self, time, endpoint, headers=None, ip=None):
        if ip:
            headers = headers or {}
            headers = {
                **headers,
                'Host': '',
                'X-Forwarded-For': ip,
                'X-Forwarded-Host': 'odoo.com',
                'X-Forwarded-Proto': 'https'
            }
        with freeze_time(time), \
            patch.dict(odoo.tools.config.options, {'proxy_mode': bool(ip)}):
            return self.url_open(url=endpoint, headers=headers)

    def info_device(self, device):
        return {
            'ip_address': device['ip_address'],
            'user_agent': device['user_agent'],
            'elapsed_time': device['last_activity'] - device['first_activity'],
        }

    def get_devices(self, user=None):
        self.DeviceLog.flush_model()
        self.DeviceLine.invalidate_model()
        self.Session.invalidate_model()

        domain = [('user_id', '=', user.id)] if user else []
        session_ids = self.Session.search(domain)
        device_ids = session_ids.device_ids  # To have the order `last_activity desc`
        device_log_ids = self.DeviceLog.search(domain)
        return session_ids, device_ids, device_log_ids

    # --------------------
    # DETECTION
    # --------------------

    def test_detection_device_readonly(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session['_devices']), 1)

    def test_detection_device_no_readonly(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session['_devices']), 1)

    def test_detection_user_public(self):
        session = self.authenticate(None, None)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 0)
        self.assertEqual(len(devices), 0)
        self.assertEqual(len(logs), 0)
        self.assertEqual(len(session['_devices']), 0)

    def test_detection_device_readonly_then_no_readonly(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session['_devices']), 1)

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session['_devices']), 1)

    def test_detection_device_according_to_time(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session['_devices']), 1)

        device_1 = next(iter(session['_devices'].values()))
        self.assertEqual(self.info_device(device_1)['elapsed_time'], 0)

        self.hit('2024-01-01 08:30:00', '/test_http/greeting-public?readonly=0')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session['_devices']), 1)

        device_1 = next(iter(session['_devices'].values()))
        self.assertEqual(self.info_device(device_1)['elapsed_time'], 0)  # No trace update (< 3600 sec)

        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 2)
        self.assertEqual(len(session['_devices']), 1)

        device_1 = next(iter(session['_devices'].values()))
        self.assertEqual(self.info_device(device_1)['elapsed_time'], 3600)

        self.hit('2024-01-01 10:00:00', '/test_http/greeting-public?readonly=0')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 3)
        self.assertEqual(len(session['_devices']), 1)

        device_1 = next(iter(session['_devices'].values()))
        self.assertEqual(self.info_device(device_1)['elapsed_time'], 7200)

    def test_detection_device_according_to_useragent(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session['_devices']), 1)

        device_1 = next(iter(session['_devices'].values()))
        self.assertEqual(self.info_device(device_1)['user_agent'], USER_AGENT_linux_chrome)

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 2)
        self.assertEqual(len(logs), 2)
        self.assertEqual(len(session['_devices']), 2)

        _, device_2 = session['_devices'].values()
        self.assertEqual(self.info_device(device_2)['user_agent'], USER_AGENT_linux_firefox)

    def test_detection_device_according_to_ipaddress(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session['_devices']), 1)

        self.hit('2024-01-01 08:00:01', '/test_http/greeting-public?readonly=0', ip=TEST_IP)

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 2)
        self.assertEqual(len(logs), 2)
        self.assertEqual(len(session['_devices']), 2)

        device_1, device_2 = session['_devices'].values()
        self.assertNotEqual(self.info_device(device_1)['ip_address'], TEST_IP)
        self.assertEqual(self.info_device(device_2)['ip_address'], TEST_IP)

        localized_device = devices.filtered(lambda device: device.ip_address == TEST_IP)
        self.assertEqual(localized_device.country, 'France')

    def test_detection_usurpation_sid(self):
        session = self.authenticate(self.user_internal.login, self.user_internal.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0')

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0', headers={'session_id': session.sid}, ip=TEST_IP)
        self.assertEqual(len(self.user_internal.session_ids), 1)
        self.assertEqual(len(self.user_internal.session_ids.device_ids), 2)

    def test_detection_devices_according_to_time_useragent(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.assertEqual(len(self.user_admin.session_ids), 1)
        self.assertEqual(len(self.user_admin.session_ids.device_ids), 1)

        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.assertEqual(len(self.user_admin.session_ids), 1)
        self.assertEqual(len(self.user_admin.session_ids.device_ids), 1)

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})
        self.assertEqual(len(self.user_admin.session_ids), 1)
        self.assertEqual(len(self.user_admin.session_ids.device_ids), 2)

        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})
        self.assertEqual(len(self.user_admin.session_ids), 1)
        self.assertEqual(len(self.user_admin.session_ids.device_ids), 2)

    def test_detection_devices_according_to_user_or_admin(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')
        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0')
        self.authenticate(self.user_internal.login, self.user_internal.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')
        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0')

        self.assertEqual(len(self.user_admin.session_ids), 1)
        self.assertEqual(len(self.user_admin.session_ids.device_ids), 1)
        self.assertEqual(len(self.user_internal.session_ids), 1)
        self.assertEqual(len(self.user_internal.session_ids.device_ids), 1)

        sessions_seen_from_admin = self.Session.with_user(self.user_admin).search([])
        sessions_seen_from_internal = self.Session.with_user(self.user_internal).search([])
        self.assertEqual(len(sessions_seen_from_admin), 2)
        self.assertEqual(len(sessions_seen_from_admin.device_ids), 2)
        self.assertEqual(len(sessions_seen_from_internal), 1)
        self.assertEqual(len(sessions_seen_from_internal.device_ids), 1)

    def test_differentiate_computer_and_mobile(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_android_chrome})

        devices = self.user_admin.session_ids.device_ids
        laptop_device = devices.filtered(lambda device: device.device_type == 'computer')
        mobile_device = devices.filtered(lambda device: device.device_type == 'mobile')
        self.assertEqual(len(laptop_device), 1)
        self.assertEqual(len(mobile_device), 1)

    def test_retrieve_linked_ip_addresses(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', ip='193.0.3.43')
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', ip='192.0.2.42')
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', ip='191.0.1.41')

        self.assertCountEqual(
            self.user_admin.session_ids.device_ids.mapped('ip_address'),
            ['193.0.3.43', '192.0.2.42', '191.0.1.41'],
        )

    def test_retrieve_linked_ip_addresses_according_to_devices(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome}, ip='193.0.3.43')
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome}, ip='192.0.2.42')
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox}, ip='191.0.1.41')

        devices = self.user_admin.session_ids.device_ids
        device_chrome = devices.filtered(lambda device: device.browser == 'chrome')
        device_firefox = devices.filtered(lambda device: device.browser == 'firefox')
        self.assertCountEqual(device_chrome.mapped('ip_address'), ['193.0.3.43', '192.0.2.42'])
        self.assertCountEqual(device_firefox.mapped('ip_address'), ['191.0.1.41'])

    def test_detection_no_trace_mechanism(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        session['_trace_disable'] = True
        odoo.http.root.session_store.save(session)
        res = self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')
        self.assertEqual(res.status_code, 200)

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 0)
        self.assertEqual(len(devices), 0)
        self.assertEqual(len(logs), 0)
        self.assertEqual(len(session['_devices']), 0)

    def test_detection_device_default_order(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.hit('2024-01-01 10:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})
        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_android_chrome})

        devices = self.user_admin.session_ids.device_ids
        self.assertEqual(
            list(zip(devices.mapped('platform'), devices.mapped('browser'))),
            [('linux', 'firefox'), ('android', 'chrome'), ('linux', 'chrome')],
            "By default, devices should be found from the most recent to the least recent (according to their last activity).",
        )

    # --------------------
    # DELETION
    # --------------------

    def test_deletion_device(self):
        """
            A user is authenticated and the administrator
            wants to block his device (and therefore its session).
        """
        self.authenticate(self.user_internal.login, self.user_internal.login)
        res = self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0')
        self.assertNotIn('/web/login', res.url)

        user_internal_session = self.user_internal.session_ids
        self.assertEqual(len(user_internal_session), 1)

        user_internal_session._revoke()

        res = self.hit('2024-01-01 08:00:01', '/test_http/greeting-user?readonly=0')
        self.assertIn('/web/login', res.url)

    def test_deletion_invalidate_sid(self):
        session = self.authenticate(self.user_internal.login, self.user_internal.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0')

        self.user_internal.session_ids._revoke()

        res = self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0', headers={'session_id': session.sid})
        self.assertIn('/web/login', res.url)

    def test_deletion_specific_device(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.hit('2024-01-01 09:00:00', '/test_http/greeting-user?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.hit('2024-01-01 09:00:00', '/test_http/greeting-user?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 2)
        self.assertEqual(len(devices), 3)
        self.assertEqual(len(logs), 5)

        self.user_admin.session_ids.filtered(
            lambda session: any(device.browser == 'firefox' for device in session.device_ids),
        )._revoke()

        sessions, devices, logs = self.get_devices(self.user_admin)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 5)

        res = self.hit('2024-01-01 08:00:30', '/test_http/greeting-user?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})
        self.assertIn('/web/login', res.url)

    # --------------------
    # FILESYSTEM REFLEXION
    # --------------------

    def _create_device_log_for_user(self, session, count):
        for _ in range(count):
            self.DeviceLog.create({
                'session_identifier': odoo.http.root.session_store.generate_key(),
                'user_id': session.uid,
                'revoked': False,
                'ip_address': TEST_IP,
                'user_agent': USER_AGENT_linux_chrome,
                'first_activity': datetime.now(),
                'last_activity': datetime.now(),
            })

    def test_filesystem_reflexion(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        with freeze_time('2025-01-01 08:00:00'):
            self._create_device_log_for_user(session, 10)

        session = self.authenticate(self.user_internal.login, self.user_internal.login)
        with freeze_time('2025-01-01 08:00:00'):
            self._create_device_log_for_user(session, 10)

        self.assertEqual(len(self.user_admin.session_ids), 10)
        self.assertEqual(len(self.user_internal.session_ids), 10)

        odoo.http.root.session_store.store.clear()

        # Update all device logs
        with freeze_time('2025-02-01 08:00:00'), patch.object(self.cr, 'commit', lambda: ...):
            self.DeviceLog.sudo()._ResDeviceLog__update_revoked()
        self.DeviceLog.flush_model()  # Because write on ``res.device.log`` and so we have new values in cache
        self.Session.invalidate_model()  # Because it depends on the ``res.device.log`` model (updated in database)

        self.assertEqual(len(self.user_admin.session_ids), 0)
        self.assertEqual(len(self.user_internal.session_ids), 0)

    # --------------------
    # SPECIFIC USE CASE
    # --------------------

    def test_specific_public_user_write(self):
        """
            A public user who hits a non-readonly route
            does not have to create a session file if there
            are no changes in the session itself.
        """
        session = self.authenticate(None, None)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        # As we don't have a uid in the session, we shouldn't go through
        # the session check and therefore we won't go through the device update.
        # `authenticate` method in the test is not the real method.
        # To check that we are not creating a session (by making it dirty),
        # we can check that there is no `_devices`.
        # This means that the device logic will not create a session file
        # (because we are not passing in the `_update_device` logic).
        self.assertFalse(session['_devices'])

    def test_keep_user_reference_after_user_deletion(self):
        self.authenticate(self.user_internal.login, self.user_internal.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public')

        sessions, devices, logs = self.get_devices(self.user_internal)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        # `user_id` field must be a recordset
        self.assertEqual(sessions.user_id, self.user_internal)
        self.assertEqual(devices.user_id, self.user_internal)
        self.assertEqual(logs.user_id, self.user_internal.id)

        self.user_internal.unlink()

        self.assertEqual(logs.user_id, self.user_internal.id)
