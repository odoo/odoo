# Part of Odoo. See LICENSE file for full copyright and licensing details.
from itertools import product

import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestAttachmentController(MailControllerAttachmentCommon):
    def test_independent_attachment_delete(self):
        """Test access to delete an attachment"""
        self._execute_subtests_delete(
            product(
                (self.guest, self.user_employee, self.user_portal, self.user_public),
                (self.WITH_TOKEN, self.NO_TOKEN),
            ),
            allowed=False,
        )
        self._execute_subtests_delete(
            product(self.user_admin, (self.WITH_TOKEN, self.NO_TOKEN)),
            allowed=True,
        )

    def test_attachment_delete_linked_to_public_thread(self):
        """Test access to delete an attachment associated with a public thread"""
        thread = self.env["mail.test.access.public"].create({"name": "Test"})
        self._execute_subtests_delete(
            product(
                (self.guest, self.user_portal, self.user_public),
                (self.WITH_TOKEN, self.NO_TOKEN),
            ),
            allowed=False,
            thread=thread,
        )
        self._execute_subtests_delete(
            product(
                (self.user_admin, self.user_employee),
                (self.WITH_TOKEN, self.NO_TOKEN),
            ),
            allowed=True,
            thread=thread,
        )

    def test_attachment_delete_linked_to_non_accessible_thread(self):
        """Test access to delete an attachment associated with a non-accessible thread"""
        thread = self.env["mail.test.access"].create({"access": "admin", "name": "Test"})
        self._execute_subtests_delete(
            product(
                (self.guest, self.user_employee, self.user_portal, self.user_public),
                (self.WITH_TOKEN, self.NO_TOKEN),
            ),
            allowed=False,
            thread=thread,
        )
        self._execute_subtests_delete(
            product(self.user_admin, (self.WITH_TOKEN, self.NO_TOKEN)),
            allowed=True,
            thread=thread,
        )

    def test_attachment_delete_linked_to_message(self):
        """Test access to delete an attachment associated with a message"""
        message = self.env["mail.message"].create({"body": "Test"})
        # Subtest format: (user, token, {"author": message author})
        author, no_author = {"author": "self_author"}, {}
        self._execute_subtests_delete(
            product(
                (self.guest, self.user_employee, self.user_portal, self.user_public),
                (self.WITH_TOKEN, self.NO_TOKEN),
                (author, no_author),
            ),
            allowed=False,
            message=message,
        )
        self._execute_subtests_delete(
            product(
                self.user_admin,
                (self.WITH_TOKEN, self.NO_TOKEN),
                (author, no_author),
            ),
            allowed=True,
            message=message,
        )

    def test_attachment_delete_linked_to_message_in_thread(self):
        """Test access to delete an attachment associated with a message in an accessible thread"""
        message = self.env["mail.message"].create({"body": "Test"})
        thread = self.env["mail.test.access.public"].create({"name": "Test"})
        author, no_author = {"author": "self_author"}, {}
        # (user(s), author or not, expected result)
        test_cases = [
            ((self.user_admin, self.user_employee), (author, no_author), True),
            ((self.guest, self.user_portal), (author,), True),
            ((self.guest, self.user_portal), (no_author,), False),
            (self.user_public, (author, no_author), False),
        ]

        for users, author_config, allowed in test_cases:
            # Subtest format: (user, token, {"author": message author})
            self._execute_subtests_delete(
                product(users, (self.WITH_TOKEN, self.NO_TOKEN), author_config),
                allowed=allowed,
                message=message,
                thread=thread,
            )

    def test_upload_multi_company(self):
        record = self.user_employee.partner_id
        record.company_id = self.user_employee.company_id
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.assertTrue(record.company_id)  # Ensure the thread has a company
        test_cases = [
            ({}, self.user_employee.company_id),
            (
                {
                    "cookies": {
                        "cids": f"{self.company_2.id}-{self.company_3.id}",
                    },
                },
                self.company_2,
            ),
            (
                {
                    "cookies": {
                        "cids": f"{self.company_2.id}-{self.user_admin.company_id.id}",
                    },
                },
                self.user_admin.company_id,
            ),
        ]
        for kwargs, expected_company in test_cases:
            with self.subTest(expected_company=expected_company):
                record.company_id = False if kwargs else record.company_id
                attachment = self.env["ir.attachment"].browse(
                    self._upload_attachment(record, kwargs)
                )
                self.assertEqual(attachment.company_id, expected_company)
