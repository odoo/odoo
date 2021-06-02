# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tools.misc import mute_logger

# test group that demo user should not have
USER_DEMO = 'base.user_demo'
GROUP_SYSTEM = 'base.group_system'


class TestACL(TransactionCase):

    def setUp(self):
        super(TestACL, self).setUp()
        self.demo_user = self.env.ref(USER_DEMO)
        self.erp_system_group = self.env.ref(GROUP_SYSTEM)

    def _set_field_groups(self, model, field_name, groups):
        field = model._fields[field_name]
        self.patch(field, 'groups', groups)

    def test_field_visibility_restriction(self):
        """Check that model-level ``groups`` parameter effectively restricts access to that
           field for users who do not belong to one of the explicitly allowed groups"""
        currency = self.env['res.currency'].with_user(self.demo_user)

        # Add a view that adds a label for the field we are going to check
        extension = self.env["ir.ui.view"].create({
            "name": "Add separate label for decimal_places",
            "model": "res.currency",
            "inherit_id": self.env.ref("base.view_currency_form").id,
            "arch": """
                <data>
                    <field name="decimal_places" position="attributes">
                        <attribute name="nolabel">1</attribute>
                    </field>
                    <field name="decimal_places" position="before">
                        <label for="decimal_places"/>
                    </field>
                </data>
            """,
        })
        currency = currency.with_context(check_view_ids=extension.ids)

        # Verify the test environment first
        original_fields = currency.fields_get([])
        form_view = currency.fields_view_get(False, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        has_group_system = self.demo_user.has_group(GROUP_SYSTEM)
        self.assertFalse(has_group_system, "`demo` user should not belong to the restricted group before the test")
        self.assertIn('decimal_places', original_fields, "'decimal_places' field must be properly visible before the test")
        self.assertNotEquals(view_arch.xpath("//field[@name='decimal_places'][@nolabel='1']"), [],
                             "Field 'decimal_places' must be found in view definition before the test")
        self.assertNotEquals(view_arch.xpath("//label[@for='decimal_places']"), [],
                             "Label for 'decimal_places' must be found in view definition before the test")

        # restrict access to the field and check it's gone
        self._set_field_groups(currency, 'decimal_places', GROUP_SYSTEM)

        fields = currency.fields_get([])
        form_view = currency.fields_view_get(False, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        self.assertNotIn('decimal_places', fields, "'decimal_places' field should be gone")
        self.assertEquals(view_arch.xpath("//field[@name='decimal_places']"), [],
                          "Field 'decimal_places' must not be found in view definition")
        self.assertEquals(view_arch.xpath("//label[@for='decimal_places']"), [],
                          "Label for 'decimal_places' must not be found in view definition")

        # Make demo user a member of the restricted group and check that the field is back
        self.erp_system_group.users += self.demo_user
        has_group_system = self.demo_user.has_group(GROUP_SYSTEM)
        fields = currency.fields_get([])
        form_view = currency.fields_view_get(False, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        self.assertTrue(has_group_system, "`demo` user should now belong to the restricted group")
        self.assertIn('decimal_places', fields, "'decimal_places' field must be properly visible again")
        self.assertNotEquals(view_arch.xpath("//field[@name='decimal_places']"), [],
                             "Field 'decimal_places' must be found in view definition again")
        self.assertNotEquals(view_arch.xpath("//label[@for='decimal_places']"), [],
                             "Label for 'decimal_places' must be found in view definition again")

    @mute_logger('odoo.models')
    def test_field_crud_restriction(self):
        "Read/Write RPC access to restricted field should be forbidden"
        partner = self.env['res.partner'].browse(1).with_user(self.demo_user)

        # Verify the test environment first
        has_group_system = self.demo_user.has_group(GROUP_SYSTEM)
        self.assertFalse(has_group_system, "`demo` user should not belong to the restricted group")
        self.assert_(partner.read(['bank_ids']))
        self.assert_(partner.write({'bank_ids': []}))

        # Now restrict access to the field and check it's forbidden
        self._set_field_groups(partner, 'bank_ids', GROUP_SYSTEM)

        with self.assertRaises(AccessError):
            partner.read(['bank_ids'])
        with self.assertRaises(AccessError):
            partner.write({'bank_ids': []})

        # Add the restricted group, and check that it works again
        self.erp_system_group.users += self.demo_user
        has_group_system = self.demo_user.has_group(GROUP_SYSTEM)
        self.assertTrue(has_group_system, "`demo` user should now belong to the restricted group")
        self.assert_(partner.read(['bank_ids']))
        self.assert_(partner.write({'bank_ids': []}))

    @mute_logger('odoo.models')
    def test_fields_browse_restriction(self):
        """Test access to records having restricted fields"""
        partner = self.env['res.partner'].with_user(self.demo_user)
        self._set_field_groups(partner, 'email', GROUP_SYSTEM)

        # accessing fields must no raise exceptions...
        partner = partner.search([], limit=1)
        partner.name
        # ... except if they are restricted
        with self.assertRaises(AccessError):
            with mute_logger('odoo.models'):
                partner.email

    def test_view_create_edit_button_invisibility(self):
        """ Test form view Create, Edit, Delete button visibility based on access right of model"""
        methods = ['create', 'edit', 'delete']
        company = self.env['res.company'].with_user(self.demo_user)
        company_view = company.fields_view_get(False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        for method in methods:
            self.assertEqual(view_arch.get(method), 'false')

    def test_view_create_edit_button_visibility(self):
        """ Test form view Create, Edit, Delete button visibility based on access right of model"""
        self.erp_system_group.users += self.demo_user
        methods = ['create', 'edit', 'delete']
        company = self.env['res.company'].with_user(self.demo_user)
        company_view = company.fields_view_get(False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        for method in methods:
            self.assertIsNone(view_arch.get(method))

    def test_m2o_field_create_edit_invisibility(self):
        """ Test many2one field Create and Edit option visibility based on access rights of relation field""" 
        methods = ['create', 'write']
        company = self.env['res.company'].with_user(self.demo_user)
        company_view = company.fields_view_get(False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        field_node = view_arch.xpath("//field[@name='currency_id']")
        self.assertTrue(len(field_node), "currency_id field should be in company from view")
        for method in methods:
            self.assertEqual(field_node[0].get('can_' + method), 'false')

    def test_m2o_field_create_edit_visibility(self):
        """ Test many2one field Create and Edit option visibility based on access rights of relation field""" 
        self.erp_system_group.users += self.demo_user
        methods = ['create', 'write']
        company = self.env['res.company'].with_user(self.demo_user)
        company_view = company.fields_view_get(False, 'form')
        view_arch = etree.fromstring(company_view['arch'])
        field_node = view_arch.xpath("//field[@name='currency_id']")
        self.assertTrue(len(field_node), "currency_id field should be in company from view")
        for method in methods:
            self.assertEqual(field_node[0].get('can_' + method), 'true')


class TestIrRule(TransactionCase):

    def test_ir_rule(self):
        model_res_partner = self.env.ref('base.model_res_partner')
        group_user = self.env.ref('base.group_user')
        user_demo = self.env.ref('base.user_demo')

        # create an ir_rule for the Employee group with an blank domain
        rule1 = self.env['ir.rule'].create({
            'name': 'test_rule1',
            'model_id': model_res_partner.id,
            'domain_force': False,
            'groups': [(6, 0, group_user.ids)],
        })

        # read as demo user the partners (one blank domain)
        partners_demo = self.env['res.partner'].with_user(user_demo)
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domain 1=1
        rule1.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domain []
        rule1.domain_force = "[]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # create another ir_rule for the Employee group (to test multiple rules)
        rule2 = self.env['ir.rule'].create({
            'name': 'test_rule2',
            'model_id': model_res_partner.id,
            'domain_force': False,
            'groups': [(6, 0, group_user.ids)],
        })

        # read as demo user with domains [] and blank
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domains 1=1 and blank
        rule1.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domains 1=1 and 1=1
        rule2.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # create another ir_rule for the Employee group (to test multiple rules)
        rule3 = self.env['ir.rule'].create({
            'name': 'test_rule3',
            'model_id': model_res_partner.id,
            'domain_force': False,
            'groups': [(6, 0, group_user.ids)],
        })

        # read the partners as demo user
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domains 1=1, 1=1 and 1=1
        rule3.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # modify the global rule on res_company which triggers a recursive check
        # of the rules on company
        global_rule = self.env.ref('base.res_company_rule_employee')
        global_rule.domain_force = "[('id','in', company_ids)]"

        # read as demo user (exercising the global company rule)
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # Modify the ir_rule for employee to have a rule that fordids seeing any
        # record. We use a domain with implicit AND operator for later tests on
        # normalization.
        rule2.domain_force = "[('id','=',False),('name','=',False)]"

        # check that demo user still sees partners, because group-rules are OR'ed
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # create a new group with demo user in it, and a complex rule
        group_test = self.env['res.groups'].create({
            'name': 'Test Group',
            'users': [(6, 0, user_demo.ids)],
        })

        # add the rule to the new group, with a domain containing an implicit
        # AND operator, which is more tricky because it will have to be
        # normalized before combining it
        rule3.write({
            'domain_force': "[('name','!=',False),('id','!=',False)]",
            'groups': [(6, 0, group_test.ids)],
        })

        # read the partners again as demo user, which should give results
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see partners even with the combined rules.")

        # delete global domains (to combine only group domains)
        self.env['ir.rule'].search([('groups', '=', False)]).unlink()

        # read the partners as demo user (several group domains, no global domain)
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partners.")
