# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch
from urllib.parse import urlencode

from odoo.tests.common import HttpCase, tagged, users
from odoo.tools import mute_logger

from odoo.addons.sale_amazon.controllers.onboarding import compute_oauth_signature
from odoo.addons.sale_amazon.tests.common import OPERATIONS_RESPONSES_MAP, TestAmazonCommon
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install')
class TestAmazonMultiCompany(TestAmazonCommon, HttpCase):

    def setUp(self):
        super().setUp()
        self.branch_company = self.env['res.company'].create({
            'name': "Test branch company",
            'currency_id': self.env.company.currency_id.id,
            'parent_id': self.env.company.id})
        self.parent_tax = self.env['account.tax'].create(
            {'name': "Test Tax", 'company_id': self.env.company.id}
        )

        self.other_amazon_account = self.env['amazon.account'].create({
            'name': 'TestAnotherAccountName',
            'seller_key': 'Random Seller Key',
            'refresh_token': 'A refresh token',
            'base_marketplace_id': self.marketplace.id,
            'available_marketplace_ids': [self.marketplace.id],
            'active_marketplace_ids': [self.marketplace.id],
            'company_id': self.branch_company.id,
        })

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_tax_application_on_sync_order_for_branch_company(self):
        """ Test the orders synchronization can assign taxes from parent company. """

        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = self.parent_tax
            return product_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            self.other_amazon_account._sync_orders(auto_commit=False)
            self.assertEqual(
                self.other_amazon_account.last_orders_sync,
                datetime(2020, 1, 1),
                msg="The last_order_sync should be equal to the date returned by get_orders_data"
                    " when the synchronization is completed."
            )
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            self.assertEqual(len(order), 1, msg="There should have been exactly one order created.")
            self.assertEqual(order.company_id.id, self.other_amazon_account.company_id.id)

            order_lines = self.env['sale.order.line'].search([('order_id', '=', order.id)])
            self.assertEqual(
                len(order_lines),
                4,
                msg="There should have been four order lines created: one for the product, one for"
                    " the gift wrapping charges, one (note) for the gift message and one for the"
                    " shipping."
            )
            product_line = order_lines.filtered(lambda l: l.product_id.default_code == 'TEST')
            self.assertEqual(
                product_line.price_unit,
                50.0,
                msg="The unitary price should be the quotient of the item price (tax excluded)"
                    " divided by the quantity.",
            )
            self.assertEqual(product_line.tax_id, self.parent_tax)

            shipping_line = order_lines.filtered(
                lambda l: l.product_id.default_code == 'SHIPPING-CODE'
            )
            self.assertEqual(shipping_line.tax_id, self.parent_tax)

            gift_wrapping_line = order_lines.filtered(
                lambda l: l.product_id.default_code == 'WRAP-CODE'
            )
            self.assertEqual(gift_wrapping_line.tax_id, self.parent_tax)

    @users('admin')
    def test_onboarding_return_not_restricted_to_website_company(self):
        if self.env['ir.module.module']._get('website').state != 'installed':
            self.skipTest("Website module is not installed")

        user = self.env.user
        company_1 = self.env.company
        company_2 = self.branch_company
        website = self.env['website'].search([], limit=1)
        account = self.other_amazon_account

        self.assertIn(company_1, user.company_ids)
        user.company_ids += company_2
        self.assertEqual(account.company_id, company_2)
        self.assertEqual(website.company_id, company_1)

        self.authenticate(user.login, user.login)
        with MockRequest(self.env):
            query_params = {
                'selling_partner_id': "dummy",
                'spapi_oauth_code': "dummy",
                'state': (
                    f'{{"account_id":{account.id},'
                    f'"signature":"{compute_oauth_signature(account.id)}"}}'
                ),
            }

        with (
            patch('odoo.addons.sale_amazon.utils.exchange_authorization_code'),
            patch.object(
                self.env.registry['amazon.account'], 'action_update_available_marketplaces'
            ),
        ):
            response = self.url_open(f'/amazon/return?{urlencode(query_params)}')

        self.assertNotEqual(response.status_code, 403, msg="Should be able to access the account")
