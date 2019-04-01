# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


class TestUi(odoo.tests.HttpCase):

    post_install = True
    at_install = False

    def test_01_admin_shop_sale_coupon_tour(self):
        # pre enable "Show # found" option to avoid race condition...
        self.env.ref("website_sale.search count").write({"active": True})
        self.phantom_js(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('shop_sale_coupon')",
            "odoo.__DEBUG__.services['web_tour.tour'].tours.shop_sale_coupon.ready",
            login="admin",
        )
