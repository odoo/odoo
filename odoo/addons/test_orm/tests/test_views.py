from lxml import etree

from odoo.exceptions import ValidationError
from odoo.tests import Form, common

from odoo.addons.base.tests.test_views import ViewCase


class TestDefaultView(common.TransactionCase):

    def test_default_form_view(self):
        self.assertEqual(
            etree.tostring(self.env['test_orm.message']._get_default_form_view()),
            b'<form><sheet string="Test ORM Message"><group><group><field name="discussion"/></group></group><group><field name="body"/></group><group><group><field name="author"/><field name="size"/><field name="discussion_name"/><field name="important"/><field name="priority"/><field name="has_important_sibling"/></group><group><field name="name"/><field name="double_size"/><field name="author_partner"/><field name="label"/><field name="active"/><field name="attributes"/></group></group><group><separator/></group></sheet></form>',
        )
        self.assertEqual(
            etree.tostring(self.env['test_orm.creativework.edition']._get_default_form_view()),
            b'<form><sheet string="Test ORM Creative Work Edition"><group><group><field name="name"/><field name="res_model_id"/></group><group><field name="res_id"/><field name="res_model"/></group></group><group><separator/></group></sheet></form>',
        )
        self.assertEqual(
            etree.tostring(self.env['test_orm.mixed']._get_default_form_view()),
            b'<form><sheet string="Test ORM Mixed"><group><group><field name="foo"/></group></group><group><field name="text"/></group><group><group><field name="truth"/><field name="number"/><field name="date"/><field name="now"/><field name="reference"/></group><group><field name="count"/><field name="number2"/><field name="moment"/><field name="lang"/></group></group><group><field name="comment0"/></group><group><field name="comment1"/></group><group><field name="comment2"/></group><group><field name="comment3"/></group><group><field name="comment4"/></group><group><field name="comment5"/></group><group><group><field name="json"/><field name="amount"/></group><group><field name="currency_id"/></group></group><group><separator/></group></sheet></form>',
        )

    def test_default_view_with_binaries(self):
        self.assertEqual(
            etree.tostring(self.env['binary.test']._get_default_form_view()),
            b'<form><sheet string="binary.test"><group><group><field name="img"/></group><group><field name="bin1"/></group></group><group><separator/></group></sheet></form>'
        )


@common.tagged('at_install', 'groups')
class TestViewGroups(ViewCase):
    def test_attrs_groups(self):
        """ Checks that attrs/modifiers with groups work
        """
        self.env.user.group_ids = [(6, 0, [self.env.ref('base.group_system').id])]
        f = Form(self.env['test_orm.model.some_access'], view='test_orm.view_model_some_access')
        f.a = 1
        f.b = 2
        with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'c'"):
            f.c = 3
        with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'e'"):
            f.e = 3
        with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'f'"):
            f.f = 3

        # other access

        self.env.user.group_ids = [(6, 0, [self.env.ref('base.group_public').id])]
        f = Form(self.env['test_orm.model.some_access'], view='test_orm.view_model_some_access')
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

        # create must warn because 'a' and the model has no 'base.group_portal'
        self.assertWarning("""
                <form>
                    <field name="a" readonly="j"/>
                </form>
            """,
            expected_message="- field “j” is accessible for groups: Only super user has access<br/>"
                """- element “&lt;field name=&#34;a&#34; readonly=&#34;j&#34;/&gt;” is shown in the view for groups: &#39;base.group_system&#39; | &#39;base.group_public&#39;""",
            model='test_orm.model.some_access')

        # a: base.group_public,base.group_system > -
        # d: base.group_public,base.group_system > base.group_erp_manager
        self.assertWarning("""
                <form>
                    <field name="a" readonly="d"/>
                </form>
            """,
            expected_message="- field “d” is accessible for groups: &#39;base.group_system&#39;<br/>"
                """- element “&lt;field name=&#34;a&#34; readonly=&#34;d&#34;/&gt;” is shown in the view for groups: &#39;base.group_system&#39; | &#39;base.group_public&#39;""",
            model='test_orm.model.some_access')

        # e: base.group_public,base.group_system > base.group_erp_manager,base.group_portal
        # d: base.group_public,base.group_system > base.group_erp_manager
        self.assertWarning("""
                <form>
                    <field name="d"/>
                    <field name="e" readonly="d"/>
                </form>
            """,
            expected_message="- field “d” is accessible for groups: &#39;base.group_system&#39;<br/>"
                """- element “&lt;field name=&#34;e&#34; readonly=&#34;d&#34;/&gt;” is shown in the view for groups: &#39;base.group_system&#39; | (&#39;base.group_multi_company&#39; &amp; &#39;base.group_public&#39;)""",
            model='test_orm.model.some_access')

        # i: base.group_public,base.group_system > !base.group_portal
        # h: base.group_public,base.group_system > base.group_erp_manager,!base.group_portal
        self.assertWarning("""
                <form>
                    <field name="i" readonly="h"/>
                </form>
            """,
            model='test_orm.model.some_access')

        # i: base.group_public,base.group_system > !base.group_portal
        # j: base.group_public,base.group_system > base.group_portal
        self.assertWarning("""
                <form>
                    <field name="i" readonly="j"/>
                </form>
            """,
            model='test_orm.model.some_access')

        # i: public,portal,user,system > !base.group_portal
        # h: public,portal,user,system > base.group_portal
        self.assertWarning("""
                <form>
                    <field name="ab" readonly="cd"/>
                </form>
            """,
            model='test_orm.model.all_access')

        # must raise for does not exists error
        with self.assertRaisesRegex(ValidationError, 'Field "ab" does not exist in model "test_orm.model.some_access"'):
            self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_orm.model.some_access',
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
            'group_ids': [(4, self.env.ref('base.group_user').id)],
        })
        view = self.env.ref('test_orm.view_model_all_access').with_user(user)
        arch = self.env['test_orm.model.all_access']._get_view_cache(view_id=view.id)['arch']
        form = etree.fromstring(arch)

        nodes = form.xpath("//field[@name='ef'][@invisible='True'][@readonly='True']")
        self.assertTrue(nodes, "form should contains the missing field 'ef'")
        self.assertFalse(nodes[0].get('groups'), "The missing field 'ef' should not have groups (groups equal to the model groups)")

    def test_tree(self):
        view = self.env.ref('test_orm.view_model_some_access_tree')
        arch = self.env['test_orm.model.some_access'].get_views([(view.id, 'list')])['views']['list']['arch']
        tree = etree.fromstring(arch)

        nodes = tree.xpath("//list/field[@name='a'][@column_invisible='True'][@readonly='True']")
        self.assertTrue(nodes, "list should contains the missing field 'a'")

        nodes = tree.xpath("//groupby/field[@name='ab'][@invisible='True'][@readonly='True']")
        self.assertTrue(nodes, "groupby should contains the missing field 'ab'")

    def test_related_field_and_groups(self):
        # group from related
        self.assertWarning("""
                <form>
                    <field name="g_id"/>
                </form>
            """,
            expected_message="&#39;base.group_erp_manager&#39; &amp; &#39;base.group_multi_company&#39;",
            model='test_orm.model2.some_access')

        # should not fail, the domain is not applied on xxx_sub_id
        self.env['ir.ui.view'].create({
            'name': 'stuff',
            'model': 'test_orm.model3.some_access',
            'arch': """
                <form>
                    <field name="xxx_sub_id" groups="base.group_erp_manager"/>
                </form>
            """,
        })

    def test_computed_invisible_modifier(self):
        self.env['ir.ui.view'].create({
                'name': 'stuff',
                'model': 'test_orm.computed.modifier',
                'arch': """
                    <form>
                        <field name="foo"/>
                        <field name="bar"/>
                        <field name="name" readonly="sub_foo or sub_bar"/>
                    </form>
                """,
            })

        with Form(self.env['test_orm.computed.modifier']) as form:
            form.name = 'toto'
            self.assertEqual(form._view['onchange']['foo'], '1')
            self.assertEqual(form._view['onchange']['bar'], '1')

        with Form(self.env['test_orm.computed.modifier']) as form:
            form.foo = 1  # should make 'name' readonly by recomputing sub_foo
            with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'name'"):
                form.name = 'toto'

        with Form(self.env['test_orm.computed.modifier']) as form:
            form.bar = 1  # should make 'name' readonly by onchange modifying sub_bar
            with self.assertRaisesRegex(AssertionError, "can't write on readonly field 'name'"):
                form.name = 'toto'

    def test_add_properties_definition_field(self):
        view = self.env['ir.ui.view'].create({
            'name': 'stuff',
            'model': 'test_orm.message',
            'arch': """
                <form>
                    <field name="attributes"/>
                </form>
            """,
        })
        views = self.env['test_orm.message'].get_views([(view.id, 'form')])
        arch = views['views']['form']['arch']
        form = etree.fromstring(arch)
        discussion_node = form.find("field[@name='discussion']")
        self.assertIsNotNone(discussion_node, "the properties definition field `discussion` should be added automatically")
        self.assertEqual(discussion_node.get("invisible"), "True")
        self.assertEqual(discussion_node.get("data-used-by"), "fieldname='attributes' (field,attributes)")
