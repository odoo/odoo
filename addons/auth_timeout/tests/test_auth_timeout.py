import json
import lxml.html
import time

import odoo.http

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.tests import HttpCase, new_test_user, tagged, TransactionCase
from odoo.tests.common import HOST

from odoo.addons.auth_totp.models.totp import TOTP
from odoo.addons.auth_totp.controllers.home import TRUSTED_DEVICE_COOKIE


class TestAuthTimeout(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, "foo", groups="base.group_user,base.group_erp_manager,base.group_system")

    def test_user_auth_methods(self):
        # By default the only authentication method of the user is the password
        self.assertEqual(self.user._get_auth_methods(), ["password"])

        # Enforce TOTP by mail, it adds TOTP by email as possible authentication method
        config = self.env["res.config.settings"].create({})
        config.auth_totp_enforce = True
        config.auth_totp_policy = "employee_required"
        config.execute()
        self.assertEqual(self.user._get_auth_methods(), ["totp_mail", "password"])

        # Set a TOTP secret, it replaces TOTP by email to TOTP by app
        self.user.totp_secret = "foo"
        self.assertEqual(self.user._get_auth_methods(), ["totp", "password"])

        # Set a passkey, it adds WebAuthN as possible authentication method
        self.env["auth.passkey.key"].create(
            {
                "name": "foo",
                "credential_identifier": "foo",
                "public_key": "foo",
                "create_uid": self.user.id,
            }
        )
        self.assertEqual(self.user._get_auth_methods(), ["webauthn", "totp", "password"])

    def test_user_lock_timeouts(self):
        group1, group2, group3 = self.user.group_ids[:3]

        # Set
        # - 15 mins session inactivity timeout,
        # - 24 hours re-authenticate interval, with required MFA
        group1.lock_timeout_inactivity = 15
        group1.lock_timeout = 24 * 60
        group1.lock_timeout_mfa = True
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(86400, True)],
                "lock_timeout_inactivity": [(900, False)],
            },
        )

        # Adding a higher inactivity timeout on another group: No change, the lowest inactivity timeout stays 15 mins
        group2.lock_timeout_inactivity = 60  # 1h
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(86400, True)],
                "lock_timeout_inactivity": [(900, False)],
            },
        )

        # But then require MFA after 1 hour of inactivity
        # Then, the lowest inactivity timeout without MFA stays 15 mins, but with MFA becomes 1h
        group2.lock_timeout_inactivity_mfa = True
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(86400, True)],
                "lock_timeout_inactivity": [(900, False), (3600, True)],
            },
        )

        # Then make it shorter than the 15 mins inactivity timeout
        # No need to specify the 15 mins timeout without MFA as now there is one shorter requiring MFA
        group2.lock_timeout_inactivity = 6
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(86400, True)],
                "lock_timeout_inactivity": [(360, True)],
            },
        )

        # Adding a higher re-authenticate interval on another group: No change, the lowest stays 1 hour
        group2.lock_timeout = 48 * 60
        group2.lock_timeout_mfa = True
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(86400, True)],
                "lock_timeout_inactivity": [(360, True)],
            },
        )

        # Make it shorter, 12 hours instead of the other group with 24 hours
        # Then the lowest lock timeout becomes 12
        group2.lock_timeout = 12 * 60
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(43200, True)],
                "lock_timeout_inactivity": [(360, True)],
            },
        )

        # Do not ask for MFA for this group.
        # Then the lowest lock timeout without MFA is 12 and with MFA is 24 hours
        group2.lock_timeout_mfa = False
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(43200, False), (86400, True)],
                "lock_timeout_inactivity": [(360, True)],
            },
        )

        # For the sake, more tests with a 3rd group
        # Set a lock timeout after 18 hours without MFA,
        # which is between the one at 12 hours without MFA and the one at 24 hours with MFA.
        # No change, as it's without MFA and higher than the one set for 12 hours without MFA.
        group3.lock_timeout = 18 * 60
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(43200, False), (86400, True)],
                "lock_timeout_inactivity": [(360, True)],
            },
        )

        # Require MFA for this 18 hours lock timeout
        # Change: The minimum lock timeout with MFA becomes 18 hours instead of 24 hours
        group3.lock_timeout_mfa = True
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(43200, False), (64800, True)],
                "lock_timeout_inactivity": [(360, True)],
            },
        )

        # Make it even shorter than the 12 hours without MFA, let's say 6 hours
        # Change: As the lowest lock timeout now becomes 6 hours, and require MFA, no need to specify the others
        group3.lock_timeout = 6 * 60
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(21600, True)],
                "lock_timeout_inactivity": [(360, True)],
            },
        )

        # Set an inactivity timeout shorter than the one at 6 minutes
        # Change: The lowest inactivity timeout without MFA becomes 180 seconds
        group3.lock_timeout_inactivity = 3
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(21600, True)],
                "lock_timeout_inactivity": [(180, False), (360, True)],
            },
        )

        # Require MFA for this 180 seconds inactivity timeout
        # Change: The lowest inactivity timeout becomes 180, with or without MFA
        group3.lock_timeout_inactivity_mfa = True
        self.assertEqual(
            self.user._get_lock_timeouts(),
            {
                "lock_timeout": [(21600, True)],
                "lock_timeout_inactivity": [(180, True)],
            },
        )


@tagged("post_install", "-at_install")
class TestAuthTimeoutHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env, "foobarbaz", groups="base.group_user,base.group_erp_manager,base.group_system"
        )

        # Mock TOTP.match to make the code 111111 always valid.
        # It will be used during the tour for authentication using TOTP by email and TOTP by app.
        cls.totp_code = 111111
        cls.totp_counter = 0
        origin_totp_match = TOTP.match

        def match(self, code, *args, **kwargs):
            if code == cls.totp_code:
                cls.totp_counter += 1
                return cls.totp_counter
            return origin_totp_match(self, code, *args, **kwargs)

        cls.classPatch(TOTP, "match", match)

        # Mock auth.passkey.key._verify_registration_options to accept the hard-coded registration during the tour
        cls.passkey_credential_id = "foo"
        cls.passkey_credential_id_base64url = "Zm9v"  # bytes_to_base64url(b"foo") == "Zm9v"
        PasskeyClass = cls.env.registry["auth.passkey.key"]
        origin_passkey_verify_registration_options = PasskeyClass._verify_registration_options

        def _verify_registration_options(self, registration):
            if registration.get("id") == cls.passkey_credential_id:
                return {
                    "credential_id": cls.passkey_credential_id.encode(),
                    "credential_public_key": cls.passkey_credential_id.encode(),
                }
            return origin_passkey_verify_registration_options(self, registration)

        cls.classPatch(PasskeyClass, "_verify_registration_options", _verify_registration_options)

        # Mock auth.passkey.key._verify_auth to accept the hard-coded authentication during the tour
        origin_passkey_verify_auth = PasskeyClass._verify_auth

        def _verify_auth(self, auth, public_key, sign_count):
            if auth.get("id") == cls.passkey_credential_id_base64url:  # bytes_to_base64url(b"foo") == "Zm9v"
                return 1
            return origin_passkey_verify_auth(self, auth, public_key, sign_count)

        cls.classPatch(PasskeyClass, "_verify_auth", _verify_auth)

    def rpc(self, model, method, *args, **kwargs):
        return self.url_open(
            "/web/dataset/call_kw", json={"params": {"model": model, "method": method, "args": args, "kwargs": kwargs}}
        ).json()

    def set_session_create_time(self, session_id, timestamp):
        session = odoo.http.root.session_store.get(session_id)
        session["create_time"] = timestamp
        odoo.http.root.session_store.save(session)

    def set_session_last_check_identity(self, session_id, timestamp):
        session = odoo.http.root.session_store.get(session_id)
        session["identity-check-last"] = timestamp
        odoo.http.root.session_store.save(session)

    def set_session_next_check_identity(self, session_id, timestamp):
        session = odoo.http.root.session_store.get(session_id)
        session["identity-check-next"] = timestamp
        odoo.http.root.session_store.save(session)

    def set_auth_totp_mail(self):
        config = self.env["res.config.settings"].create({})
        config.auth_totp_enforce = True
        config.auth_totp_policy = "employee_required"
        config.execute()

    def set_auth_totp(self):
        action = self.rpc("res.users", "action_totp_enable_wizard", [self.user.id])["result"]
        self.rpc(action["res_model"], "enable", [action["res_id"]], context={"code": str(self.totp_code)})

    def set_auth_passkey(self):
        wizard_id = self.rpc("auth.passkey.key.create", "create", {"name": "foo"})["result"]
        self.rpc("auth.passkey.key.create", "make_key", wizard_id, {"id": self.passkey_credential_id})

    def check_identity(self, credentials):
        return self.url_open("/auth-timeout/session/check-identity", json={"params": credentials})

    def assertMustCheckIdentity(self):
        result = self.rpc("res.users", "read", [self.user.id], ["login"])
        self.assertEqual(
            result.get("error", {}).get("data", {}).get("name"),
            "odoo.addons.auth_timeout.models.ir_http.CheckIdentityException",
        )

    def assertSessionExpired(self):
        result = self.rpc("res.users", "read", [self.user.id], ["login"])
        self.assertEqual(result.get("error", {}).get("data", {}).get("name"), "odoo.http.SessionExpiredException")

    def assertMustNotCheckIdentity(self):
        result = self.rpc("res.users", "read", [self.user.id], ["login"])
        self.assertTrue(result.get("result"))

    def test_check_identity_exception(self):
        group = self.user.group_ids[0]
        session_id = self.authenticate(self.user.login, self.user.login).sid

        # Set an activity timeout and simulate an inactivity in the session
        group.lock_timeout_inactivity = 15  # 15 mins
        self.set_session_next_check_identity(session_id, time.time())

        # Check identity must be checked
        self.assertMustCheckIdentity()

        # Check the identity
        self.check_identity({"type": "password", "password": self.user.login})

        # Check identity must no longer be checked
        self.assertMustNotCheckIdentity()

        # Set a lock timeout and simulate the user did not authenticate for 24+ hours
        group.lock_timeout = 24 * 60
        self.set_session_create_time(session_id, time.time() - 25 * 60 * 60)  # 25 hours

        # Check a full login is required
        self.assertSessionExpired()

    def test_authentication_methods(self):
        group = self.user.group_ids[0]
        group.lock_timeout_inactivity = 15  # 15 mins

        session_id = self.authenticate(self.user.login, self.user.login).sid
        # To avoid the check identity wizard during the configuration of TOTP, ...
        self.set_session_last_check_identity(session_id, time.time())

        # 1. Password authentication
        self.set_session_next_check_identity(session_id, time.time() - 16 * 60)
        self.assertMustCheckIdentity()
        self.check_identity({"type": "password", "password": self.user.login})
        self.assertMustNotCheckIdentity()

        # 2. TOTP by email
        # 2.1 Enable TOTP by mail
        self.set_auth_totp_mail()
        # 2.2 Identify using TOTP by email
        self.set_session_next_check_identity(session_id, time.time() - 16 * 60)
        self.assertMustCheckIdentity()
        self.check_identity({"type": "totp_mail", "token": str(self.totp_code)})
        self.assertMustNotCheckIdentity()

        # 3. TOTP by app
        self.set_auth_totp()
        # 3.2 Identify using TOTP by code
        self.set_session_next_check_identity(session_id, time.time() - 16 * 60)
        self.assertMustCheckIdentity()
        self.check_identity({"type": "totp", "token": str(self.totp_code)})
        self.assertMustNotCheckIdentity()

        # 4. Passkey
        # 4.1 Registration of the passkey
        self.set_auth_passkey()

        # 4.2 Identify using a passkey
        self.set_session_next_check_identity(session_id, time.time() - 16 * 60)
        self.assertMustCheckIdentity()
        self.check_identity(
            {"type": "webauthn", "webauthn_response": json.dumps({"id": self.passkey_credential_id_base64url})}
        )
        self.assertMustNotCheckIdentity()

    def test_multiple_lock_timeouts_mfa(self):
        group1, group2 = self.user.group_ids[:2]

        # Set 2 lock timeouts, one at 15 mins without MFA and one at 60 mins with MFA
        group1.lock_timeout_inactivity = 15
        group1.lock_timeout_inactivity_mfa = False
        group2.lock_timeout_inactivity = 60
        group2.lock_timeout_inactivity_mfa = True

        # Enforce TOTP by mail so the user has a 2FA
        config = self.env["res.config.settings"].create({})
        config.auth_totp_enforce = True
        config.auth_totp_policy = "employee_required"
        config.execute()

        session_id = self.authenticate(self.user.login, self.user.login).sid

        # Simulate the session did not authenticate for 30 minutes
        # Which falls between the 15 mins lock timeout without MFA
        # and the 60 mins lock timeout with MFA
        self.set_session_next_check_identity(session_id, time.time() - 30 * 60)

        # Assert the check identity exception is raised
        self.assertMustCheckIdentity()

        # Check the identity
        self.check_identity({"type": "password", "password": self.user.login})

        # Check identity must no longer be checked
        self.assertMustNotCheckIdentity()

        # Simulate the session did not authenticate for 90 mins
        # Which is greather than the 60 mins lock timeout with MFA
        self.set_session_next_check_identity(session_id, time.time() - 90 * 60)

        # Assert the check identity exception is raised
        self.assertMustCheckIdentity()

        # Check the identity with password
        self.check_identity({"type": "password", "password": self.user.login})

        # Assert the check identity exception is raised as it requires 2FA in addition to just password
        self.assertMustCheckIdentity()

        # Try to use password again to check identity,
        # which must not work as password cannot be used as 2FA when it was used as 1st authentication
        self.check_identity({"type": "password", "password": self.user.login})

        # Assert identity check is still raised because it requires 2FA
        self.assertMustCheckIdentity()

        # Check the identity with TOTP code as 2FA
        self.check_identity({"type": "totp_mail", "token": self.user._get_totp_mail_code()[0]})

        # Check identity must no longer be checked
        self.assertMustNotCheckIdentity()

    def test_multiple_inactivity_timeouts_mfa(self):
        group1, group2 = self.user.group_ids[:2]

        # Set 2 inactivity timeouts, one at 15 mins without MFA and one at 30 mins with MFA
        group1.lock_timeout_inactivity = 15  # 15 mins
        group1.lock_timeout_inactivity_mfa = False
        group2.lock_timeout_inactivity = 30  # 30 mins
        group2.lock_timeout_inactivity_mfa = True

        # Enforce TOTP by mail so the user has a 2FA
        config = self.env["res.config.settings"].create({})
        config.auth_totp_enforce = True
        config.auth_totp_policy = "employee_required"
        config.execute()

        session_id = self.authenticate(self.user.login, self.user.login).sid

        # Simulate the session as inactive for 25 mins.
        # `identity-check-next` is set to `now` only when the first inactivity timeout is reached.
        # By setting to `identity-check-next` to 10 mins in the past,
        # it means the session is inactive for the first inactivity timeout + 10 mins
        # As the lowest inactivity timeout is configured to 15 mins above in this test
        # Setting `identity-check-next` to `now` - 10 mins means the session is inactive for 25 mins
        # Which falls between the timeout without mfa of 15 mins and the timeout with mfa of 30 mins
        self.set_session_next_check_identity(session_id, time.time() - 10 * 60)

        # Assert the check identity exception is raised
        self.assertMustCheckIdentity()

        # Check the identity
        self.check_identity({"type": "password", "password": self.user.login})

        # Check identity must no longer be checked
        self.assertMustNotCheckIdentity()

        # Now, simulate the session inactive for more than 31 minutes,
        # by setting to `identity-check-next` to 16 mins in the past:
        # 15 mins (lowest inactivity timeout configured above) + 16 mins = 31 mins of inactivity.
        # As it's greater than the 30 mins inactivity tiemout requiring MFA, MFA is required to check the identity
        self.set_session_next_check_identity(session_id, time.time() - 16 * 60)

        # Assert the check identity exception is raised
        self.assertMustCheckIdentity()

        # Check the identity with password first
        self.check_identity({"type": "password", "password": self.user.login})

        # Assert identity check is still raised because it requires 2FA
        self.assertMustCheckIdentity()

        # Try to use password again to check identity,
        # which must not work as password cannot be used as 2FA when it was used as 1st authentication
        self.check_identity({"type": "password", "password": self.user.login})

        # Assert identity check is still raised because it requires 2FA
        self.assertMustCheckIdentity()

        # Check the identity with TOTP code as 2FA
        self.check_identity({"type": "totp_mail", "token": self.user._get_totp_mail_code()[0]})

        # Check identity must no longer be checked
        self.assertMustNotCheckIdentity()

    def test_remember_device(self):
        # 1. Set a session timeout with MFA lower than the default device age
        group = self.user.group_ids[0]
        group.lock_timeout = 24 * 60
        group.lock_timeout_mfa = True

        # 2. Connect and set a TOTP for the user
        session_id = self.authenticate(self.user.login, self.user.login).sid
        self.set_session_last_check_identity(session_id, time.time())
        self.set_auth_totp()

        # 3. Disconnect
        self.opener.cookies.clear()
        del self.session

        # 4. Login again with totp
        csrf_token = (
            lxml.html.fromstring(self.url_open("/web/login").content).xpath('//input[@name="csrf_token"]')[0].get("value")
        )
        res = self.url_open(
            "/web/login",
            data={
                "login": self.user.login,
                "password": self.user.login,
                "csrf_token": csrf_token,
            },
        )
        self.assertIn("/web/login/totp", res.url)
        csrf_token = lxml.html.fromstring(res.content).xpath('//input[@name="csrf_token"]')[0].get("value")
        res = self.url_open(
            "/web/login/totp",
            data={
                "totp_token": self.totp_code,
                "remember": True,
                "csrf_token": csrf_token,
            },
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            },
        )

        # 5. Assert the expiration date of the cookie
        expires = datetime.fromtimestamp(self.opener.cookies._cookies[HOST]["/"][TRUSTED_DEVICE_COOKIE].expires)
        # Expiration date in less than 1 day
        self.assertLessEqual(expires, datetime.now() + timedelta(seconds=group.lock_timeout * 60))
        # Expiration date in more than 1 day - 1 minute
        self.assertGreater(expires, datetime.now() + timedelta(seconds=group.lock_timeout * 60 - 60))

        # 6. Assert the expiration date of the device in database
        device = self.env["auth_totp.device"].search([("user_id", "=", self.user.id)], order="id DESC", limit=1)
        self.assertLessEqual(device.expiration_date, datetime.now() + timedelta(seconds=group.lock_timeout * 60))
        self.assertGreater(device.expiration_date, datetime.now() + timedelta(seconds=group.lock_timeout * 60 - 60))

    def test_auth_timeout_tour(self):
        session_id = self.authenticate(self.user.login, self.user.login).sid
        # To avoid the check identity wizard during the configuration of TOTP, ...
        self.set_session_last_check_identity(session_id, time.time())
        self.set_auth_totp_mail()
        self.set_auth_totp()
        self.set_auth_passkey()

        # Set a 1 second inactivity timeout, with a mock patch because the field `lock_timeout` is in minutes.
        with patch.object(
            self.env.registry["res.groups"],
            "_get_lock_timeouts",
            return_value={
                "lock_timeout": [],
                "lock_timeout_inactivity": [(1, False)],  # 1 second inactivity without MFA
            },
        ):
            self.start_tour("/odoo", "auth_timeout_tour_lock_timeout_inactivity", login=self.user.login)

        # Set a 1 second inactivity timeout with 2fa, with a mock patch because the field `lock_timeout` is in minutes.
        with patch.object(
            self.env.registry["res.groups"],
            "_get_lock_timeouts",
            return_value={
                "lock_timeout": [],
                "lock_timeout_inactivity": [(1, True)],  # 1 second inactivity with MFA
            },
        ):
            self.start_tour("/odoo", "auth_timeout_tour_lock_timeout_inactivity_2fa", login=self.user.login)

        with patch.object(
            self.env.registry["res.groups"],
            "_get_lock_timeouts",
            return_value={
                "lock_timeout": [(1, True)],  # 1 second session timeout
                "lock_timeout_inactivity": [],
            },
        ):
            self.start_tour("/odoo", "auth_timeout_tour_lock_timeout", login=self.user.login)
