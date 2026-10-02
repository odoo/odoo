# Copyright (C) 2018 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestModule(TransactionCase):
    """Tests for 'Point of Sale - Change Payment' Module"""

    def setUp(self):
        super().setUp()
        self.PosSession = self.env["pos.session"]
        self.PosOrder = self.env["pos.order"]
        self.PosPaymentMethod = self.env["pos.payment.method"]
        self.PosPayment = self.env["pos.payment"]
        self.PosMakePayment = self.env["pos.make.payment"]
        self.PosPaymentChangeWizard = self.env["pos.payment.change.wizard"]
        self.PosPaymentChangeWizardNewLine = self.env[
            "pos.payment.change.wizard.new.line"
        ]
        self.product = self.env.ref("product.product_product_3")
        self.pos_config = self.env.ref("point_of_sale.pos_config_main").copy()

    def _initialize_journals_open_session(self):
        account_id = self.env.company.account_default_pos_receivable_account_id
        self.bank_payment_method = self.PosPaymentMethod.create(
            {
                "name": "Bank",
                "receivable_account_id": account_id.id,
            }
        )
        self.cash_payment_method = self.PosPaymentMethod.create(
            {
                "name": "Cash",
                "is_cash_count": True,
                "receivable_account_id": account_id.id,
                "journal_id": self.env["account.journal"]
                .search(
                    [("type", "=", "cash"), ("company_id", "=", self.env.company.id)],
                    limit=1,
                )
                .id,
            }
        )

        # create new session and open it
        self.pos_config.payment_method_ids = [
            self.bank_payment_method.id,
            self.cash_payment_method.id,
        ]
        self.pos_config.open_ui()
        self.session = self.pos_config.current_session_id

    def _sale(self, payment_method_1, price_1, payment_method_2=False, price_2=0.0):
        price = price_1 + price_2
        line_vals = {
            "name": "OL/0001",
            "product_id": self.product.id,
            "qty": 1.0,
            "price_unit": price,
            "price_subtotal": price,
            "price_subtotal_incl": price,
        }
        order = self.PosOrder.create(
            {
                "session_id": self.session.id,
                "amount_tax": 0,
                "amount_total": price,
                "amount_paid": price,
                "amount_return": 0,
                "lines": [[0, False, line_vals]],
            }
        )
        order.add_payment(
            {
                "pos_order_id": order.id,
                "amount": price_1,
                "payment_date": fields.Date.today(),
                "payment_method_id": payment_method_1.id,
            }
        )
        if payment_method_2:
            order.add_payment(
                {
                    "pos_order_id": order.id,
                    "amount": price_2,
                    "payment_date": fields.Date.today(),
                    "payment_method_id": payment_method_2.id,
                }
            )
        order.action_pos_order_paid()
        return order

    def _change_payment(
        self, order, payment_method_1, amount_1, payment_method_2=False, amount_2=0.0
    ):
        # Switch to check journal
        wizard = self.PosPaymentChangeWizard.with_context(active_id=order.id).create({})
        self.PosPaymentChangeWizardNewLine.with_context(active_id=order.id).create(
            {
                "wizard_id": wizard.id,
                "new_payment_method_id": payment_method_1.id,
                "amount": amount_1,
            }
        )
        if payment_method_2:
            self.PosPaymentChangeWizardNewLine.with_context(active_id=order.id).create(
                {
                    "wizard_id": wizard.id,
                    "new_payment_method_id": payment_method_2.id,
                    "amount": amount_2,
                }
            )
        wizard.button_change_payment()

    # Test Section
    def test_01_payment_change_policy_update(self):
        self.pos_config.payment_change_policy = "update"

        self._initialize_journals_open_session()
        # Make a sale with 35 in cash journal and 65 in check
        order = self._sale(self.cash_payment_method, 35, self.bank_payment_method, 65)

        order_qty = len(self.PosOrder.search([]))

        with self.assertRaises(UserError):
            # Should not work if total is not correct
            self._change_payment(
                order, self.cash_payment_method, 10, self.cash_payment_method, 10
            )

        self._change_payment(
            order, self.cash_payment_method, 10, self.bank_payment_method, 90
        )

        self.bank_payment = self.session.order_ids.mapped("payment_ids").filtered(
            lambda x: x.payment_method_id == self.bank_payment_method
        )
        self.cash_payment = self.session.order_ids.mapped("payment_ids").filtered(
            lambda x: x.payment_method_id == self.cash_payment_method
        )
        # check Session
        self.assertEqual(
            self.cash_payment.amount,
            10,
            "Bad recompute of the balance for the statement cash",
        )

        self.assertEqual(
            self.bank_payment.amount,
            90,
            "Bad recompute of the balance for the statement check",
        )

        # Check Order quantity
        self.assertEqual(
            order_qty,
            len(self.PosOrder.search([])),
            "In 'Update' mode, changing payment should not create" " other PoS Orders",
        )

    def test_02_payment_change_policy_refund(self):
        self.pos_config.payment_change_policy = "refund"

        self._initialize_journals_open_session()
        # Make a sale with 35 in cash journal and 65 in check
        order = self._sale(self.cash_payment_method, 35, self.bank_payment_method, 65)

        order_qty = len(self.PosOrder.search([]))

        self._change_payment(
            order, self.cash_payment_method, 50, self.bank_payment_method, 50
        )

        # Check Order quantity
        self.assertEqual(
            order_qty + 2,
            len(self.PosOrder.search([])),
            "In 'Refund' mode, changing payment should generate" " two new PoS Orders",
        )

    def test_03_payment_change_closed_orders(self):
        self.pos_config.payment_change_policy = "update"

        self._initialize_journals_open_session()
        # Make a sale with 35 in cash journal and 65 in check
        order = self._sale(self.cash_payment_method, 35, self.bank_payment_method, 65)

        self.session.state = "closed"

        with self.assertRaises(UserError):
            self._change_payment(
                order, self.cash_payment_method, 10, self.bank_payment_method, 90
            )

    def test_04_payment_change_security(self):
        self.pos_config.payment_change_policy = "refund"
        self._initialize_journals_open_session()
        order = self._sale(self.cash_payment_method, 35, self.bank_payment_method, 65)

        # the demo user should be able to do this
        user_demo = self.env.ref("base.user_demo")
        wizard = (
            self.PosPaymentChangeWizard.with_user(user_demo)
            .with_context(active_id=order.id)
            .create({})
        )
        self.PosPaymentChangeWizardNewLine.with_user(user_demo).with_context(
            active_id=order.id
        ).create(
            {
                "wizard_id": wizard.id,
                "new_payment_method_id": self.cash_payment_method.id,
                "amount": 100.0,
            }
        )
        wizard.button_change_payment()
