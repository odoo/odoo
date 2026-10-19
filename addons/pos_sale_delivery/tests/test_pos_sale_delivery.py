# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.pos_sale.tests.test_pos_sale_flow import PoSSaleSyncCommon


@tagged("post_install", "-at_install")
class TestPosSaleDelivery(CashOnDeliveryCommon, TestPoSCommon, PoSSaleSyncCommon):
    _test_user_groups = ("point_of_sale.group_pos_user", "sales_team.group_sale_salesman")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config = cls.basic_config

    @classmethod
    def _create_so(cls, **values):
        values.setdefault("user_id", cls._test_user.id)
        return super()._create_so(**values)

    def test_settling_the_order_cancels_the_pending_transaction(self):
        sale_order = self.sale_order
        cod_tx = self._create_cod_transaction()
        self.assertEqual(
            sale_order.amount_unpaid,
            sale_order.amount_total,
            msg="The order must be settleable from the Point of Sale",
        )

        self._settle_in_pos(sale_order)

        self.assertEqual(
            cod_tx.state,
            "cancel",
            msg="The promise of a payment on delivery is superseded by the Point of Sale",
        )
        self.assertTrue(cod_tx.is_post_processed)
