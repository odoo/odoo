# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleProductPage(HttpCase, ProductVariantsCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_template_sofa.website_published = True

    def test_toggle_contact_us_button_visibility(self):
        """Check that the "Contact Us" button:
          - is shown for zero-priced products
          - is hidden for other products
          - is not displayed at the same time as the "Add to Cart" button
        """
        self.website.prevent_zero_price_sale = True

        self.product_template_sofa.list_price = 0
        red_sofa, blue_sofa = self.product_template_sofa.product_variant_ids[:2]
        blue_sofa.product_template_attribute_value_ids.price_extra = 20

        self.start_tour(red_sofa.website_url, 'website_sale_contact_us_button')

    def test_product_reviews_reactions_public(self):
        """ Check that public users can not react to reviews """
        password = "Pl1bhD@2!kXZ"
        manager = self.env.ref("base.user_admin")
        manager.write({"password": password})

        self.env["ir.ui.view"].with_context(active_test=False).search([
            ("key", "=", "website_sale.product_comment")
        ]).write({"active": True})

        self.product_product_7 = self.env["product.product"].create({
            "name": "Storage Box Test",
            "standard_price": 70.0,
            "list_price": 79.0,
            "website_published": True,
            "invoice_policy": "delivery",
        })
        message = self.product_product_7.product_tmpl_id.message_post(
            body="Bad box!",
            message_type="comment",
            rating_value="1",
            subtype_xmlid="mail.mt_comment"
        )
        self.authenticate(manager.login, password)
        self._add_reaction(message, "😊")

        self.start_tour("/", "website_sale_product_reviews_reactions_public", login=None)

    def _add_reaction(self, message, reaction):
        self.make_jsonrpc_request(
            "/mail/message/reaction",
            {
                "action": "add",
                "content": reaction,
                "message_id": message.id,
            },
        )
