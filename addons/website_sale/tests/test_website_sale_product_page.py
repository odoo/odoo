# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import file_open

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleProductPage(HttpCase, ProductVariantsCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_template_sofa.website_published = True

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

    def test_portal_user_can_upload_attachment_on_product_review(self):
        """
        A portal user must be able to attach a file when posting a
        product review once reviews are enabled for the current website.
        """
        portal_user = new_test_user(
            self.env, login='product_review_portal', groups='base.group_portal',
            password='product_review_portal',
        )
        generic_view = self.env['ir.ui.view'].with_context(active_test=False).search([
            ('key', '=', 'website_sale.product_comment'),
        ], limit=1)
        generic_view.with_context(website_id=self.website.id).write({'active': True})

        self.product_template_sofa.website_published = True

        self.authenticate(portal_user.login, 'product_review_portal')
        with file_open("addons/web/__init__.py") as file:
            response = self.url_open(
                url="/mail/attachment/upload",
                data={
                    "csrf_token": http.Request.csrf_token(self),
                    "thread_id": self.product_template_sofa.id,
                    "thread_model": "product.template",
                },
                files={"ufile": file},
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertNotIn('error', result.get('data', {}), result.get('data'))
        attachment_id = result['data']['ir.attachment'][0]['id']
        self.assertTrue(self.env['ir.attachment'].sudo().browse(attachment_id).exists())

    def _add_reaction(self, message, reaction):
        self.make_jsonrpc_request(
            "/mail/message/reaction",
            {
                "action": "add",
                "content": reaction,
                "message_id": message.id,
            },
        )

    def test_product_unpublished_without_category(self):
        """Test that products created from frontend are unpublished without category"""
        self.start_tour("/", 'product_unpublished_without_category', login="admin")
        product = self.env['product.product'].search(
            [('name', '=', 'Product Without Category')],
            limit=1,
        )
        self.assertTrue(product)
        self.assertFalse(product.website_published)

    def test_product_published_with_category(self):
        """Test that products with category are published"""
        self.env['product.public.category'].create({'name': 'Test Category'})
        self.start_tour("/", 'product_published_with_category', login="admin")
        product = self.env['product.product'].search(
            [('name', '=', 'Product With Category')],
            limit=1,
        )
        self.assertTrue(product)
        self.assertTrue(product.website_published)
