# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale_picking.tests.common import OnsiteCommon


@tagged('-at_install', 'post_install')
class TestOnsiteCheckout(HttpCase, OnsiteCommon):

    def test_onsite_payment_tour(self):
        self.provider.is_published = True

        self.start_tour('/shop', 'onsite_payment_tour')
