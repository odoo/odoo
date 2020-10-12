# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import TransactionCase
from odoo.exceptions import UserError

import odoo.tests

@odoo.tests.tagged('post_install', '-at_install')
class TestAutomation(TransactionCase):

    def test_01_on_create(self):
        """ Simple on_create with admin user """
        self.env["base.automation"].create({
            "name": "Force Archived Contacts",
            "trigger": "on_create_or_write",
            "model_id": self.env.ref("base.model_res_partner").id,
            "type": "ir.actions.server",
            "trigger_field_ids": [(6, 0, [self.env.ref("base.field_res_partner__name").id])],
            "fields_lines": [(0, 0, {
                "col1": self.env.ref("base.field_res_partner__active").id,
                "evaluation_type": "equation",
                "value": "False",
            })],
        })

        # verify the partner can be created and the action still runs
        bilbo = self.env["res.partner"].create({"name": "Bilbo Baggins"})
        self.assertFalse(bilbo.active)

        # verify the partner can be updated and the action still runs
        bilbo.active = True
        bilbo.name = "Bilbo"
        self.assertFalse(bilbo.active)


    def test_02_on_create_restricted(self):
        """ on_create action with low portal user """
        action = self.env["base.automation"].create({
            "name": "Force Archived Filters",
            "trigger": "on_create_or_write",
            "model_id": self.env.ref("base.model_ir_filters").id,
            "type": "ir.actions.server",
            "trigger_field_ids": [(6, 0, [self.env.ref("base.field_ir_filters__name").id])],
            "fields_lines": [(0, 0, {
                "col1": self.env.ref("base.field_ir_filters__active").id,
                "evaluation_type": "equation",
                "value": "False",
            })],
        })
        # action cached was cached with admin, force CacheMiss
        action.env.clear()

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
        action = self.env["base.automation"].create({
            "name": "Force Archived Filters",
            "trigger": "on_change",
            "model_id": self.env.ref("base.model_ir_filters").id,
            "type": "ir.actions.server",
            "on_change_field_ids": [(6, 0, [self.env.ref("base.field_ir_filters__name").id])],
            "state": "code",
            "code": """action = {'value': {'active': False}}""",
        })
        # action cached was cached with admin, force CacheMiss
        action.env.clear()

        self_portal = self.env["ir.filters"].with_user(self.env.ref("base.user_demo").id)

        # simulate a onchange call on name
        onchange = self_portal.onchange({}, [], {"name": "1", "active": ""})
        self.assertEqual(onchange["value"]["active"], False)
