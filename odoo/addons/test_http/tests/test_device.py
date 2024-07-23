# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
from .test_common import TestHttpBase


class TestDevice(TestHttpBase):

    def setUp(self):
        super().setUp()

        self.Device = self.env['res.device']
        self.DeviceLog = self.env['res.device.log']
        self.DeviceLog.search([]).unlink()

        self.user_admin = self.env.ref('base.user_admin')
        self.user_internal = self.env['res.users'].create({
            'login': 'internal',
            'password': 'internal',
            'name': 'Internal',
            'email': 'internal@example.com',
            'groups_id': [Command.set([self.env.ref('base.group_user').id])],
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
            res = self.url_open(url=endpoint, headers=headers)
        return res

    def info_trace(self, trace):
        return {
            'elapsed_time': trace['last_activity'] - trace['first_activity'],
            'platform': trace['platform'],
            'browser': trace['browser'],
            'ip_address': trace['ip_address'],
        }

    def get_devices_logs(self, user=None):
        domain = [('user_id', '=', user.id)] if user else []
        devices = self.Device.search(domain)
        logs = self.DeviceLog.search([
            ('session_identifier', 'in', devices.mapped('session_identifier')),
            ('platform', 'in', devices.mapped('platform')),
            ('browser', 'in', devices.mapped('browser'))
        ])
        return devices, logs

    # --------------------
    # DETECTION
    # --------------------

    def test_detection_device_readonly(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session._trace), 1)

    def test_detection_device_no_readonly(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session._trace), 1)

    def test_detection_user_public(self):
        self.authenticate(None, None)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs()
        self.assertEqual(len(devices), 0)
        self.assertEqual(len(logs), 0)

    def test_detection_device_readonly_then_no_readonly(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session._trace), 1)

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session._trace), 1)

    def test_detection_device_according_to_time(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session._trace), 1)
        self.assertEqual(self.info_trace(session._trace[0])['elapsed_time'], 0)

        self.hit('2024-01-01 08:30:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session._trace), 1)
        self.assertEqual(self.info_trace(session._trace[0])['elapsed_time'], 0)  # No trace update (< 3600 sec)

        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 2)
        self.assertEqual(len(session._trace), 1)
        self.assertEqual(self.info_trace(session._trace[0])['elapsed_time'], 3600)

        self.hit('2024-01-01 10:00:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 3)
        self.assertEqual(len(session._trace), 1)
        self.assertEqual(self.info_trace(session._trace[0])['elapsed_time'], 7200)

    def test_detection_device_according_to_useragent(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session._trace), 1)
        self.assertEqual(self.info_trace(session._trace[0])['platform'], 'linux')
        self.assertEqual(self.info_trace(session._trace[0])['browser'], 'chrome')

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 2)
        self.assertEqual(len(logs), 2)
        self.assertEqual(len(session._trace), 2)
        self.assertEqual(self.info_trace(session._trace[1])['platform'], 'linux')
        self.assertEqual(self.info_trace(session._trace[1])['browser'], 'firefox')

    def test_detection_device_according_to_ipaddress(self):
        session = self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(session._trace), 1)

        self.hit('2024-01-01 08:00:01', '/test_http/greeting-public?readonly=0', ip=TEST_IP)

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 2)
        self.assertEqual(len(session._trace), 2)
        self.assertNotEqual(self.info_trace(session._trace[0])['ip_address'], TEST_IP)
        self.assertEqual(self.info_trace(session._trace[1])['ip_address'], TEST_IP)

        localized_device = devices.filtered(lambda device: device.ip_address == TEST_IP)
        self.assertEqual(localized_device.country, 'France')

    def test_detection_usurpation_sid(self):
        session = self.authenticate(self.user_internal.login, self.user_internal.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0')

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0', headers={'session_id': session.sid}, ip=TEST_IP)
        devices, logs = self.get_devices_logs(self.user_internal)
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(logs), 2)
        self.assertEqual(len(self.user_internal.device_ids), 1)

    def test_detection_devices_according_to_time_useragent(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.assertEqual(len(self.user_admin.device_ids), 1)

        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.assertEqual(len(self.user_admin.device_ids), 1)

        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})
        self.assertEqual(len(self.user_admin.device_ids), 2)

        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})
        self.assertEqual(len(self.user_admin.device_ids), 2)

    def test_detection_devices_according_to_user_or_admin(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')
        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0')
        self.authenticate(self.user_internal.login, self.user_internal.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0')
        self.hit('2024-01-01 09:00:00', '/test_http/greeting-public?readonly=0')

        devices, logs = self.get_devices_logs()
        self.assertEqual(len(devices), 2)
        self.assertEqual(len(logs), 4)
        self.assertEqual(len(self.user_admin.device_ids), 1)
        self.assertEqual(len(self.user_internal.device_ids), 1)

        devices_from_admin = self.Device.with_user(self.user_admin).search([])
        devices_from_internal = self.Device.with_user(self.user_internal).search([])
        self.assertEqual(len(devices_from_admin), 2)
        self.assertEqual(len(devices_from_internal), 1)

    def test_differentiate_computer_and_mobile(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome})
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_android_chrome})

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 2)
        self.assertEqual(len(logs), 2)

        laptop_device = devices.filtered(lambda device: device.device_type == 'computer')
        mobile_device = devices.filtered(lambda device: device.device_type == 'mobile')
        self.assertEqual(len(laptop_device), 1)
        self.assertEqual(len(mobile_device), 1)

    def test_retrieve_linked_ip_addresses(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', ip='193.0.3.43')
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', ip='192.0.2.42')
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', ip='191.0.1.41')

        devices, _ = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 1)
        self.assertIn('193.0.3.43', devices.linked_ip_addresses)
        self.assertIn('192.0.2.42', devices.linked_ip_addresses)
        self.assertIn('191.0.1.41', devices.linked_ip_addresses)

    def test_retrieve_linked_ip_addresses_according_to_devices(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome}, ip='193.0.3.43')
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_chrome}, ip='192.0.2.42')
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-public?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox}, ip='191.0.1.41')

        devices, _ = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 2)
        device_chrome = devices.filtered(lambda device: device.browser == 'chrome')
        device_firefox = devices.filtered(lambda device: device.browser == 'firefox')
        self.assertIn('193.0.3.43', device_chrome.linked_ip_addresses)
        self.assertIn('192.0.2.42', device_chrome.linked_ip_addresses)
        self.assertNotIn('191.0.1.41', device_chrome.linked_ip_addresses)
        self.assertIn('191.0.1.41', device_firefox.linked_ip_addresses)

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

        user_internal_device = self.user_internal.device_ids
        self.assertEqual(len(user_internal_device), 1)
        self.assertEqual(user_internal_device.revoked, False)

        user_internal_device._revoke()

        res = self.hit('2024-01-01 08:00:01', '/test_http/greeting-user?readonly=0')
        self.assertIn('/web/login', res.url)

    def test_deletion_invalidate_sid(self):
        session = self.authenticate(self.user_internal.login, self.user_internal.login)
        self.hit('2024-01-01 08:00:00', '/test_http/greeting-user?readonly=0')

        self.user_internal.device_ids._revoke()

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

        devices, logs = self.get_devices_logs(self.user_admin)
        self.assertEqual(len(devices), 3)
        self.assertEqual(len(logs), 5)
        self.assertEqual(len(self.user_admin.device_ids), 3)

        self.user_admin.device_ids.filtered(lambda device: 'firefox' in device.browser)._revoke()

        res = self.hit('2024-01-01 08:00:30', '/test_http/greeting-user?readonly=0', headers={'User-Agent': USER_AGENT_linux_firefox})
        self.assertIn('/web/login', res.url)

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
        # we can check that there is no `_trace`.
        # This means that the device logic will not create a session file
        # (because we are not passing in the `_update_device` logic).
        self.assertFalse(session._trace)
