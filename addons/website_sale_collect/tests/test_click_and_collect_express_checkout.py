# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_collect.controllers.delivery import InStoreDelivery
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged("post_install", "-at_install")
class TestClickAndCollectExpressCheckout(ClickAndCollectCommon):
    _test_user_groups = (
        'base.group_user',
        'product.group_product_manager',
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    def test_exclude_in_store_delivery_methods(self):
        website = self.env["website"].search([], limit=1)
        with MockRequest(website.env, website=website):
            express_delivery_methods = InStoreDelivery._get_delivery_methods_express_checkout(
                self.cart
            )

        self.assertNotIn(self.in_store_dm, express_delivery_methods)
