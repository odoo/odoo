# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Comprehensive tests for webhook automation triggers.

Tests cover:
- Webhook setup and configuration (UUID, URL)
- Webhook execution with various payloads
- Actions integration (code, object_write, mail)
- Error handling
- Logging
- Edge cases
"""

import logging

from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestWebhookIntegration(common.TransactionCase):
    """Test webhook trigger functionality with test models."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Lead = cls.env["base.automation.lead.test"]
        cls.Project = cls.env["test_base_automation.project"]

        cls.model_lead = cls.env["ir.model"]._get("base.automation.lead.test")
        cls.model_project = cls.env["ir.model"]._get("test_base_automation.project")

        # Create test lead
        cls.test_lead = cls.Lead.create(
            {
                "name": "Webhook Test Lead",
            }
        )

    # =========================================================================
    # Test Webhook Setup and Configuration
    # =========================================================================

    def test_webhook_trigger_creates_uuid(self):
        """Test webhook trigger automatically generates UUID."""
        _logger.info("Testing webhook UUID generation")

        automation = self.Automation.create(
            {
                "name": "Webhook with UUID",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
            }
        )

        # Verify UUID generated
        self.assertTrue(automation.webhook_uuid)
        self.assertEqual(len(automation.webhook_uuid), 36)  # UUID format

    def test_webhook_url_computed(self):
        """Test webhook URL is computed correctly."""
        _logger.info("Testing webhook URL computation")

        automation = self.Automation.create(
            {
                "name": "Webhook URL Test",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
            }
        )

        # Verify URL computed
        self.assertTrue(automation.url)
        self.assertIn("/web/hook/", automation.url)
        self.assertIn(automation.webhook_uuid, automation.url)

    def test_webhook_url_only_for_webhook_trigger(self):
        """Test URL only exists for webhook trigger type."""
        _logger.info("Testing webhook URL specificity")

        # Non-webhook automation
        automation = self.Automation.create(
            {
                "name": "Not Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_create",
            }
        )

        # Should not have URL
        self.assertFalse(automation.url)

    def test_webhook_uuid_rotation(self):
        """Test webhook UUID can be rotated."""
        _logger.info("Testing webhook UUID rotation")

        automation = self.Automation.create(
            {
                "name": "Webhook Rotation Test",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
            }
        )

        old_uuid = automation.webhook_uuid
        old_url = automation.url

        # Rotate UUID
        automation.action_rotate_webhook_uuid()

        # Verify changed
        self.assertNotEqual(automation.webhook_uuid, old_uuid)
        self.assertNotEqual(automation.url, old_url)
        self.assertIn(automation.webhook_uuid, automation.url)

    def test_webhook_uuid_unique(self):
        """Test each webhook automation gets unique UUID."""
        _logger.info("Testing webhook UUID uniqueness")

        automation1 = self.Automation.create(
            {
                "name": "Webhook 1",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
            }
        )

        automation2 = self.Automation.create(
            {
                "name": "Webhook 2",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
            }
        )

        # UUIDs should be different
        self.assertNotEqual(automation1.webhook_uuid, automation2.webhook_uuid)
        self.assertNotEqual(automation1.url, automation2.url)

    # =========================================================================
    # Test Webhook Execution
    # =========================================================================

    def test_webhook_basic_execution(self):
        """Test basic webhook execution with simple payload."""
        _logger.info("Testing basic webhook execution")

        automation = self.Automation.create(
            {
                "name": "Basic Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
            }
        )

        self.Action.create(
            {
                "name": "Webhook Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Webhook triggered'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute webhook
        payload = {"event": "test"}
        automation._execute_webhook(payload)

        # Verify execution
        self.assertEqual(self.test_lead.name, "Webhook triggered")

    def test_webhook_with_payload_data(self):
        """Test webhook can access payload data in record_getter."""
        _logger.info("Testing webhook with payload data")

        automation = self.Automation.create(
            {
                "name": "Payload Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": "model.browse(payload.get('lead_id'))",
            }
        )

        self.Action.create(
            {
                "name": "Payload Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Payload processed'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute with payload containing lead_id
        payload = {"lead_id": self.test_lead.id, "event": "lead_update"}
        automation._execute_webhook(payload)

        # Verify execution
        self.assertEqual(self.test_lead.name, "Payload processed")

    def test_webhook_with_model_and_id_payload(self):
        """Test webhook with standard _model and _id payload format."""
        _logger.info("Testing webhook with _model/_id payload")

        automation = self.Automation.create(
            {
                "name": "Standard Payload Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": "env[payload['_model']].browse(payload['_id'])",
            }
        )

        self.Action.create(
            {
                "name": "Standard Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Standard payload'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute with standard payload
        payload = {"_model": "base.automation.lead.test", "_id": self.test_lead.id}
        automation._execute_webhook(payload)

        # Verify execution
        self.assertEqual(self.test_lead.name, "Standard payload")

    def test_webhook_multiple_executions(self):
        """Test webhook can be executed multiple times."""
        _logger.info("Testing webhook multiple executions")

        automation = self.Automation.create(
            {
                "name": "Multi Execution Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
            }
        )

        self.Action.create(
            {
                "name": "Counter Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": """
# Use state field to count executions
state_map = {'draft': '1', 'cancel': '2', 'open': '3'}
current = record.state if record.state in state_map else 'draft'
next_states = {'draft': 'cancel', 'cancel': 'open', 'open': 'pending'}
record.write({'state': next_states.get(current, 'cancel')})
""",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute webhook 3 times
        self.test_lead.write({"state": "draft"})
        for i in range(3):
            automation._execute_webhook({"iteration": i})

        # Should have executed 3 times (draft -> cancel -> open -> pending)
        self.assertEqual(self.test_lead.state, "pending")

    def test_webhook_with_complex_record_getter(self):
        """Test webhook with complex record_getter logic."""
        _logger.info("Testing webhook with complex record_getter")

        # Create test leads
        priority_lead = self.Lead.create({"name": "Priority Lead", "priority": True})
        regular_lead = self.Lead.create({"name": "Regular Lead", "priority": False})

        automation = self.Automation.create(
            {
                "name": "Complex Getter Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": """
lead_id = payload.get('lead_id')
is_priority = payload.get('is_priority', False)
if is_priority:
    result = model.browse(lead_id)
else:
    result = model.browse([])
""",
            }
        )

        self.Action.create(
            {
                "name": "Complex Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Priority webhook'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute for priority - should process
        payload1 = {"lead_id": priority_lead.id, "is_priority": True}
        automation._execute_webhook(payload1)
        self.assertEqual(priority_lead.name, "Priority webhook")

        # Execute for non-priority - should not process (no record)
        payload2 = {"lead_id": regular_lead.id, "is_priority": False}
        with self.assertRaises(ValidationError):
            automation._execute_webhook(payload2)

    # =========================================================================
    # Test Webhook with Actions
    # =========================================================================

    def test_webhook_with_multiple_actions(self):
        """Test webhook executes multiple actions in sequence."""
        _logger.info("Testing webhook with multiple actions")

        automation = self.Automation.create(
            {
                "name": "Multi-Action Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
            }
        )

        # Create 2 actions
        self.Action.create(
            {
                "name": "Action 1",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Action1'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
                "sequence": 10,
            }
        )

        self.Action.create(
            {
                "name": "Action 2",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'state': 'open'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
                "sequence": 20,
            }
        )

        # Execute webhook
        automation._execute_webhook({"test": "multi_action"})

        # Both actions should execute
        self.assertEqual(self.test_lead.name, "Action1")
        self.assertEqual(self.test_lead.state, "open")

    def test_webhook_with_object_write_action(self):
        """Test webhook with object_write action type."""
        _logger.info("Testing webhook with object_write action")

        automation = self.Automation.create(
            {
                "name": "Object Write Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
            }
        )

        # Get name field
        name_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "name"
        )

        self.Action.create(
            {
                "name": "Write Action",
                "model_id": self.model_lead.id,
                "state": "object_write",
                "fields_lines": [
                    (
                        0,
                        0,
                        {
                            "col1": name_field.id,
                            "value": "Object write from webhook",
                        },
                    )
                ],
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute webhook
        automation._execute_webhook({})

        # Verify object_write executed
        self.assertEqual(self.test_lead.name, "Object write from webhook")

    def test_webhook_with_mail_action(self):
        """Test webhook can send email via mail_post action."""
        _logger.info("Testing webhook with mail action")

        # Use threaded lead for mail
        LeadThread = self.env["base.automation.lead.thread.test"]
        thread_lead = LeadThread.create({"name": "Mail Test Lead"})

        model_thread = self.env["ir.model"]._get("base.automation.lead.thread.test")

        automation = self.Automation.create(
            {
                "name": "Mail Webhook",
                "model_id": model_thread.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({thread_lead.id})",
            }
        )

        self.Action.create(
            {
                "name": "Mail Action",
                "model_id": model_thread.id,
                "state": "mail_post",
                "template_id": False,  # No template, just post message
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute webhook
        automation._execute_webhook({"subject": "Test notification"})

        # Verify message posted (check message count)
        messages = thread_lead.message_ids
        self.assertTrue(len(messages) > 0)

    # =========================================================================
    # Test Webhook Error Handling
    # =========================================================================

    def test_webhook_invalid_record_getter(self):
        """Test webhook with invalid record_getter raises error."""
        _logger.info("Testing webhook with invalid record_getter")

        automation = self.Automation.create(
            {
                "name": "Invalid Getter",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": "invalid_python_code {",  # Syntax error
            }
        )

        self.Action.create(
            {
                "name": "Test Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "pass",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Should raise error
        with self.assertRaises(Exception):
            automation._execute_webhook({})

    def test_webhook_record_getter_returns_no_record(self):
        """Test webhook fails when record_getter returns no record."""
        _logger.info("Testing webhook with no record")

        automation = self.Automation.create(
            {
                "name": "No Record",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": "model.browse([])",  # Empty recordset
            }
        )

        self.Action.create(
            {
                "name": "Test Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "pass",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Should raise ValidationError
        with self.assertRaises(ValidationError):
            automation._execute_webhook({})

    def test_webhook_record_getter_returns_deleted_record(self):
        """Test webhook fails when record_getter returns deleted record."""
        _logger.info("Testing webhook with deleted record")

        # Create and delete lead
        temp_lead = self.Lead.create({"name": "Temp Lead"})
        temp_id = temp_lead.id
        temp_lead.unlink()

        automation = self.Automation.create(
            {
                "name": "Deleted Record",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({temp_id})",
            }
        )

        self.Action.create(
            {
                "name": "Test Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "pass",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Should raise ValidationError (record doesn't exist)
        with self.assertRaises(ValidationError):
            automation._execute_webhook({})

    def test_webhook_action_execution_error(self):
        """Test webhook handles action execution errors."""
        _logger.info("Testing webhook action error handling")

        automation = self.Automation.create(
            {
                "name": "Error Action Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
            }
        )

        self.Action.create(
            {
                "name": "Failing Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "raise Exception('Action failed!')",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Should raise exception
        with self.assertRaises(Exception) as context:
            automation._execute_webhook({})

        self.assertIn("Action failed!", str(context.exception))

    def test_webhook_empty_payload(self):
        """Test webhook works with empty payload."""
        _logger.info("Testing webhook with empty payload")

        automation = self.Automation.create(
            {
                "name": "Empty Payload Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
            }
        )

        self.Action.create(
            {
                "name": "Simple Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Empty payload OK'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute with empty payload
        automation._execute_webhook({})

        # Should still work
        self.assertEqual(self.test_lead.name, "Empty payload OK")

    # =========================================================================
    # Test Webhook Logging
    # =========================================================================

    def test_webhook_logging_enabled(self):
        """Test webhook logging when log_webhook_calls is enabled."""
        _logger.info("Testing webhook logging")

        automation = self.Automation.create(
            {
                "name": "Logged Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
                "log_webhook_calls": True,
            }
        )

        self.Action.create(
            {
                "name": "Logged Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "pass",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Clear existing logs
        initial_log_count = self.env["ir.logging"].sudo().search_count([])

        # Execute webhook
        automation._execute_webhook({"test": "logging"})

        # Should create log entry
        final_log_count = self.env["ir.logging"].sudo().search_count([])
        self.assertGreater(final_log_count, initial_log_count)

    def test_webhook_logging_error(self):
        """Test webhook logs errors when log_webhook_calls is enabled."""
        _logger.info("Testing webhook error logging")

        automation = self.Automation.create(
            {
                "name": "Error Logged Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": "model.browse([])",  # Will fail
                "log_webhook_calls": True,
            }
        )

        self.Action.create(
            {
                "name": "Test Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "pass",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute webhook - will fail
        try:
            automation._execute_webhook({})
        except ValidationError:
            pass

        # Should have logged error
        error_logs = (
            self.env["ir.logging"]
            .sudo()
            .search([("level", "=", "ERROR")], order="id desc", limit=1)
        )
        self.assertTrue(error_logs)

    # =========================================================================
    # Test Webhook with Different Models
    # =========================================================================

    def test_webhook_on_different_model(self):
        """Test webhook can work with different models."""
        _logger.info("Testing webhook on project model")

        # Create project
        project = self.Project.create({"name": "Test Project"})

        automation = self.Automation.create(
            {
                "name": "Project Webhook",
                "model_id": self.model_project.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({project.id})",
            }
        )

        self.Action.create(
            {
                "name": "Project Action",
                "model_id": self.model_project.id,
                "state": "code",
                "code": "record.write({'name': 'Webhook triggered'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute webhook
        automation._execute_webhook({"project_id": project.id})

        # Verify execution
        self.assertEqual(project.name, "Webhook triggered")

    def test_webhook_search_by_field(self):
        """Test webhook can find record by custom field."""
        _logger.info("Testing webhook with field search")

        # Create lead with specific state
        self.test_lead.write({"state": "draft"})

        automation = self.Automation.create(
            {
                "name": "Field Search Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": "model.search([('state', '=', payload.get('state'))], limit=1)",
            }
        )

        self.Action.create(
            {
                "name": "Field Search Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Found by field'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute with field value
        payload = {"state": "draft"}
        automation._execute_webhook(payload)

        # Verify found and executed
        self.assertEqual(self.test_lead.name, "Found by field")

    # =========================================================================
    # Test Webhook Edge Cases
    # =========================================================================

    def test_webhook_with_no_record_getter(self):
        """Test webhook with no record_getter (should fail)."""
        _logger.info("Testing webhook without record_getter")

        automation = self.Automation.create(
            {
                "name": "No Getter Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": False,  # No getter
            }
        )

        self.Action.create(
            {
                "name": "Test Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "pass",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Should fail (no record to run on)
        with self.assertRaises(ValidationError):
            automation._execute_webhook({})

    def test_webhook_inactive_automation(self):
        """Test inactive webhook automation still executes via direct call."""
        _logger.info("Testing inactive webhook automation")

        automation = self.Automation.create(
            {
                "name": "Inactive Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
                "active": False,  # Inactive
            }
        )

        self.Action.create(
            {
                "name": "Test Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Inactive executed'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Direct execution still works (method doesn't check active status)
        automation._execute_webhook({})

        # Should execute (method doesn't check active status)
        self.assertEqual(self.test_lead.name, "Inactive executed")

    def test_webhook_with_large_payload(self):
        """Test webhook handles large payload data."""
        _logger.info("Testing webhook with large payload")

        automation = self.Automation.create(
            {
                "name": "Large Payload Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
            }
        )

        self.Action.create(
            {
                "name": "Payload Size Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': f'Payload size: {len(str(payload))}'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create large payload (1000 items)
        large_payload = {f"item_{i}": f"value_{i}" for i in range(1000)}

        # Execute webhook
        automation._execute_webhook(large_payload)

        # Should handle large payload
        self.assertTrue(self.test_lead.name)
        self.assertIn("Payload size:", self.test_lead.name)

    def test_webhook_payload_access_in_action(self):
        """Test payload is accessible in action execution context."""
        _logger.info("Testing payload access in action")

        automation = self.Automation.create(
            {
                "name": "Payload Access Webhook",
                "model_id": self.model_lead.id,
                "trigger": "on_webhook",
                "record_getter": f"model.browse({self.test_lead.id})",
            }
        )

        self.Action.create(
            {
                "name": "Payload Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": """
event_type = payload.get('event_type', 'unknown')
record.write({'name': f'Event: {event_type}'})
""",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Execute with payload
        automation._execute_webhook({"event_type": "lead.created"})

        # Action should access payload
        self.assertEqual(self.test_lead.name, "Event: lead.created")
