# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.addons.website_sale_external_tax.controllers.main import WebsiteSaleExternalTaxCalculation, WebsiteSaleDelivery
from odoo.exceptions import ValidationError, UserError
from odoo.tests import tagged
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.website.tools import MockRequest
from odoo.addons.sale_external_tax.models.sale_order import SaleOrder as SaleOrderExternalTax


@tagged('post_install', '-at_install')
class TestWebsiteSaleExternalTaxCalculation(PaymentHttpCommon):
    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.Controller = WebsiteSaleExternalTaxCalculation()

    def test_validate_payment_with_error_from_external_provider(self):
        """
        Payment should be blocked if external tax provider raises an error
        (invalid address, connection issue, etc ...)
        """
        with patch(
            'odoo.addons.account_external_tax.models.account_external_tax_mixin.AccountExternalTaxMixin._get_external_taxes',
            side_effect=UserError('bim bam boom')
        ):
            with MockRequest(self.env, website=self.website):
                self.website.sale_get_order(force_create=True)
                with self.assertRaisesRegex(ValidationError, 'bim bam boom'):
                    self.Controller.shop_payment_validate()

    def test_order_summary_values_with_external_tax_error(self):
        """_order_summary_values should return external_tax_error if tax calc fails."""
        with MockRequest(self.env, website=self.website):
            order = self.website.sale_get_order(force_create=True)

            with patch.object(
                SaleOrderExternalTax,
                '_get_and_set_external_taxes_on_eligible_records',
                side_effect=UserError("Simulated external tax failure")
            ):
                controller = WebsiteSaleDelivery()
                res = controller._order_summary_values(order)
                self.assertIn('external_tax_error', res)
                self.assertEqual(res['external_tax_error'], "Simulated external tax failure")

    def test_external_taxes_apply_on_express_checkout(self):
        """Ensure external taxes are computed during express checkout route call."""
        published_product = self.env['product.product'].search(
            [('website_published', '=', True)],
            limit=1,
        )
        self.make_jsonrpc_request("/shop/cart/update_json", {
            'product_id': published_product.id,
            'add_qty': 1,
        })

        with patch.object(
            self.env.registry['sale.order'],
            '_get_and_set_external_taxes_on_eligible_records',
        ) as mock:
            self.make_jsonrpc_request(
                WebsiteSaleDelivery._express_checkout_delivery_route + '/compute_taxes', {}
            )
            self.assertEqual(mock.call_count, 1)
