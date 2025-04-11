from odoo.tests import HttpCase, tagged
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("mail_message", "post_install", "-at_install")
class TestMessageLinks(HttpCase, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env["ir.ui.view"].with_context(active_test=False).search([
            ("key", "=", "website_sale.product_comment")
        ]).write({"active": True})
        cls.review_message = cls.product.product_tmpl_id.message_post(
            body="Here is the pizza menu!",
            message_type="comment",
            subtype_xmlid="mail.mt_comment"
        )

    def test_message_link_employee_ecommerce_product(self):
        self.start_tour(
            f"/mail/view?model=product.template&res_id={self.product.product_tmpl_id.id}&highlight_message_id={self.review_message.id}",
            "message_link_tour", login="demo"
        )

    def test_message_link_public_user_ecommerce_product(self):
        self.start_tour(
            f"/mail/view?model=product.template&res_id={self.product.product_tmpl_id.id}&highlight_message_id={self.review_message.id}",
            "website_sale_message_link_tour"
        )
