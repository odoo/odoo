from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestTestDocumentIsNotProductionSurface(ApprovalCommon):
    def test_plain_internal_user_cannot_create_the_test_document(self):
        plain = self.env["res.users"].create(
            {
                "name": "Plain Internal",
                "login": "sec_plain_internal",
                "email": "plain@sec.test",
            },
        )
        with self.assertRaises(AccessError):
            self.env["approval.test.document"].with_user(plain).create(
                {"name": "should not be reachable"},
            )

    def test_the_test_document_has_no_access_row_at_all(self):
        acl = self.env["ir.access"].search(
            [
                ("model_id.model", "=", "approval.test.document"),
                ("kind", "=", "permission"),
            ],
        )
        self.assertFalse(
            acl,
            "approval.test.document must carry no ir.access permission: this "
            "module ships none, and the fixture is reached as superuser or "
            "as a manager. Found: %s" % acl.mapped("name"),
        )
