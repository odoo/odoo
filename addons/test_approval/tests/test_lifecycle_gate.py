from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestLifecycleGate(ApprovalCommon):
    """Confirming is one operation whichever door it comes through: the button,
    a write of the confirmed state, a create or an import that starts there."""

    def setUp(self):
        super().setUp()
        self.category = self._make_category(
            name=f"Lifecycle Gate Cat {self.id()}",
            approvers=[self.approver_1],
        )
        self.env["ir.access"].create(
            {
                "name": "approval.test.lifecycle clerk",
                "model_id": self.env["ir.model"]._get("approval.test.lifecycle").id,
                "group_id": self.env.ref("base.group_user").id,
                "kind": "permission",
                "operation": "crud",
            }
        )
        self.clerk = self.owner_user
        self.gate = self.env["approval.gate"].search(
            [
                ("model_name", "=", "approval.test.lifecycle"),
                ("operation", "=", "action_confirm"),
            ]
        )

    def _values(self, **values):
        return {
            "name": "Lifecycle",
            "partner_id": self.partner.id,
            "test_category_id": self.category.id,
            **values,
        }

    def _document(self, **values):
        return (
            self.env["approval.test.lifecycle"]
            .with_user(self.clerk)
            .create(self._values(**values))
        )

    def _observed(self, document):
        return self.env["approval.observation"].search(
            [
                ("model_name", "=", "approval.test.lifecycle"),
                ("operation", "=", "action_confirm"),
                ("res_id", "=", document.id),
            ]
        )

    def test_the_confirmed_state_is_a_gate_with_a_switch(self):
        self.assertEqual(len(self.gate), 1, "the registry declares the row")
        self.assertFalse(self.gate.enforced)

    def test_the_button_asks_instead_of_confirming(self):
        document = self._document()
        document.action_confirm()
        self.assertEqual(document.state, "draft")
        self.assertEqual(document.approval_state, "pending")

    def test_writing_the_confirmed_state_is_watched(self):
        document = self._document()
        document.write({"state": "done"})
        self.assertTrue(self._observed(document).would_block)

    def test_writing_the_confirmed_state_is_refused_once_enforced(self):
        self.gate.enforced = True
        document = self._document()
        with self.assertRaises(UserError):
            document.write({"state": "done"})
        with self.assertRaises(UserError):
            document.sudo().write({"state": "done"})
        self.assertEqual(document.state, "draft")
        self.assertFalse(document.approval_request_id)

    def test_creating_in_the_confirmed_state_is_refused_once_enforced(self):
        self.gate.enforced = True
        with self.assertRaises(UserError):
            self._document(state="done")
        with self.assertRaises(UserError):
            self.env["approval.test.lifecycle"].with_user(self.clerk).with_context(
                default_state="done"
            ).create(self._values())

    def test_importing_in_the_confirmed_state_is_refused_once_enforced(self):
        self.gate.enforced = True
        result = (
            self.env["approval.test.lifecycle"]
            .with_user(self.clerk)
            .load(
                ["name", "partner_id/.id", "test_category_id/.id", "state"],
                [["Imported", str(self.partner.id), str(self.category.id), "done"]],
            )
        )
        self.assertFalse(result["ids"])
        self.assertFalse(
            self.env["approval.test.lifecycle"].search([("name", "=", "Imported")])
        )

    def test_a_document_that_needs_no_approval_confirms_by_any_door(self):
        self.gate.enforced = True
        document = self._document(test_category_id=False)
        document.write({"state": "done"})
        self.assertEqual(document.state, "done")
        self.assertTrue(self._document(test_category_id=False, state="done"))

    def test_the_grant_confirms_through_the_gate(self):
        self.gate.enforced = True
        document = self._document()
        document.action_confirm()
        document.approval_request_id.with_user(self.approver_1).action_approve()
        self.assertEqual(document.state, "done")
        self.assertTrue(document.date_confirmed)

    def test_a_batch_confirms_only_what_needs_no_approval(self):
        needs = self._document(name="Needs approval")
        free = self._document(name="Needs none", test_category_id=False)
        (needs | free).action_confirm()
        self.assertEqual(free.state, "done")
        self.assertEqual(needs.state, "draft")
        self.assertEqual(needs.approval_state, "pending")
        self.assertFalse(self._observed(needs))

    def test_a_create_starts_where_the_lifecycle_starts(self):
        Lifecycle = self.env["approval.test.lifecycle"]
        with self.assertRaises(UserError):
            self._document(test_category_id=False, state="closed")
        with self.assertRaises(UserError):
            Lifecycle.with_user(self.clerk).with_context(default_state="closed").create(
                self._values(test_category_id=False)
            )
        self.assertEqual(
            Lifecycle.create(
                self._values(test_category_id=False, state="closed")
            ).state,
            "closed",
            "the superuser may seed a record in any state",
        )
