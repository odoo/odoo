# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.sale.tests.common import SaleCommon
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged("-at_install", "post_install")
class TestPayWithGiftCard(TestSaleCouponCommon):
    """Gift cards and eWallets are payment methods; they never add (negative) lines to orders."""

    _test_user_groups = None  # FIXME list needed groups

    def _generate_gift_card(self, points=100):
        self.env["loyalty.generate.wizard"].with_context(
            active_id=self.program_gift_card.id
        ).create({"coupon_qty": 1, "points_granted": points}).generate_coupons()
        return self.program_gift_card.coupon_ids[-1]

    def test_gift_card_code_is_refused_as_discount(self):
        gift_card = self._generate_gift_card()
        order = self._create_so(order_line=[Command.create({"product_id": self.product_A.id})])
        amount_total = order.amount_total

        status = order._try_apply_code(gift_card.code)

        self.assertIn("error", status)
        self.assertFalse(order.order_line.filtered("is_reward_line"))
        self.assertEqual(order.amount_total, amount_total)
        self.assertEqual(gift_card.points, 100, "The gift card balance should be untouched.")
        with self.assertRaises(ValidationError):
            self._apply_promo_code(order, gift_card.code)

    def test_payment_program_rewards_are_not_claimable(self):
        ewallet_program = self.env["loyalty.program"].create({
            "name": "eWallet",
            "program_type": "ewallet",
            "applies_on": "future",
            "trigger": "auto",
            "reward_ids": [
                Command.create({
                    "reward_type": "discount",
                    "discount_mode": "per_point",
                    "discount": 1,
                    "discount_applicability": "order",
                })
            ],
        })
        ewallet = self.env["loyalty.card"].create({
            "program_id": ewallet_program.id,
            "partner_id": self.partner.id,
        })
        ewallet._adjust_points(50, "test top up")
        gift_card = self._generate_gift_card()
        order = self._create_so(order_line=[Command.create({"product_id": self.product_A.id})])
        order.applied_coupon_ids = gift_card
        order._update_programs_and_rewards()

        self.assertNotIn(ewallet, order.applied_coupon_ids, "eWallets are not auto-loaded.")
        self.assertFalse(
            order._get_claimable_rewards().keys() & {gift_card, ewallet},
            "Gift cards and eWallets are never claimable as rewards.",
        )
        self.assertFalse(order._get_claimable_rewards(forced_coupons=gift_card | ewallet))
        status = order._apply_program_reward(ewallet_program.reward_ids, ewallet)
        self.assertIn("error", status)
        self.assertFalse(order.order_line.filtered("is_reward_line"))

    def test_legacy_payment_reward_lines_are_removed(self):
        gift_card = self._generate_gift_card()
        order = self._create_so(order_line=[Command.create({"product_id": self.product_A.id})])
        amount_total = order.amount_total
        # Simulate a gift card line added before gift cards became payment methods.
        order.write({
            "applied_coupon_ids": [Command.link(gift_card.id)],
            "order_line": [
                Command.create({
                    "product_id": self.program_gift_card.reward_ids.discount_line_product_id.id,
                    "price_unit": -10,
                    "reward_id": self.program_gift_card.reward_ids.id,
                    "coupon_id": gift_card.id,
                    "reward_identifier_code": "legacy",
                    "tax_ids": False,
                })
            ],
        })
        order._update_programs_and_rewards()
        self.assertFalse(order.order_line.filtered("is_reward_line"))
        self.assertEqual(order.amount_total, amount_total)

    def test_gift_card_product_has_no_taxes_on_creation(self):
        gift_card_program = self.env["loyalty.program"].create({
            "name": "Gift Cards",
            "applies_on": "future",
            "program_type": "gift_card",
            "trigger": "auto",
            "rule_ids": [
                Command.create({
                    "product_ids": self.product_gift_card,
                    "reward_point_amount": 1,
                    "reward_point_mode": "money",
                    "reward_point_split": True,
                })
            ],
            "reward_ids": [
                Command.create({
                    "reward_type": "discount",
                    "discount": 1,
                    "discount_mode": "per_point",
                    "discount_applicability": "order",
                })
            ],
        })
        self.assertFalse(gift_card_program.reward_ids.discount_line_product_id.taxes_id)


@tagged("-at_install", "post_install")
class TestSaleOrderLoyaltyPayment(AccountPaymentCommon, SaleCommon):
    """Paying sales orders with gift cards creates payments, possibly alongside other payments."""

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.sale_order.currency_id
        cls.partner = cls.sale_order.partner_invoice_id
        cls.provider.journal_id.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_provider_id == cls.provider
        ).payment_account_id = cls.inbound_payment_method_line.payment_account_id

        cls.env.company._setup_loyalty_accounting()
        cls.gift_card_provider = cls.env["payment.provider"].search(
            [("code", "=", "gift_card"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.gift_card_program = cls.env["loyalty.program"].sudo().create({
            "name": "Test Gift Cards",
            "program_type": "gift_card",
            "applies_on": "future",
            "trigger": "auto",
            "reward_ids": [
                Command.create({
                    "reward_type": "discount",
                    "discount_mode": "per_point",
                    "discount": 1,
                    "discount_applicability": "order",
                    "required_points": 1,
                })
            ],
        })
        cls.gift_card = cls.env["loyalty.card"].sudo().create({
            "program_id": cls.gift_card_program.id,
            "points": 100,
        })

    def setUp(self):
        super().setUp()
        self.enable_post_process_patcher = False

    def _pay_with_gift_card(self, order, amount):
        tx = self._create_transaction(
            "direct",
            reference=f"{order.name}-gift-card",
            provider_id=self.gift_card_provider.id,
            payment_method_id=self.gift_card_provider.payment_method_ids[:1].id,
            amount=amount,
            loyalty_card_id=self.gift_card.id,
            sale_order_ids=[Command.set(order.ids)],
        )
        tx._get_processing_values()
        return tx

    def test_partial_gift_card_payment_then_card_payment(self):
        order = self.sale_order
        order.prepayment_percent = 1.0
        total = order.amount_total
        self.assertGreater(total, 100)

        gift_card_tx = self._pay_with_gift_card(order, 100)

        self.assertEqual(gift_card_tx.state, "done")
        self.assertEqual(self.gift_card.points, 0)
        self.assertFalse(order.order_line.filtered("is_reward_line"), "No negative line is added.")
        self.assertEqual(order.amount_total, total)
        self.assertEqual(order.amount_paid, 100)
        self.assertTrue(order._is_partially_paid())
        self.assertEqual(order.state, "draft", "The order is not paid entirely yet.")
        self.assertEqual(order.payment_count, 1)

        # Pay the rest with another provider.
        self.env.company.sale_automatic_invoice = True
        card_tx = self._create_transaction(
            "redirect",
            reference=f"{order.name}-card",
            amount=total - 100,
            sale_order_ids=[Command.set(order.ids)],
            state="done",
        )
        card_tx._post_process_with_lock()

        self.assertEqual(order.state, "sale")
        self.assertEqual(order.payment_count, 2)
        self.assertEqual(
            order._get_payments(), gift_card_tx.payment_id | card_tx.payment_id
        )
        invoice = order.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.amount_total, total, "The invoice has no gift card line either.")
        self.assertEqual(invoice.payment_state, "paid")
        self.assertTrue(gift_card_tx.payment_id.is_reconciled)

    def test_full_gift_card_payment_confirms_order(self):
        order = self._create_so(
            order_line=[Command.create({"product_id": self.product.id, "price_unit": 60.0})]
        )
        self._pay_with_gift_card(order, order.amount_total)
        self.assertEqual(order.state, "sale")
        self.assertEqual(self.gift_card.points, 100 - order.amount_total)
        action = order.action_view_payments()
        self.assertEqual(action["res_model"], "account.payment")
        self.assertEqual(action["res_id"], order.transaction_ids.payment_id.id)
