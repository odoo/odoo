from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.base.tests.common import converted_reach


@tagged("post_install", "-at_install")
class TestCannedResponseAdministrator(TransactionCase):
    def test_an_administrator_reaches_every_shared_response(self):
        author = new_test_user(
            self.env, login="canned_author", groups="base.group_user"
        )
        administrator = new_test_user(
            self.env,
            login="canned_administrator",
            groups="base.group_user,mail.group_mail_canned_response_admin",
        )
        Canned = self.env["mail.canned.response"].with_user(author)
        shared = Canned.create(
            {
                "source": "shared-elsewhere",
                "substitution": "Shared with the settings group",
                "group_ids": [self.env.ref("base.group_erp_manager").id],
            }
        )
        private = Canned.create({"source": "private", "substitution": "Only mine"})
        responses = (shared | private).sudo()

        self.assertEqual(
            responses.with_user(administrator).search([("id", "in", responses.ids)]),
            shared,
        )
        for operation in ("read", "write", "unlink"):
            with self.subTest(operation=operation):
                reached = converted_reach(
                    self.env, "mail.canned.response", administrator, operation
                )
                self.assertEqual(reached & responses, shared)
