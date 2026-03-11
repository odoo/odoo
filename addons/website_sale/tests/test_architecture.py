# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, Command
from odoo.tests import tagged
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleArchitecture(ProductVariantsCommon, WebsiteSaleCommon):
    """
    Models and templates must be usable without a request. This allows the code to
    be used in the backend or other processes such as cron jobs. MockRequest is
    used only for controllers.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_render_product_proposal_without_request(self):
        parseltongue = self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.env['res.lang']._activate_lang(parseltongue.code)
        self.product_sofa_red.with_context(lang=parseltongue.code).product_tmpl_id.write({'name': 'Sofa Parseltongue'})

        # Automatically prepare an order for a previous customer, based on their wish list.
        user_values = dict(self.dummy_partner_address_values,
            name='Toto',
            login='long_enough_password',
            password='long_enough_password',
            lang=parseltongue.code,
            group_ids=[Command.link(self.env.ref('base.group_portal').id)],
        )
        test_user_sudo = self.env['res.users'].create(user_values)

        website = self.env['website'].search([], limit=1)

        # The order was created with SUPERUSER_ID
        so_data = website._prepare_sale_order_values(test_user_sudo.partner_id)
        order_sudo = self.env['sale.order'].with_user(SUPERUSER_ID).create(so_data)

        # Select some products
        order_sudo.with_context(skip_cart_verification=True)._cart_add(
            product_id=self.product_sofa_red.id,
            quantity=7,
        )
        order_sudo.with_context(skip_cart_verification=True)._cart_add(
            product_id=self.product_sofa_blue.id,
            quantity=13,
        )
        order_sudo.with_context(skip_cart_verification=True)._cart_add(
            product_id=self.product_sofa_green.id,
            quantity=1,
        )

        # Set the customer user to the order and products to use the lang, correct pricelist, fiscal position...
        irQweb = self.env['ir.qweb'].with_user(test_user_sudo).with_context(lang=test_user_sudo.lang).sudo()
        order_sudo = order_sudo.with_user(test_user_sudo).with_context(lang=test_user_sudo.lang).sudo()
        values = {
            'website': website,
            'is_view_active': website.is_view_active,
            'website_sale_order': order_sudo,
        }

        # In this test, the template is not important; what matters is using
        # methods such as _get_sales_prices or _get_combination_info and other
        # computed methods defined on BaseModel classes.
        content = irQweb._render('website_sale.cart_lines', values)

        self.assertIn('Sofa Parseltongue', content)
        self.assertIn(f'data-product-id="{self.product_sofa_red.id}" value="7"', content)
        self.assertIn(f'data-product-id="{self.product_sofa_blue.id}" value="13"', content)
        self.assertIn(f'data-product-id="{self.product_sofa_green.id}" value="1"', content)
