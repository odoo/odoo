# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestLoyaltyPayment(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company._setup_loyalty_accounting()
        cls.gift_card_provider = cls._get_loyalty_provider("gift_card")
        cls.ewallet_provider = cls._get_loyalty_provider("ewallet")

        cls.gift_card_program = (
            cls
            .env["loyalty.program"]
            .sudo()
            .create({
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
        )
        cls.ewallet_program = (
            cls
            .env["loyalty.program"]
            .sudo()
            .create({
                "name": "Test eWallet",
                "program_type": "ewallet",
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
        )
        cls.gift_card = cls._create_card(cls.gift_card_program, 100)
        cls.ewallet = cls._create_card(cls.ewallet_program, 200, partner=cls.partner_a)

    @classmethod
    def _create_card(cls, program, points, partner=None):
        card = (
            cls
            .env["loyalty.card"]
            .sudo()
            .create({
                "program_id": program.id,
                "partner_id": partner and partner.id,
                "points": points,
            })
        )
        return card.sudo(False)

    @classmethod
    def _get_loyalty_provider(cls, code):
        return cls.env["payment.provider"].search(
            [("code", "=", code), ("company_id", "=", cls.env.company.id)], limit=1
        )

    def _get_method_line(self, provider):
        return self.env["account.payment.method.line"].search(
            [("payment_provider_id", "=", provider.id)], limit=1
        )

    def _create_payment(self, provider, card, amount, partner=None):
        method_line = self._get_method_line(provider)
        return self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": (partner or self.partner_a).id,
            "amount": amount,
            "journal_id": method_line.journal_id.id,
            "payment_method_line_id": method_line.id,
            "loyalty_card_id": card.id,
        })

    # === PROVIDERS === #

    def test_loyalty_providers_setup(self):
        liability_account = self.company._get_loyalty_liability_account()
        self.assertEqual(liability_account.account_type, "liability_current")
        for provider in self.gift_card_provider | self.ewallet_provider:
            method_line = self._get_method_line(provider)
            self.assertTrue(method_line, "The provider should have a payment method line.")
            self.assertEqual(method_line.payment_account_id, liability_account)
        self.assertEqual(
            self.env
            .ref("loyalty.ewallet_product_50")
            .with_company(self.company)
            .property_account_income_id,
            liability_account,
            "eWallet top-ups should be sold on the liability account.",
        )

    def test_provider_publication_follows_programs(self):
        self.assertTrue(self.ewallet_provider.is_published)
        self.env["loyalty.program"].sudo().search([
            ("program_type", "=", "ewallet")
        ]).action_archive()
        self.assertFalse(self.ewallet_provider.is_published)
        self.ewallet_program.sudo().action_unarchive()
        self.assertTrue(self.ewallet_provider.is_published)

    def test_ewallet_provider_only_available_with_ewallet(self):
        providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner_a.id, 100.0, currency_id=self.company.currency_id.id
        )
        self.assertIn(self.ewallet_provider, providers)
        providers = self.env["payment.provider"]._find_available_providers(
            self.company.id, self.partner_b.id, 100.0, currency_id=self.company.currency_id.id
        )
        self.assertNotIn(self.ewallet_provider, providers)

    # === ACCOUNT PAYMENTS === #

    def test_payment_consumes_and_restores_card_balance(self):
        payment = self._create_payment(self.gift_card_provider, self.gift_card, 40.0)
        self.assertEqual(self.gift_card.points, 100, "Draft payments don't consume the balance.")

        payment.action_post()
        self.assertEqual(self.gift_card.points, 60)
        liquidity_line = payment.move_id.line_ids.filtered(lambda line: line.debit)
        self.assertEqual(liquidity_line.account_id, self.company._get_loyalty_liability_account())

        payment.action_draft()
        self.assertEqual(self.gift_card.points, 100)

        payment.action_post()
        self.assertEqual(self.gift_card.points, 60)
        payment.action_cancel()
        self.assertEqual(self.gift_card.points, 100)

    def test_payment_cannot_exceed_card_balance(self):
        payment = self._create_payment(self.gift_card_provider, self.gift_card, 150.0)
        with self.assertRaises(ValidationError):
            payment.action_post()

    def test_payment_requires_partner_ewallet(self):
        with self.assertRaises(ValidationError):
            self._create_payment(
                self.ewallet_provider, self.ewallet, 10.0, partner=self.partner_b
            ).action_post()

    def test_payment_form_ewallet_autoselection(self):
        method_line = self._get_method_line(self.ewallet_provider)
        with Form(self.env["account.payment"].with_context(default_payment_type="inbound")) as form:
            form.partner_id = self.partner_a
            form.amount = 500.0
            form.journal_id = method_line.journal_id
            form.payment_method_line_id = method_line
            self.assertEqual(form.loyalty_card_id, self.ewallet)
            self.assertFalse(form.show_loyalty_card_id, "A single eWallet is selected silently.")
        payment = form.record
        self.assertEqual(payment.amount, 200.0, "The amount is limited to the eWallet balance.")

        second_ewallet = self._create_card(self.ewallet_program, 10, partner=self.partner_a)
        payment.invalidate_recordset(["show_loyalty_card_id"])
        self.assertTrue(payment.show_loyalty_card_id, "The eWallet can be chosen among several.")
        payment.loyalty_card_id = second_ewallet
        self.assertEqual(payment.loyalty_card_balance, 10.0)

    def test_register_payment_wizard_with_ewallet(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[1000.0], taxes=[], post=True
        )
        method_line = self._get_method_line(self.ewallet_provider)
        wizard = (
            self
            .env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"journal_id": method_line.journal_id.id})
        )
        wizard.payment_method_line_id = method_line
        self.assertEqual(wizard.loyalty_card_id, self.ewallet)
        self.assertEqual(wizard.amount, 200.0)
        payment = wizard._create_payments()

        self.assertEqual(payment.loyalty_card_id, self.ewallet)
        self.assertEqual(self.ewallet.points, 0)
        self.assertEqual(invoice.amount_residual, 800.0)
        self.assertEqual(invoice.payment_state, "partial")

    # === TRANSACTIONS === #

    def test_transaction_processing_consumes_card(self):
        tx = self.env["payment.transaction"].create({
            "provider_id": self.gift_card_provider.id,
            "payment_method_id": self.gift_card_provider.payment_method_ids[:1].id,
            "amount": 30.0,
            "currency_id": self.company.currency_id.id,
            "partner_id": self.partner_b.id,
            "operation": "online_direct",
            "loyalty_card_id": self.gift_card.id,
        })
        processing_values = tx._get_processing_values()
        self.assertEqual(processing_values["state"], "done")
        self.assertTrue(tx.payment_id, "The payment should be created right away.")
        self.assertEqual(tx.payment_id.loyalty_card_id, self.gift_card)
        self.assertEqual(self.gift_card.points, 70)

    def test_transaction_exceeding_balance_is_refused(self):
        tx = self.env["payment.transaction"].create({
            "provider_id": self.gift_card_provider.id,
            "payment_method_id": self.gift_card_provider.payment_method_ids[:1].id,
            "amount": 130.0,
            "currency_id": self.company.currency_id.id,
            "partner_id": self.partner_b.id,
            "operation": "online_direct",
            "loyalty_card_id": self.gift_card.id,
        })
        with self.assertRaises(ValidationError):
            tx._get_processing_values()

    def test_transaction_requires_owned_ewallet(self):
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"].create({
                "provider_id": self.ewallet_provider.id,
                "payment_method_id": self.ewallet_provider.payment_method_ids[:1].id,
                "amount": 10.0,
                "currency_id": self.company.currency_id.id,
                "partner_id": self.partner_b.id,
                "operation": "online_direct",
                "loyalty_card_id": self.ewallet.id,
            })
