# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, HttpCase
from odoo import Command


@tagged("mail_canned_response", "post_install", "-at_install")
class TestCannedResponse(MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # admin is system but no canned response admin
        cls.user_admin.write({"groups_id": [(3, cls.env.ref("mail.group_mail_canned_response_admin").id)]})
        # response admin
        cls.response_admin = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            groups='base.group_user,mail.group_mail_canned_response_admin',
            login='response_admin',
            name='Response Admin',
        )

        cls.response_user, cls.response_user_group_user = cls.env["mail.canned.response"].with_user(cls.user_employee).create([
            {
                "source": "hlp1",
                "substitution": "help1",
            },
            {
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
                "source": "hlp2",
                "substitution": "help2",
            },
        ])
        cls.response_admin_group_system, cls.response_admin_group_user = cls.env["mail.canned.response"].with_user(cls.user_admin).create([
            {
                'group_ids': [Command.set([cls.env.ref('base.group_system').id])],
                "source": "hlp3",
                "substitution": "help3",
            },
            {
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
                "source": "hlp4",
                "substitution": "help4",
            },
        ])
        cls.response_all = (cls.response_user + cls.response_user_group_user + cls.response_admin_group_system + cls.response_admin_group_user).sudo()

    def test_controller_mail_data_canned_response(self):
        """ Check returned canned responses in '/mail/data' contains personal
        answers or the one linked to the user group """
        for test_user, expected_responses in [
            (
                self.user_employee,
                self.response_admin_group_user + self.response_user_group_user + self.response_user
            ),
            (
                self.user_admin,
                # response_user is limited to creator, even admin does not receive it
                self.response_admin_group_user + self.response_admin_group_system + self.response_user_group_user
            ),
            (
                self.response_admin,
                # even with full access, see only own + groups
                self.response_admin_group_user + self.response_user_group_user
            ),
        ]:
            with self.subTest(user_login=test_user.login):
                self.authenticate(test_user.login, test_user.login)
                request = self.make_jsonrpc_request("/mail/data", {"canned_responses": True})
                expected_content = [
                    {
                        'id': cr.id,
                        'source': cr.source,
                        'substitution': cr.substitution
                    } for cr in expected_responses
                ]
                self.assertListEqual(request["CannedResponse"], expected_content)

    def test_mail_canned_response_permissions(self):
        """ Test ACLs and security on 'mail.canned.response' model, notably that
        group_ids restrict edition """
        for test_user, write_ok in [
            (self.user_employee, self.response_user + self.response_user_group_user),
            (self.user_admin, self.response_admin_group_system + self.response_admin_group_user),
            (self.response_admin, self.response_all),
        ]:
            for canned_response in self.response_all:
                with self.subTest(user_login=test_user.login, response_name=canned_response.source):
                    canned_response_as_user = canned_response.with_user(test_user)
                    if canned_response in write_ok:
                        canned_response_as_user.write({"substitution": f"{canned_response.source} UPDATED"})
                    else:
                        with self.assertRaises(AccessError):
                            canned_response_as_user.write({"substitution": f"{canned_response.source} UPDATED"})

        employee_unlink_ok = self.response_user + self.response_user_group_user
        for canned_response in self.response_all:
            with self.subTest(response_name=canned_response.source):
                canned_response_as_user = canned_response.with_user(self.user_employee)
                if canned_response in employee_unlink_ok:
                    canned_response_as_user.unlink()
                else:
                    with self.assertRaises(AccessError):
                        canned_response_as_user.unlink()
