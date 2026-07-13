# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
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

    def test_default_view_with_binaries(self):
        self.assertEqual(
            etree.tostring(self.env['binary.test']._get_default_form_view()),
            b'<form><sheet string="binary.test"><group><group><field name="img"/></group><group><field name="bin1"/></group></group><group><separator/></group></sheet></form>'
        )
