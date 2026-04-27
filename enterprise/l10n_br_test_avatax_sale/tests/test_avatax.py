# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import tagged
from odoo.addons.l10n_br_avatax.tests.test_br_avatax import TestAvalaraBrCommon
from .mocked_so_response import generate_response

@tagged("post_install_l10n", "-at_install", "post_install")
class TestSaleAvalaraBr(TestAvalaraBrCommon):
    def assertOrder(self, order, mocked_response=None):
        if mocked_response:
            amount_total = 95.00
            amount_tax = 11.4 + 5.21
            self.assertRecordValues(order, [{
                'amount_total': amount_total,
                'amount_untaxed': amount_total - amount_tax,
                'amount_tax': amount_tax,
            }])
            totals = order.tax_totals
            subtotals = totals['subtotals']
            self.assertEqual(len(subtotals), 1)
            subtotal = subtotals[0]
            self.assertEqual(subtotal['base_amount_currency'], order.amount_untaxed)
            self.assertEqual(subtotal['tax_amount_currency'], order.amount_tax)
            self.assertEqual(totals['total_amount_currency'], order.amount_total)
            for avatax_line in mocked_response['lines']:
                so_line = order.order_line.filtered(lambda l: l.id == avatax_line['lineCode'])
                total_tax_amount = sum(detail['tax'] for detail in avatax_line['taxDetails'] if detail['taxImpact']['impactOnNetAmount'] != 'Informative')
                self.assertRecordValues(so_line, [{
                    'price_subtotal': avatax_line['lineNetFigure'],
                    'price_tax': total_tax_amount,
                    'price_total': avatax_line['lineNetFigure'] + total_tax_amount,
                }])
        else:
            for line in order.order_line:
                product_name = line.product_id.display_name
                self.assertGreater(len(line.tax_id), 0, "Line with %s did not get any taxes set." % product_name)

            self.assertGreater(order.amount_tax, 0.0, "Invoice has a tax_amount of 0.0.")

    def _create_sale_order(self):
        products = (
            self.product_user,
            self.product_accounting,
            self.product_expenses,
            self.product_invoicing,
        )
        order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner.id,
            'fiscal_position_id': self.fp_avatax.id,
            'date_order': '2021-01-01',
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'price_unit': product.list_price,
                    'tax_id': None,
                }) for product in products
            ]
        })
        return order, generate_response(order.order_line)

    def test_01_sale_order_br(self):
        order, mocked_response = self._create_sale_order()
        order.currency_id = self.env.ref('base.BRL')
        with self._capture_request_br(return_value=mocked_response):
            order.button_external_tax_calculation()
        self.assertOrder(order, mocked_response=mocked_response)

    def test_02_sale_order_br_integration(self):
        order, _ = self._create_sale_order()
        order.currency_id = self.env.ref('base.BRL')
        with self._skip_no_credentials():
            order.button_external_tax_calculation()
            self.assertOrder(order, mocked_response=False)
