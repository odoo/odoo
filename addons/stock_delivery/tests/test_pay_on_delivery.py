# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged('post_install', '-at_install')
class TestPayOnDelivery(CashOnDeliveryCommon):
    _test_user_groups = (
        'account.group_account_invoice',
        'sales_team.group_sale_salesman',
        'stock.group_stock_user',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order.order_line = [Command.create({'product_id': cls.service_product.id})]
        cls._create_cod_transaction()
        cls.sale_order.action_confirm()
        cls.picking = cls.sale_order.picking_ids
        cls.picking.move_ids._set_quantity_done(cls.sale_order.order_line[0].product_uom_qty)

    @classmethod
    def _create_so(cls, **values):
        values.setdefault('user_id', cls._test_user.id)
        return super()._create_so(**values)

    def open_pod_wizard(self, action):
        msg = "Action should open a wizard of 'pay.on.delivery'"
        expected = {
            'type': 'ir.actions.act_window',
            'res_model': 'pay.on.delivery',
            'target': 'new',
        }
        self.assertIsInstance(action, dict, msg=msg)
        self.assertDictEqual(
            {key: action[key] for key in action.keys() & expected.keys()}, expected, msg=msg
        )
        return Form.from_action(self.env, action).save()

    def test_show_wizard_of_outstanding_payment_on_delivery(self):
        self.assertTrue(self.sale_order.amount_unpaid)

        self.open_pod_wizard(self.picking.button_validate())

    def test_full_prepayment_skips_wizard(self):
        self._create_transaction(
            'direct',
            sale_order_ids=[Command.set(self.sale_order.ids)],
            amount=self.sale_order.amount_total,
            state='done',
        )

        action = self.picking.button_validate()

        self.assertIs(action, True)

    def test_skip_wizard_without_pay_on_delivery(self):
        """Orders without "Pay on Delivery" should not display a message to collect money."""
        order = self._create_so(state='sale')
        self._create_transaction('direct', sale_order_ids=[Command.set(order.ids)])
        picking = order.picking_ids
        picking.move_ids._set_quantity_done(1)  # Fully delivered

        action = picking.button_validate()

        self.assertIs(action, True)

    def test_multiple_orders_summed_in_one_wizard(self):
        """
        In the case where multiple pickings are validated at once, a single confirmation wizard
        should open, summing the amounts to collect for all the orders.
        """
        order1, order2 = self.sale_order + self._create_so(state='sale')
        self._create_cod_transaction(sale_order=order2)
        order2.picking_ids.move_ids._set_quantity_done(1)

        wizard = self.open_pod_wizard((order1 + order2).picking_ids.button_validate())

        self.assertEqual(wizard.amount_to_collect, order1.amount_total + order2.amount_total)

    def test_multiple_orders_exclude_non_pay_on_delivery(self):
        """
        In the case where multiple pickings are validated at once, orders not using "Pay on
        delivery" should be excluded from the wizard.
        """
        order1, order2 = self.sale_order + self._create_so(state='sale')
        order2.picking_ids.move_ids._set_quantity_done(1)

        wizard = self.open_pod_wizard((order1 + order2).picking_ids.button_validate())

        self.assertEqual(wizard.order_ids, order1, msg="Orders without COD should not be included")

    def test_orders_with_mixed_currencies_raises(self):
        pricelist = self._create_pricelist(
            name="Other Currency Pricelist", currency_id=self.currency_euro.id
        )
        orders = self._create_so(state='sale') + self._create_so(
            state='sale', pricelist_id=pricelist.id
        )
        for order in orders:
            self._create_cod_transaction(sale_order=order)
            order.picking_ids.move_ids._set_quantity_done(1)

        with self.assertRaises(UserError):
            self.open_pod_wizard(orders.picking_ids.button_validate())
