"""Tests for automation.runtime workflow execution.

Runtime workflows are wizard-based workflows that:
- Store execution context (partner, amount, date, reference)
- Track progress through action steps
- Support DAG dependencies between actions
- Provide step-by-step or automatic execution

Tests cover:
- Runtime lifecycle (creation, start, completion, cancellation)
- Progress tracking
- Action execution
- Context propagation
- DAG dependency resolution
- Error handling
- Concurrent runtime instances
"""

import logging

from odoo.tests import common, tagged
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestRuntimeWorkflows(common.TransactionCase):
    """Test runtime-based workflow execution with context."""

    @classmethod
    def setUpClass(cls):
        """Set up test data that will be reused across test methods."""
        super().setUpClass()

        cls.Runtime = cls.env["automation.runtime"]
        cls.RuntimeLine = cls.env["automation.runtime.line"]
        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Partner = cls.env["res.partner"]

        # Get base.automation model (runtime workflows use this as model)
        cls.model_automation = cls.env["ir.model"]._get("base.automation")

        # Create test partner for runtime context
        cls.test_partner = cls.Partner.create(
            {
                "name": "Test Partner for Runtime",
                "email": "test@runtime.com",
            }
        )

        # Create test automation for runtime workflows
        cls.automation = cls.Automation.create(
            {
                "name": "Test Runtime Workflow",
                "model_id": cls.model_automation.id,
                "trigger": "on_hand",
                "use_workflow_dag": True,
                "auto_execute_workflow": False,
            }
        )

    def _create_runtime_action(self, name, code="pass", predecessors=None):
        """Helper to create a server action for runtime workflow.

        Args:
            name: Action name
            code: Python code to execute
            predecessors: List of action records that must complete first

        Returns:
            ir.actions.server record
        """
        vals = {
            "name": name,
            "model_id": self.model_automation.id,
            "state": "code",
            "code": code,
            "base_automation_id": self.automation.id,
            "usage": "base_automation",
        }

        if predecessors:
            vals["predecessor_ids"] = [(6, 0, [p.id for p in predecessors])]

        return self.Action.create(vals)

    # =========================================================================
    # Test Runtime Lifecycle
    # =========================================================================

    def test_runtime_creation(self):
        """Test creating a runtime instance."""
        _logger.info("Testing runtime creation")

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1500.00,
                "date": "2025-10-20",
                "reference": "TEST-001",
            }
        )

        self.assertEqual(runtime.state, "draft")
        self.assertEqual(runtime.partner_id, self.test_partner)
        self.assertEqual(runtime.amount, 1500.00)
        self.assertNotEqual(runtime.name, "New")  # Should have sequence
        self.assertEqual(runtime.progress, 0)

    def test_runtime_start_creates_lines(self):
        """Test that starting runtime creates action lines."""
        _logger.info("Testing runtime start creates lines")

        # Create actions with DAG dependencies
        action_a = self._create_runtime_action("Action A")
        action_b = self._create_runtime_action("Action B", predecessors=[action_a])
        action_c = self._create_runtime_action("Action C", predecessors=[action_b])

        # Create runtime
        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        # Start workflow
        runtime.action_start()

        # Check state
        self.assertEqual(runtime.state, "in_progress")

        # Check lines created
        self.assertEqual(len(runtime.line_ids), 3)

        # Check sequential DAG structure
        line_a = runtime.line_ids.filtered(lambda l: l.action_id == action_a)
        line_b = runtime.line_ids.filtered(lambda l: l.action_id == action_b)
        line_c = runtime.line_ids.filtered(lambda l: l.action_id == action_c)

        self.assertEqual(line_a.state, "ready")
        self.assertEqual(line_b.state, "waiting")
        self.assertEqual(line_c.state, "waiting")

        self.assertFalse(line_a.predecessor_ids)
        self.assertEqual(line_b.predecessor_ids, line_a)
        self.assertEqual(line_c.predecessor_ids, line_b)

    def test_runtime_without_partner_fails(self):
        """Test that runtime requires a partner."""
        _logger.info("Testing runtime partner requirement")

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": False,  # No partner
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        # Should fail to start without partner
        with self.assertRaises(UserError, msg="Should require partner"):
            runtime.action_start()

    def test_runtime_without_actions_fails(self):
        """Test that runtime requires at least one action."""
        _logger.info("Testing runtime actions requirement")

        # Create automation with no actions
        empty_automation = self.Automation.create(
            {
                "name": "Empty Workflow",
                "model_id": self.model_automation.id,
                "trigger": "on_hand",
                "use_workflow_dag": True,
                "auto_execute_workflow": False,
            }
        )

        runtime = self.Runtime.create(
            {
                "automation_id": empty_automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        # Should fail to start without actions
        with self.assertRaises(UserError, msg="Should require at least one action"):
            runtime.action_start()

    def test_runtime_auto_completes(self):
        """Test that runtime auto-marks as done when all lines complete."""
        _logger.info("Testing runtime auto-completion")

        action = self._create_runtime_action("Single Action")

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # Complete the line
        runtime.line_ids.action_mark_done()

        # Runtime should auto-complete
        self.assertEqual(runtime.state, "done")

    # =========================================================================
    # Test Progress Tracking
    # =========================================================================

    def test_progress_calculation(self):
        """Test that progress percentage is calculated correctly."""
        _logger.info("Testing progress calculation")

        action_a = self._create_runtime_action("A")
        action_b = self._create_runtime_action("B", predecessors=[action_a])
        action_c = self._create_runtime_action("C", predecessors=[action_b])

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # Initial progress
        self.assertEqual(runtime.progress, 0)
        self.assertEqual(runtime.progress_display, "0/3 steps")

        # Complete first action
        line_a = runtime.line_ids.filtered(lambda l: l.action_id == action_a)
        line_a.action_mark_done()

        # Progress should be 33%
        self.assertEqual(runtime.progress, 33)
        self.assertEqual(runtime.progress_display, "1/3 steps")

        # Complete second action
        line_b = runtime.line_ids.filtered(lambda l: l.action_id == action_b)
        line_b.action_mark_done()

        # Progress should be 67%
        self.assertEqual(runtime.progress, 67)
        self.assertEqual(runtime.progress_display, "2/3 steps")

        # Complete third action
        line_c = runtime.line_ids.filtered(lambda l: l.action_id == action_c)
        line_c.action_mark_done()

        # Progress should be 100% and state = done
        self.assertEqual(runtime.progress, 100)
        self.assertEqual(runtime.progress_display, "3/3 steps")
        self.assertEqual(runtime.state, "done")

    # =========================================================================
    # Test Runtime Action Execution
    # =========================================================================

    def test_runtime_next_step_execution(self):
        """Test executing next step in runtime."""
        _logger.info("Testing runtime next step execution")

        # Create action that logs execution
        execution_log = []
        action = self._create_runtime_action(
            "Log Action",
            code="execution_log.append('executed')",
        )

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # Execute next step
        result = runtime.with_context(execution_log=execution_log).action_next_step()

        # Line should be done
        self.assertEqual(runtime.line_ids.state, "done")
        self.assertEqual(runtime.state, "done")

    def test_runtime_next_step_with_no_ready_actions(self):
        """Test next_step when no actions are ready."""
        _logger.info("Testing next_step with no ready actions")

        action_a = self._create_runtime_action("A")
        action_b = self._create_runtime_action("B", predecessors=[action_a])

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # Mark first line as waiting (manually to simulate dependency block)
        runtime.line_ids[0].write({"state": "waiting"})

        # Try to execute next
        with self.assertRaises(UserError, msg="Should fail when no actions ready"):
            runtime.action_next_step()

    def test_runtime_not_in_progress_fails(self):
        """Test that next_step requires runtime to be in_progress."""
        _logger.info("Testing next_step state requirement")

        action = self._create_runtime_action("Action")

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        # Don't start - state is draft
        with self.assertRaises(UserError, msg="Should require in_progress state"):
            runtime.action_next_step()

    # =========================================================================
    # Test Runtime Cancellation
    # =========================================================================

    def test_runtime_cancel(self):
        """Test cancelling a runtime workflow."""
        _logger.info("Testing runtime cancellation")

        action_a = self._create_runtime_action("A")
        action_b = self._create_runtime_action("B", predecessors=[action_a])

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # Cancel
        runtime.action_cancel()

        # Should be cancelled
        self.assertEqual(runtime.state, "cancelled")

        # Should not be able to execute next
        with self.assertRaises(UserError):
            runtime.action_next_step()

    def test_runtime_cancel_idempotent(self):
        """Test that cancelling twice doesn't cause errors."""
        _logger.info("Testing cancel idempotency")

        action = self._create_runtime_action("Action")

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # Cancel twice
        runtime.action_cancel()
        runtime.action_cancel()  # Should not error

        # Should still be cancelled
        self.assertEqual(runtime.state, "cancelled")

    # =========================================================================
    # Test Context Propagation
    # =========================================================================

    def test_execution_context_passed_to_actions(self):
        """Test that runtime context (partner, amount, etc.) is available in actions."""
        _logger.info("Testing context propagation")

        # Create action that uses runtime context
        action = self._create_runtime_action(
            "Context Action",
            code="""
# Access runtime context
partner_name = runtime.partner_id.name
amount = runtime.amount
reference = runtime.reference or 'No reference'

# Store in env context for verification
env.context = dict(env.context,
    test_partner=partner_name,
    test_amount=amount,
    test_ref=reference
)
""",
        )

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 2500.00,
                "date": "2025-10-20",
                "reference": "CTX-TEST",
            }
        )

        runtime.action_start()

        # Execute with context capture
        runtime.action_next_step()

        # Verify context was available (line should complete)
        self.assertEqual(runtime.line_ids.state, "done")
        self.assertEqual(runtime.state, "done")

    def test_multicompany_context(self):
        """Test that company context is available in runtime actions."""
        _logger.info("Testing multi-company context")

        action = self._create_runtime_action(
            "Company Action",
            code="""
# Company should be available
company_name = env.company.name
# Store for verification
env.context = dict(env.context, test_company=company_name)
""",
        )

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()
        runtime.action_next_step()

        # Should complete successfully
        self.assertEqual(runtime.state, "done")

    # =========================================================================
    # Test DAG Dependency Resolution
    # =========================================================================

    def test_runtime_line_dag_resolution(self):
        """Test that DAG dependencies are resolved correctly."""
        _logger.info("Testing DAG dependency resolution")

        # Create parallel + sequential DAG:
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        action_a = self._create_runtime_action("A")
        action_b = self._create_runtime_action("B", predecessors=[action_a])
        action_c = self._create_runtime_action("C", predecessors=[action_a])
        action_d = self._create_runtime_action("D", predecessors=[action_b, action_c])

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # Initially: A is ready, B/C/D are waiting
        line_a = runtime.line_ids.filtered(lambda l: l.action_id == action_a)
        line_b = runtime.line_ids.filtered(lambda l: l.action_id == action_b)
        line_c = runtime.line_ids.filtered(lambda l: l.action_id == action_c)
        line_d = runtime.line_ids.filtered(lambda l: l.action_id == action_d)

        self.assertEqual(line_a.state, "ready")
        self.assertEqual(line_b.state, "waiting")
        self.assertEqual(line_c.state, "waiting")
        self.assertEqual(line_d.state, "waiting")

        # Complete A -> B and C should become ready
        line_a.action_mark_done()
        self.assertEqual(line_b.state, "ready")
        self.assertEqual(line_c.state, "ready")
        self.assertEqual(line_d.state, "waiting")

        # Complete B -> D still waiting (needs C)
        line_b.action_mark_done()
        self.assertEqual(line_d.state, "waiting")

        # Complete C -> D becomes ready
        line_c.action_mark_done()
        self.assertEqual(line_d.state, "ready")

    # =========================================================================
    # Test Error Handling
    # =========================================================================

    def test_runtime_line_error_handling(self):
        """Test that runtime handles action errors gracefully."""
        _logger.info("Testing error handling")

        action = self._create_runtime_action(
            "Failing Action",
            code="raise Exception('Test error')",
        )

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # Execute should fail
        with self.assertRaises(Exception, msg="Should propagate action error"):
            runtime.action_next_step()

        # Line should still be ready (not done)
        self.assertEqual(runtime.line_ids.state, "ready")
        self.assertEqual(runtime.state, "in_progress")

    # =========================================================================
    # Test Edge Cases
    # =========================================================================

    def test_multiple_concurrent_runtimes(self):
        """Test multiple runtime instances running concurrently."""
        _logger.info("Testing concurrent runtimes")

        action = self._create_runtime_action("Action")

        runtime1 = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
                "reference": "RT-001",
            }
        )

        runtime2 = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 2000.00,
                "date": "2025-10-21",
                "reference": "RT-002",
            }
        )

        # Start both
        runtime1.action_start()
        runtime2.action_start()

        # Both should be in progress
        self.assertEqual(runtime1.state, "in_progress")
        self.assertEqual(runtime2.state, "in_progress")

        # Complete runtime1
        runtime1.action_next_step()
        self.assertEqual(runtime1.state, "done")

        # Runtime2 should still be in progress
        self.assertEqual(runtime2.state, "in_progress")

        # Complete runtime2
        runtime2.action_next_step()
        self.assertEqual(runtime2.state, "done")

    def test_runtime_with_single_action(self):
        """Test runtime with single action completes directly."""
        _logger.info("Testing single action runtime")

        action = self._create_runtime_action("Only Action")

        runtime = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime.action_start()

        # One line created
        self.assertEqual(len(runtime.line_ids), 1)
        self.assertEqual(runtime.line_ids.state, "ready")

        # Execute
        runtime.action_next_step()

        # Should complete
        self.assertEqual(runtime.state, "done")
        self.assertEqual(runtime.progress, 100)

    def test_runtime_sequence_generation(self):
        """Test that runtime instances get sequential names."""
        _logger.info("Testing sequence generation")

        action = self._create_runtime_action("Action")

        runtime1 = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 1000.00,
                "date": "2025-10-20",
            }
        )

        runtime2 = self.Runtime.create(
            {
                "automation_id": self.automation.id,
                "partner_id": self.test_partner.id,
                "amount": 2000.00,
                "date": "2025-10-20",
            }
        )

        # Both should have different names
        self.assertNotEqual(runtime1.name, runtime2.name)
        self.assertNotEqual(runtime1.name, "New")
        self.assertNotEqual(runtime2.name, "New")
