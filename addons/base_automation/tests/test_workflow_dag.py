# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for DAG workflow functionality in base_automation."""

import logging

from odoo import Command
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TestWorkflowDAG(TransactionCase):
    """Test DAG dependency and orchestration features."""

    def setUp(self):
        super().setUp()
        self.Automation = self.env["base.automation"]
        self.Action = self.env["ir.actions.server"]
        self.Partner = self.env["res.partner"]

        # Get partner model
        self.model_partner = self.env["ir.model"]._get("res.partner")

        # Create test automation with workflow DAG enabled
        self.automation = self.Automation.create(
            {
                "name": "Test DAG Workflow",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
                "use_workflow_dag": True,
                "auto_execute_workflow": False,  # Manual execution for testing
            }
        )

    def _create_action(self, name, code="pass", predecessors=None):
        """Helper to create a server action.

        Args:
            name: Action name
            code: Python code to execute
            predecessors: List of action records that must complete first

        Returns:
            ir.actions.server record
        """
        vals = {
            "name": name,
            "model_id": self.model_partner.id,
            "state": "code",
            "code": code,
            "base_automation_id": self.automation.id,
            "usage": "base_automation",
        }

        if predecessors:
            vals["predecessor_ids"] = [Command.set([p.id for p in predecessors])]

        return self.Action.create(vals)

    # =========================================================================
    # Test Basic Dependency Chain
    # =========================================================================

    def test_simple_linear_chain(self):
        """Test simple A → B → C linear dependency chain."""
        _logger.info("Testing simple linear chain A → B → C")

        action_a = self._create_action("Action A")
        action_b = self._create_action("Action B", predecessors=[action_a])
        action_c = self._create_action("Action C", predecessors=[action_b])

        # Reset workflow
        self.automation.action_reset_workflow()

        # Check initial state
        self.assertEqual(
            action_a.action_state, "ready", "A should be ready (no predecessors)"
        )
        self.assertEqual(action_b.action_state, "waiting", "B should be waiting for A")
        self.assertEqual(action_c.action_state, "waiting", "C should be waiting for B")

        self.assertTrue(action_a.is_ready, "A is_ready should be True")
        self.assertFalse(action_b.is_ready, "B is_ready should be False")
        self.assertFalse(action_c.is_ready, "C is_ready should be False")

        # Complete action A
        action_a.action_mark_done()

        # Check that B is now ready
        self.assertEqual(action_a.action_state, "done", "A should be done")
        self.assertEqual(
            action_b.action_state, "ready", "B should be ready after A completes"
        )
        self.assertEqual(action_c.action_state, "waiting", "C still waiting for B")

        self.assertTrue(action_b.is_ready, "B is_ready should be True")
        self.assertFalse(action_c.is_ready, "C is_ready should be False")

        # Complete action B
        action_b.action_mark_done()

        # Check that C is now ready
        self.assertEqual(action_b.action_state, "done", "B should be done")
        self.assertEqual(
            action_c.action_state, "ready", "C should be ready after B completes"
        )

        self.assertTrue(action_c.is_ready, "C is_ready should be True")

        # Complete action C
        action_c.action_mark_done()

        self.assertEqual(action_c.action_state, "done", "C should be done")

    # =========================================================================
    # Test Parallel Execution
    # =========================================================================

    def test_parallel_branches(self):
        """Test parallel branches: A → B and A → C execute in parallel."""
        _logger.info("Testing parallel branches")

        action_a = self._create_action("Action A")
        action_b = self._create_action("Action B", predecessors=[action_a])
        action_c = self._create_action("Action C", predecessors=[action_a])

        # Reset workflow
        self.automation.action_reset_workflow()

        # Only A should be ready
        self.assertEqual(action_a.action_state, "ready")
        self.assertEqual(action_b.action_state, "waiting")
        self.assertEqual(action_c.action_state, "waiting")

        # Complete A
        action_a.action_mark_done()

        # Both B and C should be ready (parallel execution)
        self.assertEqual(action_b.action_state, "ready", "B should be ready after A")
        self.assertEqual(action_c.action_state, "ready", "C should be ready after A")

        self.assertTrue(action_b.is_ready, "B can execute in parallel with C")
        self.assertTrue(action_c.is_ready, "C can execute in parallel with B")

    def test_diamond_pattern(self):
        """Test diamond dependency: A → B,C → D (D waits for both B and C)."""
        _logger.info("Testing diamond pattern")

        action_a = self._create_action("Action A")
        action_b = self._create_action("Action B", predecessors=[action_a])
        action_c = self._create_action("Action C", predecessors=[action_a])
        action_d = self._create_action("Action D", predecessors=[action_b, action_c])

        # Reset workflow
        self.automation.action_reset_workflow()

        # Only A should be ready
        self.assertTrue(action_a.is_ready)
        self.assertFalse(action_d.is_ready)

        # Complete A
        action_a.action_mark_done()

        # B and C should be ready, but not D
        self.assertEqual(action_b.action_state, "ready")
        self.assertEqual(action_c.action_state, "ready")
        self.assertEqual(action_d.action_state, "waiting")
        self.assertFalse(action_d.is_ready, "D needs both B and C to complete")

        # Complete B
        action_b.action_mark_done()

        # D still not ready (waiting for C)
        self.assertEqual(action_d.action_state, "waiting")
        self.assertFalse(action_d.is_ready, "D still needs C to complete")

        # Complete C
        action_c.action_mark_done()

        # Now D is ready
        self.assertEqual(action_d.action_state, "ready")
        self.assertTrue(action_d.is_ready, "D is ready after both B and C complete")

    # =========================================================================
    # Test Cycle Detection
    # =========================================================================

    def test_cycle_detection_direct(self):
        """Test that direct cycles are prevented: A → B → A."""
        _logger.info("Testing direct cycle detection")

        action_a = self._create_action("Action A")
        action_b = self._create_action("Action B", predecessors=[action_a])

        # Try to create cycle: A depends on B
        with self.assertRaises(
            ValidationError, msg="Should prevent direct cycle A → B → A"
        ):
            action_a.write({"predecessor_ids": [Command.link(action_b.id)]})

    def test_cycle_detection_indirect(self):
        """Test that indirect cycles are prevented: A → B → C → A."""
        _logger.info("Testing indirect cycle detection")

        action_a = self._create_action("Action A")
        action_b = self._create_action("Action B", predecessors=[action_a])
        action_c = self._create_action("Action C", predecessors=[action_b])

        # Try to create cycle: A depends on C
        with self.assertRaises(
            ValidationError, msg="Should prevent indirect cycle A → B → C → A"
        ):
            action_a.write({"predecessor_ids": [Command.link(action_c.id)]})

    def test_self_dependency_prevented(self):
        """Test that an action cannot depend on itself."""
        _logger.info("Testing self-dependency prevention")

        action_a = self._create_action("Action A")

        # Try to make A depend on itself
        with self.assertRaises(ValidationError, msg="Should prevent self-dependency"):
            action_a.write({"predecessor_ids": [Command.link(action_a.id)]})

    # =========================================================================
    # Test State Management
    # =========================================================================

    def test_action_reset(self):
        """Test that action reset works correctly."""
        _logger.info("Testing action reset")

        action = self._create_action("Action A")

        # Mark as done
        action.action_mark_done()
        self.assertEqual(action.action_state, "done")

        # Reset
        action.action_reset()
        self.assertEqual(action.action_state, "waiting")
        self.assertFalse(action.error_message)

    def test_action_error_state(self):
        """Test error state management."""
        _logger.info("Testing error state")

        action = self._create_action("Action A")

        # Mark as error
        error_msg = "Test error message"
        action.action_mark_error(error_msg)

        self.assertEqual(action.action_state, "error")
        self.assertEqual(action.error_message, error_msg)

        # Reset should clear error
        action.action_reset()
        self.assertEqual(action.action_state, "waiting")
        self.assertFalse(action.error_message)

    def test_workflow_reset(self):
        """Test workflow reset functionality."""
        _logger.info("Testing workflow reset")

        action_a = self._create_action("Action A")
        action_b = self._create_action("Action B", predecessors=[action_a])

        # Manually set states
        action_a.write({"action_state": "done"})
        action_b.write({"action_state": "in_progress"})

        # Reset workflow
        result = self.automation.action_reset_workflow()

        # Check states
        self.assertEqual(
            action_a.action_state, "ready", "A should be ready (no predecessors)"
        )
        self.assertEqual(action_b.action_state, "waiting", "B should be waiting")

        # Check notification
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "success")

    # =========================================================================
    # Test Complex Workflows
    # =========================================================================

    def test_complex_workflow(self):
        """Test complex workflow with multiple branches and joins.

        Structure:
            A
            ├─→ B ─→ D
            └─→ C ─→ D
            D → E
        """
        _logger.info("Testing complex workflow")

        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])
        action_c = self._create_action("C", predecessors=[action_a])
        action_d = self._create_action("D", predecessors=[action_b, action_c])
        action_e = self._create_action("E", predecessors=[action_d])

        # Reset
        self.automation.action_reset_workflow()

        # Only A ready
        self.assertEqual(action_a.action_state, "ready")
        self.assertEqual(action_b.action_state, "waiting")
        self.assertEqual(action_c.action_state, "waiting")
        self.assertEqual(action_d.action_state, "waiting")
        self.assertEqual(action_e.action_state, "waiting")

        # Complete A
        action_a.action_mark_done()

        self.assertEqual(action_b.action_state, "ready")
        self.assertEqual(action_c.action_state, "ready")
        self.assertEqual(action_d.action_state, "waiting")

        # Complete B
        action_b.action_mark_done()

        self.assertEqual(action_d.action_state, "waiting", "D still needs C")

        # Complete C
        action_c.action_mark_done()

        self.assertEqual(action_d.action_state, "ready", "D ready after B and C")
        self.assertEqual(action_e.action_state, "waiting")

        # Complete D
        action_d.action_mark_done()

        self.assertEqual(action_e.action_state, "ready")

    def test_multiple_root_actions(self):
        """Test workflow with multiple root actions (no predecessors)."""
        _logger.info("Testing multiple root actions")

        action_a = self._create_action("Action A")
        action_b = self._create_action("Action B")  # Also no predecessors
        action_c = self._create_action("Action C", predecessors=[action_a, action_b])

        # Reset
        self.automation.action_reset_workflow()

        # Both A and B should be ready
        self.assertEqual(action_a.action_state, "ready")
        self.assertEqual(action_b.action_state, "ready")
        self.assertEqual(action_c.action_state, "waiting")

        # Complete A
        action_a.action_mark_done()
        self.assertEqual(action_c.action_state, "waiting", "C needs B too")

        # Complete B
        action_b.action_mark_done()
        self.assertEqual(action_c.action_state, "ready", "C ready after A and B")

    # =========================================================================
    # Test Orchestration
    # =========================================================================

    def test_orchestration_manual_mode(self):
        """Test manual step-by-step execution."""
        _logger.info("Testing manual orchestration")

        # Create simple chain with tracking
        execution_log = []

        action_a = self._create_action("A", code=f'execution_log.append("A")')
        action_b = self._create_action(
            "B", code=f'execution_log.append("B")', predecessors=[action_a]
        )
        action_c = self._create_action(
            "C", code=f'execution_log.append("C")', predecessors=[action_b]
        )

        # Reset
        self.automation.action_reset_workflow()

        # Verify manual mode
        self.assertFalse(self.automation.auto_execute_workflow)

        # Get ready actions
        ready = self.automation.action_server_ids.filtered(
            lambda a: a.action_state == "ready"
        )
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready.name, "A")

    def test_workflow_without_dag_flag(self):
        """Test that workflow methods check use_workflow_dag flag."""
        _logger.info("Testing workflow without DAG flag")

        # Create automation without DAG flag
        automation_no_dag = self.Automation.create(
            {
                "name": "No DAG Automation",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
                "use_workflow_dag": False,  # DAG disabled
            }
        )

        # Try to reset workflow
        result = automation_no_dag.action_reset_workflow()

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("Not a Workflow", result["params"]["title"])

    def test_execute_next_no_ready_actions(self):
        """Test execute_next when no actions are ready."""
        _logger.info("Testing execute_next with no ready actions")

        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])

        # Don't reset - all actions in waiting state
        result = self.automation.action_execute_next()

        # Should get blocked message
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertIn("Blocked", result["params"]["title"])

    def test_execute_next_workflow_complete(self):
        """Test execute_next when all actions are done."""
        _logger.info("Testing execute_next when complete")

        action_a = self._create_action("A")

        # Mark as done
        action_a.write({"action_state": "done"})

        result = self.automation.action_execute_next()

        # Should get complete message
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertIn("Complete", result["params"]["title"])

    # =========================================================================
    # Test Edge Cases
    # =========================================================================

    def test_empty_workflow(self):
        """Test workflow with no actions."""
        _logger.info("Testing empty workflow")

        # Create automation with no actions
        empty_automation = self.Automation.create(
            {
                "name": "Empty Workflow",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
                "use_workflow_dag": True,
            }
        )

        result = empty_automation.action_reset_workflow()

        # Should warn about no root actions
        self.assertEqual(result["params"]["type"], "danger")
        self.assertIn("No Root Actions", result["params"]["title"])

    def test_is_ready_computation_after_predecessor_change(self):
        """Test that is_ready updates when predecessors change state."""
        _logger.info("Testing is_ready computation triggers")

        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])

        self.automation.action_reset_workflow()

        # B should not be ready
        self.assertFalse(action_b.is_ready)

        # Mark A as done
        action_a.write({"action_state": "done"})

        # Trigger recomputation
        action_b._compute_is_ready()

        # B should now be ready
        self.assertTrue(action_b.is_ready)

    def test_successor_relationship_computed(self):
        """Test that successor_ids is properly computed from predecessor_ids."""
        _logger.info("Testing successor computation")

        action_a = self._create_action("A")
        action_b = self._create_action("B", predecessors=[action_a])

        # Check both directions
        self.assertIn(action_b, action_a.successor_ids)
        self.assertIn(action_a, action_b.predecessor_ids)

        # Add another predecessor
        action_c = self._create_action("C")
        action_b.write({"predecessor_ids": [Command.link(action_c.id)]})

        # Check C's successors updated
        self.assertIn(action_b, action_c.successor_ids)

    def test_action_with_no_predecessors_always_ready_after_reset(self):
        """Test that actions with no predecessors are ready after reset."""
        _logger.info("Testing root actions are ready")

        action = self._create_action("Root Action")

        # Initially waiting
        self.assertEqual(action.action_state, "waiting")

        # Reset workflow
        self.automation.action_reset_workflow()

        # Should be ready
        self.assertEqual(action.action_state, "ready")
        self.assertTrue(action.is_ready)


class TestWorkflowDAGIntegration(TransactionCase):
    """Integration tests for workflow execution."""

    def setUp(self):
        super().setUp()
        self.Automation = self.env["base.automation"]
        self.Action = self.env["ir.actions.server"]
        self.Partner = self.env["res.partner"]

        self.model_partner = self.env["ir.model"]._get("res.partner")

    def test_actual_code_execution_in_workflow(self):
        """Test that server actions actually execute their code in workflow."""
        _logger.info("Testing actual code execution")

        # Create test partner
        test_partner = self.Partner.create({"name": "Test Partner"})

        # Create automation
        automation = self.Automation.create(
            {
                "name": "Test Execution Workflow",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
                "use_workflow_dag": True,
                "auto_execute_workflow": False,
            }
        )

        # Create actions that modify the partner
        action_a = self.Action.create(
            {
                "name": "Set Email",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'email': 'test@example.com'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        action_b = self.Action.create(
            {
                "name": "Set Phone",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'phone': '123-456-7890'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
                "predecessor_ids": [Command.link(action_a.id)],
            }
        )

        # Reset workflow
        automation.action_reset_workflow()

        # Execute first action
        action_a.action_mark_in_progress()
        action_a.with_context(
            active_model="res.partner",
            active_id=test_partner.id,
            active_ids=test_partner.ids,
        ).run()
        action_a.action_mark_done()

        # Check email was set
        self.assertEqual(test_partner.email, "test@example.com")

        # B should now be ready
        self.assertEqual(action_b.action_state, "ready")

        # Execute second action
        action_b.action_mark_in_progress()
        action_b.with_context(
            active_model="res.partner",
            active_id=test_partner.id,
            active_ids=test_partner.ids,
        ).run()
        action_b.action_mark_done()

        # Check phone was set
        self.assertEqual(test_partner.phone, "123-456-7890")

    def test_error_handling_in_workflow(self):
        """Test that errors are properly caught and logged."""
        _logger.info("Testing error handling")

        automation = self.Automation.create(
            {
                "name": "Error Test Workflow",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
                "use_workflow_dag": True,
            }
        )

        # Create action that will fail
        action = self.Action.create(
            {
                "name": "Failing Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "raise Exception('Test error')",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        automation.action_reset_workflow()

        # Try to execute - should raise exception
        with self.assertRaises(Exception):
            automation._execute_workflow_action(action)

        # Action should be in error state
        self.assertEqual(action.action_state, "error")
        self.assertIn("Test error", action.error_message)
