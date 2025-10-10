from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged
from odoo.exceptions import UserError

CALL_API_METHOD = 'odoo.addons.l10n_tw_edi_ecpay_website_sale.controllers.main.call_ecpay_api'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(HttpCase):
    def setUp(self):
        super().setUp()
        self.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 60.0,
            'list_price': 68.0,
            'website_published': True,
        })
        # set current company's fiscal country to Colombia
        website = self.env['website'].get_current_website()
        website.company_id.account_fiscal_country_id = website.company_id.country_id = self.env.ref('base.tw')

    def test_validate_customer_info_error(self):
        with patch(CALL_API_METHOD, new=self._test_validation_mock):
            self.start_tour("/shop", "test_validate_customer_info_error", watch=True)

    def test_checkout_b2c(self):
        self.start_tour("/shop", "test_checkout_b2c")
        # Check the invoice info is updated on the sale order
        sale_order = self.env['sale.order'].search([], limit=1, order="create_date desc")
        self.assertRecordValues(sale_order, [{
            'l10n_tw_edi_carrier_type': "4",
            'l10n_tw_edi_carrier_number': "123",
            'l10n_tw_edi_carrier_number_2': "456",
        }])

    def test_checkout_b2b(self):
        with patch(CALL_API_METHOD, new=self._test_checkout_b2b_mock):
            self.start_tour("/shop", "test_checkout_b2b")
        # Check the invoice info is updated on the sale order
        sale_order = self.env['sale.order'].search([], limit=1, order="create_date desc")
        self.assertRecordValues(sale_order, [{
            'l10n_tw_edi_is_print': True,
        }])

    # -------------------------------------------------------------------------
    # Patched methods
    # -------------------------------------------------------------------------
    def _test_validation_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 0,
                "CompanyName": False,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_checkout_b2b_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 1,
                "CompanyName": "Test Company",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))
