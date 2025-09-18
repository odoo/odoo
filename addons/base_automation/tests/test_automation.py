# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestAutomation(TransactionCaseWithUserDemo):

    def test_01_on_create_or_write(self):
        """Simple on_create with admin user"""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Force Archived Contacts",
                "trigger": "on_create_or_write",
                "model_id": model.id,
                "trigger_field_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.field_res_partner__name").id,
                            self.env.ref("base.field_res_partner__vat").id,
                        ],
                    )
                ],
            }
        )

        # trg_field should only be set when trigger is 'on_stage_set' or 'on_tag_set'
        self.assertFalse(automation.trg_field_ref)
        self.assertFalse(automation.trg_field_ref_model_name)

        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Active To False",
                "base_automation_id": automation.id,
                "state": "object_write",
                "update_path": "active",
                "update_boolean_value": "false",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # verify the partner can be created and the action still runs
        bilbo = self.env["res.partner"].create({"name": "Bilbo Baggins"})
        self.assertFalse(bilbo.active)

        # verify the partner can be updated and the action still runs
        bilbo.active = True
        bilbo.name = "Bilbo"
        self.assertFalse(bilbo.active)

    def test_02_on_create_or_write_restricted(self):
        """on_create action with low portal user"""
        model = self.env.ref("base.model_ir_filters")
        automation = self.env["base.automation"].create(
            {
                "name": "Force Archived Filters",
                "trigger": "on_create_or_write",
                "model_id": model.id,
                "trigger_field_ids": [
                    Command.set([self.env.ref("base.field_ir_filters__name").id])
                ],
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Active To False",
                "base_automation_id": automation.id,
                "model_id": model.id,
                "state": "object_write",
                "update_path": "active",
                "update_boolean_value": "false",
            }
        )
        action.flush_recordset()
        automation.write({"action_server_ids": [Command.link(action.id)]})
        # action cached was cached with admin, force CacheMiss
        automation.env.clear()

        self_portal = self.env["ir.filters"].with_user(self.user_demo.id)
        # verify the portal user can create ir.filters but can not read base.automation
        self.assertTrue(self_portal.env["ir.filters"].has_access("create"))
        self.assertFalse(self_portal.env["base.automation"].has_access("read"))

        # verify the filter can be created and the action still runs
        filters = self_portal.create(
            {
                "name": "Where is Bilbo?",
                "domain": "[('name', 'ilike', 'bilbo')]",
                "model_id": "res.partner",
            }
        )
        self.assertFalse(filters.active)

        # verify the filter can be updated and the action still runs
        filters.active = True
        filters.name = "Where is Bilbo Baggins?"
        self.assertFalse(filters.active)

    def test_03_on_change_restricted(self):
        """on_create action with low portal user"""
        model = self.env.ref("base.model_ir_filters")
        automation = self.env["base.automation"].create(
            {
                "name": "Force Archived Filters",
                "trigger": "on_change",
                "model_id": model.id,
                "on_change_field_ids": [
                    Command.set([self.env.ref("base.field_ir_filters__name").id])
                ],
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Active To False",
                "base_automation_id": automation.id,
                "model_id": model.id,
                "state": "code",
                "code": """action = {'value': {'active': False}}""",
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})
        # action cached was cached with admin, force CacheMiss
        automation.env.clear()

        self_portal = self.env["ir.filters"].with_user(self.user_demo.id)

        # simulate a onchange call on name
        result = self_portal.onchange({}, [], {"name": {}, "active": {}})
        self.assertEqual(result["value"]["active"], False)

    def test_04_on_create_or_write_differentiate(self):
        """
        The purpose is to differentiate create and empty write.
        """
        model = self.env.ref("base.model_res_partner")
        model_field_id = self.env["ir.model.fields"].search(
            [("model", "=", model.model), ("name", "=", "id")], limit=1
        )
        automation = self.env["base.automation"].create(
            {
                "name": "Test automated action",
                "trigger": "on_create_or_write",
                "model_id": model.id,
                "trigger_field_ids": [Command.set([model_field_id.id])],
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Modify name",
                "base_automation_id": automation.id,
                "model_id": model.id,
                "state": "code",
                "code": "record.write({'name': 'Modified Name'})",
            }
        )
        action.flush_recordset()
        automation.write({"action_server_ids": [Command.link(action.id)]})
        # action cached was cached with admin, force CacheMiss
        automation.env.clear()

        server_action = self.env["ir.actions.server"].create(
            {
                "name": "Empty write",
                "model_id": model.id,
                "state": "code",
                "code": "record.write({})",
            }
        )

        partner = self.env[model.model].create({"name": "Test Name"})
        self.assertEqual(
            partner.name, "Modified Name", "The automatic action must be performed"
        )
        partner.name = "Reset Name"
        self.assertEqual(
            partner.name, "Reset Name", "The automatic action must not be performed"
        )

        context = {
            "active_model": model.model,
            "active_id": partner.id,
        }
        server_action.with_context(context).run()
        self.assertEqual(
            partner.name, "Reset Name", "The automatic action must not be performed"
        )

    def test_create_automation_rule_for_valid_model(self):
        """
        Automation rules cannot be created for models that have no fields.
        """
        model_field = self.env["base.automation"]._fields["model_id"]
        base_model = self.env["base"]

        # Verify that the base model is abstract and has _auto set to False
        self.assertTrue(base_model._abstract, "The base model should be abstract")
        self.assertFalse(
            base_model._auto, "The base model should have _auto set to False"
        )

        # check whether the field hase domain attribute
        self.assertTrue(model_field.domain)
        domain = model_field.domain

        allowed_models = self.env["ir.model"].search(domain)
        self.assertTrue(
            base_model._name not in allowed_models.mapped("model"),
            "The base model should not be in the allowed models",
        )

    def test_scheduled_action_updates_for_timebased_automations(self):
        cron = self.env.ref("base_automation.ir_cron_data_base_automation_check")
        self.assertRecordValues(
            cron,
            [
                {
                    "active": False,
                    "interval_type": "hours",
                    "interval_number": 4,
                }
            ],
        )

        # Create a time-based automation
        automation1 = self.env["base.automation"].create(
            {
                "active": True,
                "name": "Automation 1",
                "trigger": "on_time",
                "model_id": self.env.ref("base.model_res_partner").id,
                "trg_date_range": 2,
                "trg_date_range_type": "hour",
                "trg_date_range_mode": "before",
                # of course the chosen field does not really make sense here, but hey its testing data
                "trg_date_id": self.env.ref("base.field_res_partner__write_date").id,
            }
        )
        self.assertRecordValues(
            cron,
            [
                {
                    "active": True,
                    "interval_type": "minutes",
                    "interval_number": 12,  # 10% of automation1 delay
                }
            ],
        )

        automation2 = self.env["base.automation"].create(
            {
                "active": True,
                "name": "Automation 2",
                "trigger": "on_time_created",
                "model_id": self.env.ref("base.model_res_partner").id,
                "trg_date_range": 1,
                "trg_date_range_type": "hour",
            }
        )
        self.assertRecordValues(
            cron,
            [
                {
                    "active": True,
                    "interval_type": "minutes",
                    "interval_number": 6,  # 10% of automation2 delay
                }
            ],
        )

        # Disable automation2
        automation2.active = False
        self.assertRecordValues(
            cron,
            [
                {
                    "active": True,
                    "interval_type": "minutes",
                    "interval_number": 6,  # did not change as the new delay is higher
                }
            ],
        )

        # Disable automation1
        automation1.active = False
        self.assertRecordValues(
            cron,
            [
                {
                    "active": False,
                    "interval_type": "minutes",
                    "interval_number": 6,  # did not change as the new delay is higher
                }
            ],
        )

        # Enable automation1 and automation2
        automation1.active = True
        automation2.active = True
        self.assertRecordValues(
            cron,
            [
                {
                    "active": True,
                    "interval_type": "minutes",
                    "interval_number": 6,  # still 10% of automation2 delay
                }
            ],
        )

        # Create another automation with no delay
        self.env["base.automation"].create(
            {
                "active": True,
                "name": "Automation 3",
                "trigger": "on_time_created",
                "model_id": self.env.ref("base.model_res_partner").id,
                "trg_date_range": 0,
                "trg_date_range_type": "hour",
            }
        )
        self.assertRecordValues(
            cron,
            [
                {
                    "active": True,
                    "interval_type": "minutes",
                    "interval_number": 6,  # should have not changed either
                }
            ],
        )

    def test_computed_on_scheduled_action(self):
        with Form(
            self.env["base.automation"],
            view="base_automation.view_base_automation_form",
        ) as f:
            f.name = "Test Automation"
            f.model_id = self.env.ref("base.model_res_partner")
            f.trigger = "on_time"
            f.trg_date_range = 2
            f.trg_date_range_type = "hour"
            f.trg_date_range_mode = "after"
            f.trg_date_id = self.env.ref("base.field_res_partner__write_date")
            # Negate trg_date_range should toggle trg_date_range_mode
            f.trg_date_range = -2
            self.assertEqual(f.trg_date_range_mode, "before")
            self.assertEqual(f.trg_date_range, 2)
            # Change without negating should not toggle trg_date_range_mode
            f.trg_date_range = 3
            self.assertEqual(f.trg_date_range_mode, "before")
            self.assertEqual(f.trg_date_range, 3)
            # Negate trg_date_range should toggle trg_date_range_mode
            f.trg_date_range = -3
            self.assertEqual(f.trg_date_range_mode, "after")
            self.assertEqual(f.trg_date_range, 3)
            # Change without negating should not toggle trg_date_range_mode
            f.trg_date_range = 2
            self.assertEqual(f.trg_date_range_mode, "after")
            self.assertEqual(f.trg_date_range, 2)

    # =========================================================================
    # Domain Filtering Tests
    # =========================================================================

    def test_domain_filtering_on_create(self):
        """Test filter_domain works correctly on create."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Filter VIP Only",
                "trigger": "on_create",
                "model_id": model.id,
                "filter_domain": "[('name', 'ilike', 'VIP')]",
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Mark as Company",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'is_company': True})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Create non-VIP partner - should NOT trigger
        regular = self.env["res.partner"].create({"name": "Regular Customer"})
        self.assertFalse(regular.is_company)

        # Create VIP partner - SHOULD trigger
        vip = self.env["res.partner"].create({"name": "VIP Customer"})
        self.assertTrue(vip.is_company)

    def test_filter_pre_domain_on_write(self):
        """Test filter_pre_domain checks condition before update."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Track Active to Inactive",
                "trigger": "on_write",
                "model_id": model.id,
                "filter_pre_domain": "[('active', '=', True)]",
                "filter_domain": "[('active', '=', False)]",
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': 'Was archived'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Create active partner
        partner = self.env["res.partner"].create({"name": "Test", "active": True})

        # Archive it - should trigger (pre: active, post: inactive)
        partner.write({"active": False})
        self.assertEqual(partner.comment, "Was archived")

        # Reactivate - should NOT trigger (pre: inactive, not matching)
        partner.comment = False
        partner.write({"active": True})
        self.assertFalse(partner.comment)

    def test_complex_domain_with_multiple_conditions(self):
        """Test complex domain with AND/OR conditions."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Complex Filter",
                "trigger": "on_create",
                "model_id": model.id,
                "filter_domain": "[('is_company', '=', True), ('email', '!=', False)]",
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Phone",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'phone': '555-0000'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Not company with email - should NOT trigger
        p1 = self.env["res.partner"].create(
            {"name": "Individual", "is_company": False, "email": "test@example.com"}
        )
        self.assertFalse(p1.phone)

        # Company without email - should NOT trigger
        p2 = self.env["res.partner"].create({"name": "Company", "is_company": True})
        self.assertFalse(p2.phone)

        # Company with email - SHOULD trigger
        p3 = self.env["res.partner"].create(
            {"name": "Company", "is_company": True, "email": "company@example.com"}
        )
        self.assertEqual(p3.phone, "555-0000")

    # =========================================================================
    # Action Type Tests
    # =========================================================================

    def test_code_action_execution(self):
        """Test Python code action executes correctly."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Code Action Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Complex Code",
                "base_automation_id": automation.id,
                "state": "code",
                "code": """
# Complex Python code
partner_name = record.name.upper()
record.write({
    'comment': f'Created: {partner_name}',
    'phone': '123-456-7890',
})
""",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test Partner"})
        self.assertEqual(partner.comment, "Created: TEST PARTNER")
        self.assertEqual(partner.phone, "123-456-7890")

    def test_object_write_action(self):
        """Test object_write action type."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Object Write Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Company",
                "base_automation_id": automation.id,
                "state": "object_write",
                "update_path": "is_company",
                "update_boolean_value": "true",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})
        self.assertTrue(partner.is_company)

    def test_multiple_actions_execution_order(self):
        """Test multiple actions execute in sequence order."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Multi Action Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )

        # Create actions with different sequences
        action1 = self.env["ir.actions.server"].create(
            {
                "name": "Action 1",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'A'})",
                "model_id": model.id,
                "sequence": 30,
            }
        )
        action2 = self.env["ir.actions.server"].create(
            {
                "name": "Action 2",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'B'})",
                "model_id": model.id,
                "sequence": 10,
            }
        )
        action3 = self.env["ir.actions.server"].create(
            {
                "name": "Action 3",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'C'})",
                "model_id": model.id,
                "sequence": 20,
            }
        )
        automation.write(
            {
                "action_server_ids": [
                    Command.link(action1.id),
                    Command.link(action2.id),
                    Command.link(action3.id),
                ]
            }
        )

        partner = self.env["res.partner"].create({"name": "Test"})
        # Should execute in sequence order: 10, 20, 30 = B, C, A
        self.assertEqual(partner.comment, "BCA")

    # =========================================================================
    # Automation Lifecycle Tests
    # =========================================================================

    def test_automation_activation_deactivation(self):
        """Test automation can be activated and deactivated."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Toggle Test",
                "trigger": "on_create",
                "model_id": model.id,
                "active": False,  # Start inactive
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': 'Triggered'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Create partner - should NOT trigger (automation inactive)
        p1 = self.env["res.partner"].create({"name": "Test 1"})
        self.assertFalse(p1.comment)

        # Activate automation
        automation.write({"active": True})

        # Create partner - SHOULD trigger
        p2 = self.env["res.partner"].create({"name": "Test 2"})
        self.assertEqual(p2.comment, "Triggered")

    def test_automation_update_trigger_type(self):
        """Test automation trigger type can be changed."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Change Trigger Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': 'Triggered'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Test with on_create trigger
        p1 = self.env["res.partner"].create({"name": "Test 1"})
        self.assertEqual(p1.comment, "Triggered")

        # Change to on_write trigger
        automation.write({"trigger": "on_write"})

        # Create should NOT trigger anymore
        p2 = self.env["res.partner"].create({"name": "Test 2"})
        self.assertFalse(p2.comment)

        # Write SHOULD trigger
        p2.write({"name": "Test 2 Updated"})
        self.assertEqual(p2.comment, "Triggered")

    def test_automation_deletion(self):
        """Test automation can be deleted and stops triggering."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Delete Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': 'Triggered'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Verify automation works
        p1 = self.env["res.partner"].create({"name": "Test 1"})
        self.assertEqual(p1.comment, "Triggered")

        # Delete automation
        automation.unlink()

        # Should not trigger anymore
        p2 = self.env["res.partner"].create({"name": "Test 2"})
        self.assertFalse(p2.comment)

    # =========================================================================
    # Trigger Field Filtering Tests
    # =========================================================================

    def test_trigger_specific_fields_only(self):
        """Test trigger_field_ids filters to specific fields."""
        model = self.env.ref("base.model_res_partner")
        email_field = self.env.ref("base.field_res_partner__email")

        automation = self.env["base.automation"].create(
            {
                "name": "Email Change Only",
                "trigger": "on_write",
                "model_id": model.id,
                "trigger_field_ids": [Command.set([email_field.id])],
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': 'Email changed'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})

        # Change name - should NOT trigger
        partner.write({"name": "New Name"})
        self.assertFalse(partner.comment)

        # Change email - SHOULD trigger
        partner.write({"email": "test@example.com"})
        self.assertEqual(partner.comment, "Email changed")

    def test_trigger_multiple_fields(self):
        """Test trigger_field_ids with multiple fields."""
        model = self.env.ref("base.model_res_partner")
        name_field = self.env.ref("base.field_res_partner__name")
        email_field = self.env.ref("base.field_res_partner__email")

        automation = self.env["base.automation"].create(
            {
                "name": "Name or Email Change",
                "trigger": "on_write",
                "model_id": model.id,
                "trigger_field_ids": [Command.set([name_field.id, email_field.id])],
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': 'Triggered'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})

        # Change phone - should NOT trigger
        partner.write({"phone": "123-456"})
        self.assertFalse(partner.comment)

        # Change name - SHOULD trigger
        partner.write({"name": "New Name"})
        self.assertEqual(partner.comment, "Triggered")

        partner.comment = False

        # Change email - SHOULD trigger
        partner.write({"email": "test@example.com"})
        self.assertEqual(partner.comment, "Triggered")

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    def test_action_error_does_not_break_record_creation(self):
        """Test that action errors don't prevent record creation."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Failing Action",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Fail",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "raise Exception('Test error')",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Should raise exception
        with self.assertRaises(Exception):
            self.env["res.partner"].create({"name": "Test"})

    def test_invalid_code_in_action(self):
        """Test invalid Python code in action."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Invalid Code",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Bad Code",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "invalid python syntax !!!",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Should raise syntax error
        with self.assertRaises(SyntaxError):
            self.env["res.partner"].create({"name": "Test"})

    # =========================================================================
    # Model Validation Tests
    # =========================================================================

    def test_automation_model_consistency(self):
        """Test automation and action must have same model."""
        partner_model = self.env.ref("base.model_res_partner")
        country_model = self.env.ref("base.model_res_country")

        automation = self.env["base.automation"].create(
            {
                "name": "Model Consistency Test",
                "trigger": "on_create",
                "model_id": partner_model.id,
            }
        )

        # Create action with different model - should show warning
        action = self.env["ir.actions.server"].create(
            {
                "name": "Wrong Model",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "pass",
                "model_id": country_model.id,
            }
        )

        # Check warning exists
        warnings = action._get_warning_messages()
        self.assertTrue(any("should match" in w for w in warnings))

    def test_automation_cannot_be_created_for_abstract_model(self):
        """Test automation cannot use abstract models."""
        model_field = self.env["base.automation"]._fields["model_id"]
        domain = model_field.domain

        # Get all allowed models
        allowed_models = self.env["ir.model"].search(domain)
        allowed_model_names = allowed_models.mapped("model")

        # Verify 'base' (abstract model) is not in allowed list
        self.assertNotIn("base", allowed_model_names)

    # =========================================================================
    # Performance and Bulk Operation Tests
    # =========================================================================

    def test_automation_with_bulk_create(self):
        """Test automation works with bulk record creation."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Bulk Create Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Mark Company",
                "base_automation_id": automation.id,
                "state": "object_write",
                "update_path": "is_company",
                "update_boolean_value": "true",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Create 10 partners at once
        partners = self.env["res.partner"].create(
            [{"name": f"Partner {i}"} for i in range(10)]
        )

        # All should be marked as company
        self.assertTrue(all(p.is_company for p in partners))

    def test_automation_with_bulk_write(self):
        """Test automation works with bulk record updates."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Bulk Write Test",
                "trigger": "on_write",
                "model_id": model.id,
                "trigger_field_ids": [
                    Command.set([self.env.ref("base.field_res_partner__email").id])
                ],
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': 'Email updated'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # Create 5 partners
        partners = self.env["res.partner"].create(
            [{"name": f"Partner {i}"} for i in range(5)]
        )

        # Bulk update email
        partners.write({"email": "bulk@example.com"})

        # All should have comment set
        self.assertTrue(all(p.comment == "Email updated" for p in partners))

    # =========================================================================
    # Context and Environment Tests
    # =========================================================================

    def test_automation_respects_company_context(self):
        """Test automation respects company context."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Company Context Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Store Company",
                "base_automation_id": automation.id,
                "state": "code",
                "code": "record.write({'comment': env.company.name})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})
        # Should have company name from environment
        self.assertTrue(partner.comment)

    def test_automation_access_to_env_variables(self):
        """Test action code has access to environment variables."""
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create(
            {
                "name": "Env Access Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Use Env",
                "base_automation_id": automation.id,
                "state": "code",
                "code": """
# Test access to environment
user = env.user
partner_count = env['res.partner'].search_count([])
record.write({'comment': f'User: {user.name}, Count: {partner_count}'})
""",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})
        # Should have environment info
        self.assertIn("User:", partner.comment)
        self.assertIn("Count:", partner.comment)

    # =========================================================================
    # Sequence and Ordering Tests
    # =========================================================================

    def test_automation_sequence_ordering(self):
        """Test multiple automations execute in sequence order."""
        model = self.env.ref("base.model_res_partner")

        # Create 3 automations with different sequences
        auto1 = self.env["base.automation"].create(
            {
                "name": "Auto 1",
                "trigger": "on_create",
                "model_id": model.id,
                "sequence": 30,
            }
        )
        action1 = self.env["ir.actions.server"].create(
            {
                "name": "Action 1",
                "base_automation_id": auto1.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'A'})",
                "model_id": model.id,
            }
        )
        auto1.write({"action_server_ids": [Command.link(action1.id)]})

        auto2 = self.env["base.automation"].create(
            {
                "name": "Auto 2",
                "trigger": "on_create",
                "model_id": model.id,
                "sequence": 10,
            }
        )
        action2 = self.env["ir.actions.server"].create(
            {
                "name": "Action 2",
                "base_automation_id": auto2.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'B'})",
                "model_id": model.id,
            }
        )
        auto2.write({"action_server_ids": [Command.link(action2.id)]})

        auto3 = self.env["base.automation"].create(
            {
                "name": "Auto 3",
                "trigger": "on_create",
                "model_id": model.id,
                "sequence": 20,
            }
        )
        action3 = self.env["ir.actions.server"].create(
            {
                "name": "Action 3",
                "base_automation_id": auto3.id,
                "state": "code",
                "code": "record.write({'comment': (record.comment or '') + 'C'})",
                "model_id": model.id,
            }
        )
        auto3.write({"action_server_ids": [Command.link(action3.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})
        # Should execute in sequence order: 10, 20, 30 = B, C, A
        self.assertEqual(partner.comment, "BCA")
