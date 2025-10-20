from lxml import etree

from odoo.tests import tagged, common
from odoo.addons.base.tests.test_views import ViewCase


@tagged('at_install', '-post_install')  # LEGACY at_install
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
            b'<form><sheet string="Test ORM Mixed"><group><group><field name="foo"/></group></group><group><field name="text"/></group><group><group><field name="truth"/><field name="number"/><field name="date"/><field name="now"/><field name="reference"/></group><group><field name="count"/><field name="number2"/><field name="moment"/><field name="lang"/></group></group><group><field name="comment0"/></group><group><field name="comment1"/></group><group><field name="comment2"/></group><group><field name="comment3"/></group><group><field name="comment4"/></group><group><field name="comment5"/></group><group><group><field name="currency_id"/></group><group><field name="amount"/></group></group><group><separator/></group></sheet></form>',
        )

    def test_default_view_with_binaries(self):
        self.assertEqual(
            etree.tostring(self.env['binary.test']._get_default_form_view()),
            b'<form><sheet string="binary.test"><group><group><field name="img"/></group><group><field name="bin1"/></group></group><group><separator/></group></sheet></form>'
        )

    def test_default_calender_view(self):
        self.assertEqual(
            etree.tostring(self.env['calendar.test']._get_default_calendar_view()),
            b'<calendar string="calendar.test" date_start="x_date_start" date_stop="x_date_end"><field name="id"/></calendar>'
        )


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
