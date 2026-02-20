# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.fields import Command
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
        cls.product_move._set_quantity_done(cls.product_line.product_uom_qty)
        cls.cod_tx = cls._create_cod_transaction()

    def test_payment_on_delivery_required_before_picking_validation(self):
        action = self.picking.button_validate()

        self.assert_dict_almost_equal(
            action, {'type': 'ir.actions.act_window', 'res_model': 'pay.on.delivery'}
        )

    def test_picking_validation_is_resumed_after_payment_confirmation(self):
        def spy(obj, attr_name):
            """Wrap the given object method to "spy" when it is called."""
            return patch.object(obj, attr_name, autospec=True, side_effect=getattr(obj, attr_name))

        with (
            spy(self.env.registry['stock.picking'], 'button_validate') as button_validate_spy,
            spy(self.env.registry['stock.picking'], '_action_done') as action_done_spy,
        ):
            wizard = Form.from_action(self.env, self.picking.button_validate()).save()
            button_validate_spy.assert_called_once()
            action_done_spy.assert_not_called()
            button_validate_spy.reset_mock()

            wizard.action_confirm_next_payment()

            button_validate_spy.assert_called_once()
            action_done_spy.assert_called_once()
            self.assertRecordValues(self.cod_tx, [{'state': 'done'}])

    def test_amount_on_delivery_includes_undeliverable_base_amount(self):
        self.product_move._set_quantity_done(3)  # Out of 5

        backorder_wizard = Form.from_action(self.env, self.picking.button_validate()).save()
        pay_on_delivery_wizard = Form.from_action(
            backorder_wizard.env, backorder_wizard.process()
        ).save()

        self.assertAlmostEqual(
            pay_on_delivery_wizard.amount_on_delivery,
            self.sale_order.amount_total - 2 / 5 * self.product_line.price_total,
            msg="Expected to pay the total - undelivered quantities",
        )

    def test_amount_on_delivery_considers_picked_quantity(self):
        order = self._create_so(
            state='sale',
            order_line=[Command.create({'product_id': self.product.id}) for _ in range(2)],
        )
        picking = order.picking_ids
        self._create_cod_transaction(sale_order=order)
        first_move, second_move = picking.move_ids
        first_move._set_quantity_done(1)
        first_move.picked = True
        second_move._set_quantity_done(0)
        second_move.picked = False

        backorder_wizard = Form.from_action(self.env, picking.button_validate()).save()
        pay_on_delivery_wizard = Form.from_action(
            backorder_wizard.env, backorder_wizard.process()
        ).save()

        self.assertAlmostEqual(
            pay_on_delivery_wizard.amount_on_delivery,
            order.amount_total / 2,
            msg="Expected to pay the total - undelivered quantities",
        )
