from odoo.addons.website_sale_picking.tests.common import OnsiteCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestOnsitePayment(OnsiteCommon):

    def test_onsite_provider_available_when_onsite_delivery_is_chosen(self):
        order = self._create_so()
        order.carrier_id = self.carrier.id
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(any(
            p.code == 'custom' and p.custom_mode == 'onsite' for p in compatible_providers
        ))

    def test_onsite_provider_unavailable_when_no_onsite_delivery(self):
        order = self._create_so()
        compatible_providers = self.env['payment.provider'].sudo()._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, sale_order_id=order.id
        )
        self.assertTrue(not any(
            p.code == 'custom' and p.custom_mode == 'onsite' for p in compatible_providers
        ))
