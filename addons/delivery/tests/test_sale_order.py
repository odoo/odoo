from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(SaleCommon):

    def test_avoid_setting_pickup_location_as_default_delivery_address(self):
        self._create_partner(type='delivery', parent_id=self.partner.id, is_pickup_location=True)
        so = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.assertFalse(so.partner_shipping_id.is_pickup_location)
