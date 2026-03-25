from lxml import etree

from odoo.tests import tagged, common


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
