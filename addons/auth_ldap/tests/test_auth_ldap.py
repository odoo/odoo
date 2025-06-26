import re
import requests
from unittest.mock import patch

import odoo
from odoo.modules.registry import Registry, DummyRLock
from odoo.tests.common import BaseCase, tagged, get_db_name


@tagged("-standard", "-at_install", "post_install", "database_breaking")
class TestAuthLDAP(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = Registry(get_db_name())

    def setUp(self):
        super().setUp()
        self.patch(Registry, "_lock", DummyRLock())  # prevent deadlock (see #161438)
        self.opener = requests.Session()

        def remove_ldap_user():
            with self.registry.cursor() as cr:
                cr.execute("DELETE FROM res_users WHERE login = 'test_ldap_user'")
        self.addCleanup(remove_ldap_user)

    def test_auth_ldap(self):
        def _get_ldap_dicts(*args, **kwargs):
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
                    "user": (6, "Marc Demo"),
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

        with self.registry.cursor() as cr:
            cr.execute("SELECT id FROM res_users WHERE login = 'test_ldap_user'")
            self.assertFalse(cr.rowcount, "User should not be present")

        body = self.url_open("/web/login").text
        csrf = re.search(r'csrf_token: "(\w*?)"', body).group(1)

        with patch.object(self.registry["res.company.ldap"], "_get_ldap_dicts", _get_ldap_dicts),\
            patch.object(self.registry["res.company.ldap"], "_authenticate", _authenticate):
            res = self.opener.post(
                f"{self.base_url()}/web/login",
                data={
                    "login": "test_ldap_user",
                    "password": "test",
                    "csrf_token": csrf,
                },
            )
            res.raise_for_status()

        session = odoo.http.root.session_store.get(res.cookies["session_id"])
        self.assertEqual(
            session.sid, res.cookies["session_id"], "A session must exist at this point")

        with self.registry.cursor() as cr:
            cr.execute(
                "SELECT id FROM res_users WHERE login = %s and id = %s",
                ("test_ldap_user", session.uid))
            self.assertTrue(cr.rowcount, "User should be present")
