from odoo.addons.account.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummary
from odoo.addons.account_tax_python.tests.common import TestTaxCommonAccountTaxPython
from odoo.addons.point_of_sale.tests.test_frontend import TestTaxCommonPOS
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestTaxesTaxTotalsSummaryL10nInPos(TestTaxCommonAccountTaxPython, TestTaxCommonPOS, TestTaxesTaxTotalsSummary):
    """ This test is a standard one and is not related to the indian localization.
    However, we want to test the POS using python taxes and there is no bridge between point_of_sale and account_tax_python.
    Then, we exploit this module to do it. To do so, let's just use a field that is not loaded into the POS by default.
    """

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
