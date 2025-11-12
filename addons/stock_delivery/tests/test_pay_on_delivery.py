# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

        cls.product_line = cls.sale_order.order_line[0]
        cls.sale_order.order_line = [Command.create({'product_id': cls.service_product.id})]
        cls.cod_tx = cls._create_cod_transaction()
        cls.sale_order.action_confirm()
        cls.picking = cls.sale_order.picking_ids
        cls.product_move = cls.picking.move_ids
        cls.product_move._set_quantity_done(cls.product_line.product_uom_qty)  # Fully delivered

    @classmethod
    def _create_so(cls, **values):
        values.setdefault('user_id', cls._test_user.id)
        return super()._create_so(**values)

    def assert_dict_almost_equal(self, d1, d2, msg=None):
        self.assertIsInstance(d1, dict, msg=msg)
        self.assertIsInstance(d2, dict, msg=msg)
        self.assertDictEqual({key: d1[key] for key in d1.keys() & d2.keys()}, d2, msg=msg)

    def open_wizard(self, env, action, wizard_model='pay.on.delivery'):
        self.assert_dict_almost_equal(
            action,
            {'type': 'ir.actions.act_window', 'res_model': wizard_model, 'target': 'new'},
            msg=f"Action should open a wizard of {wizard_model!r}",
        )
        return Form.from_action(env, action).save()

    def test_partial_delivery(self):
        self.product_move._set_quantity_done(3)  # Out of 5

        backorder_wizard = self.open_wizard(
            self.env, self.picking.button_validate(), 'stock.backorder.confirmation'
        )
        pay_on_delivery_wizard = self.open_wizard(backorder_wizard.env, backorder_wizard.process())

        self.assertEqual(
            pay_on_delivery_wizard.amount_on_delivery,
            self.sale_order.amount_total - 2 / 5 * self.product_line.price_total,
            msg="Expected to pay the total (service included) minus undelivered quantities",
        )

    def test_full_delivery(self):
        pay_on_delivery_wizard = self.open_wizard(self.env, self.picking.button_validate())

        self.assertEqual(pay_on_delivery_wizard.amount_on_delivery, self.sale_order.amount_total)

    def test_partially_prepaid_delivery(self):
        prepaid_amount = self.sale_order.currency_id.round(0.2 * self.sale_order.amount_total)
        self._create_transaction(
            'direct',
            sale_order_ids=[Command.set(self.sale_order.ids)],
            amount=prepaid_amount,
            state='done',
        )

        pay_on_delivery_wizard = self.open_wizard(self.env, self.picking.button_validate())

        self.assertEqual(
            pay_on_delivery_wizard.amount_on_delivery, self.sale_order.amount_total - prepaid_amount
        )

    def test_fully_prepaid_delivery(self):
        self._create_transaction(
            'direct',
            sale_order_ids=[Command.set(self.sale_order.ids)],
            amount=self.sale_order.amount_total,
            state='done',
        )

        action = self.picking.button_validate()

        self.assertIs(action, True)

    def test_offline_invoices(self):
        """Invoices recorded outside the payment engine should be subtracted from the amount to
        collect."""
        downpayment_wizard = self.env['sale.advance.payment.inv'].create({
            'sale_order_ids': [Command.set(self.sale_order.ids)],
            'advance_payment_method': 'percentage',
            'amount': 20,
        })
        downpayment_wizard._create_invoices(self.sale_order)  # Draft
        downpayment_wizard._create_invoices(self.sale_order).action_post()
        downpayment_wizard._create_invoices(self.sale_order).button_cancel()

        pay_on_delivery_wizard = self.open_wizard(self.env, self.picking.button_validate())

        self.assertEqual(
            pay_on_delivery_wizard.amount_on_delivery,
            0.6 * self.sale_order.amount_total,
            msg="Downpayments should not be included",
        )

    def test_without_pay_on_delivery(self):
        """Orders without "Pay on Delivery" should not display a message to collect money."""
        order = self._create_so(state='sale')
        self._create_transaction('direct', sale_order_ids=[Command.set(order.ids)])
        picking = order.picking_ids
        picking.move_ids._set_quantity_done(1)  # Fully delivered

        action = picking.button_validate()

        self.assertIs(action, True)

    def test_confirm_orders_sequentially(self):
        """
        In the case where multiple pickings are validated at once, a confirmation wizard should open
        for each order, each one collecting the payment of its own order, before the validation of
        the pickings is resumed.
        """
        orders = order1, order2, _ = (
            self._create_so(state='sale')
            + self._create_so(state='sale')
            + self._create_so(state='sale')
        )
        # Use COD only for two orders
        self._create_cod_transaction(sale_order=order1)
        self._create_cod_transaction(sale_order=order2)
        for move in orders.picking_ids.move_ids:
            move._set_quantity_done(1)  # All fully delivered

        # 1. Click "Validate" which should open the first "Pay on Delivery" wizard
        wizard = self.open_wizard(self.env, orders.picking_ids.button_validate())
        self.assertEqual(wizard.order_id, order1)

        # 2. Click "Confirm Payment" which should open the second "Pay on Delivery" wizard
        wizard = self.open_wizard(wizard.env, wizard.action_confirm_payment())
        self.assertEqual(wizard.order_id, order2)

        # 3. Click "Confirm Payment" for the final time
        action = wizard.action_confirm_payment()
        self.assertIs(action, True, msg="Last order without COD doesn't need payment confirmation")
