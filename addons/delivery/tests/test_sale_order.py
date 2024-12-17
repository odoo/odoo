from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(SaleCommon):
    def test_compute_partner_shipping_id_set_no_pickup_point_addresses(self):
        delivery_address = self._create_partner(type='delivery', parent_id=self.partner.id)
        so = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.assertEqual(so.partner_shipping_id, delivery_address)
        delivery_address.is_pickup_location = True
        so._compute_partner_shipping_id()
        self.assertEqual(so.partner_shipping_id, self.partner)

    def test_when_pickup_location_create_pickup_location_partner_on_confirm(self):
        pickup_location = {
            'street': 'Test Street',
            'city': 'Test City',
            'zip_code': 'Test Zip Code',
            'country_code': 'BE',
        }
        order = self.env['sale.order'].create(
            {
                'partner_id': self.partner.id,
                'pickup_location_data': pickup_location,
            }
        )
        order._action_confirm()
        self.assertTrue(order.partner_shipping_id.is_pickup_location)
