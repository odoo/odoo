# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.tools.misc import mute_logger

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestACL(TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.TEST_GROUP = 'base.base_test_group'
        cls.test_group = cls.env['res.groups'].create({
            'name': 'test with implied user',
            'implied_ids': [Command.link(cls.env.ref('base.group_user').id)]
        })
        cls.env["ir.model.data"].create({
            "module": "base",
            "name": "base_test_group",
            "model": "res.groups",
            "res_id": cls.test_group.id,
        })

    def _set_field_groups(self, model, field_name, groups):
        field = model._fields[field_name]
        self.patch(field, 'groups', groups)
        self.env.transaction.clear()
        # because of monkey patching, we clear everything including caches
        self.env.transaction.invalidate_ormcache('stable')
        self.env.transaction.invalidate_ormcache('groups')
        self.env.transaction.invalidate_ormcache('templates')

    def test_field_visibility_restriction(self):
        """Check that model-level ``groups`` parameter effectively restricts access to that
           field for users who do not belong to one of the explicitly allowed groups"""
        country = self.env['test_orm.country'].with_user(self.user_demo)

        # Add a view that adds a label for the field we are going to check
        primary = self.env["ir.ui.view"].create({
            "name": "Add separate label for code",
            "model": "test_orm.country",
            "type": "form",
            "priority": 1,
            "arch": """<form>
                <group>
                    <group string="Details">
                        <field name="name"/>
                        <label for="code"/>
                        <field name="code" nolabel="1"/>
                    </group>
                </group>
            </form>""",
        })

        # Verify the test environment first
        original_fields = country.fields_get([])
        form_view = country.get_view(primary.id, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        self.assertFalse(has_group_test, "`demo` user should not belong to the restricted group before the test")
        self.assertIn('code', original_fields, "'code' field must be properly visible before the test")
        self.assertNotEqual(view_arch.xpath("//field[@name='code'][@nolabel='1']"), [],
                             "Field 'code' must be found in view definition before the test")
        self.assertNotEqual(view_arch.xpath("//label[@for='code']"), [],
                             "Label for 'code' must be found in view definition before the test")

        # restrict access to the field and check it's gone
        self._set_field_groups(country, 'code', self.TEST_GROUP)

        fields = country.fields_get([])
        form_view = country.get_view(primary.id, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        self.assertNotIn('code', fields, "'code' field should be gone")
        self.assertEqual(view_arch.xpath("//field[@name='code']"), [],
                          "Field 'code' must not be found in view definition")
        self.assertEqual(view_arch.xpath("//label[@for='code']"), [],
                          "Label for 'code' must not be found in view definition")

        # Make demo user a member of the restricted group and check that the field is back
        self.test_group.user_ids += self.user_demo
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        fields = country.fields_get([])
        form_view = country.get_view(primary.id, 'form')
        view_arch = etree.fromstring(form_view.get('arch'))
        self.assertTrue(has_group_test, "`demo` user should now belong to the restricted group")
        self.assertIn('code', fields, "'code' field must be properly visible again")
        self.assertNotEqual(view_arch.xpath("//field[@name='code']"), [],
                             "Field 'code' must be found in view definition again")
        self.assertNotEqual(view_arch.xpath("//label[@for='code']"), [],
                             "Label for 'code' must be found in view definition again")

    @mute_logger('odoo.models')
    def test_field_crud_restriction(self):
        "Read/Write RPC access to restricted field should be forbidden"
        partner = self.env['test_orm.acl.partner'].with_user(self.user_demo).create({'name': 'foo'})

        # Verify the test environment first
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        self.assertFalse(has_group_test, "`demo` user should not belong to the restricted group")
        self.assertTrue(partner.read(['bank_ids']))
        self.assertTrue(partner.write({'bank_ids': []}))
        some_bank = partner.bank_ids.create({'account_number': '1234', 'partner_id': partner.id})

        # Now restrict access to the field and check it's forbidden
        self._set_field_groups(partner, 'bank_ids', self.TEST_GROUP)

        with self.assertRaises(AccessError):
            partner.search_fetch([], ['bank_ids'])
        with self.assertRaises(AccessError):
            partner.fetch(['bank_ids'])
        with self.assertRaises(AccessError):
            partner.read(['bank_ids'])
        with self.assertRaises(AccessError):
            partner.write({'bank_ids': []})
        with self.assertRaises(AccessError):
            partner.write({'bank_ids': [Command.create({'account_number': 'TEST 1234', 'holder_name': 'test'})]})
        with self.assertRaises(AccessError):
            partner.create({'name': 'create bank', 'bank_ids': [Command.create({'account_number': 'TEST 1234', 'holder_name': 'test'})]})
        with self.assertRaises(AccessError):
            partner.write({'bank_ids': [Command.delete(some_bank.id)]})
        self.assertTrue(some_bank.exists())

        # Add the restricted group, and check that it works again
        self.test_group.user_ids += self.user_demo
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        self.assertTrue(has_group_test, "`demo` user should now belong to the restricted group")
        self.assertTrue(partner.read(['bank_ids']))
        self.assertTrue(partner.write({'bank_ids': []}))

    @mute_logger('odoo.models')
    def test_field_on_comodel_restriction(self):
        partner = self.env['test_orm.acl.partner'].with_user(self.user_demo).create({'name': 'foo'})
        has_group_test = self.user_demo.has_group(self.TEST_GROUP)
        self.assertFalse(has_group_test, "`demo` user should not belong to the restricted group")

        partner.write({'bank_ids': [Command.clear(), Command.create({'partner_id': partner.id, 'account_number': '1234'})]})
        bank = partner.bank_ids
        bank.ensure_one()

        self._set_field_groups(bank, 'holder_name', self.TEST_GROUP)
        with self.assertRaises(AccessError):
            partner.write({'bank_ids': [Command.create({'account_number': 'TEST 1234', 'holder_name': 'test'})]})
        with self.assertRaises(AccessError):
            partner.write({'bank_ids': [Command.update(bank.id, {'holder_name': 'test'})]})

        with self.assertRaises(AccessError):
            partner.create({'name': 'ok', 'bank_ids': [Command.create({'account_number': 'TEST 1234', 'holder_name': 'test'})]})
        with self.assertRaises(AccessError):
            partner.create({'name': 'ok', 'bank_ids': [Command.update(bank.id, {'holder_name': 'test'})]})

        with self.assertRaises(AccessError):
            partner.with_context(default_bank_ids=[Command.create({'account_number': 'TEST 1234', 'holder_name': 'test'})]).create({'name': 'ok'})
        with self.assertRaises(AccessError):
            partner.with_context(default_bank_ids=[Command.update(bank.id, {'holder_name': 'test'})]).create({'name': 'ok'})

    @mute_logger('odoo.models')
    def test_create_comodel_restriction(self):
        state_access = self.env['ir.access'].search([('model_id.model', '=', 'test_orm.country.state')])
        state_access.write({'operation': 'cru'})  # Remove delete operation.

        country = self.env['test_orm.country'].with_user(self.user_demo).create({
            'name': 'New Guy',
            'state_ids': [Command.create({'name': '9876'})]
        })

        # check we can create countries
        country.create({'name': 'ok'})

        country.write({'state_ids': [Command.clear(), Command.create({'country_id': country.id, 'name': '1234'})]})
        state = country.state_ids
        state.ensure_one()

        self._set_field_groups(state, 'code', self.TEST_GROUP)
        with self.assertRaises(AccessError):
            country.write({'state_ids': [Command.create({'name': 'TEST 1234', 'code': 'test'})]})
        with self.assertRaises(AccessError):
            country.write({'state_ids': [Command.update(state.id, {'code': 'test'})]})
        with self.assertRaises(AccessError):
            country.write({'state_ids': [Command.delete(state.id)]})

    @mute_logger('odoo.models')
    def test_fields_browse_restriction(self):
        """Test access to records having restricted fields"""
        # Invalidate cache to avoid restricted value to be available
        # in the cache
        partner = self.env['test_orm.partner'].with_user(self.user_demo)
        self._set_field_groups(partner, 'email', self.TEST_GROUP)

        # accessing fields must no raise exceptions...
        partner = partner.search([], limit=1)
        partner.name
        # ... except if they are restricted
        with self.assertRaises(AccessError):
            with mute_logger('odoo.models'):
                partner.email

    def test_view_create_edit_button(self):
        """ Test form view Create, Edit, Delete button visibility based on access right of model.
        Test the user with and without access in the same unit test / transaction
        to test the views cache is properly working """
        methods = ['create', 'edit', 'delete']
        acl = self.env['test_orm.acl'].with_user(self.user_demo)
        acl_view = acl.get_view(False, 'form')
        view_arch = etree.fromstring(acl_view['arch'])

        # demo not part of the group_test, create edit and delete must be False
        for method in methods:
            self.assertEqual(view_arch.get(method), 'False')

        # demo part of the group_test, create edit and delete must not be specified
        acl = self.env['test_orm.acl'].with_user(self.env.ref("base.user_admin"))
        acl_view = acl.get_view(False, 'form')
        view_arch = etree.fromstring(acl_view['arch'])
        for method in methods:
            self.assertIsNone(view_arch.get(method))

    def test_m2o_field_create_edit(self):
        """ Test many2one field Create and Edit option visibility based on access rights of relation field
        Test the user with and without access in the same unit test / transaction
        to test the views cache is properly working """
        methods = ['create', 'write']
        acl = self.env['test_orm.acl'].with_user(self.user_demo)
        acl_view = acl.get_view(False, 'form')
        view_arch = etree.fromstring(acl_view['arch'])
        field_node = view_arch.xpath("//field[@name='many2one_id']")
        self.assertTrue(len(field_node), "many2one_id field should be in acl from view")
        for method in methods:
            self.assertEqual(field_node[0].get('can_' + method), 'False')

        acl = self.env['test_orm.acl'].with_user(self.env.ref("base.user_admin"))
        acl_view = acl.get_view(False, 'form')
        view_arch = etree.fromstring(acl_view['arch'])
        field_node = view_arch.xpath("//field[@name='many2one_id']")
        for method in methods:
            self.assertEqual(field_node[0].get('can_' + method), 'True')

    def test_get_views_fields(self):
        """ Tests fields restricted to group_test are not passed when calling `get_views` as demo
        but the same fields are well passed when calling `get_views` as admin"""
        Partner = self.env['test_orm.partner']
        self._set_field_groups(Partner, 'email', self.TEST_GROUP)
        views = Partner.with_user(self.user_demo).get_views([(False, 'form')])
        self.assertFalse('email' in views['models']['test_orm.partner']["fields"])
        self.user_demo.group_ids = [Command.link(self.test_group.id)]
        views = Partner.with_user(self.user_demo).get_views([(False, 'form')])
        self.assertTrue('email' in views['models']['test_orm.partner']["fields"])
