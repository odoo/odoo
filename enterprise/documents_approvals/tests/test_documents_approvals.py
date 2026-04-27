# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import mail_new_test_user


class TestDocumentApprovals(TransactionCase):

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_documents_access(self):
        approval_user = mail_new_test_user(
            self.env,
            "approval_user",
            "approvals.group_approval_user,base.group_user",
        )
        internal_user_1 = mail_new_test_user(
            self.env, "internal_user_1", "base.group_user"
        )
        internal_user_2 = mail_new_test_user(
            self.env, "internal_user_2", "base.group_user"
        )
        self.env.company.documents_approvals_settings = True
        self.env["documents.access"].create({
            "document_id": self.env.company.approvals_folder_id.id,
            "partner_id": approval_user.partner_id.id,
            "role": "edit",
        })

        approval = self.env["approval.request"].create(
            {
                "request_owner_id": internal_user_1.id,
                "category_id": self.env["approval.category"].create({"name": "cat"}).id,
            }
        )

        attachment = self.env["ir.attachment"].with_user(approval_user).create({
            "name": "Test document",
            "res_id": approval.id,
            "res_model": "approval.request",
        })
        document = self.env["documents.document"].search([("attachment_id", "=", attachment.id)])
        self.assertEqual(len(document), 1)
        self.assertEqual(len(document.access_ids), 2)
        access_id_by_partner = document.access_ids.grouped('partner_id')
        internal_user_1_access = access_id_by_partner.get(internal_user_1.partner_id)
        self.assertTrue(internal_user_1_access)
        self.assertEqual(internal_user_1_access.role, 'view')
        access_id_approval_user = access_id_by_partner.get(approval_user.partner_id)
        self.assertTrue(access_id_approval_user)
        self.assertIn(access_id_approval_user.role, {'edit', False})
        self.assertEqual(document.owner_id, approval_user)

        document.with_user(internal_user_1).read()
        document.with_user(approval_user).read()

        with self.assertRaises(AccessError):
            document.with_user(internal_user_2).read()
