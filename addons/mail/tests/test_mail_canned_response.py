# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, HttpCase
from odoo import Command


@tagged("mail_canned_response", "post_install", "-at_install")
class TestCannedResponse(MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.canned_response = cls.env["mail.canned.response"].with_user(cls.user_employee).create({
            "source": "hlp",
            "substitution": "help",
        })
        cls.canned_response_system = cls.env["mail.canned.response"].with_user(cls.user_admin).create({
            "source": "hlp",
            "substitution": "help",
            'group_ids': [Command.set([cls.env.ref('base.group_system').id])],
        })
        cls.canned_response_group_user_by_admin = cls.env["mail.canned.response"].with_user(cls.user_admin).create({
            "source": "hlp",
            "substitution": "help",
            "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
        })
        cls.canned_response_group_user = cls.env["mail.canned.response"].with_user(cls.user_employee).create({
            "source": "hlp",
            "substitution": "help",
            "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
        })

    def test_user_canned_response(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        request = self.make_jsonrpc_request("/mail/data", {"canned_responses": True})
        self.assertEqual(len(request["CannedResponse"]), 3)

    def test_canned_response_permissions(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        self.canned_response.with_user(self.user_employee).write({"source": "help"})
        self.assertEqual(self.canned_response.source, "help")
        self.canned_response_group_user.with_user(self.user_employee).write({"source": "help"})
        self.assertEqual(self.canned_response_group_user.source, "help")
        with self.assertRaises(AccessError):
            self.canned_response_group_user_by_admin.with_user(self.user_employee).write({"source": "test"})
        with self.assertRaises(AccessError):
            self.canned_response_group_user_by_admin.with_user(self.user_employee).unlink()
