# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestGiftCardPromotion(TestPointOfSaleHttpCommon):
    def test_gift_card_promotion(self):
        """PoS Coupon Basic Tour"""
        self.product1 = self.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'list_price': 10,
            'available_in_pos': True,
            'taxes_id': False,
        })

        self.tax = self.env['account.tax'].create({
            'name': 'Tax 0%',
            'amount': 0,
            'amount_type': 'percent',
        })
        self.gift_card_product = self.env['product.product'].create({
            'name': 'Gift Card',
            'type': 'service',
            'taxes_id': [(6, 0, self.tax.ids)],
            'available_in_pos': True,
        })

        self.auto_promo_program_current = self.env["coupon.program"].create(
            {
                "name": "Auto Promo Program - Cheapest Product",
                "program_type": "promotion_program",
                "promo_code_usage": "no_code_needed",
                "discount_apply_on": "on_order",
                "reward_type":  "discount",
                "discount_percentage": 10,
            }
        )

        self.gift_card = self.env["gift.card"].create(
            {
                "code": "1234",
                "initial_amount": 100,
            })

        with Form(self.main_pos_config) as pos_config:
            pos_config.use_gift_card = True
            pos_config.use_coupon_programs = True
            pos_config.promo_program_ids.add(self.auto_promo_program_current)
            pos_config.gift_card_product_id = self.gift_card_product

        self.main_pos_config.open_session_cb(check_coa=False)
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosGiftCardTour",
            login="accountman",
        )
