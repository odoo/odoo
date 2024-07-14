# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from . import common

from odoo.exceptions import UserError
from odoo.fields import Command

class TestSaleCouponTaxCloudFlow(common.TestSaleCouponTaxCloudCommon):

    def setUp(self):
        super(TestSaleCouponTaxCloudFlow, self).setUp()

        self.env.company.country_id = self.env.ref('base.us')
        self.env['account.tax.group'].create(
            {'name': 'Test Account Tax Group', 'company_id': self.env.company.id}
        )

        # the response for the full order, without any discount
        self.response_full = {'values': {0: 8.88, 1: 4.44, 2: 0.89}}
        # the response for the half price order
        self.response_discounted = {'values': {0: 7.99, 1: 3.99, 2: 0.8}}

        order = self.order
        TaxCloud = order._get_TaxCloudRequest("id", "api_key")
        SaleOrder_get_TaxCloudRequest = type(order)._get_TaxCloudRequest

        def _get_TaxCloudRequest(self, api_id, api_key):
            if self == order:
                return TaxCloud
            return SaleOrder_get_TaxCloudRequest(self, api_id, api_key)

        patchers = [
            patch.object(type(order), '_get_TaxCloudRequest', _get_TaxCloudRequest),
            patch('odoo.addons.account_taxcloud.models.taxcloud_request.TaxCloudRequest.verify_address', self._verify_address),
            patch('odoo.addons.account_taxcloud.models.taxcloud_request.TaxCloudRequest.get_all_taxes_values', self._get_all_taxes_values),
        ]
        for patcher in patchers:
            self.startPatcher(patcher)

    def _verify_address(self, *args):
        return {
        'apiLoginID': '',
        'apiKey': '',
        'Address1': '',
        'Address2': '',
        'City': '',
        "State": '',
        "Zip5": '',
        "Zip4": '',
    }

    def _get_all_taxes_values(self):
        if self.response == 'full':
            return self.response_full
        return self.response_discounted

    def test_flow(self):
        """We mock the actual requests to TaxCloud, but besides that the test
           covers most points of the flow, that is:
            - user can get taxes / apply coupon / recompute taxes / etc
            - when applying a discount, taxes should be wiped first, as discount
              lines would be split by taxes and have taxes applied on them
            - validating taxes should not modify the order except for taxes
            - tax application should be coherent with the discount
            - the discount has been applied has it should and taxes reflect that
        """
        self.assertEqual(self.order.amount_total, 160)
        self.assertEqual(self.order.amount_tax, 0)

        self.response = 'full'
        self.order.validate_taxes_on_sales_order()

        self.assertEqual(self.order.amount_untaxed, 160)
        self.assertEqual(self.order.amount_tax, 14.21)

        # we now add a 10% discount on order
        # Normally we always go through `_update_programs_and_rewards` which resets the taxes but it is not required here
        self.order.order_line.write({'tax_id': [(Command.CLEAR,)]})
        self._apply_promo_code(self.order, self.program_order_percent.coupon_ids.code)

        self.assertEqual(self.order.amount_total, 144)
        self.assertFalse(self.order.order_line.mapped('tax_id'),
            "All taxes have been wiped from the order to start clean.")
        self.assertEqual(len(self.order.order_line), 4,
            "Only one discount line has been added; it was not split by taxes")

        discount_line = self.order.order_line.filtered('reward_id')
        self.assertEqual(discount_line.reward_id.program_id, self.program_order_percent,
            "The program origin should be linked on the discount line")
        self.assertEqual(discount_line.price_unit, -16)
        self.assertEqual(discount_line.product_uom_qty, 1)

        self.response = 'discounted'
        self.order.validate_taxes_on_sales_order()

        self.assertEqual(self.order.amount_untaxed, 144, "Untaxed amount did not change")
        self.assertAlmostEqual(self.order.amount_tax, 12.78, 4, "Taxes have been reduced by 10%")
        for line in self.order.order_line.filtered(lambda l: not l.reward_id):
            self.assertEqual(line.price_taxcloud, line.price_unit * .9,
                             "The discount should have been applied evenly.")

        self.order.action_confirm()
        self.assertAlmostEqual(self.order.amount_tax, 12.78, 4,
                               "Confirming the sale order should not alter the taxes")

    def test_flow_with_auto_done(self):
        self.env.user.groups_id += self.env.ref('sale.group_auto_done_setting')
        try:
            self.test_flow()
        except UserError:
            self.fail(
                "We should be able to confirm the sale order, even if 'Lock Confirmed Sales' is enabled.")
