# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_taxcloud.tests.common import TestAccountTaxcloudCommon
from odoo.addons.website_sale_account_taxcloud.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.exceptions import ValidationError
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestWebsiteSaleTaxcloudController(TestAccountTaxcloudCommon):
    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.Controller = WebsiteSale()

    def test_validate_payment_error(self):
        """
        Payment should be blocked if Taxcloud raises an error
        (invalid address, connection issue, etc ...)
        """
        main_company = self.env.ref('base.main_company')

        self.env.user.partner_id.with_company(main_company).write({
            'property_account_position_id': self.fiscal_position.id,
        })

        with MockRequest(self.env, website=self.website):
            self.website.sale_get_order(force_create=True)
            with self.assertRaisesRegex(ValidationError, 'This address does not appear to be valid.'):
                self.Controller.shop_payment_validate()
