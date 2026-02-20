# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged('post_install', '-at_install')
class TestCODPaymentTransaction(CashOnDeliveryCommon):

    def test_choosing_cod_payment_confirms_order(self):
        order = self.sale_order
        tx = self._create_cod_transaction()
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._post_process()

        self.assertEqual(order.state, 'sale')
