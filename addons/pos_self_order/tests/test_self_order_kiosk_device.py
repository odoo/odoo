import time
from datetime import timedelta

import odoo.tests
from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tools import mute_logger

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_self_order.models.pos_self_order_kiosk_pairing_request import (
    DEFAULT_MAX_PENDING_REQUESTS_PER_IP,
    MAX_PENDING_REQUESTS_PER_IP_PARAM,
)


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSelfOrderKioskDevice(SelfOrderCommonTest):

    def setUp(self):
        super().setUp()
        self.Device = self.env['pos_self_order.kiosk.device']
        self.PairingRequest = self.env['pos_self_order.kiosk.pairing.request']
        self.Wizard = self.env['pos_self_order.kiosk.device_pairing.wizard']

    def test_get_device_from_token(self):
        device = self.paired_device

        found = self.Device._get_kiosk_device_from_token(device._format_auth_cookie())
        self.assertEqual(found, device)

        # empty or malformed cookies resolve to an empty recordset
        self.assertFalse(self.Device._get_kiosk_device_from_token(""))
        self.assertFalse(self.Device._get_kiosk_device_from_token("no-separator"))
        self.assertFalse(self.Device._get_kiosk_device_from_token(f"{device.id}|{device.access_token}|extra"))

        # right id, wrong access token
        self.assertFalse(self.Device._get_kiosk_device_from_token(f"{device.id}|not-the-token"))

        # unknown id
        self.assertFalse(
            self.Device._get_kiosk_device_from_token(f"{device.id + 10000}|{device.access_token}"),
        )

    def test_compute_device_info(self):
        device = self.Device.create({
            'config_id': self.pos_config.id,
            'approved_by': self.pos_admin.id,
            'user_agent': (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        })
        self.assertEqual(device.platform, "linux")
        self.assertEqual(device.browser, "chrome")

        blank = self.Device.create({
            'config_id': self.pos_config.id,
            'approved_by': self.pos_admin.id,
        })
        self.assertEqual(blank.platform, "Unknown")
        self.assertEqual(blank.browser, "Unknown")

    def test_pairing_request_state_helpers(self):
        req = self.PairingRequest._create_request(self.pos_config, '127.0.0.1', 'kiosk-ua')

        self.assertTrue(req.pairing_code.startswith(str(self.pos_config.id)))
        self.assertTrue(req.is_pending())
        self.assertFalse(req.is_expired())

        req.expiration_date = fields.Datetime.now() - timedelta(seconds=1)
        self.assertTrue(req.is_expired())
        self.assertFalse(req.is_pending())

        req.write({'expiration_date': fields.Datetime.now() + timedelta(minutes=5), 'approved': True})
        self.assertFalse(req.is_pending())

    def test_cron_cleanup_expired_pairing_requests(self):
        live = self.PairingRequest._create_request(self.pos_config, '127.0.0.1', 'ua')
        stale = self.PairingRequest._create_request(self.pos_config, '127.0.0.1', 'ua')
        stale.expiration_date = fields.Datetime.now() - timedelta(hours=1)

        self.PairingRequest._cron_cleanup_expired()

        self.assertTrue(live.exists())
        self.assertFalse(stale.exists())

    def test_wizard_pairs_a_new_device(self):
        req = self.PairingRequest._create_request(self.pos_config, '10.0.0.1', 'kiosk-ua')

        wizard = self.Wizard.with_user(self.pos_admin).create({
            # check that whitespace is stripped from the pairing code
            'pairing_code': f"  {req.pairing_code}  ",
        })
        action = wizard.action_confirm()

        self.assertTrue(wizard.is_done)
        self.assertEqual(action['params']['type'], 'success')
        self.assertEqual(wizard.pairing_request_id, req)

        req.invalidate_recordset()
        self.assertTrue(req.approved)
        self.assertFalse(req.is_pending())

        # a new device record is created and linked to the pairing request, with a short grace period
        self.assertAlmostEqual(
            req.expiration_date, fields.Datetime.now() + timedelta(minutes=5),
            delta=timedelta(seconds=30),
        )

        device = req.device_id
        self.assertTrue(device)
        self.assertEqual(device.config_id, self.pos_config)
        self.assertEqual(device.approved_by, self.pos_admin)
        self.assertEqual(device.ip_address, '10.0.0.1')
        self.assertEqual(device.user_agent, 'kiosk-ua')

    def test_wizard_rejects_unknown_code(self):
        devices_before = self.Device.search([])

        wizard = self.Wizard.with_user(self.pos_admin).create({'pairing_code': '000000'})
        action = wizard.action_confirm()

        self.assertFalse(wizard.is_done)
        self.assertEqual(action['params']['type'], 'warning')
        self.assertFalse(wizard.pairing_request_id)
        self.assertEqual(self.Device.search([]), devices_before, "no device should have been created")

    def test_wizard_rejects_expired_code(self):
        req = self.PairingRequest._create_request(self.pos_config, '127.0.0.1', 'ua')
        req.expiration_date = fields.Datetime.now() - timedelta(minutes=1)

        wizard = self.Wizard.with_user(self.pos_admin).create({'pairing_code': req.pairing_code})
        action = wizard.action_confirm()

        self.assertFalse(wizard.is_done)
        self.assertEqual(action['params']['type'], 'warning')
        req.invalidate_recordset()
        self.assertFalse(req.approved)
        self.assertFalse(req.device_id)

    def test_pairing_requests_capped_per_ip(self):
        self.env['ir.config_parameter'].sudo().set_int(MAX_PENDING_REQUESTS_PER_IP_PARAM, 3)

        for _i in range(3):
            self.PairingRequest._create_request(self.pos_config, '203.0.113.7', 'ua')

        # next request from the same IP is rejected
        with self.assertRaises(UserError):
            self.PairingRequest._create_request(self.pos_config, '203.0.113.7', 'ua')

        # other IPs are unaffected
        self.assertTrue(self.PairingRequest._create_request(self.pos_config, '203.0.113.8', 'ua'))

        # approved or expired requests no longer count towards the cap
        self.PairingRequest.search([('ip_address', '=', '203.0.113.7')])[0].approved = True
        self.assertTrue(self.PairingRequest._create_request(self.pos_config, '203.0.113.7', 'ua'))

    def test_max_pending_requests_per_ip_param(self):
        Param = self.env['ir.config_parameter'].sudo()
        DEFAULT = DEFAULT_MAX_PENDING_REQUESTS_PER_IP
        self.assertEqual(self.PairingRequest._max_pending_requests_per_ip(), DEFAULT)
        Param.set_int(MAX_PENDING_REQUESTS_PER_IP_PARAM, 7)
        self.assertEqual(self.PairingRequest._max_pending_requests_per_ip(), 7)
        Param.set_str(MAX_PENDING_REQUESTS_PER_IP_PARAM, 'not-a-number')
        self.assertEqual(self.PairingRequest._max_pending_requests_per_ip(), DEFAULT)
        Param.set_int(MAX_PENDING_REQUESTS_PER_IP_PARAM, 0)
        self.assertEqual(self.PairingRequest._max_pending_requests_per_ip(), DEFAULT)
        Param.set_int(MAX_PENDING_REQUESTS_PER_IP_PARAM, -3)
        self.assertGreaterEqual(self.PairingRequest._max_pending_requests_per_ip(), -3)

    def test_device_model_access_rights(self):
        # only the POS manager group can access the device model
        with self.assertRaises(AccessError):
            self.Device.with_user(self.pos_user).search([])
        self.Device.with_user(self.pos_admin).search([])


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSelfOrderKioskDeviceController(SelfOrderCommonTest):
    def _setup_kiosk(self):
        self.pos_config.write({'self_ordering_mode': 'kiosk'})
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

    def test_kiosk_pairing_flow(self):
        self._setup_kiosk()

        # 1. the device requests a pairing code
        result = self._request_pairing_code()['result']
        self.assertIn('pairing_code', result)
        self.assertGreater(result['expires_in'], 0)
        code = result['pairing_code']

        req = self.env['pos_self_order.kiosk.pairing.request'].search([('pairing_code', '=', code)])
        self.assertTrue(req.is_pending())
        self.assertFalse(req.device_id)

        # 2. asking again reuses the pending request (session-scoped), no duplicate code
        self.assertEqual(self._request_pairing_code()['result']['pairing_code'], code)
        self.assertEqual(
            self.env['pos_self_order.kiosk.pairing.request'].search_count([('pairing_code', '=', code)]), 1,
        )

        # 3. while waiting for approval the status endpoint answers "waiting"
        self.assertEqual(self._poll_pairing_status()['result']['status'], 'waiting')

        # 4. a manager approves the code from the backend
        self.env['pos_self_order.kiosk.device_pairing.wizard'].with_user(self.pos_admin).create(
            {'pairing_code': code},
        ).action_confirm()
        req.invalidate_recordset()
        device = req.device_id
        self.assertTrue(device)

        # 5. the next status poll returns "approved" and drops the auth cookie in the jar
        cookie_name = self.env['pos_self_order.kiosk.device']._format_auth_cookie_name(self.pos_config.id)
        self.opener.cookies.pop(cookie_name, None)
        self.assertEqual(self._poll_pairing_status()['result']['status'], 'approved')
        self.assertIn(cookie_name, self.opener.cookies)

        # 6. the paired device can now reach kiosk-protected endpoints
        data = self._load_self_data()
        self.assertIn('result', data)
        self.assertIn('pos.config', data['result'])

    def test_pairing_code_skipped_when_already_paired(self):
        self._setup_kiosk()
        cookie = self._get_pairing_cookie()

        body = self._request_pairing_code(cookies={cookie['name']: cookie['value']})

        self.assertEqual(body['result'], {'already_paired': True})

    @mute_logger('odoo.http')
    def test_pairing_status_without_request_is_invalid(self):
        self._setup_kiosk()
        self.assertEqual(self._poll_pairing_status()['result']['status'], 'invalid')

    @mute_logger('odoo.http')
    def test_pairing_access_denied_outside_kiosk_mode(self):
        self.pos_config.write({'self_ordering_mode': 'mobile'})
        body = self._request_pairing_code()
        self.assertIn('error', body)
        self.assertIn('Forbidden', body['error']['data']['name'])

    @mute_logger('odoo.http')
    def test_pairing_access_denied_with_wrong_config_token(self):
        self._setup_kiosk()
        self.assertIn('error', self._request_pairing_code(access_token='not-the-config-token'))

    @mute_logger('odoo.http')
    def test_kiosk_data_access_requires_paired_device(self):
        self._setup_kiosk()
        body = self._load_self_data()
        self.assertIn('error', body)
        self.assertIn('Unauthorized', body['error']['data']['name'])

    def test_kiosk_access_granted_to_logged_in_pos_user_without_pairing(self):
        self._setup_kiosk()
        Device = self.env['pos_self_order.kiosk.device']
        self.authenticate('pos_user', 'pos_user')

        self.assertEqual(self._request_pairing_code()['result'], {'already_paired': True})

        # and can reach kiosk-protected endpoints directly
        data = self._load_self_data()
        self.assertIn('result', data)
        self.assertIn('pos.config', data['result'])

        # No device record is created for this user
        self.assertEqual(Device.search_count([]), 0)

    @mute_logger('odoo.http')
    def test_pairing_code_request_reports_ip_quota(self):
        self._setup_kiosk()
        PairingRequest = self.env['pos_self_order.kiosk.pairing.request']
        for _i in range(10):
            PairingRequest._create_request(self.pos_config, '127.0.0.1', 'ua')

        body = self._request_pairing_code()

        self.assertEqual(body['result'], {'error': 'unavailable'})
        self.assertEqual(
            PairingRequest.search_count([('ip_address', '=', '127.0.0.1'), ('approved', '=', False)]), 10,
            "the refused request must not have been persisted",
        )

    def test_touch_device_throttles_activity_writes(self):
        self._setup_kiosk()
        cookie = self._get_pairing_cookie()
        cookies = {cookie['name']: cookie['value']}
        device = self.paired_device

        # the request updates activity, ip and user agent
        device.write({
            'last_activity': fields.Datetime.now() - timedelta(minutes=10),
            'ip_address': 'stale',
        })
        before = fields.Datetime.now() - timedelta(minutes=1)
        self._load_self_data(cookies=cookies)
        device.invalidate_recordset()
        self.assertGreater(device.last_activity, before)
        self.assertEqual(device.ip_address, '127.0.0.1')

        # a second request within the throttle window must not write
        device.write({'ip_address': 'old_value'})
        self._load_self_data(cookies=cookies)
        device.invalidate_recordset()
        self.assertEqual(device.ip_address, 'old_value')

    def test_touch_device_refreshes_the_auth_cookie(self):
        self._setup_kiosk()
        cookie = self._get_pairing_cookie()
        cookies = {cookie['name']: cookie['value']}
        device = self.paired_device
        route = f'/pos-self/data/{self.pos_config.id}'
        body = {'jsonrpc': '2.0', 'method': 'call', 'params': self._token_params(None)}

        # old activity-> the request must re-issue the cookie
        device.last_activity = fields.Datetime.now() - timedelta(days=2)
        response = self.url_open(route, json=body, cookies=cookies)
        self.assertEqual(response.status_code, 200)
        refreshed = next((c for c in response.cookies if c.name == cookie['name']), None)
        self.assertIsNotNone(refreshed)
        self.assertEqual(refreshed.value, cookie['value'])
        self.assertIsNotNone(refreshed.expires)
        self.assertGreater(refreshed.expires, time.time() + timedelta(days=300).total_seconds())

        # within REFRESH_THRESHOLD  the cookie is  untouched
        device.last_activity = fields.Datetime.now() - timedelta(minutes=10)
        response = self.url_open(route, json=body, cookies=cookies)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.cookies.get(cookie['name']))

    def test_auth_cookie_is_hardened(self):
        self._setup_kiosk()
        code = self._request_pairing_code()['result']['pairing_code']
        self.env['pos_self_order.kiosk.device_pairing.wizard'].with_user(self.pos_admin).create(
            {'pairing_code': code},
        ).action_confirm()

        cookie_name = self.env['pos_self_order.kiosk.device']._format_auth_cookie_name(self.pos_config.id)
        self.opener.cookies.pop(cookie_name, None)
        response = self.url_open(
            f'/pos-self-kiosk/pairing/{self.pos_config.id}/status',
            json={'jsonrpc': '2.0', 'method': 'call', 'params': self._token_params(None)},
        )

        set_cookie = next(v for v in response.raw.headers.getlist('Set-Cookie') if v.startswith(f'{cookie_name}='))
        self.assertIn('HttpOnly', set_cookie)
        self.assertIn('SameSite=Lax', set_cookie)

    def _rpc(self, route, params, cookies=None):
        response = self.url_open(
            route,
            json={'jsonrpc': '2.0', 'method': 'call', 'params': params},
            cookies=cookies,
        )
        return response.json()

    def _token_params(self, access_token):
        return {'access_token': self.pos_config.access_token if access_token is None else access_token}

    def _request_pairing_code(self, *, access_token=None, cookies=None):
        return self._rpc(
            f'/pos-self-kiosk/pairing/{self.pos_config.id}', self._token_params(access_token), cookies,
        )

    def _poll_pairing_status(self, *, access_token=None, cookies=None):
        return self._rpc(
            f'/pos-self-kiosk/pairing/{self.pos_config.id}/status', self._token_params(access_token), cookies,
        )

    def _load_self_data(self, *, access_token=None, cookies=None):
        return self._rpc(
            f'/pos-self/data/{self.pos_config.id}', self._token_params(access_token), cookies,
        )
