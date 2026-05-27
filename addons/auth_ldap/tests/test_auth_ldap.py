import re
import time
from unittest.mock import Mock, patch

import ldap

import odoo.http
from odoo.exceptions import AccessDenied
from odoo.tests import Form, tagged, users

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("-at_install", "post_install")
class TestAuthLDAP(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.company.ldap"].create(
            {
                "company": cls.env.company.id,
                "ldap_binddn": "cn=admin,dc=example,dc=org",
                "ldap_password": "admin",
                "ldap_filter": "uid=%s",
                "ldap_base": "dc=example,dc=org",
            }
        )

        # Mock the connection to the LDAP server
        ldap_connection_mock = Mock()
        # List of users in the LDAP
        ldap_connection_mock._users = {}

        def search_st(base, scope, filter, *args, **kwargs):
            user = ldap_connection_mock._users.get(f"{filter},{base}")
            return [(f"{filter},{base}", {"uid": [user["uid"]]})] if user else []

        def modify_s(dn, changes):
            ldap_connection_mock._users[dn]["password"] = changes[0][2].decode()

        def simple_bind_s(dn, password):
            if ldap_connection_mock._users.get(dn, {}).get("password") != password:
                raise ldap.INVALID_CREDENTIALS()

        ldap_connection_mock.search_st.side_effect = search_st
        ldap_connection_mock.modify_s.side_effect = modify_s
        ldap_connection_mock.simple_bind_s.side_effect = simple_bind_s

        cls.ldap_connection_mock = ldap_connection_mock
        cls.classPatch(cls.env.registry["res.company.ldap"], "_connect", lambda self, conf: ldap_connection_mock)

    def setUp(self):
        super().setUp()

        # Reset the LDAP users between unit tests, so each unit test does not have to take care of the users cleanup
        self.ldap_connection_mock._users = {
            # The user account on the LDAP server that is used to query the directory.
            # Not the account linked to the admin user in the odoo database
            "cn=admin,dc=example,dc=org": {
                "uid": "admin",
                "password": "admin",
            },
            # The user linked to the admin user in the odoo databae
            "uid=admin,dc=example,dc=org": {
                "uid": "admin",
                "password": "xyz",
            },
            # The user linked to the demo user in the odoo databae
            "uid=demo,dc=example,dc=org": {
                "uid": "demo",
                "password": "foo",
            },
        }

    def mock_check_identity(self):
        odoo.http.requestlib._request_stack.push(
            Mock(
                httprequest=Mock(environ={"REMOTE_ADDR": "123.123.123.123"}),
                session=odoo.http.session.Session({"identity-check-last": time.time()}, "foo"),
            )
        )
        self.addCleanup(odoo.http.requestlib._request_stack.pop)

    def test_auth_ldap(self):
        def _get_ldap_dicts(self):
            template_user = self.env.ref("base.template_portal_user_id")
            return [
                {
                    "id": 1,
                    "company": (1, "YourCompany"),
                    "ldap_server": "127.0.0.1",
                    "ldap_server_port": 389,
                    "ldap_binddn": "cn=admin,dc=odoo,dc=com",
                    "ldap_password": "admin",
                    "ldap_filter": "cn=%s",
                    "ldap_base": "dc=odoo,dc=com",
                    "user": (template_user.id, template_user.name),
                    "create_user": True,
                    "ldap_tls": False,
                }
            ]

        def _authenticate(*args, **kwargs):
            return (
                "cn=test_ldap_user,dc=odoo,dc=com",
                {
                    "sn": [b"test_ldap_user"],
                    "cn": [b"test_ldap_user"],
                    "objectClass": [b"inetOrgPerson", b"top"],
                    "userPassword": [b"{MD5}CY9rzUYh03PK3k6DJie09g=="],
                },
            )

        self.env.cr.execute("SELECT id FROM res_users WHERE login = 'test_ldap_user'")
        self.assertFalse(self.env.cr.rowcount, "User should not be present")

        body = self.url_open("/web/login").text
        csrf = re.search(r'csrf_token: "(\w*?)"', body).group(1)

        with patch.object(self.registry["res.company.ldap"], "_get_ldap_dicts", _get_ldap_dicts),\
            patch.object(self.registry["res.company.ldap"], "_authenticate", _authenticate):
            res = self.url_open(
                f"{self.base_url()}/web/login",
                data={
                    "login": "test_ldap_user",
                    "password": "test",
                    "csrf_token": csrf,
                },
            )
            res.raise_for_status()

        self.assertTrue(res.session, "A session must exist at this point")

        self.env.cr.execute(
            "SELECT id FROM res_users WHERE login = %s and id = %s",
            ("test_ldap_user", res.session.uid))
        self.assertTrue(self.env.cr.rowcount, "User should be present")

    @users("demo")
    def test_user_change_own_password(self):
        """Tests that, when a user is linked to an LDAP user and changes his password,
        the password gets updated in the LDAP server rather than updating the local password in the odoo database.
        """
        # Check the user cannot connect with a random password
        with self.assertRaises(AccessDenied):
            self.env["res.users"].authenticate(
                {"login": "demo", "password": "random", "type": "password"},
                {"interactive": True},
            )

        # Check the user can connect with the above defined password in the LDAP mock
        result = self.env["res.users"].authenticate(
            {"login": "demo", "password": "foo", "type": "password"},
            {"interactive": True},
        )
        self.assertEqual(result["uid"], self.env.uid)

        # Bypass the check identity dialog
        # When a user tries to change its password, he gets presented with the check identity dialog
        self.mock_check_identity()

        # User changes his password through the preferences menu / change password wizard form
        with Form(self.env["change.password.own"]) as form:
            form.new_password = "bar"
            form.confirm_password = "bar"
        with self.assertLogs("odoo.addons.base.models.res_users") as log_catcher:
            form.record.change_password()

        self.assertIn("LDAP password change for 'demo'", log_catcher.output[0])

        # The password must have been updated in the LDAP server
        self.assertEqual(
            self.ldap_connection_mock._users[f"uid={self.env.user.login},dc=example,dc=org"]["password"],
            "bar",
        )

        # Check the user can connect with the new password
        result = self.env["res.users"].authenticate(
            {"login": "demo", "password": "bar", "type": "password"},
            {"interactive": True},
        )
        self.assertEqual(result["uid"], self.env.uid)

        # Check the user cannot connect with the old password
        with self.assertRaises(AccessDenied):
            self.env["res.users"].authenticate(
                {"login": "demo", "password": "foo", "type": "password"},
                {"interactive": True},
            )

        # The password must not have been set in the "local" database
        self.env.cr.execute("SELECT password FROM res_users WHERE id = %s", [self.env.uid])
        [password] = self.env.cr.fetchone()
        self.assertFalse(password, "The local password should not have been set")

    @users("admin")
    def test_admin_change_users_password(self):
        """Tests that, when an admin changes the password of users linked to LDAP accounts,
        the passwords gets updated in the LDAP server rather than updating the local passwords in the odoo database.
        """

        # Check the users can connect with their above defined password in the LDAP mock
        for user, password in [(self.user_demo, "foo"), (self.user_admin, "xyz")]:
            result = self.env["res.users"].authenticate(
                {"login": user.login, "password": password, "type": "password"},
                {"interactive": True},
            )
            self.assertEqual(result["uid"], user.id)

        # Bypass the check identity dialog.
        # When an admin loads the action to change the password of users,
        # he gets presented with the check identity dialog.
        self.mock_check_identity()

        # Trigger the change password action on multiple users
        action = (self.user_demo + self.user_admin).action_change_password_wizard()
        self.assertEqual(
            action["res_model"],
            "change.password.wizard",
            "The expected wizard model when an admin loads the action to change the password of a user",
        )

        # Change the password of each user in the wizard form.
        # `action["context"]` holds the `active_model` and `active_ids` needed for `change.password.wizard`
        # to fill by default the users in the wizard.
        with Form(self.env[action["res_model"]].with_context(**action["context"])) as form:
            for index, (user, new_password) in enumerate([(self.user_demo, "bar"), (self.user_admin, "123")]):
                with form.user_ids.edit(index) as form_line:
                    self.assertEqual(form_line.user_login, user.login)
                    form_line.new_passwd = new_password
        with self.assertLogs("odoo.addons.base.models.res_users") as log_catcher:
            form.record.change_password_button()

        self.assertIn("LDAP password change for 'demo'", log_catcher.output[0])
        self.assertIn("LDAP password change for 'admin'", log_catcher.output[1])

        # The passwords must have been updated in the LDAP server
        for user, new_password in [(self.user_demo, "bar"), (self.user_admin, "123")]:
            self.assertEqual(
                self.ldap_connection_mock._users[f"uid={user.login},dc=example,dc=org"]["password"],
                new_password,
            )

        # Check the users can connect with their new passwords
        for user, password in [(self.user_demo, "bar"), (self.user_admin, "123")]:
            result = self.env["res.users"].authenticate(
                {"login": user.login, "password": password, "type": "password"},
                {"interactive": True},
            )
            self.assertEqual(result["uid"], user.id)

        # Check the users cannot connect with the old password
        for user, password in [(self.user_demo, "foo"), (self.user_admin, "xyz")]:
            with self.assertRaises(AccessDenied):
                self.env["res.users"].authenticate(
                    {"login": user.login, "password": password, "type": "password"},
                    {"interactive": True},
                )

        # The password must not have been set in the "local" database
        self.env.cr.execute(
            "SELECT password FROM res_users WHERE id IN %s",
            [tuple((self.user_demo + self.user_admin).ids)],
        )
        for [password] in self.env.cr.fetchall():
            self.assertFalse(password, "The local password should not have been set")
