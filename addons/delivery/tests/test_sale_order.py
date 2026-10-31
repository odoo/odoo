from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(SaleCommon):

    def test_avoid_setting_pickup_location_as_default_delivery_address(self):
        self._create_partner(type='delivery', parent_id=self.partner.id, is_pickup_location=True)
        so = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.assertFalse(so.partner_shipping_id.is_pickup_location)

    def test_unlink_delivery_line_keeps_carrier_while_one_remains(self):
        carrier = self.env['delivery.carrier'].create({
            'name': "Test Carrier",
            'delivery_type': 'fixed',
            'fixed_price': 5.0,
            'product_id': self.env['product.product'].create({'name': "Carrier Product", 'type': 'service'}).id,
        })
        order = self.sale_order
        order.set_delivery_line(carrier, 5.0)
        order._create_delivery_line(carrier, 7.0)
        first_line, second_line = order.order_line.filtered('is_delivery')

        first_line.unlink()
        self.assertEqual(order.carrier_id, carrier, "The delivery method should stay while a delivery line remains")
        second_line.unlink()
        self.assertFalse(order.carrier_id, "The delivery method should be cleared with the last delivery line")
