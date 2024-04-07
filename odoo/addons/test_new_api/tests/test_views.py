# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form
from odoo.exceptions import ValidationError
from lxml import etree


class TestDefaultView(common.TransactionCase):

    def test_default_form_view(self):
        self.assertEqual(
            etree.tostring(self.env['test_new_api.message']._get_default_form_view()),
            b'<form><sheet string="Test New API Message"><group><group><field name="discussion"/></group></group><group><field name="body"/></group><group><group><field name="author"/><field name="display_name"/><field name="double_size"/><field name="author_partner"/><field name="label"/><field name="active"/><field name="attributes"/></group><group><field name="name"/><field name="size"/><field name="discussion_name"/><field name="important"/><field name="priority"/><field name="has_important_sibling"/></group></group><group><separator/></group></sheet></form>'
        )
        self.assertEqual(
            etree.tostring(self.env['test_new_api.creativework.edition']._get_default_form_view()),
            b'<form><sheet string="Test New API Creative Work Edition"><group><group><field name="name"/><field name="res_model_id"/></group><group><field name="res_id"/><field name="res_model"/></group></group><group><separator/></group></sheet></form>'
        )
        self.assertEqual(
            etree.tostring(self.env['test_new_api.mixed']._get_default_form_view()),
            b'<form><sheet string="Test New API Mixed"><group><group><field name="number"/><field name="date"/><field name="now"/><field name="reference"/></group><group><field name="number2"/><field name="moment"/><field name="lang"/></group></group><group><field name="comment1"/></group><group><field name="comment2"/></group><group><field name="comment3"/></group><group><field name="comment4"/></group><group><field name="comment5"/></group><group><group><field name="currency_id"/></group><group><field name="amount"/></group></group><group><separator/></group></sheet></form>'
        )


@common.tagged('at_install', 'groups')
class TestViewGroups(common.TransactionCase):
    def test_attrs_groups(self):
        """ Checks that attrs/modifiers with groups work
        """
        self.env.user.groups_id = [(6, 0, [self.env.ref('base.group_system').id])]
        f = Form(self.env['test_new_api.model.some_access'], view='test_new_api.view_model_some_access')
        f.a = 1
        f.b = 2
        with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'c'"):
            f.c = 3
        with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'e'"):
            f.e = 3
        with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'f'"):
            f.f = 3

        # other access

        self.env.user.groups_id = [(6, 0, [self.env.ref('base.group_public').id])]
        f = Form(self.env['test_new_api.model.some_access'], view='test_new_api.view_model_some_access')
        f.a = 1
        with self.assertRaisesRegex(AssertionError, "'b' was not found in the view"):
            f.b = 2
        with self.assertRaisesRegex(AssertionError, "'c' was not found in the view"):
            f.c = 3
        with self.assertRaisesRegex(AssertionError, "'e' was not found in the view"):
            # field added automatically but removed from used groups (base.group_erp_manager,base.group_portal on field 'd' and 'f')
            f.e = 3
        with self.assertRaisesRegex(AssertionError, "'f' was not found in the view"):
            f.f = 3
        with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'k'"):
            # field add automatically
            f.k = 3

        with self.assertRaises(ValidationError) as catcher:
            # create must fail because 'a' and the model has no 'base.group_portal'
            self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_new_api.model.some_access',
                'arch': """
                    <form>
                        <field name="a" readonly="j"/>
                    </form>
                """,
            })
        error_message = str(catcher.exception.args[0])
        self.assertIn("Field 'j' is restricted by groups without matching with the common mandatory groups.", error_message)
        self.assertIn("field 'j' (Only super user has access)", error_message)
        self.assertIn("""<field name="a" readonly="j"/>    ('base.group_system' | 'base.group_public')""", error_message)

        with self.assertRaises(ValidationError) as catcher:
            # a: base.group_public,base.group_system > -
            # d: base.group_public,base.group_system > base.group_erp_manager
            self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_new_api.model.some_access',
                'arch': """
                    <form>
                        <field name="a" readonly="d"/>
                    </form>
                """,
            })
        error_message = str(catcher.exception.args[0])
        self.assertIn("Field 'd' is restricted by groups without matching with the common mandatory groups.", error_message)
        self.assertIn("field 'd' ('base.group_system')", error_message)
        self.assertIn("""<field name="a" readonly="d"/>    ('base.group_system' | 'base.group_public')""", error_message)

        with self.assertRaises(ValidationError) as catcher:
            # e: base.group_public,base.group_system > base.group_erp_manager,base.group_portal
            # d: base.group_public,base.group_system > base.group_erp_manager
            self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_new_api.model.some_access',
                'arch': """
                    <form>
                        <field name="d"/>
                        <field name="e" readonly="d"/>
                    </form>
                """,
            })
        error_message = str(catcher.exception.args[0])
        self.assertIn("Field 'd' is restricted by groups without matching with the common mandatory groups.", error_message)
        self.assertIn("field 'd' ('base.group_system')", error_message)
        self.assertIn("""<field name="e" readonly="d"/>    ('base.group_system' | ('base.group_multi_company' & 'base.group_public'))""", error_message)

        with self.assertRaises(ValidationError):
            # i: base.group_public,base.group_system > !base.group_portal
            # h: base.group_public,base.group_system > base.group_erp_manager,!base.group_portal
            self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_new_api.model.some_access',
                'arch': """
                    <form>
                        <field name="i" readonly="h"/>
                    </form>
                """,
            })

        with self.assertRaises(ValidationError):
            # i: base.group_public,base.group_system > !base.group_portal
            # j: base.group_public,base.group_system > base.group_portal
            self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_new_api.model.some_access',
                'arch': """
                    <form>
                        <field name="i" readonly="j"/>
                    </form>
                """,
            })

        with self.assertRaises(ValidationError):
            # i: public,portal,user,system > !base.group_portal
            # h: public,portal,user,system > base.group_portal
            self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_new_api.model.all_access',
                'arch': """
                    <form>
                        <field name="ab" readonly="cd"/>
                    </form>
                """,
            })

    def test_model_access(self):
        user = self.env['res.users'].create({
            'name': 'A User',
            'login': 'a_user',
            'email': 'a@user.com',
            'groups_id': [(4, self.env.ref('base.group_user').id)],
        })
        view = self.env.ref('test_new_api.view_model_all_access').with_user(user)
        arch = self.env['test_new_api.model.all_access']._get_view_cache(view_id=view.id)['arch']
        form = etree.fromstring(arch)

        nodes = form.xpath("//field[@name='ef'][@invisible='True'][@readonly='True']")
        self.assertTrue(nodes, "form should contains the missing field 'ef'")
        self.assertFalse(nodes[0].get('groups'), "The missing field 'ef' should not have groups (groups equal to the model groups)")

    def test_tree(self):
        view = self.env.ref('test_new_api.view_model_some_access_tree')
        arch = self.env['test_new_api.model.some_access'].get_views([(view.id, 'tree')])['views']['tree']['arch']
        tree = etree.fromstring(arch)

        nodes = tree.xpath("//tree/field[@name='a'][@column_invisible='True'][@readonly='True']")
        self.assertTrue(nodes, "tree should contains the missing field 'a'")

        nodes = tree.xpath("//groupby/field[@name='ab'][@invisible='True'][@readonly='True']")
        self.assertTrue(nodes, "groupby should contains the missing field 'ab'")

    def test_related_field_and_groups(self):
        # group from related
        with self.assertRaisesRegex(ValidationError, "'base.group_erp_manager' & 'base.group_multi_company'"):
            self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_new_api.model2.some_access',
                'arch': """
                    <form>
                        <field name="g_id"/>
                    </form>
                """,
            })

        # should not fail, the domain is not applied on xxx_sub_id
        self.env['ir.ui.view'].create({
            'name': 'stuff',
            'model': 'test_new_api.model3.some_access',
            'arch': """
                <form>
                    <field name="xxx_sub_id" groups="base.group_erp_manager"/>
                </form>
            """,
        })
