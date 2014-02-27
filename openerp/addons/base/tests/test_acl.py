import unittest2
from lxml import etree

import openerp
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
        _, self.demo_uid = self.registry('ir.model.data').get_object_reference(self.cr, self.uid, 'base', 'user_demo')
        self.tech_group = self.registry('ir.model.data').get_object(self.cr, self.uid,
                                                                    *(GROUP_TECHNICAL_FEATURES.split('.')))

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

        # Restrict access to the field and check it's gone
        self.res_currency._columns['accuracy'].groups = GROUP_TECHNICAL_FEATURES
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
        self.res_currency._columns['accuracy'].groups = False

    @mute_logger('openerp.osv.orm')
    def test_field_crud_restriction(self):
        "Read/Write RPC access to restricted field should be forbidden"
        # Verify the test environment first
        has_tech_feat = self.res_users.has_group(self.cr, self.demo_uid, GROUP_TECHNICAL_FEATURES)
        self.assertFalse(has_tech_feat, "`demo` user should not belong to the restricted group")
        self.assert_(self.res_partner.read(self.cr, self.demo_uid, [1], ['bank_ids']))
        self.assert_(self.res_partner.write(self.cr, self.demo_uid, [1], {'bank_ids': []}))

        # Now restrict access to the field and check it's forbidden
        self.res_partner._columns['bank_ids'].groups = GROUP_TECHNICAL_FEATURES
        with self.assertRaises(openerp.osv.orm.except_orm):
            self.res_partner.read(self.cr, self.demo_uid, [1], ['bank_ids'])
        with self.assertRaises(openerp.osv.orm.except_orm):
            self.res_partner.write(self.cr, self.demo_uid, [1], {'bank_ids': []})

        # Add the restricted group, and check that it works again
        self.tech_group.write({'users': [(4, self.demo_uid)]})
        has_tech_feat = self.res_users.has_group(self.cr, self.demo_uid, GROUP_TECHNICAL_FEATURES)
        self.assertTrue(has_tech_feat, "`demo` user should now belong to the restricted group")
        self.assert_(self.res_partner.read(self.cr, self.demo_uid, [1], ['bank_ids']))
        self.assert_(self.res_partner.write(self.cr, self.demo_uid, [1], {'bank_ids': []}))

        #cleanup
        self.tech_group.write({'users': [(3, self.demo_uid)]})
        self.res_partner._columns['bank_ids'].groups = False

    def test_fields_browse_restriction(self):
        """Test access to records having restricted fields"""
        self.res_partner._columns['email'].groups = GROUP_TECHNICAL_FEATURES
        try:
            P = self.res_partner
            pid = P.search(self.cr, self.demo_uid, [], limit=1)[0]
            part = P.browse(self.cr, self.demo_uid, pid)
            # accessing fields must no raise exceptions...
            part.name
            # ... except if they are restricted
            with self.assertRaises(openerp.osv.orm.except_orm) as cm:
                with mute_logger('openerp.osv.orm'):
                    part.email

            self.assertEqual(cm.exception.args[0], 'Access Denied')
        finally:
            self.res_partner._columns['email'].groups = False

if __name__ == '__main__':
    unittest2.main()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
