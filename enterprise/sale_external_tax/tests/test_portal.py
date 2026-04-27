# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserPortal


@tagged('post_install', '-at_install')
class TestSaleExternalTaxesSalePortal(HttpCaseWithUserPortal):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fp_external = cls.env['account.fiscal.position'].create({
            'name': 'External',
        })
        cls.product_test = cls.env['product.product'].create({
            'name': 'Test product',
            'list_price': 10.00,
            'standard_price': 10.00,
            'supplier_taxes_id': None,
        })

    def _create_sale_order(self, partner):
        return self.env['sale.order'].create({
            'name': 'test',
            'partner_id': partner.id,
            'fiscal_position_id': self.fp_external.id,
            'date_order': '2023-01-01',
            'order_line': [
                (0, 0, {
                    'product_id': self.product_test.id,
                    'tax_id': None,
                    'price_unit': self.product_test.list_price,
                }),
            ],
            'sale_order_option_ids': [
                (0, 0, {
                    'name': 'optional product',
                    'price_unit': 1,
                    'uom_id': self.env.ref('uom.product_uom_unit').id,
                    'product_id': self.env['product.product'].create({'name': 'optional product'}).id,
                }),
            ],
        })

    # TODO: sale_management is not a dependency of sale_external_tax...
    def test_01_portal_test_optional_products(self):
        """ Make sure that adding, deleting and changing the qty on optional products calculates taxes externally. """
        sale_management = self.env['ir.module.module']._get('sale_management')
        if sale_management.state != 'installed':
            self.skipTest("sale_management module is not installed")

        self.env['product.pricelist'].search([]).unlink()
        portal_partner = self.env['res.users'].sudo().search([('login', '=', 'portal')]).partner_id
        portal_partner.write({
            'state_id': self.env.ref('base.state_us_25').id,
            'zip': '07002',
            'country_id': self.env.ref('base.us').id,
        })
        order = self._create_sale_order(portal_partner)

        # Moving the portal user to order.company_id still results in
        # request.env.company.id == 1 in the /my/quotes controller
        # when called through start_tour. To work around this disable
        # multi-company record rules just for this test.
        self.env.ref('sale.sale_order_comp_rule').active = False
        self.env.ref('sale.sale_order_line_comp_rule').active = False

        # must be sent to the user, so he can see it
        order.action_quotation_sent()

        mixin_path = 'odoo.addons.account_external_tax.models.account_external_tax_mixin.AccountExternalTaxMixin'
        with patch(f'{mixin_path}._get_and_set_external_taxes_on_eligible_records') as mocked_get_and_set, \
             patch(f'{mixin_path}._compute_is_tax_computed_externally', lambda self: self.write({'is_tax_computed_externally': True})):
            self.start_tour('/', 'sale_external_optional_products', login='portal')
            mocked_get_and_set.assert_called()

            # There should be 4 calls:
            # 1/ when the quote is displayed via portal_order_page()
            # 2/ when the tour adds the optional product
            # 3/ when the tour increments the quantity on the optional product
            # 4/ when the tour deletes the optional product
            self.assertEqual(mocked_get_and_set.call_count, 4, 'External taxes were not calculated enough times during this tour.')
