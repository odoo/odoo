# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests import Form, tagged, users


@tagged('post_install', '-at_install')
class TestAutomation(TransactionCaseWithUserDemo):

    def test_01_on_create_or_write(self):
        """ Simple on_create with admin user """
        model = self.env.ref("base.model_res_partner")
        automation = self.env["base.automation"].create({
            "name": "Force Archived Contacts",
            "trigger": "on_create_or_write",
            "model_id": model.id,
            "trigger_field_ids": [(6, 0, [
                self.env.ref("base.field_res_partner__name").id,
                self.env.ref("base.field_res_partner__vat").id,
            ])],
        })

        # trg_field should only be set when trigger is 'on_stage_set' or 'on_tag_set'
        self.assertFalse(automation.trg_field_ref)
        self.assertFalse(automation.trg_field_ref_model_name)

        action = self.env["ir.actions.server"].create({
            "name": "Set Active To False",
            "base_automation_id": automation.id,
            "state": "object_write",
            "update_path": "active",
            "update_boolean_value": "false",
            "model_id": model.id,
        })
        automation.write({"action_server_ids": [Command.link(action.id)]})

        # verify the partner can be created and the action still runs
        bilbo = self.env["res.partner"].create({"name": "Bilbo Baggins"})
        self.assertFalse(bilbo.active)

        # verify the partner can be updated and the action still runs
        bilbo.active = True
        bilbo.name = "Bilbo"
        self.assertFalse(bilbo.active)

    def test_02_on_create_or_write_restricted(self):
        """ on_create action with low portal user """
        model = self.env.ref("base.model_ir_filters")
        automation = self.env["base.automation"].create({
            "name": "Force Archived Filters",
            "trigger": "on_create_or_write",
            "model_id": model.id,
            "trigger_field_ids": [(6, 0, [self.env.ref("base.field_ir_filters__name").id])],
        })
        action = self.env["ir.actions.server"].create({
            "name": "Set Active To False",
            "base_automation_id": automation.id,
            "model_id": model.id,
            "state": "object_write",
            "update_path": "active",
            "update_boolean_value": "false",
        })
        action.flush_recordset()
        automation.write({"action_server_ids": [Command.link(action.id)]})
        # action cached was cached with admin, force CacheMiss
        automation.env.clear()

        self_portal = self.env["ir.filters"].with_user(self.user_demo.id)
        # verify the portal user can create ir.filters but can not read base.automation
        self.assertTrue(self_portal.env["ir.filters"].has_access("create"))
        self.assertFalse(self_portal.env["base.automation"].has_access("read"))

        # verify the filter can be created and the action still runs
        filters = self_portal.create({
            "name": "Where is Bilbo?",
            "domain": "[('name', 'ilike', 'bilbo')]",
            "model_id": "res.partner",
        })
        self.assertFalse(filters.active)

        # verify the filter can be updated and the action still runs
        filters.active = True
        filters.name = "Where is Bilbo Baggins?"
        self.assertFalse(filters.active)

    def test_03_on_change_restricted(self):
        """ on_create action with low portal user """
        model = self.env.ref("base.model_ir_filters")
        automation = self.env["base.automation"].create({
            "name": "Force Archived Filters",
            "trigger": "on_change",
            "model_id": model.id,
            "on_change_field_ids": [(6, 0, [self.env.ref("base.field_ir_filters__name").id])],
        })
        action = self.env["ir.actions.server"].create({
            "name": "Set Active To False",
            "base_automation_id": automation.id,
            "model_id": model.id,
            "state": "code",
            "code": """action = {'value': {'active': False}}""",
        })
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
        model_field_id = self.env['ir.model.fields'].search([('model', '=', model.model), ('name', '=', 'id')], limit=1)
        automation = self.env["base.automation"].create({
            "name": "Test automated action",
            "trigger": "on_create_or_write",
            "model_id": model.id,
            "trigger_field_ids": [Command.set([model_field_id.id])],
        })
        action = self.env["ir.actions.server"].create({
            "name": "Modify name",
            "base_automation_id": automation.id,
            "model_id": model.id,
            "state": "code",
            "code": "record.write({'name': 'Modified Name'})"
        })
        action.flush_recordset()
        automation.write({"action_server_ids": [Command.link(action.id)]})
        # action cached was cached with admin, force CacheMiss
        automation.env.clear()

        server_action = self.env["ir.actions.server"].create({
            "name": "Empty write",
            "model_id": model.id,
            "state": "code",
            "code": "record.write({})"
        })

        partner = self.env[model.model].create({'name': 'Test Name'})
        self.assertEqual(partner.name, 'Modified Name', 'The automatic action must be performed')
        partner.name = 'Reset Name'
        self.assertEqual(partner.name, 'Reset Name', 'The automatic action must not be performed')

        context = {
            'active_model': model.model,
            'active_id': partner.id,
        }
        server_action.with_context(context).run()
        self.assertEqual(partner.name, 'Reset Name', 'The automatic action must not be performed')

    def test_create_automation_rule_for_valid_model(self):
        """
        Automation rules cannot be created for models that have no fields.
        """
        model_field = self.env['base.automation']._fields['model_id']
        base_model = self.env['base']

        # Verify that the base model is abstract and has _auto set to False
        self.assertTrue(base_model._abstract, "The base model should be abstract")
        self.assertFalse(base_model._auto, "The base model should have _auto set to False")

        # check whether the field hase domain attribute
        self.assertTrue(model_field.domain)
        domain = model_field.domain

        allowed_models = self.env['ir.model'].search(domain)
        self.assertTrue(base_model._name not in allowed_models.mapped('model'), "The base model should not be in the allowed models")

    def test_scheduled_action_updates_for_timebased_automations(self):
        cron = self.env.ref('base_automation.ir_cron_data_base_automation_check')
        self.assertRecordValues(cron, [{
            'active': False,
            'interval_type': 'hours',
            'interval_number': 4,
        }])

        # Create a time-based automation
        automation1 = self.env['base.automation'].create({
            'active': True,
            'name': 'Automation 1',
            'trigger': 'on_time',
            'model_id': self.env.ref('base.model_res_partner').id,
            'trg_date_range': 2,
            'trg_date_range_type': 'hour',
            'trg_date_range_mode': 'before',
            # of course the chosen field does not really make sense here, but hey its testing data
            "trg_date_id": self.env.ref("base.field_res_partner__write_date").id,
        })
        self.assertRecordValues(cron, [{
            'active': True,
            'interval_type': 'minutes',
            'interval_number': 12,  # 10% of automation1 delay
        }])

        automation2 = self.env['base.automation'].create({
            'active': True,
            'name': 'Automation 2',
            'trigger': 'on_time_created',
            'model_id': self.env.ref('base.model_res_partner').id,
            'trg_date_range': 1,
            'trg_date_range_type': 'hour',
        })
        self.assertRecordValues(cron, [{
            'active': True,
            'interval_type': 'minutes',
            'interval_number': 6,  # 10% of automation2 delay
        }])

        # Disable automation2
        automation2.active = False
        self.assertRecordValues(cron, [{
            'active': True,
            'interval_type': 'minutes',
            'interval_number': 12,  # 10% of automation1 delay
        }])

        # Disable automation1
        automation1.active = False
        self.assertRecordValues(cron, [{
            'active': False,
            'interval_type': 'hours',
            'interval_number': 4,
        }])

        # Enable automation1 and automation2
        automation1.active = True
        automation2.active = True
        self.assertRecordValues(cron, [{
            'active': True,
            'interval_type': 'minutes',
            'interval_number': 6,  # 10% of least delay (automation2)
        }])

        # Create another automation with no delay
        self.env['base.automation'].create({
            'active': True,
            'name': 'Automation 3',
            'trigger': 'on_time_created',
            'model_id': self.env.ref('base.model_res_partner').id,
            'trg_date_range': 0,
            'trg_date_range_type': 'hour',
        })
        self.assertRecordValues(cron, [{
            'active': True,
            'interval_type': 'minutes',
            'interval_number': 6,  # should have not changed
        }])

    def test_computed_on_scheduled_action(self):
        with Form(self.env['base.automation'], view='base_automation.view_base_automation_form') as f:
            f.name = 'Test Automation'
            f.model_id = self.env.ref('base.model_res_partner')
            f.trigger = 'on_time'
            f.trg_date_range = 2
            f.trg_date_range_type = 'hour'
            f.trg_date_range_mode = 'after'
            f.trg_date_id = self.env.ref('base.field_res_partner__write_date')
            # Negate trg_date_range should toggle trg_date_range_mode
            f.trg_date_range = -2
            self.assertEqual(f.trg_date_range_mode, 'before')
            self.assertEqual(f.trg_date_range, 2)
            # Change without negating should not toggle trg_date_range_mode
            f.trg_date_range = 3
            self.assertEqual(f.trg_date_range_mode, 'before')
            self.assertEqual(f.trg_date_range, 3)
            # Negate trg_date_range should toggle trg_date_range_mode
            f.trg_date_range = -3
            self.assertEqual(f.trg_date_range_mode, 'after')
            self.assertEqual(f.trg_date_range, 3)
            # Change without negating should not toggle trg_date_range_mode
            f.trg_date_range = 2
            self.assertEqual(f.trg_date_range_mode, 'after')
            self.assertEqual(f.trg_date_range, 2)

    @users('admin')
    def test_on_mail_received(self):
        model = self.env.ref("mail.model_discuss_channel")
        automation = self.env["base.automation"].create({
            "name": "Test Incoming Message",
            "trigger": "on_message_received",
            "model_id": model.id,
        })
        action = self.env["ir.actions.server"].create({
            "name": "Add 'X' to name",
            "base_automation_id": automation.id,
            "model_id": model.id,
            "state": "code",
            "code": """record.write({'name': record.name + 'X'})""",
        })

        action.flush_recordset()
        automation.write({"action_server_ids": [Command.link(action.id)]})
        # action cached was cached with admin, force CacheMiss
        automation.env.clear()

        # Comment
        channel_admin_user = self.env['discuss.channel']._create_channel(group_id=None, name='New Channel')
        channel_admin_user.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertEqual('New Channel', channel_admin_user.name, 'Comment should not trigger automation')

        # Incoming Mail
        channel_admin_user.message_post(
             author_id=False, body='I love you!', subject='Hello, you fool!', message_type='email',
             email_from='test@test.org', subtype_xmlid='mail.mt_comment'
        )
        self.assertEqual('New ChannelX', channel_admin_user.name, 'Incoming Mail should trigger automation')

        # Outgoing Mail
        self.env.company.email = 'info@example.org'
        channel_admin_user.message_post(
            body='Thank you!', subject='Hello, you fool!', message_type='email_outgoing',
            email_from=self.env.company.email, author_id=self.env.ref('base.partner_root').id
        )
        self.assertEqual('New ChannelX', channel_admin_user.name, 'Outgoing mail should not trigger automation')
