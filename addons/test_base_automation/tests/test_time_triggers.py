# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Comprehensive tests for time-based automation triggers.

Tests cover:
- on_time (custom date field)
- on_time_created (automatic create_date)
- on_time_updated (automatic write_date)
- Cron processing
- Domain filtering
- Last run tracking
- Edge cases
"""

import datetime
import logging

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestTimeBasedTriggers(common.TransactionCase):
    """Test time-based triggers (on_time, on_time_created, on_time_updated)."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        cls.Automation = cls.env["base.automation"]
        cls.Action = cls.env["ir.actions.server"]
        cls.Lead = cls.env["base.automation.lead.test"]

        cls.model_lead = cls.env["ir.model"]._get("base.automation.lead.test")

    # =========================================================================
    # Test Basic Time Trigger Setup
    # =========================================================================

    def test_on_time_trigger_setup(self):
        """Test on_time trigger configuration."""
        _logger.info("Testing on_time trigger setup")

        # Get date field
        date_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "create_date"
        )

        # Create automation that triggers 1 day after creation
        automation = self.Automation.create(
            {
                "name": "One Day After Creation",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        self.Action.create(
            {
                "name": "Time Trigger Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'One day passed'})",
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
                "model_id": self.model_lead.id,
                "trigger": "on_time_created",
                "trg_date_range": 2,
                "trg_date_range_type": "hour",
            }
        )

        self.Action.create(
            {
                "name": "After Creation Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': '2 hours passed'})",
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
                "model_id": self.model_lead.id,
                "trigger": "on_time_updated",
                "trg_date_range": 30,
                "trg_date_range_type": "minutes",
            }
        )

        self.Action.create(
            {
                "name": "After Update Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': '30 minutes since update'})",
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
                    "model_id": self.model_lead.id,
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

        # Get create_date field
        date_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "create_date"
        )

        # Create automation: 1 day after create_date
        automation = self.Automation.create(
            {
                "name": "1 Day After",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        # Create leads at different times
        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)
        one_day_ago = now - datetime.timedelta(days=1, hours=1)
        one_hour_ago = now - datetime.timedelta(hours=1)

        # Lead created 2 days ago - SHOULD be found (1 day trigger passed)
        lead1 = self.Lead.create({"name": "Old Lead"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (two_days_ago, lead1.id),
        )

        # Lead created 1 day ago - SHOULD be found
        lead2 = self.Lead.create({"name": "Recent Lead"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (one_day_ago, lead2.id),
        )

        # Lead created 1 hour ago - should NOT be found (too recent)
        lead3 = self.Lead.create({"name": "Very Recent Lead"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (one_hour_ago, lead3.id),
        )

        # Invalidate cache to reflect DB changes
        self.env.invalidate_all()

        # Search for records
        records = automation._search_time_based_automation_records(until=now)

        # Verify results
        self.assertIn(lead1, records)
        self.assertIn(lead2, records)
        self.assertNotIn(lead3, records)

    def test_search_time_based_records_with_domain_filter(self):
        """Test time trigger with domain filtering."""
        _logger.info("Testing time trigger with domain filter")

        date_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "create_date"
        )

        # Create automation with domain filter
        automation = self.Automation.create(
            {
                "name": "Priority Only Time Trigger",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
                "filter_domain": "[('priority', '=', True)]",
            }
        )

        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        # Create priority lead (matches domain)
        priority_lead = self.Lead.create({"name": "Priority Lead", "priority": True})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (two_days_ago, priority_lead.id),
        )

        # Create regular lead (doesn't match domain)
        regular_lead = self.Lead.create({"name": "Regular Lead", "priority": False})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (two_days_ago, regular_lead.id),
        )

        self.env.invalidate_all()

        # Search for records
        records = automation._search_time_based_automation_records(until=now)

        # Only priority lead should be found
        self.assertIn(priority_lead, records)
        self.assertNotIn(regular_lead, records)

    def test_time_trigger_last_run_tracking(self):
        """Test that last_run prevents duplicate executions."""
        _logger.info("Testing last_run tracking")

        date_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "create_date"
        )

        automation = self.Automation.create(
            {
                "name": "Last Run Test",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        now = fields.Datetime.now()
        three_days_ago = now - datetime.timedelta(days=3)
        two_days_ago = now - datetime.timedelta(days=2)

        # Create lead 3 days ago
        lead = self.Lead.create({"name": "Test Lead"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (three_days_ago, lead.id),
        )
        self.env.invalidate_all()

        # First search - should find lead
        records1 = automation._search_time_based_automation_records(until=now)
        self.assertIn(lead, records1)

        # Update last_run to 2 days ago (simulating previous execution)
        automation.write({"last_run": two_days_ago})

        # Second search - should NOT find lead (already processed)
        records2 = automation._search_time_based_automation_records(until=now)
        self.assertNotIn(lead, records2)

    # =========================================================================
    # Test Cron Execution
    # =========================================================================

    def test_cron_process_time_based_actions(self):
        """Test cron job processes time-based automations."""
        _logger.info("Testing cron processing of time triggers")

        date_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "create_date"
        )

        automation = self.Automation.create(
            {
                "name": "Cron Test Automation",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        self.Action.create(
            {
                "name": "Cron Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Cron executed'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        # Create lead 2 days ago
        lead = self.Lead.create({"name": "Cron Target"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (two_days_ago, lead.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Verify action executed
        self.assertEqual(lead.name, "Cron executed")

        # Verify last_run updated
        self.assertTrue(automation.last_run)
        self.assertGreaterEqual(automation.last_run, now)

    def test_cron_processes_multiple_automations(self):
        """Test cron processes all active time-based automations."""
        _logger.info("Testing cron with multiple automations")

        date_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "create_date"
        )
        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        # Create 2 automations
        automation1 = self.Automation.create(
            {
                "name": "Auto 1",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )
        self.Action.create(
            {
                "name": "Action 1",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Auto1'})",
                "base_automation_id": automation1.id,
                "usage": "base_automation",
            }
        )

        automation2 = self.Automation.create(
            {
                "name": "Auto 2",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )
        self.Action.create(
            {
                "name": "Action 2",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'state': 'open'})",
                "base_automation_id": automation2.id,
                "usage": "base_automation",
            }
        )

        # Create lead
        lead = self.Lead.create({"name": "Multi Auto", "state": "draft"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (two_days_ago, lead.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Both automations should execute
        self.assertEqual(lead.name, "Auto1")
        self.assertEqual(lead.state, "open")

    def test_cron_skips_inactive_automations(self):
        """Test cron skips inactive automations."""
        _logger.info("Testing cron skips inactive automations")

        date_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "create_date"
        )

        automation = self.Automation.create(
            {
                "name": "Inactive Automation",
                "model_id": self.model_lead.id,
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
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Should not see this'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        lead = self.Lead.create({"name": "Test Lead"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (two_days_ago, lead.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Should NOT execute
        self.assertEqual(lead.name, "Test Lead")  # Name unchanged

    # =========================================================================
    # Test on_time_created and on_time_updated Specifics
    # =========================================================================

    def test_on_time_created_uses_create_date(self):
        """Test on_time_created automatically uses create_date field."""
        _logger.info("Testing on_time_created uses create_date")

        automation = self.Automation.create(
            {
                "name": "On Time Created",
                "model_id": self.model_lead.id,
                "trigger": "on_time_created",
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )

        self.Action.create(
            {
                "name": "Created Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Created trigger'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        now = fields.Datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)

        # Create lead (create_date will be set automatically)
        lead = self.Lead.create({"name": "Created Test"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (two_days_ago, lead.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Should execute based on create_date
        self.assertEqual(lead.name, "Created trigger")

    def test_on_time_updated_uses_write_date(self):
        """Test on_time_updated automatically uses write_date field."""
        _logger.info("Testing on_time_updated uses write_date")

        automation = self.Automation.create(
            {
                "name": "On Time Updated",
                "model_id": self.model_lead.id,
                "trigger": "on_time_updated",
                "trg_date_range": 1,
                "trg_date_range_type": "hour",
            }
        )

        self.Action.create(
            {
                "name": "Updated Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Updated trigger'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        now = fields.Datetime.now()
        three_hours_ago = now - datetime.timedelta(hours=3)

        # Create and update lead
        lead = self.Lead.create({"name": "Updated Test"})
        lead.write({"state": "open"})

        # Manually set write_date to 3 hours ago
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET write_date = %s WHERE id = %s",
            (three_hours_ago, lead.id),
        )
        self.env.invalidate_all()

        # Execute cron
        self.Automation._cron_process_time_based_actions()

        # Should execute based on write_date
        self.assertEqual(lead.name, "Updated trigger")

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
                "model_id": self.model_lead.id,
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

        now = fields.Datetime.now()

        # Should return empty recordset, not crash
        records = automation._search_time_based_automation_records(until=now)
        self.assertFalse(records)

    def test_time_trigger_validation_negative_range(self):
        """Test validation prevents negative date ranges."""
        _logger.info("Testing negative range validation")

        # Attempt to create automation with negative range
        with self.assertRaises(ValidationError):
            self.Automation.create(
                {
                    "name": "Negative Range",
                    "model_id": self.model_lead.id,
                    "trigger": "on_time_created",
                    "trg_date_range": -5,  # Negative!
                    "trg_date_range_type": "day",
                }
            )

    def test_time_trigger_multiple_range_types_same_model(self):
        """Test multiple automations with different range types."""
        _logger.info("Testing multiple range types")

        date_field = self.env["ir.model.fields"]._get(
            "base.automation.lead.test", "create_date"
        )
        now = fields.Datetime.now()

        # 1 hour automation
        auto_hour = self.Automation.create(
            {
                "name": "Hour Range",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "hour",
            }
        )
        self.Action.create(
            {
                "name": "Hour Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Hour'})",
                "base_automation_id": auto_hour.id,
                "usage": "base_automation",
            }
        )

        # 1 day automation
        auto_day = self.Automation.create(
            {
                "name": "Day Range",
                "model_id": self.model_lead.id,
                "trigger": "on_time",
                "trg_date_id": date_field.id,
                "trg_date_range": 1,
                "trg_date_range_type": "day",
            }
        )
        self.Action.create(
            {
                "name": "Day Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'state': 'open'})",
                "base_automation_id": auto_day.id,
                "usage": "base_automation",
            }
        )

        # Lead created 2 days ago
        two_days_ago = now - datetime.timedelta(days=2)
        lead = self.Lead.create({"name": "Multi Range", "state": "draft"})
        self.env.cr.execute(
            "UPDATE base_automation_lead_test SET create_date = %s WHERE id = %s",
            (two_days_ago, lead.id),
        )
        self.env.invalidate_all()

        # Execute cron - both should trigger
        self.Automation._cron_process_time_based_actions()

        # Both automations should execute
        self.assertEqual(lead.name, "Hour")
        self.assertEqual(lead.state, "open")

    def test_time_trigger_with_zero_range(self):
        """Test time trigger with zero range (immediate trigger)."""
        _logger.info("Testing zero range")

        automation = self.Automation.create(
            {
                "name": "Zero Range",
                "model_id": self.model_lead.id,
                "trigger": "on_time_created",
                "trg_date_range": 0,
                "trg_date_range_type": "day",
            }
        )

        self.Action.create(
            {
                "name": "Zero Action",
                "model_id": self.model_lead.id,
                "state": "code",
                "code": "record.write({'name': 'Zero range'})",
                "base_automation_id": automation.id,
                "usage": "base_automation",
            }
        )

        # Create lead
        lead = self.Lead.create({"name": "Zero Test"})

        # Execute cron immediately
        self.Automation._cron_process_time_based_actions()

        # Should trigger immediately (0 delay)
        self.assertEqual(lead.name, "Zero range")
