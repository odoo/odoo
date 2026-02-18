from lxml import etree
from odoo.tests import tagged, TransactionCase


@tagged("at_install", "-post_install")
class TestSlideViews(TransactionCase):
    def test_slide_question_view_form_has_display_name(self):
        """Regression Test: Ensure 'display_name' is present in the slide.question form view."""
        view = self.env.ref("website_slides.slide_question_view_form")
        doc = etree.fromstring(view.arch_db)
        nodes = doc.xpath("//field[@name='answer_ids']//list//field[@name='display_name']")
        self.assertTrue(nodes)
