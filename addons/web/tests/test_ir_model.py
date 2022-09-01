# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase

from odoo.tests import tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class IrModelAccessTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(IrModelAccessTest, cls).setUpClass()

        cls.env['ir.model.access'].create({
            'name': "read",
            'model_id': cls.env['ir.model'].search([("model", "=", "res.company")]).id,
            'group_id': cls.env.ref("base.group_public").id,
            'perm_read': False,
        })

        cls.env['ir.model.access'].create({
            'name': "read",
            'model_id': cls.env['ir.model'].search([("model", "=", "res.company")]).id,
            'group_id': cls.env.ref("base.group_portal").id,
            'perm_read': True,
        })

        cls.env['ir.model.access'].create({
            'name': "read",
            'model_id': cls.env['ir.model'].search([("model", "=", "res.company")]).id,
            'group_id': cls.env.ref("base.group_user").id,
            'perm_read': True,
        })

        cls.portal_user = new_test_user(
            cls.env, login="portalDude", groups="base.group_portal"
        )
        cls.public_user = new_test_user(
            cls.env, login="publicDude", groups="base.group_public"
        )
        cls.spreadsheet_user = new_test_user(
            cls.env, login="spreadsheetDude", groups="base.group_user"
        )

    def test_display_name_for(self):
        # Internal User with access rights can access the business name
        result = self.env['ir.model'].with_user(self.spreadsheet_user).display_name_for(["res.company"])
        self.assertEqual(result, [{"display_name": "Companies", "model": "res.company"}])
        # external user with access rights cannot access business name
        result = self.env['ir.model'].with_user(self.portal_user).display_name_for(["res.company"])
        self.assertEqual(result, [{"display_name": "res.company", "model": "res.company"}])
        # external user without access rights cannot access business name
        result = self.env['ir.model'].with_user(self.public_user).display_name_for(["res.company"])
        self.assertEqual(result, [{"display_name": "res.company", "model": "res.company"}])
        # admin has all rights
        result = self.env['ir.model'].display_name_for(["res.company"])
        self.assertEqual(result, [{"display_name": "Companies", "model": "res.company"}])
        # non existent model yields same result as a lack of access rights
        result = self.env['ir.model'].display_name_for(["unexistent"])
        self.assertEqual(result, [{"display_name": "unexistent", "model": "unexistent"}])
        # non existent model comes after existent model
        result = self.env['ir.model'].display_name_for(["res.company", "unexistent"])
        self.assertEqual(result, [{"display_name": "Companies", "model": "res.company"}, {"display_name": "unexistent", "model": "unexistent"}])
