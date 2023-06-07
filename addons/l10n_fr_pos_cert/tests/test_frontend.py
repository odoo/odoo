# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
import odoo.tests

@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestFrenchPoS(TestPointOfSaleHttpCommon):
    def test_old_price_display(self):

        #change company country to France
        self.env.user.company_id.country_id = self.env.ref('base.fr')
        self.assertEqual(self.env.user.company_id.country_id, self.env.ref('base.fr'))
        #create product A with price 10€ and a pricelist that set the price of this product to 5€
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
        })
        base_pricelist = self.env['product.pricelist'].create({
            'name': 'base_pricelist',
            'discount_policy': 'without_discount',
        })
        special_pricelist = self.env['product.pricelist'].create({
            'name': 'special_pricelist',
            'item_ids': [(0, 0, {
                'applied_on': '0_product_variant',
                'product_id': product_a.id,
                'compute_price': 'fixed',
                'fixed_price': 5,
            })],
        })
        #add the price list to the pos config
        self.main_pos_config.write({
            'pricelist_id': base_pricelist.id,
            'available_pricelist_ids': [(6, 0, [base_pricelist.id, special_pricelist.id])],
        })
        self.main_pos_config.open_session_cb()
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "OldPriceProductTour",
            login="accountman",
        )
