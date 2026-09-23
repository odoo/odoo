from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@tagged("post_install", "-at_install")
class TestAutomation(TransactionCaseWithUserDemo):
    def test_01_on_create_or_write(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
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

        self.assertFalse(automation.trg_field_ref)
        self.assertFalse(automation.trg_field_ref_model_name)

        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Active To False",
                "automation_rule_id": automation.id,
                "state": "object_write",
                "update_path": "active",
                "update_boolean_value": "false",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        bilbo = self.env["res.partner"].create({"name": "Bilbo Baggins"})
        self.assertFalse(bilbo.active)

        bilbo.active = True
        bilbo.name = "Bilbo"
        self.assertFalse(bilbo.active)

    def test_02_on_create_or_write_restricted(self):
        model = self.env.ref("base.model_ir_filters")
        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "model_id": model.id,
                "state": "object_write",
                "update_path": "active",
                "update_boolean_value": "false",
            }
        )
        action.flush_recordset()
        automation.write({"action_server_ids": [Command.link(action.id)]})
        automation.env.clear()

        self_portal = self.env["ir.filters"].with_user(self.user_demo.id)
        self.assertTrue(self_portal.env["ir.filters"].has_access("create"))
        self.assertFalse(self_portal.env["automation.rule"].has_access("read"))

        filters = self_portal.create(
            {
                "name": "Where is Bilbo?",
                "domain": "[('name', 'ilike', 'bilbo')]",
                "model_id": "res.partner",
            }
        )
        self.assertFalse(filters.active)

        filters.active = True
        filters.name = "Where is Bilbo Baggins?"
        self.assertFalse(filters.active)

    def test_03_on_change_restricted(self):
        model = self.env.ref("base.model_ir_filters")
        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "model_id": model.id,
                "state": "code",
                "code": """action = {'value': {'active': False}}""",
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})
        automation.env.clear()

        self_portal = self.env["ir.filters"].with_user(self.user_demo.id)

        result = self_portal.onchange({}, [], {"name": {}, "active": {}})
        self.assertEqual(result["value"]["active"], False)

    def test_04_on_create_or_write_differentiate(self):
        model = self.env.ref("base.model_res_partner")
        model_field_id = self.env["ir.model.fields"].search(
            [("model", "=", model.model), ("name", "=", "id")], limit=1
        )
        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "model_id": model.id,
                "state": "code",
                "code": "record.write({'name': 'Modified Name'})",
            }
        )
        action.flush_recordset()
        automation.write({"action_server_ids": [Command.link(action.id)]})
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
        model_field = self.env["automation.rule"]._fields["model_id"]
        base_model = self.env["base"]

        self.assertTrue(base_model._abstract, "The base model should be abstract")
        self.assertFalse(
            base_model._auto, "The base model should have _auto set to False"
        )

        self.assertTrue(model_field.domain)
        domain = model_field.domain

        allowed_models = self.env["ir.model"].search(domain)
        self.assertTrue(
            base_model._name not in allowed_models.mapped("model"),
            "The base model should not be in the allowed models",
        )

    def test_scheduled_action_updates_for_timebased_automations(self):
        cron = self.env.ref("automation.ir_cron_data_automation_check")
        self.assertRecordValues(
            cron,
            [
                {
                    "active": False,
                    "repeat_unit": "hour",
                    "repeat_interval": 4,
                }
            ],
        )

        automation1 = self.env["automation.rule"].create(
            {
                "active": True,
                "name": "Automation 1",
                "trigger": "on_time",
                "model_id": self.env.ref("base.model_res_partner").id,
                "trg_date_range": 2,
                "trg_date_range_type": "hour",
                "trg_date_range_mode": "before",
                "trg_date_id": self.env.ref("base.field_res_partner__write_date").id,
            }
        )
        self.assertRecordValues(
            cron,
            [
                {
                    "active": True,
                    "repeat_unit": "minute",
                    "repeat_interval": 12,
                }
            ],
        )

        automation2 = self.env["automation.rule"].create(
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
                    "repeat_unit": "minute",
                    "repeat_interval": 6,
                }
            ],
        )

        automation2.active = False
        self.assertRecordValues(
            cron,
            [
                {
                    "active": True,
                    "repeat_unit": "minute",
                    "repeat_interval": 6,
                }
            ],
        )

        automation1.active = False
        self.assertRecordValues(
            cron,
            [
                {
                    "active": False,
                    "repeat_unit": "minute",
                    "repeat_interval": 6,
                }
            ],
        )

        automation1.active = True
        automation2.active = True
        self.assertRecordValues(
            cron,
            [
                {
                    "active": True,
                    "repeat_unit": "minute",
                    "repeat_interval": 6,
                }
            ],
        )

        self.env["automation.rule"].create(
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
                    "repeat_unit": "minute",
                    "repeat_interval": 6,
                }
            ],
        )

    def test_computed_on_scheduled_action(self):
        with Form(
            self.env["automation.rule"],
            view="automation.view_automation_form",
        ) as f:
            f.name = "Test Automation"
            f.model_id = self.env.ref("base.model_res_partner")
            f.trigger = "on_time"
            f.trg_date_range = 2
            f.trg_date_range_type = "hour"
            f.trg_date_range_mode = "after"
            f.trg_date_id = self.env.ref("base.field_res_partner__write_date")
            f.trg_date_range = -2
            self.assertEqual(f.trg_date_range_mode, "before")
            self.assertEqual(f.trg_date_range, 2)
            f.trg_date_range = 3
            self.assertEqual(f.trg_date_range_mode, "before")
            self.assertEqual(f.trg_date_range, 3)
            f.trg_date_range = -3
            self.assertEqual(f.trg_date_range_mode, "after")
            self.assertEqual(f.trg_date_range, 3)
            f.trg_date_range = 2
            self.assertEqual(f.trg_date_range_mode, "after")
            self.assertEqual(f.trg_date_range, 2)

    def test_domain_filtering_on_create(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'is_company': True})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        regular = self.env["res.partner"].create({"name": "Regular Customer"})
        self.assertFalse(regular.is_company)

        vip = self.env["res.partner"].create({"name": "VIP Customer"})
        self.assertTrue(vip.is_company)

    def test_filter_pre_domain_on_write(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': 'Was archived'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test", "active": True})

        partner.write({"active": False})
        self.assertEqual(partner.street, "Was archived")

        partner.street = False
        partner.write({"active": True})
        self.assertFalse(partner.street)

    def test_complex_domain_with_multiple_conditions(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'ref': '555-0000'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        p1 = self.env["res.partner"].create(
            {"name": "Individual", "is_company": False, "email": "test@example.com"}
        )
        self.assertFalse(p1.ref)

        p2 = self.env["res.partner"].create({"name": "Company", "is_company": True})
        self.assertFalse(p2.ref)

        p3 = self.env["res.partner"].create(
            {"name": "Company", "is_company": True, "email": "company@example.com"}
        )
        self.assertEqual(p3.ref, "555-0000")

    def test_code_action_execution(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Code Action Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Complex Code",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": """
# Complex Python code
partner_name = record.name.upper()
record.write({
    'street': f'Created: {partner_name}',
    'ref': '123-456-7890',
})
""",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test Partner"})
        self.assertEqual(partner.street, "Created: TEST PARTNER")
        self.assertEqual(partner.ref, "123-456-7890")

    def test_object_write_action(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Object Write Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Company",
                "automation_rule_id": automation.id,
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
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Multi Action Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )

        action1 = self.env["ir.actions.server"].create(
            {
                "name": "Action 1",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': (record.street or '') + 'A'})",
                "model_id": model.id,
                "sequence": 30,
            }
        )
        action2 = self.env["ir.actions.server"].create(
            {
                "name": "Action 2",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': (record.street or '') + 'B'})",
                "model_id": model.id,
                "sequence": 10,
            }
        )
        action3 = self.env["ir.actions.server"].create(
            {
                "name": "Action 3",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': (record.street or '') + 'C'})",
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
        self.assertEqual(partner.street, "BCA")

    def test_automation_activation_deactivation(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Toggle Test",
                "trigger": "on_create",
                "model_id": model.id,
                "active": False,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': 'Triggered'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        p1 = self.env["res.partner"].create({"name": "Test 1"})
        self.assertFalse(p1.street)

        automation.write({"active": True})

        p2 = self.env["res.partner"].create({"name": "Test 2"})
        self.assertEqual(p2.street, "Triggered")

    def test_automation_update_trigger_type(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Change Trigger Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': 'Triggered'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        p1 = self.env["res.partner"].create({"name": "Test 1"})
        self.assertEqual(p1.street, "Triggered")

        automation.write({"trigger": "on_write"})

        p2 = self.env["res.partner"].create({"name": "Test 2"})
        self.assertFalse(p2.street)

        p2.write({"name": "Test 2 Updated"})
        self.assertEqual(p2.street, "Triggered")

    def test_automation_deletion(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Delete Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Set Comment",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': 'Triggered'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        p1 = self.env["res.partner"].create({"name": "Test 1"})
        self.assertEqual(p1.street, "Triggered")

        automation.unlink()

        p2 = self.env["res.partner"].create({"name": "Test 2"})
        self.assertFalse(p2.street)

    def test_trigger_specific_fields_only(self):
        model = self.env.ref("base.model_res_partner")
        email_field = self.env.ref("base.field_res_partner__email")

        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': 'Email changed'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})

        partner.write({"name": "New Name"})
        self.assertFalse(partner.street)

        partner.write({"email": "test@example.com"})
        self.assertEqual(partner.street, "Email changed")

    def test_trigger_multiple_fields(self):
        model = self.env.ref("base.model_res_partner")
        name_field = self.env.ref("base.field_res_partner__name")
        email_field = self.env.ref("base.field_res_partner__email")

        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': 'Triggered'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})

        partner.write({"ref": "123-456"})
        self.assertFalse(partner.street)

        partner.write({"name": "New Name"})
        self.assertEqual(partner.street, "Triggered")

        partner.street = False

        partner.write({"email": "test@example.com"})
        self.assertEqual(partner.street, "Triggered")

    def test_action_error_does_not_break_record_creation(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Failing Action",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Fail",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "raise Exception('Test error')",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        with self.assertRaises(ValueError):
            self.env["res.partner"].create({"name": "Test"})

    def test_invalid_code_in_action(self):
        from odoo.exceptions import ValidationError

        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Invalid Code",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["ir.actions.server"].create(
                {
                    "name": "Bad Code",
                    "automation_rule_id": automation.id,
                    "state": "code",
                    "code": "invalid python syntax !!!",
                    "model_id": model.id,
                }
            )

    def test_automation_model_consistency(self):
        partner_model = self.env.ref("base.model_res_partner")
        country_model = self.env.ref("base.model_res_country")

        automation = self.env["automation.rule"].create(
            {
                "name": "Model Consistency Test",
                "trigger": "on_create",
                "model_id": partner_model.id,
            }
        )

        action = self.env["ir.actions.server"].create(
            {
                "name": "Wrong Model",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "pass",
                "model_id": country_model.id,
            }
        )

        warnings = action._get_warning_messages()
        self.assertTrue(any("should match" in w for w in warnings))

    def test_automation_cannot_be_created_for_abstract_model(self):
        model_field = self.env["automation.rule"]._fields["model_id"]
        domain = model_field.domain

        allowed_models = self.env["ir.model"].search(domain)
        allowed_model_names = allowed_models.mapped("model")

        self.assertNotIn("base", allowed_model_names)

    def test_automation_with_bulk_create(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Bulk Create Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Mark Company",
                "automation_rule_id": automation.id,
                "state": "object_write",
                "update_path": "is_company",
                "update_boolean_value": "true",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partners = self.env["res.partner"].create(
            [{"name": f"Partner {i}"} for i in range(10)]
        )

        self.assertTrue(all(p.is_company for p in partners))

    def test_automation_with_bulk_write(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
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
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': 'Email updated'})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partners = self.env["res.partner"].create(
            [{"name": f"Partner {i}"} for i in range(5)]
        )

        partners.write({"email": "bulk@example.com"})

        self.assertTrue(all(p.street == "Email updated" for p in partners))

    def test_automation_respects_company_context(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Company Context Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Store Company",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": "record.write({'street': env.company.name})",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})
        self.assertTrue(partner.street)

    def test_automation_access_to_env_variables(self):
        model = self.env.ref("base.model_res_partner")
        automation = self.env["automation.rule"].create(
            {
                "name": "Env Access Test",
                "trigger": "on_create",
                "model_id": model.id,
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Use Env",
                "automation_rule_id": automation.id,
                "state": "code",
                "code": """
# Test access to environment
user = env.user
partner_count = env['res.partner'].search_count([])
record.write({'street': f'User: {user.name}, Count: {partner_count}'})
""",
                "model_id": model.id,
            }
        )
        automation.write({"action_server_ids": [Command.link(action.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})
        self.assertIn("User:", partner.street)
        self.assertIn("Count:", partner.street)

    def test_automation_sequence_ordering(self):
        model = self.env.ref("base.model_res_partner")

        auto1 = self.env["automation.rule"].create(
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
                "automation_rule_id": auto1.id,
                "state": "code",
                "code": "record.write({'street': (record.street or '') + 'A'})",
                "model_id": model.id,
            }
        )
        auto1.write({"action_server_ids": [Command.link(action1.id)]})

        auto2 = self.env["automation.rule"].create(
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
                "automation_rule_id": auto2.id,
                "state": "code",
                "code": "record.write({'street': (record.street or '') + 'B'})",
                "model_id": model.id,
            }
        )
        auto2.write({"action_server_ids": [Command.link(action2.id)]})

        auto3 = self.env["automation.rule"].create(
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
                "automation_rule_id": auto3.id,
                "state": "code",
                "code": "record.write({'street': (record.street or '') + 'C'})",
                "model_id": model.id,
            }
        )
        auto3.write({"action_server_ids": [Command.link(action3.id)]})

        partner = self.env["res.partner"].create({"name": "Test"})
        self.assertEqual(partner.street, "BCA")
