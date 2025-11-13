from odoo.tests import Form, common

from odoo.exceptions import ValidationError
from odoo.addons.base.tests.test_views import ViewCase


@common.tagged('at_install', '-post_install', 'groups')
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

    def test_computed_invisible_modifier(self):
        self.env["ir.ui.view"].create(
            {
                "name": "stuff",
                "model": "test_orm.computed.modifier",
                "arch": """
                    <form>
                        <field name="foo"/>
                        <field name="bar"/>
                        <field name="name" readonly="sub_foo or sub_bar"/>
                    </form>
                """,
            }
        )

        with Form(self.env["test_orm.computed.modifier"]) as form:
            form.name = "toto"
            self.assertEqual(form._view["onchange"]["foo"], "1")
            self.assertEqual(form._view["onchange"]["bar"], "1")

        with Form(self.env["test_orm.computed.modifier"]) as form:
            form.foo = 1  # should make 'name' readonly by recomputing sub_foo
            with self.assertRaisesRegex(
                AssertionError, "can't write on readonly field 'name'"
            ):
                form.name = "toto"

        with Form(self.env["test_orm.computed.modifier"]) as form:
            form.bar = 1  # should make 'name' readonly by onchange modifying sub_bar
            with self.assertRaisesRegex(
                AssertionError, "can't write on readonly field 'name'"
            ):
                form.name = "toto"
