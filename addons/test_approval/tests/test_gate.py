from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestApprovalGate(ApprovalCommon):
    """A document gates its own terminal transitions, one grant per operation."""

    def setUp(self):
        super().setUp()
        self.category = self._make_category(
            name=f"Gate Cat {self.id()}",
            approvers=[self.approver_1],
        )

    def _document(self, name="Gated", amount=100.0, **values):
        return self.env["approval.test.gated"].create(
            {
                "name": name,
                "partner_id": self.partner.id,
                "amount_total": amount,
                "test_category_id": self.category.id,
                **values,
            }
        )

    def _approve(self, document):
        document.approval_request_id.with_user(self.approver_1).action_approve()

    def _enforce(self, operation):
        gate = self.env["approval.gate"].search(
            [("model_name", "=", "approval.test.gated"), ("operation", "=", operation)]
        )
        self.assertEqual(len(gate), 1, "the registry declares this gate")
        gate.enforced = True
        return gate

    def test_the_operation_asks_instead_of_running(self):
        document = self._document()
        document.action_ship()
        self.assertEqual(document.ship_count, 0)
        self.assertEqual(document.approval_state, "pending")
        self.assertEqual(document.approval_request_id.operation, "action_ship")
        with self.assertRaises(UserError):
            document.action_ship()

    def test_the_grant_runs_the_operation_once(self):
        document = self._document()
        document.action_ship()
        self._approve(document)
        self.assertEqual(document.ship_count, 1)
        self.assertEqual(document.state, "shipped")
        self.assertTrue(document.approval_request_id.date_operation_run)
        document.approval_request_id.with_user(self.approver_1).action_withdraw()
        self._approve(document)
        self.assertEqual(document.ship_count, 1)

    def test_a_grant_that_does_not_run_leaves_the_operation_to_its_caller(self):
        document = self._document(runs_on_approval=False)
        document.action_ship()
        self._approve(document)
        self.assertEqual(document.ship_count, 0)
        document.action_ship()
        self.assertEqual(document.ship_count, 1)

    def test_a_grant_clears_the_operation_it_was_asked_for_and_no_other(self):
        document = self._document(runs_on_approval=False)
        document.action_ship()
        self._approve(document)
        with self.assertRaises(UserError):
            document.action_bill()
        self.assertEqual(document.bill_count, 0)

    def test_a_document_changed_after_its_grant_is_refused(self):
        document = self._document(runs_on_approval=False)
        document.action_ship()
        self._approve(document)
        document.sudo().amount_total = 400.0
        with self.assertRaises(UserError):
            document.action_ship()
        self.assertEqual(document.ship_count, 0)

    def test_what_needs_no_approval_goes_through_beside_what_does(self):
        gated = self._document("Gated one")
        plain = self._document("Plain one", test_category_id=False)
        (gated | plain).action_ship()
        self.assertEqual(plain.ship_count, 1)
        self.assertEqual(gated.ship_count, 0)
        self.assertEqual(gated.approval_state, "pending")

    def test_another_path_is_watched_before_it_is_held(self):
        document = self._document()
        document.action_ship()
        Observation = self.env["approval.observation"]
        before = Observation.search_count([])
        document.action_ship_from_elsewhere()
        self.assertEqual(document.ship_count, 1, "the watching gate refuses nothing")
        observed = Observation.search([], order="id desc", limit=1)
        self.assertEqual(Observation.search_count([]), before + 1)
        self.assertRecordValues(
            observed,
            [
                {
                    "model_name": "approval.test.gated",
                    "operation": "action_ship",
                    "res_id": document.id,
                    "would_block": True,
                }
            ],
        )

    def test_another_path_is_refused_once_the_gate_is_enforced(self):
        self._enforce("action_ship")
        document = self._document()
        document.action_ship()
        with self.assertRaises(UserError):
            document.action_ship_from_elsewhere()
        self.assertEqual(document.ship_count, 0)

    def test_the_gate_admits_what_it_let_through(self):
        self._enforce("action_ship")
        document = self._document(test_category_id=False)
        document.action_ship()
        self.assertEqual(document.ship_count, 1)

    def test_only_an_operation_with_a_checkpoint_gets_a_row(self):
        gates = self.env["approval.gate"].search(
            [("model_name", "=", "approval.test.gated")]
        )
        self.assertEqual(
            set(gates.mapped("operation")),
            {"action_ship"},
            "the registry declares the row and nobody created it -- and action_bill "
            "names no checkpoint, so enforcing it could close no path and it is "
            "given no switch that would govern nothing",
        )
        self.assertFalse(
            gates.filtered("enforced"),
            "a gate starts out watching, so shipping the code changes nothing",
        )

    def test_enforcing_one_operation_leaves_the_other_watching(self):
        self._enforce("action_ship")
        document = self._document()

        self.assertTrue(document._is_approval_gate_enforced("action_ship"))
        self.assertFalse(
            document._is_approval_gate_enforced("action_bill"),
            "a gate is switched on per operation, so a cheap one need not wait "
            "for an expensive one",
        )

        document.action_ship()
        with self.assertRaises(UserError):
            document.action_ship_from_elsewhere()

    def test_the_count_beside_a_gate_is_its_own(self):
        document = self._document()
        document.action_ship()
        document.action_ship_from_elsewhere()

        ship = self.env["approval.gate"].search(
            [
                ("model_name", "=", "approval.test.gated"),
                ("operation", "=", "action_ship"),
            ]
        )
        self.assertEqual(ship.would_block_count, 1)

        self.env["approval.observation"].sudo().create(
            {
                "model_name": "approval.test.gated",
                "operation": "action_elsewhere",
                "res_id": document.id,
                "elevation": "none",
                "would_block": True,
            }
        )
        ship.invalidate_recordset(["would_block_count"])
        self.assertEqual(
            ship.would_block_count,
            1,
            "a gate counts what reached its own operation, not its neighbour's",
        )

    def test_a_database_that_was_enforcing_globally_keeps_enforcing(self):
        parameters = self.env["ir.config_parameter"].sudo()
        parameters.set_param("approval.gate_enforced", "1")

        self.env["approval.gate"]._adopt_legacy_enforcement()

        gates = self.env["approval.gate"].search(
            [("model_name", "=", "approval.test.gated")]
        )
        self.assertTrue(
            all(gates.mapped("enforced")),
            "the single switch meant every gate, so every gate keeps it",
        )
        self.assertFalse(
            parameters.search([("key", "=", "approval.gate_enforced")]),
            "and the superseded parameter is gone, so it cannot disagree later",
        )
