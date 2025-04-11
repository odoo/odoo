from odoo.tests import HttpCase, tagged
from odoo.addons.website_slides.tests.common import SlidesCase


@tagged("mail_message", "post_install", "-at_install")
class TestMessageLinks(HttpCase, SlidesCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.review_message = cls.channel.message_post(
            body="Here is the pizza menu!",
            message_type="comment",
            rating_value="5",
            subtype_xmlid="mail.mt_comment"
        )

    def test_message_link_employee_course(self):
        self.start_tour(
            f"/mail/view?model=slide.channel&res_id={self.channel.id}&highlight_message_id={self.review_message.id}",
            "message_link_tour", login="demo"
        )

    def test_message_link_public_user_course(self):
        self.start_tour(
            f"/mail/view?model=slide.channel&res_id={self.channel.id}&highlight_message_id={self.review_message.id}",
            "slides_message_link_tour"
        )
