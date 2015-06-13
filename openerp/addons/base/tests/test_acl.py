import unittest2
from lxml import etree

from openerp.exceptions import AccessError
from openerp.tools.misc import mute_logger
from openerp.tests import common

# test group that demo user should not have
GROUP_TECHNICAL_FEATURES = 'base.group_no_one'


class TestACL(common.TransactionCase):

    def setUp(self):
        super(TestACL, self).setUp()
        self.res_currency = self.registry('res.currency')
        self.res_partner = self.registry('res.partner')
        self.res_users = self.registry('res.users')
        self.res_company = self.registry('res.company')
        self.demo_uid = self.registry('ir.model.data').xmlid_to_res_id(self.cr, self.uid, 'base.user_demo')
        self.tech_group = self.registry('ir.model.data').xmlid_to_object(self.cr, self.uid, GROUP_TECHNICAL_FEATURES)
        self.erp_manager_group = self.registry('ir.model.data').xmlid_to_object(self.cr, self.uid, 'base.group_erp_manager')
        self.erp_system_group = self.registry('ir.model.data').xmlid_to_object(self.cr, self.uid, 'base.group_system')

    def _set_field_groups(self, model, field_name, groups):
        field = model._fields[field_name]
        column = model._columns[field_name]
        old_groups = field.groups
        old_prefetch = column._prefetch
    
        field.groups = groups
        column.groups = groups
        column._prefetch = False

        @self.addCleanup
        def cleanup():
            field.groups = old_groups
            column.groups = old_groups
            column._prefetch = old_prefetch

    def test_field_visibility_restriction(self):
        """Check that model-level ``groups`` parameter effectively restricts access to that
           field for users who do not belong to one of the explicitly allowed groups"""
        # Verify the test environment first
        original_fields = self.res_currency.fields_get(self.cr, self.demo_uid, [])
        form_view = self.res_currency.fields_view_get(self.cr, self.demo_uid, False, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        has_tech_feat = self.res_users.has_group(self.cr, self.demo_uid, GROUP_TECHNICAL_FEATURES)
        self.assertFalse(has_tech_feat, "`demo` user should not belong to the restricted group before the test")
        self.assertTrue('accuracy' in original_fields, "'accuracy' field must be properly visible before the test")
        self.assertNotEquals(view_arch.xpath("//field[@name='accuracy']"), [],
                             "Field 'accuracy' must be found in view definition before the test")

        # restrict access to the field and check it's gone
        self._set_field_groups(self.res_currency, 'accuracy', GROUP_TECHNICAL_FEATURES)

        fields = self.res_currency.fields_get(self.cr, self.demo_uid, [])
        form_view = self.res_currency.fields_view_get(self.cr, self.demo_uid, False, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        self.assertFalse('accuracy' in fields, "'accuracy' field should be gone")
        self.assertEquals(view_arch.xpath("//field[@name='accuracy']"), [],
                          "Field 'accuracy' must not be found in view definition")

        # Make demo user a member of the restricted group and check that the field is back
        self.tech_group.write({'users': [(4, self.demo_uid)]})
        has_tech_feat = self.res_users.has_group(self.cr, self.demo_uid, GROUP_TECHNICAL_FEATURES)
        fields = self.res_currency.fields_get(self.cr, self.demo_uid, [])
        form_view = self.res_currency.fields_view_get(self.cr, self.demo_uid, False, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        #import pprint; pprint.pprint(fields); pprint.pprint(form_view)
        self.assertTrue(has_tech_feat, "`demo` user should now belong to the restricted group")
        self.assertTrue('accuracy' in fields, "'accuracy' field must be properly visible again")
        self.assertNotEquals(view_arch.xpath("//field[@name='accuracy']"), [],
                             "Field 'accuracy' must be found in view definition again")

        #cleanup
        self.tech_group.write({'users': [(3, self.demo_uid)]})

    @mute_logger('openerp.models')
    def test_field_crud_restriction(self):
        "Read/Write RPC access to restricted field should be forbidden"
        # Verify the test environment first
        has_tech_feat = self.res_users.has_group(self.cr, self.demo_uid, GROUP_TECHNICAL_FEATURES)
        self.assertFalse(has_tech_feat, "`demo` user should not belong to the restricted group")
        self.assert_(self.res_partner.read(self.cr, self.demo_uid, [1], ['bank_ids']))
        self.assert_(self.res_partner.write(self.cr, self.demo_uid, [1], {'bank_ids': []}))

        # Now restrict access to the field and check it's forbidden
        self._set_field_groups(self.res_partner, 'bank_ids', GROUP_TECHNICAL_FEATURES)

        with self.assertRaises(AccessError):
            self.res_partner.read(self.cr, self.demo_uid, [1], ['bank_ids'])
        with self.assertRaises(AccessError):
            self.res_partner.write(self.cr, self.demo_uid, [1], {'bank_ids': []})

        # Add the restricted group, and check that it works again
        self.tech_group.write({'users': [(4, self.demo_uid)]})
        has_tech_feat = self.res_users.has_group(self.cr, self.demo_uid, GROUP_TECHNICAL_FEATURES)
        self.assertTrue(has_tech_feat, "`demo` user should now belong to the restricted group")
        self.assert_(self.res_partner.read(self.cr, self.demo_uid, [1], ['bank_ids']))
        self.assert_(self.res_partner.write(self.cr, self.demo_uid, [1], {'bank_ids': []}))

        #cleanup
        self.tech_group.write({'users': [(3, self.demo_uid)]})

    @mute_logger('openerp.models')
    def test_fields_browse_restriction(self):
        """Test access to records having restricted fields"""
        self._set_field_groups(self.res_partner, 'email', GROUP_TECHNICAL_FEATURES)

        pid = self.res_partner.search(self.cr, self.demo_uid, [], limit=1)[0]
        part = self.res_partner.browse(self.cr, self.demo_uid, pid)
        # accessing fields must no raise exceptions...
        part.name
        # ... except if they are restricted
        with self.assertRaises(AccessError) as cm:
            with mute_logger('openerp.models'):
                part.email

        #Useless because we get the title in the client side now in the chrome.js file(map_title)
        #self.assertEqual(cm.exception.args[0], 'Access Error')

    def test_view_create_edit_button_invisibility(self):
        """ Test form view Create, Edit, Delete button visibility based on access right of model"""
        methods = ['create', 'edit', 'delete']
        company_view = self.res_company.fields_view_get(self.cr, self.demo_uid, False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        for method in methods:
            self.assertEqual(view_arch.get(method), 'false')

    def test_view_create_edit_button_visibility(self):
        """ Test form view Create, Edit, Delete button visibility based on access right of model"""
        methods = ['create', 'edit', 'delete']
        self.erp_manager_group.write({'users': [(4, self.demo_uid)]})
        company_view = self.res_company.fields_view_get(self.cr, self.demo_uid, False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        for method in methods:
            self.assertIsNone(view_arch.get(method))
        # cleanup
        self.erp_manager_group.write({'users': [(3, self.demo_uid)]})

    def test_m2o_field_create_edit_invisibility(self):
        """ Test many2one field Create and Edit option visibility based on access rights of relation field""" 
        methods = ['create', 'write']

        company_view = self.res_company.fields_view_get(self.cr, self.demo_uid, False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        field_node = view_arch.xpath("//field[@name='currency_id']")
        self.assertTrue(len(field_node), "currency_id field should be in company from view")
        for method in methods:
            self.assertEqual(field_node[0].get('can_' + method), 'false')

    def test_m2o_field_create_edit_visibility(self):
        """ Test many2one field Create and Edit option visibility based on access rights of relation field""" 
        methods = ['create', 'write']

        self.erp_system_group.write({'users': [(4, self.demo_uid)]})
        company_view = self.res_company.fields_view_get(self.cr, self.demo_uid, False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        field_node = view_arch.xpath("//field[@name='currency_id']")
        self.assertTrue(len(field_node), "currency_id field should be in company from view")
        for method in methods:
            self.assertEqual(field_node[0].get('can_' + method), 'true')
        # cleanup
        self.erp_manager_group.write({'users': [(3, self.demo_uid)]})

if __name__ == '__main__':
    unittest2.main()
