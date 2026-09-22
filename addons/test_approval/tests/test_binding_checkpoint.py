from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestBindingCheckpoint(ApprovalCommon):
    """A binding on an operation holds on every path its model says the operation crosses.

    `approval.test.document` declares that `action_record_operation` and
    `action_record_operation_from_list` both cross `_check_record_operation`, the
    way `account.move` declares that every posting path crosses
    `_post_check_business_rules`.
    """

    def setUp(self):
        super().setUp()
        self.category = self._make_category(
            name=f"Checkpoint Cat {self.id()}",
            approvers=[self.approver_1],
        )
        self.doc = self._document("Checkpointed")
        self.binding = self.env["approval.binding"].create(
            {
                "model_id": self.env["ir.model"]._get("approval.test.document").id,
                "method": "action_record_operation",
                "mode": "block",
                "category_id": self.category.id,
                "sudo_policy": "enforce",
            },
        )

    def tearDown(self):
        self.env["approval.binding"]._unregister_hook()
        super().tearDown()

    def _document(self, name):
        return self.env["approval.test.document"].create(
            {
                "name": name,
                "partner_id": self.partner.id,
                "test_category_id": self.category.id,
            },
        )

    def _approve(self, document):
        document.action_create_approval_request()
        document.approval_request_id.with_user(self.approver_1).action_approve()

    def test_another_path_through_the_checkpoint_is_gated(self):
        with self.assertRaises(UserError):
            self.doc.action_record_operation_from_list()
        self.assertEqual(self.doc.operation_count, 0)

    def test_an_approved_record_passes_on_every_path(self):
        self._approve(self.doc)
        self.doc.action_record_operation()
        self.doc.action_record_operation_from_list()
        self.assertEqual(self.doc.operation_count, 2)

    def test_request_mode_refuses_at_the_checkpoint_instead_of_asking(self):
        self.binding.mode = "request"
        with self.assertRaises(UserError):
            self.doc.action_record_operation_from_list()
        self.assertFalse(
            self.doc.approval_request_id, "a checkpoint cannot keep a request"
        )

    def test_the_entry_point_is_observed_once_not_again_at_its_checkpoint(self):
        self.binding.mode = "advise"
        self.doc.action_record_operation()
        self.assertEqual(self.doc.operation_count, 1)
        self.assertEqual(len(self.binding.observation_ids), 1)

    def test_admitting_one_record_does_not_admit_another(self):
        other = self._document("Posted inside an admitted call")
        with self.assertRaises(UserError):
            self.env["approval.binding"]._run_admitted(
                self.doc,
                "action_record_operation",
                lambda admitted: other.action_record_operation_from_list(),
            )
        self.assertEqual(other.operation_count, 0)

    def test_a_forged_admission_in_the_context_admits_nothing(self):
        forged = self.doc.with_context(
            approval_binding_admitted=[
                ["approval.test.document", "action_record_operation", [self.doc.id]]
            ]
        )
        with self.assertRaises(UserError):
            forged.action_record_operation_from_list()
        self.assertEqual(self.doc.operation_count, 0)
