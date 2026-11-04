from odoo.addons.account.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummary
from odoo.addons.point_of_sale.tests.test_frontend import TestTaxCommonPOS
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestTaxesTaxTotalsSummaryAccountTaxPython(TestTaxCommonPOS, TestTaxesTaxTotalsSummary):

    def test_point_of_sale_custom_tax_with_extra_product_field(self):
        assert 'weight' not in self.env['product.template']._load_pos_data_fields(self.main_pos_config.id)

        tax = self.python_tax('product.weight * quantity')
        document_params = self.init_document(
            lines=[
                {'price_unit': 200.0, 'quantity': 10.0, 'tax_ids': tax},
            ],
        )
        document = self.populate_document(document_params)

        self.ensure_products_on_document(document, 'product_1')
        product = document['lines'][0]['product_id']
        product.weight = 4.2

        expected_values = {
            'base_amount_currency': 2000.00,
            'tax_amount_currency': 42.0,
            'total_amount_currency': 2042.0,
        }

        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_point_of_sale_custom_tax_with_extra_product_field')
            order = self.env['pos.order'].search([('session_id', '=', session.id)])
            self.assert_pos_order_totals(order, expected_values)
            self.assertTrue(order.account_move)
            self.assert_invoice_totals(order.account_move, expected_values)

    def test_point_of_sale_custom_tax_with_extra_product_uom_field(self):
        assert 'ratio' not in self.env['uom.uom']._load_pos_data_fields(self.main_pos_config.id)

        tax = self.python_tax('uom.ratio * quantity')
        document_params = self.init_document(
            lines=[
                {'price_unit': 200.0, 'quantity': 10.0, 'tax_ids': tax},
            ],
        )
        document = self.populate_document(document_params)

        self.ensure_products_on_document(document, 'product_1')
        product = document['lines'][0]['product_id']
        product.uom_id = self.env['uom.uom'].create({
            'name': "test_point_of_sale_custom_tax_with_extra_product_uom_field",
            'category_id': self.env.ref('uom.product_uom_categ_unit').id,
            'uom_type': 'bigger',
            'ratio': 4.2,
        })

        expected_values = {
            'base_amount_currency': 2000.00,
            'tax_amount_currency': 42.0,
            'total_amount_currency': 2042.0,
        }

        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_point_of_sale_custom_tax_with_extra_product_field')
            order = self.env['pos.order'].search([('session_id', '=', session.id)])
            self.assert_pos_order_totals(order, expected_values)
            self.assertTrue(order.account_move)
            self.assert_invoice_totals(order.account_move, expected_values)
