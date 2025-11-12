# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import Form, tagged

from odoo.addons.delivery.tests.cash_on_delivery_common import CashOnDeliveryCommon


@tagged('post_install', '-at_install')
class TestPayOnDelivery(CashOnDeliveryCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_order.action_confirm()
        cls.product_line = cls.sale_order.order_line[0]
        cls.picking = cls.sale_order.picking_ids
        cls.product_move = cls.picking.move_ids
        cls.product_move._set_quantity_done(cls.product_line.product_uom_qty)  # Fully delivered
        cls.cod_tx = cls._create_cod_transaction()

    def assert_opens_wizard(self, env, action, wizard_model='pay.on.delivery'):
        self.assert_dict_almost_equal(
            action,
            {'type': 'ir.actions.act_window', 'res_model': wizard_model, 'target': 'new'},
            msg=f"Action should open a wizard of {wizard_model!r}",
        )
        return Form.from_action(env, action).save()

    def test_payment_on_delivery_required_before_picking_validation(self):
        self.assert_opens_wizard(self.env, self.picking.button_validate())

    def test_picking_validation_is_resumed_after_payment_confirmation(self):
        def spy(obj, attr_name):
            """Wrap the given object method to "spy" when it is called."""
            return patch.object(obj, attr_name, autospec=True, side_effect=getattr(obj, attr_name))

        with (
            spy(self.env.registry['stock.picking'], 'button_validate') as button_validate_spy,
            spy(self.env.registry['stock.picking'], '_action_done') as action_done_spy,
        ):
            pay_on_delivery_wizard = self.assert_opens_wizard(
                self.env, self.picking.button_validate()
            )
            button_validate_spy.assert_called_once()
            action_done_spy.assert_not_called()
            button_validate_spy.reset_mock()

            pay_on_delivery_wizard.action_confirm_payment()

            button_validate_spy.assert_called_once()
            action_done_spy.assert_called_once()
            self.assertEqual(self.cod_tx.state, 'done')

    def test_amount_on_delivery_considers_picked_quantity(self):
        self.product_move._set_quantity_done(3)  # Out of 5

        backorder_wizard = self.assert_opens_wizard(
            self.env, self.picking.button_validate(), 'stock.backorder.confirmation'
        )
        pay_on_delivery_wizard = self.assert_opens_wizard(
            backorder_wizard.env, backorder_wizard.process()
        )

        self.assertEqual(
            pay_on_delivery_wizard.amount_on_delivery,
            self.sale_order.amount_total - 2 / 5 * self.product_line.price_total,
            msg="Expected to pay the total minus undelivered quantities",
        )

    def test_followup_on_backorder(self):
        self.product_move._set_quantity_done(3)  # Out of 5

        backorder_wizard = self.assert_opens_wizard(
            self.env, self.picking.button_validate(), 'stock.backorder.confirmation'
        )
        pay_on_delivery_wizard = self.assert_opens_wizard(
            backorder_wizard.env, backorder_wizard.process()
        )
        amount_on_delivery = pay_on_delivery_wizard.amount_on_delivery
        pay_on_delivery_wizard.action_confirm_payment()

        self.assertEqual(self.cod_tx.state, 'cancel', msg="Should be splitted")
        self.assertRecordValues(self.cod_tx.child_transaction_ids, [
            {'state': 'done', 'amount': amount_on_delivery},
            {'state': 'pending', 'amount': self.sale_order.amount_total - amount_on_delivery},
        ])  # fmt: skip

    def test_no_followup_if_no_backorder(self):
        self.product_move._set_quantity_done(3)  # Out of 5

        backorder_wizard = self.assert_opens_wizard(
            self.env, self.picking.button_validate(), 'stock.backorder.confirmation'
        )
        pay_on_delivery_wizard = self.assert_opens_wizard(
            backorder_wizard.env, backorder_wizard.process_cancel_backorder()
        )
        amount_on_delivery = pay_on_delivery_wizard.amount_on_delivery
        pay_on_delivery_wizard.action_confirm_payment()

        self.assertEqual(
            self.cod_tx.state,
            'cancel',
            msg="Canceled since we confirmed a payment smaller than the original total.",
        )
        self.assertRecordValues(
            self.cod_tx.child_transaction_ids, [{'state': 'done', 'amount': amount_on_delivery}]
        )

    def test_confirm_orders_sequentially(self):
        """
        In the case where we validate multiple pickings at once, a confirmation wizard should open
        for each order before confirming them all at once.
        """
        order1, order2, _ = orders = (
            self._create_so(state='sale')
            + self._create_so(state='sale')
            + self._create_so(state='sale')
        )
        # Use COD only for two orders
        cod_txs = self._create_cod_transaction(sale_order=order1) + self._create_cod_transaction(
            sale_order=order2
        )
        for move in orders.picking_ids.move_ids:
            move._set_quantity_done(1)  # All fully delivered

        # 1. Click "Validate" which should open the first "Pay on Delivery" wizard
        wizard = self.assert_opens_wizard(self.env, orders.picking_ids.button_validate())
        self.assertEqual(wizard.order_id, order1)
        # Should not have confirmed the transactions yet
        self.assertRecordValues(cod_txs, [{'state': 'pending'}, {'state': 'pending'}])

        # 2. Click "Confirm Payment" which should open the second "Pay on Delivery" wizard
        wizard = self.assert_opens_wizard(wizard.env, wizard.action_confirm_payment())
        self.assertEqual(wizard.order_id, order2)
        # Should not have confirmed the transactions yet
        self.assertRecordValues(cod_txs, [{'state': 'pending'}, {'state': 'pending'}])

        # 3. Click "Confirm Payment" for the final time
        action = wizard.action_confirm_payment()

        self.assertIs(action, True, msg="Last order without COD doesn't need payment confirmation")
        # Should confirm all the transactions at the end
        self.assertRecordValues(cod_txs, [{'state': 'done'}, {'state': 'done'}])
