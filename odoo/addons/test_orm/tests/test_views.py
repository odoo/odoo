from lxml import etree

from odoo.tests import common
from odoo.addons.base.tests.test_ir_ui_view import ViewCase


@common.tagged('at_install', '-post_install', 'groups')
class TestViewGroups(ViewCase):
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

    def test_auto_add_filename_with_binary_requesting(self):
        view = self.env['ir.ui.view'].create({
            'name': 'stuff',
            'model': 'test_orm.model_binary',
            'arch': """
                <form>
                    <field name="binary" filename="binary_x_filename" readonly="context.get('dummy')"/>
                    <field name="binary" filename="binary_x_filename2"/>
                    <field name="binary" filename="i_dont_exist"/>
                </form>
            """,
        })
        views = self.env['test_orm.model_binary'].get_views([(view.id, 'form')])
        arch = views['views']['form']['arch']
        form = etree.fromstring(arch)
        filename = form.xpath("//field[@name='binary_x_filename']")[0]
        self.assertEqual(dict(filename.attrib), {'name': 'binary_x_filename', 'invisible': 'True', 'readonly': "context.get('dummy')", 'data-used-by': "filename='binary_x_filename' (field,binary)"})

        filename2 = form.xpath("//field[@name='binary_x_filename2']")[0]
        self.assertEqual(dict(filename2.attrib), {'name': 'binary_x_filename2', 'invisible': 'True', 'readonly': 'False', 'data-used-by': "filename='binary_x_filename2' (field,binary)"})

        self.assertEqual(form.xpath("//field[@name='i_dont_exist']"), [])
