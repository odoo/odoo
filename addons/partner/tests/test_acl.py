# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.exceptions import AccessError
from odoo.addons.base.tests.test_acl import TestACLCommon
from odoo.tools.misc import mute_logger

GROUP_SYSTEM = 'base.group_system'


class TestACL(TestACLCommon):

    @mute_logger('odoo.models')
    def test_field_crud_restriction(self):
        "Read/Write RPC access to restricted field should be forbidden"
        partner = self.env['res.partner'].browse(1).with_user(self.user_demo)

        # Verify the test environment first
        has_group_system = self.user_demo.has_group(GROUP_SYSTEM)
        self.assertFalse(has_group_system, "`demo` user should not belong to the restricted group")
        self.assertTrue(partner.read(['bank_ids']))
        self.assertTrue(partner.write({'bank_ids': []}))

        # Now restrict access to the field and check it's forbidden
        self._set_field_groups(partner, 'bank_ids', GROUP_SYSTEM)

        with self.assertRaises(AccessError):
            partner.read(['bank_ids'])
        with self.assertRaises(AccessError):
            partner.write({'bank_ids': []})

        # Add the restricted group, and check that it works again
        self.erp_system_group.users += self.user_demo
        has_group_system = self.user_demo.has_group(GROUP_SYSTEM)
        self.assertTrue(has_group_system, "`demo` user should now belong to the restricted group")
        self.assertTrue(partner.read(['bank_ids']))
        self.assertTrue(partner.write({'bank_ids': []}))

    def test_m2o_field_create_edit_invisibility(self):
        """ Test many2one field Create and Edit option visibility based on access rights of relation field""" 
        methods = ['create', 'write']
        company = self.env['res.company'].with_user(self.user_demo)
        company_view = company.fields_view_get(False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        field_node = view_arch.xpath("//field[@name='currency_id']")
        self.assertTrue(len(field_node), "currency_id field should be in company from view")
        for method in methods:
            self.assertEqual(field_node[0].get('can_' + method), 'false')

    def test_m2o_field_create_edit_visibility(self):
        """ Test many2one field Create and Edit option visibility based on access rights of relation field""" 
        self.erp_system_group.users += self.user_demo
        methods = ['create', 'write']
        company = self.env['res.company'].with_user(self.user_demo)
        company_view = company.fields_view_get(False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        field_node = view_arch.xpath("//field[@name='currency_id']")
        self.assertTrue(len(field_node), "currency_id field should be in company from view")
        for method in methods:
            self.assertEqual(field_node[0].get('can_' + method), 'true')
