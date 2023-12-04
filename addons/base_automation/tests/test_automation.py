# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import TransactionCase
from odoo import Command

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestAutomation(TransactionCase):

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
        self.assertFalse(automation.trg_field_ref_display_name)
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

        self_portal = self.env["ir.filters"].with_user(self.env.ref("base.user_demo").id)
        # verify the portal user can create ir.filters but can not read base.automation
        self.assertTrue(self_portal.env["ir.filters"].check_access_rights("create", raise_exception=False))
        self.assertFalse(self_portal.env["base.automation"].check_access_rights("read", raise_exception=False))

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

        self_portal = self.env["ir.filters"].with_user(self.env.ref("base.user_demo").id)

        # simulate a onchange call on name
        result = self_portal.onchange({}, [], {"name": {}, "active": {}})
        self.assertEqual(result["value"]["active"], False)
