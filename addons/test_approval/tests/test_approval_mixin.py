from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import add_category_approver


@tagged("post_install", "-at_install")
class TestApprovalMixin(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin_user = cls.env.ref("base.user_admin")
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Mixin Test Approver",
                "login": "mixin_test_approver",
                "email": "mixin_approver@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.test_partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner for Mixin",
                "email": "mixinpartner@test.com",
            }
        )

        cls.test_category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0003",
                "name": "Test Mixin Category",
                "approval_minimum": 1,
                "description": "Category for testing mixin.approval",
            }
        )

        add_category_approver(cls.test_category, cls.approver_user, required=True)

    def _create_test_document(self, **kwargs):
        vals = {
            "name": "Test Document",
            "description": "Test description",
            "amount": 100.0,
            "partner_id": self.test_partner.id,
            "test_category_id": self.test_category.id,
        }
        vals.update(kwargs)
        return self.env["approval.test.document"].create(vals)

    def test_mixin_fields_exist(self):
        doc = self._create_test_document()

        self.assertIn("approval_request_id", doc._fields)
        self.assertIn("approval_state", doc._fields)
        self.assertIn("approval_required", doc._fields)
        self.assertIn("can_request_approval", doc._fields)
        self.assertIn("approval_user_ids", doc._fields)
        self.assertIn("pending_approver_ids", doc._fields)
        self.assertIn("date_approval_requested", doc._fields)
        self.assertIn("date_approval_granted", doc._fields)
        self.assertIn("approval_progress", doc._fields)

    def test_mixin_creates_approval_request(self):
        doc = self._create_test_document()

        self.assertFalse(doc.approval_request_id)

        doc.action_create_approval_request()

        self.assertTrue(doc.approval_request_id)
        self.assertEqual(doc.approval_request_id.state, "pending")
        request = doc.approval_request_id
        self.assertTrue(request.name)
        self.assertTrue(
            request.name.startswith(request.category_id.sequence_id.prefix),
            f"{request.name!r} should carry the category sequence prefix",
        )

    def test_mixin_bidirectional_linking(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        approval = doc.approval_request_id

        self.assertEqual(approval.res_model, "approval.test.document")
        self.assertEqual(approval.res_id, doc.id)

        self.assertEqual(doc.approval_request_id.id, approval.id)

        source = approval.get_source_document()
        self.assertEqual(source, doc)

    def test_mixin_state_synchronization(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        self.assertEqual(doc.approval_state, "pending")

        approval = doc.approval_request_id
        approver = approval.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approval.action_approve(approver)

        self.assertEqual(doc.approval_state, "approved")

    def test_mixin_hook_on_approval_granted(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        self.assertEqual(doc.hook_call_count, 0)

        approval = doc.approval_request_id
        approver = approval.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approval.action_approve(approver)

        doc.invalidate_recordset()
        self.assertEqual(doc.hook_call_count, 1)
        self.assertEqual(doc.last_approval_state, "approved")

        self.assertEqual(doc.state, "approved")

    def test_mixin_hook_on_refusal(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        approval = doc.approval_request_id
        approver = approval.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approval.action_refuse(approver)

        doc.invalidate_recordset()
        self.assertEqual(doc.hook_call_count, 1)
        self.assertEqual(doc.last_approval_state, "refused")
        self.assertEqual(doc.state, "rejected")

    def test_mixin_approval_required_computed(self):
        doc = self._create_test_document()
        self.assertTrue(doc.approval_required)

        doc_no_category = self.env["approval.test.document"].create(
            {
                "name": "No Category Doc",
                "partner_id": self.test_partner.id,
            }
        )
        self.assertFalse(doc_no_category.approval_required)

    def test_mixin_can_request_approval_validation(self):
        doc = self._create_test_document()
        self.assertTrue(doc.can_request_approval)

        doc_missing = self._create_test_document(
            name="Missing Partner",
            partner_id=False,
        )
        self.assertFalse(doc_missing.can_request_approval)

    def test_mixin_action_blocks_when_compute_overridden_for_other_reason(self):
        doc = self._create_test_document()

        def _blocked_compute(records):
            for record in records:
                record.can_request_approval = False

        with patch.object(type(doc), "_compute_can_request_approval", _blocked_compute):
            doc.invalidate_recordset(["can_request_approval"])
            self.assertFalse(doc.can_request_approval)
            with self.assertRaises(UserError):
                doc.action_create_approval_request()

        self.assertFalse(
            doc.approval_request_id,
            "No request should have been created while blocked.",
        )

    def test_mixin_prevents_duplicate_approval_request(self):
        doc = self._create_test_document()

        doc.action_create_approval_request()
        self.assertTrue(doc.approval_request_id)

        with self.assertRaises(UserError) as ctx:
            doc.action_create_approval_request()

        self.assertIn("already exists", str(ctx.exception))

    def test_mixin_action_refuse_approval(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        self.assertEqual(doc.approval_request_id.state, "pending")

        doc.action_refuse_approval()

        self.assertEqual(doc.approval_request_id.state, "refused")
        self.assertEqual(doc.approval_state, "refused")

    def test_clear_refused_link_unlinks(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()
        doc.action_refuse_approval()
        self.assertEqual(doc.approval_state, "refused")

        self.assertTrue(doc.date_approval_requested)

        doc._clear_refused_approval_link()

        self.assertFalse(
            doc.approval_request_id,
            "Refused approval link should be cleared on reopen",
        )
        self.assertFalse(doc.approval_state)
        self.assertFalse(doc.date_approval_requested)
        self.assertFalse(doc.date_approval_granted)

    def test_clear_refused_link_keeps_approved(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()
        approval = doc.approval_request_id
        approver = approval.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user,
        )
        approval.action_approve(approver)
        self.assertEqual(doc.approval_state, "approved")

        doc._clear_refused_approval_link()

        self.assertEqual(
            doc.approval_request_id,
            approval,
            "Approved approval link must be preserved for the audit trail",
        )

    def test_clear_refused_link_keeps_pending(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()
        approval = doc.approval_request_id
        self.assertEqual(doc.approval_state, "pending")

        doc._clear_refused_approval_link()

        self.assertEqual(
            doc.approval_request_id,
            approval,
            "Pending approval link must not be cleared",
        )

    def test_mixin_approval_user_ids_computed(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        self.assertIn(self.approver_user, doc.approval_user_ids)

    def test_mixin_date_tracking(self):
        doc = self._create_test_document()

        self.assertFalse(doc.date_approval_requested)
        self.assertFalse(doc.date_approval_granted)

        doc.action_create_approval_request()

        self.assertTrue(doc.date_approval_requested)

        approval = doc.approval_request_id
        approver = approval.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approval.action_approve(approver)

        doc.invalidate_recordset()
        self.assertTrue(doc.date_approval_granted)

    def test_mixin_approval_progress(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        self.assertEqual(doc.approval_progress, 0.0)

        approval = doc.approval_request_id
        approver = approval.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approval.action_approve(approver)

        doc.invalidate_recordset()
        self.assertEqual(doc.approval_progress, 100.0)

    def test_mixin_pending_approvers(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        self.assertIn(self.approver_user, doc.pending_approver_ids)

        approval = doc.approval_request_id
        approver = approval.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approval.action_approve(approver)

        doc.invalidate_recordset()
        self.assertNotIn(self.approver_user, doc.pending_approver_ids)

    def test_mixin_view_approval_request_action(self):
        doc = self._create_test_document()
        doc.action_create_approval_request()

        action = doc.action_view_approval_request()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "approval.request")
        self.assertEqual(action["res_id"], doc.approval_request_id.id)
        self.assertEqual(action["view_mode"], "form")

    def test_mixin_missing_category_raises_error(self):
        other_category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0004",
                "name": "Other Category",
                "approval_minimum": 1,
            }
        )
        doc = self._create_test_document(
            test_category_id=other_category.id,
        )

        doc.test_category_id = False

        with self.assertRaises(UserError) as ctx:
            doc.action_create_approval_request()

        self.assertIn("No approval category found", str(ctx.exception))

    def test_mixin_missing_required_fields_raises_error(self):
        doc = self._create_test_document(partner_id=False)

        with self.assertRaises(UserError) as ctx:
            doc.action_create_approval_request()

        self.assertIn("required fields", str(ctx.exception).lower())

    def test_mixin_chatter_messages(self):
        doc = self._create_test_document()

        msg_count_before = len(doc.message_ids)

        doc.action_create_approval_request()

        self.assertGreater(len(doc.message_ids), msg_count_before)

        approval = doc.approval_request_id
        approver = approval.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approval.action_approve(approver)

        doc.invalidate_recordset()
        approval_messages = doc.message_ids.filtered(
            lambda m: m.body and ("granted" in m.body.lower() or "\u2713" in m.body)
        )
        self.assertTrue(approval_messages, "Should have approval granted message")

    def test_mixin_can_request_after_cancel(self):
        doc = self._create_test_document()

        doc.action_create_approval_request()
        first_approval = doc.approval_request_id
        doc.action_refuse_approval()

        doc.approval_request_id = False

        doc.action_create_approval_request()
        self.assertTrue(doc.approval_request_id)
        self.assertNotEqual(doc.approval_request_id, first_approval)
