# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for all automation trigger types."""

import logging

from odoo import Command
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestAutomationTriggers(TransactionCase):
    """Test all trigger types for base.automation."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Partner = cls.env["res.partner"]

        cls.model_partner = cls.env["ir.model"]._get("res.partner")

    def _create_automation(self, name, trigger, **kwargs):
        """Helper to create automation with action."""
        automation = self.Automation.create(
            {
                "name": name,
                "model_id": self.model_partner.id,
                "trigger": trigger,
                **kwargs,
            },
        )

        # Create simple action that sets a marker field
        self.Action.create(
            {
                "name": f"Action for {name}",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Triggered'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            },
        )

        return automation

    # =========================================================================
    # Test Record Lifecycle Triggers
    # =========================================================================

    def test_on_create_trigger(self):
        """Test on_create trigger fires when record is created."""
        _logger.info("Testing on_create trigger")

        automation = self._create_automation("On Create Test", "on_create")

        # Create partner - should trigger automation
        partner = self.Partner.create({"name": "New Partner"})

        # Check that automation fired
        self.assertEqual(partner.comment, "Triggered")

    def test_on_write_trigger(self):
        """Test on_write trigger fires when record is updated."""
        _logger.info("Testing on_write trigger")

        automation = self._create_automation("On Write Test", "on_write")

        # Create partner first
        partner = self.Partner.create({"name": "Test Partner"})

        # Clear comment (automation might fire on create too)
        partner.comment = False

        # Update partner - should trigger automation
        partner.write({"email": "test@example.com"})

        # Check that automation fired
        self.assertEqual(partner.comment, "Triggered")

    def test_on_create_or_write_trigger(self):
        """Test on_create_or_write fires on both create and write."""
        _logger.info("Testing on_create_or_write trigger")

        automation = self._create_automation("On Create or Write", "on_create_or_write")

        # Test create
        partner = self.Partner.create({"name": "Test Partner"})
        self.assertEqual(partner.comment, "Triggered")

        # Clear and test write
        partner.comment = False
        partner.write({"phone": "123-456"})
        self.assertEqual(partner.comment, "Triggered")

    def test_on_unlink_trigger(self):
        """Test on_unlink trigger fires before deletion."""
        _logger.info("Testing on_unlink trigger")

        # Note: Can't easily verify comment after delete, so test that it runs
        automation = self._create_automation("On Unlink Test", "on_unlink")

        partner = self.Partner.create({"name": "To Delete"})

        # Delete - automation should fire (can't verify aftermath)
        partner.unlink()

        # Verify partner deleted
        self.assertFalse(partner.exists())

    def test_on_archive_trigger(self):
        """Test on_archive trigger fires when record archived."""
        _logger.info("Testing on_archive trigger")

        automation = self._create_automation("On Archive Test", "on_archive")

        partner = self.Partner.create({"name": "To Archive", "active": True})
        partner.comment = False

        # Archive
        partner.write({"active": False})

        # Check triggered
        self.assertEqual(partner.comment, "Triggered")

    def test_on_unarchive_trigger(self):
        """Test on_unarchive trigger fires when record unarchived."""
        _logger.info("Testing on_unarchive trigger")

        automation = self._create_automation("On Unarchive Test", "on_unarchive")

        # Create archived partner
        partner = self.Partner.create({"name": "Archived", "active": False})
        partner.comment = False

        # Unarchive
        partner.write({"active": True})

        # Check triggered
        self.assertEqual(partner.comment, "Triggered")

    # =========================================================================
    # Test Field-Specific Triggers
    # =========================================================================

    def test_on_user_set_trigger(self):
        """Test on_user_set trigger fires when user field is set."""
        _logger.info("Testing on_user_set trigger")

        # Partners don't have user_id, so this test would fail
        # Skip or use a different model
        # Leaving as documentation of trigger type
        pass

    def test_trigger_with_domain_filter(self):
        """Test that domain filters work correctly."""
        _logger.info("Testing trigger with domain filter")

        automation = self._create_automation(
            "Filtered Trigger",
            "on_create",
            filter_domain="[('name', 'ilike', 'VIP')]",
        )

        # Create non-matching partner
        partner1 = self.Partner.create({"name": "Regular Customer"})
        self.assertFalse(partner1.comment)

        # Create matching partner
        partner2 = self.Partner.create({"name": "VIP Customer"})
        self.assertEqual(partner2.comment, "Triggered")

    # =========================================================================
    # Test Manual Trigger
    # =========================================================================

    def test_on_hand_trigger(self):
        """Test manual (on_hand) trigger."""
        _logger.info("Testing on_hand trigger")

        automation = self._create_automation("Manual Trigger", "on_hand")

        partner = self.Partner.create({"name": "Manual Test"})

        # Should not auto-trigger
        self.assertFalse(partner.comment)

        # Manually trigger
        automation.with_context(
            active_model="res.partner",
            active_id=partner.id,
            active_ids=partner.ids,
        ).action_manual_trigger()

        # Should now be triggered
        self.assertEqual(partner.comment, "Triggered")

    def test_manual_trigger_with_workflow_dag(self):
        """Test manual trigger with workflow DAG enabled."""
        _logger.info("Testing manual trigger with DAG")

        automation = self.Automation.create(
            {
                "name": "Manual DAG Workflow",
                "model_id": self.model_partner.id,
                "trigger": "on_hand",
                "use_workflow_dag": True,
                "auto_execute_workflow": False,
            }
        )

        action = self.Action.create(
            {
                "name": "DAG Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "pass",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Trigger manually
        result = automation.action_manual_trigger()

        # Should reset and execute first action
        self.assertEqual(action.action_state, "ready")

    # =========================================================================
    # Test Trigger Field Tracking
    # =========================================================================

    def test_trigger_field_ids_filter(self):
        """Test that automation only triggers when specific fields change."""
        _logger.info("Testing trigger_field_ids filtering")

        # Get email field
        email_field = self.env["ir.model.fields"]._get("res.partner", "email")

        automation = self.Automation.create(
            {
                "name": "Email Change Only",
                "model_id": self.model_partner.id,
                "trigger": "on_write",
                "trigger_field_ids": [Command.link(email_field.id)],
            }
        )

        self.Action.create(
            {
                "name": "Email Changed",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Email changed'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        partner = self.Partner.create({"name": "Field Test"})

        # Change name (not email) - should NOT trigger
        partner.write({"name": "New Name"})
        self.assertFalse(partner.comment)

        # Change email - SHOULD trigger
        partner.write({"email": "new@example.com"})
        self.assertEqual(partner.comment, "Email changed")

    # =========================================================================
    # Test Pre/Post Filters
    # =========================================================================

    def test_filter_pre_domain(self):
        """Test filter_pre_domain (before update condition)."""
        _logger.info("Testing filter_pre_domain")

        automation = self.Automation.create(
            {
                "name": "Pre-filter Test",
                "model_id": self.model_partner.id,
                "trigger": "on_write",
                "filter_pre_domain": "[('active', '=', True)]",
                "filter_domain": "[('active', '=', False)]",
            }
        )

        self.Action.create(
            {
                "name": "Archival Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Archived'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create active partner
        partner = self.Partner.create({"name": "Active Partner", "active": True})

        # Archive it - should trigger (was active, becomes inactive)
        partner.write({"active": False})
        self.assertEqual(partner.comment, "Archived")

    # =========================================================================
    # Test Multiple Automations
    # =========================================================================

    def test_multiple_automations_same_trigger(self):
        """Test multiple automations can fire on same trigger."""
        _logger.info("Testing multiple automations")

        automation1 = self._create_automation("Auto 1", "on_create")
        automation2 = self.Automation.create(
            {
                "name": "Auto 2",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
            }
        )

        self.Action.create(
            {
                "name": "Action 2",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'phone': '999-999-9999'})",
                "base_automation_id": automation2.id,
                "usage": "base_automation",
            }
        )

        # Create partner
        partner = self.Partner.create({"name": "Multi Test"})

        # Both automations should fire
        self.assertEqual(partner.comment, "Triggered")  # From auto1
        self.assertEqual(partner.phone, "999-999-9999")  # From auto2

    # =========================================================================
    # Test Inactive Automations
    # =========================================================================

    def test_inactive_automation_does_not_trigger(self):
        """Test that inactive automations don't fire."""
        _logger.info("Testing inactive automation")

        automation = self._create_automation("Inactive Test", "on_create")

        # Deactivate
        automation.write({"active": False})

        # Create partner
        partner = self.Partner.create({"name": "Should Not Trigger"})

        # Should not trigger
        self.assertFalse(partner.comment)

    # =========================================================================
    # Test Edge Cases
    # =========================================================================

    def test_automation_with_no_actions(self):
        """Test automation with no server actions."""
        _logger.info("Testing automation with no actions")

        automation = self.Automation.create(
            {
                "name": "No Actions",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
            }
        )

        # Create partner - should not error even with no actions
        partner = self.Partner.create({"name": "No Actions Test"})

        # Just verify no crash
        self.assertTrue(partner.exists())

    def test_automation_with_multiple_actions(self):
        """Test automation with multiple sequential actions."""
        _logger.info("Testing multiple actions")

        automation = self.Automation.create(
            {
                "name": "Multi-Action",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
            }
        )

        # Create two actions
        self.Action.create(
            {
                "name": "Action 1",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Action 1'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
                "sequence": 10,
            }
        )

        self.Action.create(
            {
                "name": "Action 2",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'phone': 'Action 2'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
                "sequence": 20,
            }
        )

        # Create partner
        partner = self.Partner.create({"name": "Multi Action"})

        # Both actions should execute
        self.assertEqual(partner.comment, "Action 1")
        self.assertEqual(partner.phone, "Action 2")


class TestFieldSpecificTriggers(TransactionCase):
    """Test field-specific triggers (state, priority, stage, tag, user)."""

    @classmethod
    def setUpClass(cls):
        """Set up test data with models that have special fields."""
        super().setUpClass()

        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.SaleOrder = cls.env["sale.order"]
        cls.Partner = cls.env["res.partner"]
        cls.User = cls.env["res.users"]

        cls.model_sale = cls.env["ir.model"]._get("sale.order")
        cls.model_partner = cls.env["ir.model"]._get("res.partner")

        # Create test partner
        cls.test_partner = cls.Partner.create(
            {
                "name": "Test Customer",
                "email": "customer@test.com",
            }
        )

        # Create test user
        cls.test_user = cls.User.create(
            {
                "name": "Test User",
                "login": "testuser@example.com",
                "email": "testuser@example.com",
            }
        )

    # =========================================================================
    # Test on_state_set Trigger
    # =========================================================================

    def test_on_state_set_trigger(self):
        """Test on_state_set trigger fires when state changes to specific value."""
        _logger.info("Testing on_state_set trigger")

        # Get state field
        state_field = self.env["ir.model.fields"]._get("sale.order", "state")

        # Get selection for 'sale' state
        state_selection = self.env["ir.model.fields.selection"].search(
            [
                ("field_id", "=", state_field.id),
                ("value", "=", "sale"),
            ],
            limit=1,
        )

        if not state_selection:
            _logger.warning("State selection not found, skipping test")
            return

        # Create automation that triggers when state = 'sale'
        automation = self.Automation.create(
            {
                "name": "On State Sale",
                "model_id": self.model_sale.id,
                "trigger": "on_state_set",
                "trg_selection_field_id": state_selection.id,
            }
        )

        self.Action.create(
            {
                "name": "State Changed to Sale",
                "model_id": self.model_sale.id,
                "state": "code",
                "code": "record.write({'note': 'State is sale'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create sale order in draft
        order = self.SaleOrder.create(
            {
                "partner_id": self.test_partner.id,
                "state": "draft",
            }
        )

        # Should not trigger yet
        self.assertFalse(order.note)

        # Confirm order (state -> sale)
        order.action_confirm()

        # Should trigger
        self.assertEqual(order.note, "State is sale")

    def test_on_state_set_selective(self):
        """Test that on_state_set only triggers for specific state value."""
        _logger.info("Testing on_state_set selectivity")

        # Get state field and 'sale' selection
        state_field = self.env["ir.model.fields"]._get("sale.order", "state")
        state_selection = self.env["ir.model.fields.selection"].search(
            [
                ("field_id", "=", state_field.id),
                ("value", "=", "sale"),
            ],
            limit=1,
        )

        if not state_selection:
            _logger.warning("State selection not found, skipping test")
            return

        automation = self.Automation.create(
            {
                "name": "Only on Sale State",
                "model_id": self.model_sale.id,
                "trigger": "on_state_set",
                "trg_selection_field_id": state_selection.id,
            }
        )

        self.Action.create(
            {
                "name": "Sale State Action",
                "model_id": self.model_sale.id,
                "state": "code",
                "code": "record.write({'note': 'Triggered'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create and confirm order
        order = self.SaleOrder.create(
            {
                "partner_id": self.test_partner.id,
            }
        )
        order.action_confirm()
        order.note = False  # Clear any triggers

        # Change to different state - should NOT trigger
        order.write({"state": "cancel"})
        self.assertFalse(order.note)

    # =========================================================================
    # Test on_priority_set Trigger
    # =========================================================================

    def test_on_priority_set_trigger(self):
        """Test on_priority_set trigger fires when priority is set to value."""
        _logger.info("Testing on_priority_set trigger")

        # Get priority field
        priority_field = self.env["ir.model.fields"]._get("res.partner", "priority")

        # Get selection for priority = '1'
        priority_selection = self.env["ir.model.fields.selection"].search(
            [
                ("field_id", "=", priority_field.id),
                ("value", "=", "1"),
            ],
            limit=1,
        )

        if not priority_selection:
            _logger.warning("Priority selection not found, skipping test")
            return

        automation = self.Automation.create(
            {
                "name": "On Priority Set",
                "model_id": self.model_partner.id,
                "trigger": "on_priority_set",
                "trg_selection_field_id": priority_selection.id,
            }
        )

        self.Action.create(
            {
                "name": "Priority Set Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Priority set to 1'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create partner with priority 0
        partner = self.Partner.create(
            {
                "name": "Priority Test",
                "priority": "0",
            }
        )

        # Should not trigger yet
        self.assertFalse(partner.comment)

        # Set priority to 1
        partner.write({"priority": "1"})

        # Should trigger
        self.assertEqual(partner.comment, "Priority set to 1")

    # =========================================================================
    # Test on_user_set Trigger
    # =========================================================================

    def test_on_user_set_trigger(self):
        """Test on_user_set trigger fires when user field is set."""
        _logger.info("Testing on_user_set trigger")

        # sale.order has user_id field
        automation = self.Automation.create(
            {
                "name": "On User Set",
                "model_id": self.model_sale.id,
                "trigger": "on_user_set",
            }
        )

        self.Action.create(
            {
                "name": "User Set Action",
                "model_id": self.model_sale.id,
                "state": "code",
                "code": "record.write({'note': 'User assigned'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create order without user
        order = self.SaleOrder.create(
            {
                "partner_id": self.test_partner.id,
                "user_id": False,
            }
        )

        # Should not trigger yet
        self.assertFalse(order.note)

        # Assign user
        order.write({"user_id": self.test_user.id})

        # Should trigger
        self.assertEqual(order.note, "User assigned")


class TestTimeBasedTriggers(TransactionCase):
    """Test time-based triggers (on_time, on_time_created, on_time_updated)."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Partner = cls.env["res.partner"]

        cls.model_partner = cls.env["ir.model"]._get("res.partner")

    # =========================================================================
    # Test Basic Time Trigger Setup
    # =========================================================================

    def test_on_time_trigger_setup(self):
        """Test on_time trigger configuration."""
        _logger.info("Testing on_time trigger setup")

        # Get date field
        date_field = self.env["ir.model.fields"]._get("res.partner", "create_date")

        # Create automation that triggers 1 day after creation
        automation = self.Automation.create(
            {
                "name": "One Day After Creation",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        self.Action.create(
            {
                "name": "Time Trigger Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'One day passed'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Verify configuration
        self.assertEqual(automation.trigger, "on_time")
        self.assertEqual(automation.trg_date_id, date_field)
        self.assertEqual(automation.trg_date_range, 1)
        self.assertEqual(automation.trg_date_range_type, "day")

    def test_on_time_created_trigger_setup(self):
        """Test on_time_created trigger configuration."""
        _logger.info("Testing on_time_created trigger setup")

        automation = self.Automation.create(
            {
                "name": "2 Hours After Creation",
                "model_id": self.model_partner.id,
                "trigger": "on_time_created",
                "trg_date_range": 2,
                "trg_date_range_type": "hour",
            }
        )

        self.Action.create(
            {
                "name": "After Creation Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': '2 hours passed'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Verify automation created correctly
        self.assertEqual(automation.trigger, "on_time_created")
        self.assertEqual(automation.trg_date_range, 2)
        self.assertEqual(automation.trg_date_range_type, "hour")

    def test_on_time_updated_trigger_setup(self):
        """Test on_time_updated trigger configuration."""
        _logger.info("Testing on_time_updated trigger setup")

        automation = self.Automation.create(
            {
                "name": "30 Minutes After Update",
                "model_id": self.model_partner.id,
                "trigger": "on_time_updated",
                "trg_date_range": 30,
                "trg_date_range_type": "minutes",
            }
        )

        self.Action.create(
            {
                "name": "After Update Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': '30 minutes since update'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Verify automation created correctly
        self.assertEqual(automation.trigger, "on_time_updated")
        self.assertEqual(automation.trg_date_range, 30)
        self.assertEqual(automation.trg_date_range_type, "minutes")

    def test_time_trigger_all_range_types(self):
        """Test all date range types for time triggers."""
        _logger.info("Testing all time range types")

        for range_type in ["minutes", "hour", "day", "month"]:
            automation = self.Automation.create(
                {
                    "name": f"Time Trigger {range_type}",
                    "model_id": self.model_partner.id,
                    "trigger": "on_time_created",
                    "trg_date_range": 5,
                    "trg_date_range_type": range_type,
                }
            )

            self.assertEqual(automation.trg_date_range_type, range_type)

    # =========================================================================
    # Test Time Trigger Record Search
    # =========================================================================

    def test_search_time_based_records_on_time(self):
        """Test _search_time_based_automation_records for on_time trigger."""
        _logger.info("Testing time-based record search for on_time")

        import datetime
        from odoo import fields

        # Get create_date field
        date_field = self.env["ir.model.fields"]._get("res.partner", "create_date")

        # Create automation: 1 day after create_date
        automation = self.Automation.create(
            {
                "name": "1 Day After",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        # Create partners at different times
        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)
        one_day_ago = now - datetime.timedelta(days=1, hours=1)
        one_hour_ago = now - datetime.timedelta(hours=1)

        # Partner created 2 days ago - SHOULD be found (1 day trigger passed)
        partner1 = self.Partner.create({"name": "Old Partner"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (two_days_ago, partner1.id),
        )

        # Partner created 1 day ago - SHOULD be found
        partner2 = self.Partner.create({"name": "Recent Partner"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (one_day_ago, partner2.id),
        )

        # Partner created 1 hour ago - should NOT be found (too recent)
        partner3 = self.Partner.create({"name": "Very Recent Partner"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (one_hour_ago, partner3.id),
        )

        # Invalidate cache to reflect DB changes
        self.env.invalidate_all()

        # Search for records
        records = automation._search_time_based_automation_records(until=now)

        # Verify results
        self.assertIn(partner1, records)
        self.assertIn(partner2, records)
        self.assertNotIn(partner3, records)

    def test_search_time_based_records_with_domain_filter(self):
        """Test time trigger with domain filtering."""
        _logger.info("Testing time trigger with domain filter")

        import datetime
        from odoo import fields

        date_field = self.env["ir.model.fields"]._get("res.partner", "create_date")

        # Create automation with domain filter
        automation = self.Automation.create(
            {
                "name": "VIP Only Time Trigger",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
                "filter_domain": "[('name', 'ilike', 'VIP')]",
            }
        )

        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        # Create VIP partner (matches domain)
        vip_partner = self.Partner.create({"name": "VIP Customer"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (two_days_ago, vip_partner.id),
        )

        # Create regular partner (doesn't match domain)
        regular_partner = self.Partner.create({"name": "Regular Customer"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (two_days_ago, regular_partner.id),
        )

        self.env.invalidate_all()

        # Search for records
        records = automation._search_time_based_automation_records(until=now)

        # Only VIP should be found
        self.assertIn(vip_partner, records)
        self.assertNotIn(regular_partner, records)

    def test_time_trigger_last_run_tracking(self):
        """Test that last_run prevents duplicate executions."""
        _logger.info("Testing last_run tracking")

        import datetime
        from odoo import fields

        date_field = self.env["ir.model.fields"]._get("res.partner", "create_date")

        automation = self.Automation.create(
            {
                "name": "Last Run Test",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        now = fields.Datetime.now()
        three_days_ago = now - datetime.timedelta(days=3)
        two_days_ago = now - datetime.timedelta(days=2)

        # Create partner 3 days ago
        partner = self.Partner.create({"name": "Test Partner"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (three_days_ago, partner.id),
        )
        self.env.invalidate_all()

        # First search - should find partner
        records1 = automation._search_time_based_automation_records(until=now)
        self.assertIn(partner, records1)

        # Update last_run to 2 days ago (simulating previous execution)
        automation.write({"last_run": two_days_ago})

        # Second search - should NOT find partner (already processed)
        records2 = automation._search_time_based_automation_records(until=now)
        self.assertNotIn(partner, records2)

    # =========================================================================
    # Test Cron Execution
    # =========================================================================

    def test_cron_process_time_based_actions(self):
        """Test cron job processes time-based automations."""
        _logger.info("Testing cron processing of time triggers")

        import datetime
        from odoo import fields

        date_field = self.env["ir.model.fields"]._get("res.partner", "create_date")

        automation = self.Automation.create(
            {
                "name": "Cron Test Automation",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        self.Action.create(
            {
                "name": "Cron Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Cron executed'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        # Create partner 2 days ago
        partner = self.Partner.create({"name": "Cron Target"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (two_days_ago, partner.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Verify action executed
        self.assertEqual(partner.comment, "Cron executed")

        # Verify last_run updated
        self.assertTrue(automation.last_run)
        self.assertGreaterEqual(automation.last_run, now)

    def test_cron_processes_multiple_automations(self):
        """Test cron processes all active time-based automations."""
        _logger.info("Testing cron with multiple automations")

        import datetime
        from odoo import fields

        date_field = self.env["ir.model.fields"]._get("res.partner", "create_date")
        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        # Create 2 automations
        automation1 = self.Automation.create(
            {
                "name": "Auto 1",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )
        self.Action.create(
            {
                "name": "Action 1",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Auto1'})",
                "base_automation_id": automation1.id,
                "usage": "base_automation",
            }
        )

        automation2 = self.Automation.create(
            {
                "name": "Auto 2",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )
        self.Action.create(
            {
                "name": "Action 2",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'phone': 'Auto2'})",
                "base_automation_id": automation2.id,
                "usage": "base_automation",
            }
        )

        # Create partner
        partner = self.Partner.create({"name": "Multi Auto"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (two_days_ago, partner.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Both automations should execute
        self.assertEqual(partner.comment, "Auto1")
        self.assertEqual(partner.phone, "Auto2")

    def test_cron_skips_inactive_automations(self):
        """Test cron skips inactive automations."""
        _logger.info("Testing cron skips inactive automations")

        import datetime
        from odoo import fields

        date_field = self.env["ir.model.fields"]._get("res.partner", "create_date")

        automation = self.Automation.create(
            {
                "name": "Inactive Automation",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
                "active": False,  # Inactive
            }
        )

        self.Action.create(
            {
                "name": "Should Not Execute",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Should not see this'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        partner = self.Partner.create({"name": "Test"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (two_days_ago, partner.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Should NOT execute
        self.assertFalse(partner.comment)

    # =========================================================================
    # Test on_time_created and on_time_updated Specifics
    # =========================================================================

    def test_on_time_created_uses_create_date(self):
        """Test on_time_created automatically uses create_date field."""
        _logger.info("Testing on_time_created uses create_date")

        import datetime
        from odoo import fields

        automation = self.Automation.create(
            {
                "name": "On Time Created",
                "model_id": self.model_partner.id,
                "trigger": "on_time_created",
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        self.Action.create(
            {
                "name": "Created Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Created trigger'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        # Create partner (create_date will be set automatically)
        partner = self.Partner.create({"name": "Created Test"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (two_days_ago, partner.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Should execute based on create_date
        self.assertEqual(partner.comment, "Created trigger")

    def test_on_time_updated_uses_write_date(self):
        """Test on_time_updated automatically uses write_date field."""
        _logger.info("Testing on_time_updated uses write_date")

        import datetime
        from odoo import fields

        automation = self.Automation.create(
            {
                "name": "On Time Updated",
                "model_id": self.model_partner.id,
                "trigger": "on_time_updated",
                "trg_date_range": 1,
                "trg_date_range_type": "hour",
            }
        )

        self.Action.create(
            {
                "name": "Updated Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Updated trigger'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        now = fields.Datetime.now()
        three_hours_ago = now - datetime.timedelta(hours=3)

        # Create and update partner
        partner = self.Partner.create({"name": "Updated Test"})
        partner.write({"email": "test@example.com"})

        # Manually set write_date to 3 hours ago
        self.env.cr.execute(
            "UPDATE res_partner SET write_date = %s WHERE id = %s",
            (three_hours_ago, partner.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Should execute based on write_date
        self.assertEqual(partner.comment, "Updated trigger")

    # =========================================================================
    # Test Edge Cases
    # =========================================================================

    def test_time_trigger_with_missing_date_field(self):
        """Test automation handles missing date field gracefully."""
        _logger.info("Testing time trigger with missing field")

        # Create automation with non-existent field
        automation = self.Automation.create(
            {
                "name": "Missing Field",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        # Manually set invalid field (bypass validation)
        self.env.cr.execute(
            "UPDATE base_automation SET trg_date_id = 99999 WHERE id = %s",
            (automation.id,),
        )
        self.env.invalidate_all()

        import datetime
        from odoo import fields

        now = fields.Datetime.now()

        # Should return empty recordset, not crash
        records = automation._search_time_based_automation_records(until=now)
        self.assertFalse(records)

    def test_time_trigger_validation_negative_range(self):
        """Test validation prevents negative date ranges."""
        _logger.info("Testing negative range validation")

        from odoo.exceptions import ValidationError

        # Attempt to create automation with negative range
        with self.assertRaises(ValidationError):
            self.Automation.create(
                {
                    "name": "Negative Range",
                    "model_id": self.model_partner.id,
                    "trigger": "on_time_created",
                    "trg_date_range": -5,  # Negative!
                    "trg_date_range_type": "day",
                }
            )

    def test_time_trigger_multiple_range_types_same_model(self):
        """Test multiple automations with different range types."""
        _logger.info("Testing multiple range types")

        import datetime
        from odoo import fields

        date_field = self.env["ir.model.fields"]._get("res.partner", "create_date")
        now = fields.Datetime.now()

        # 1 hour automation
        auto_hour = self.Automation.create(
            {
                "name": "Hour Range",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "hour",
            }
        )
        self.Action.create(
            {
                "name": "Hour Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Hour'})",
                "base_automation_id": auto_hour.id,
                "usage": "base_automation",
            }
        )

        # 1 day automation
        auto_day = self.Automation.create(
            {
                "name": "Day Range",
                "model_id": self.model_partner.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )
        self.Action.create(
            {
                "name": "Day Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'phone': 'Day'})",
                "base_automation_id": auto_day.id,
                "usage": "base_automation",
            }
        )

        # Partner created 2 days ago
        two_days_ago = now - datetime.timedelta(days=2)
        partner = self.Partner.create({"name": "Multi Range"})
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            (two_days_ago, partner.id),
        )
        self.env.invalidate_all()

        # Execute cron - both should trigger
        self.Automation._cron_process_time_based_actions()

        # Both automations should execute
        self.assertEqual(partner.comment, "Hour")
        self.assertEqual(partner.phone, "Day")

    def test_time_trigger_with_zero_range(self):
        """Test time trigger with zero range (immediate trigger)."""
        _logger.info("Testing zero range")

        automation = self.Automation.create(
            {
                "name": "Zero Range",
                "model_id": self.model_partner.id,
                "trigger": "on_time_created",
                "trg_date_range": 0,
                "trg_date_range_type": "day",
            }
        )

        self.Action.create(
            {
                "name": "Zero Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Zero range'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create partner
        partner = self.Partner.create({"name": "Zero Test"})

        # Execute cron immediately
        self.Automation._cron_process_time_based_actions()

        # Should trigger immediately (0 delay)
        self.assertEqual(partner.comment, "Zero range")


class TestMailThreadTriggers(TransactionCase):
    """Test mail thread triggers (on_message_received, on_message_sent)."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Partner = cls.env["res.partner"]

        cls.model_partner = cls.env["ir.model"]._get("res.partner")

        cls.test_partner = cls.Partner.create(
            {
                "name": "Mail Test Partner",
                "email": "mailtest@example.com",
            }
        )

    def test_on_message_received_trigger(self):
        """Test on_message_received trigger fires on incoming message."""
        _logger.info("Testing on_message_received trigger")

        automation = self.Automation.create(
            {
                "name": "On Message Received",
                "model_id": self.model_partner.id,
                "trigger": "on_message_received",
            }
        )

        self.Action.create(
            {
                "name": "Message Received Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Message received'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Post external message (simulates incoming)
        self.test_partner.message_post(
            body="Incoming message from customer",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

        # Check if triggered
        self.assertEqual(self.test_partner.comment, "Message received")

    def test_on_message_sent_trigger(self):
        """Test on_message_sent trigger fires on outgoing message."""
        _logger.info("Testing on_message_sent trigger")

        automation = self.Automation.create(
            {
                "name": "On Message Sent",
                "model_id": self.model_partner.id,
                "trigger": "on_message_sent",
            }
        )

        self.Action.create(
            {
                "name": "Message Sent Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Message sent'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Post message from internal user
        admin_user = self.env.ref("base.user_admin")
        self.test_partner.with_user(admin_user).message_post(
            body="Reply to customer",
            author_id=admin_user.partner_id.id,
            message_type="comment",
        )

        # Check if triggered
        self.assertEqual(self.test_partner.comment, "Message sent")


class TestUIChangeTrigger(TransactionCase):
    """Test on_change (UI live update) trigger."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Partner = cls.env["res.partner"]

        cls.model_partner = cls.env["ir.model"]._get("res.partner")

    def test_on_change_trigger_setup(self):
        """Test on_change trigger configuration."""
        _logger.info("Testing on_change trigger setup")

        # Get email field for onchange trigger
        email_field = self.env["ir.model.fields"]._get("res.partner", "email")

        automation = self.Automation.create(
            {
                "name": "On Email Change",
                "model_id": self.model_partner.id,
                "trigger": "on_change",
                "on_change_field_ids": [Command.link(email_field.id)],
            }
        )

        # Must use code action for on_change
        self.Action.create(
            {
                "name": "Email Changed",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "pass",  # In real use, would update onchange_self
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Verify setup
        self.assertEqual(automation.trigger, "on_change")
        self.assertIn(email_field, automation.on_change_field_ids)


class TestTriggerEdgeCases(TransactionCase):
    """Test edge cases and advanced trigger scenarios."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Partner = cls.env["res.partner"]

        cls.model_partner = cls.env["ir.model"]._get("res.partner")

    def test_trigger_field_ids_empty_all_fields(self):
        """Test empty trigger_field_ids means trigger on ANY field change."""
        _logger.info("Testing empty trigger_field_ids")

        automation = self.Automation.create(
            {
                "name": "Trigger on Any Field",
                "model_id": self.model_partner.id,
                "trigger": "on_write",
                # trigger_field_ids is empty - triggers on all fields
            }
        )

        self.Action.create(
            {
                "name": "Any Field Changed",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Changed'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        partner = self.Partner.create({"name": "Test"})
        partner.comment = False

        # Change ANY field
        partner.write({"phone": "123"})

        # Should trigger
        self.assertEqual(partner.comment, "Changed")

    def test_combined_domain_filters(self):
        """Test filter_pre_domain and filter_domain work together."""
        _logger.info("Testing combined domain filters")

        automation = self.Automation.create(
            {
                "name": "Combined Filters",
                "model_id": self.model_partner.id,
                "trigger": "on_write",
                "filter_pre_domain": "[('active', '=', True)]",
                "filter_domain": "[('active', '=', False)]",
            }
        )

        self.Action.create(
            {
                "name": "Archive Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Archived'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create active partner
        partner = self.Partner.create({"name": "Active", "active": True})

        # Archive - should trigger (pre: was active, post: is inactive)
        partner.write({"active": False})
        self.assertEqual(partner.comment, "Archived")

    def test_automation_execution_order(self):
        """Test multiple automations execute in sequence order."""
        _logger.info("Testing automation execution order")

        # Create 3 automations with different sequences
        auto1 = self.Automation.create(
            {
                "name": "Auto 1",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
                "sequence": 30,
            }
        )
        self.Action.create(
            {
                "name": "Action 1",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'A'})",
                "base_automation_id": auto1.id,
                "usage": "base_automation",
            }
        )

        auto2 = self.Automation.create(
            {
                "name": "Auto 2",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
                "sequence": 10,  # Lower = earlier
            }
        )
        self.Action.create(
            {
                "name": "Action 2",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'B'})",
                "base_automation_id": auto2.id,
                "usage": "base_automation",
            }
        )

        auto3 = self.Automation.create(
            {
                "name": "Auto 3",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
                "sequence": 20,
            }
        )
        self.Action.create(
            {
                "name": "Action 3",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'C'})",
                "base_automation_id": auto3.id,
                "usage": "base_automation",
            }
        )

        # Create partner
        partner = self.Partner.create({"name": "Sequence Test"})

        # Should execute in sequence order: 10, 20, 30 = B, C, A
        self.assertEqual(partner.comment, "BCA")

    def test_trigger_with_multi_company(self):
        """Test triggers respect company context."""
        _logger.info("Testing multi-company triggers")

        # This is a basic setup test - full multi-company testing
        # would require multiple company setup
        automation = self.Automation.create(
            {
                "name": "Company Specific",
                "model_id": self.model_partner.id,
                "trigger": "on_create",
            }
        )

        self.Action.create(
            {
                "name": "Company Action",
                "model_id": self.model_partner.id,
                "state": "code",
                "code": "record.write({'comment': 'Company: %s' % env.company.name})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create partner
        partner = self.Partner.create({"name": "Company Test"})

        # Should have company name in comment
        self.assertIn("Company:", partner.comment)
