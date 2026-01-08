from odoo.tests import tagged

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(SaleCommon, DeliveryCommon):

    def test_avoid_setting_pickup_location_as_default_delivery_address(self):
        self._create_partner(type='delivery', parent_id=self.partner.id, pickup_delivery_carrier_id=self.carrier.id)
        so = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.assertFalse(so.partner_shipping_id.pickup_delivery_carrier_id)
