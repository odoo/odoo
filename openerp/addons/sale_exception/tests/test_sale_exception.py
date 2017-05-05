from openerp.exceptions import ValidationError
from openerp.addons.sale.tests.test_sale_order import TestSaleOrder


class TestSaleException(TestSaleOrder):

    def test_sale_order_exception(self):
        exception = self.env.ref('sale_exception.excep_no_zip')
        exception.active = True
        partner = self.env.ref('base.res_partner_1')
        partner.zip = False
        p = self.env.ref('product.product_product_6')
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [(0, 0, {'name': p.name,
                                   'product_id': p.id,
                                   'product_uom_qty': 2,
                                   'product_uom': p.uom_id.id,
                                   'price_unit': p.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        })

        # confirm quotation
        so.action_confirm()
        self.assertTrue(so.state == 'draft')

        # Set ignore_exception flag  (Done after ignore is selected at wizard)
        so.ignore_exception = True
        so.action_confirm()
        self.assertTrue(so.state == 'sale')

        # Add a order line to test after SO is confirmed
        p = self.env.ref('product.product_product_7')

        # set ignore_exception = False  (Done by onchange of order_line)
        self.assertRaises(
            ValidationError,
            so.write,
            {
                'ignore_exception': False,
                'order_line': [(0, 0, {'name': p.name,
                                       'product_id': p.id,
                                       'product_uom_qty': 2,
                                       'product_uom': p.uom_id.id,
                                       'price_unit': p.list_price})]
            },
        )

        p = self.env.ref('product.product_product_7')

        # Set ignore exception True  (Done manually by user)
        so.write({
            'ignore_exception': True,
            'order_line': [(0, 0, {'name': p.name,
                                   'product_id': p.id,
                                   'product_uom_qty': 2,
                                   'product_uom': p.uom_id.id,
                                   'price_unit': p.list_price})]
        })
        exception.active = False
