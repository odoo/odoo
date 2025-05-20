from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestAccountPaymentMethod(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bank_journal_1 = cls.company_data['default_journal_bank']
        cls.bank_journal_2 = cls.company_data['default_journal_bank'].copy()

        cls.inbound_payment_method_1 = cls.env['account.payment.method'].create({
            'name': 'Inbound payment method 1',
            'payment_type': 'inbound',
            'code': 'manual',
        })
        cls.inbound_payment_method_2 = cls.env['account.payment.method'].create({
            'name': 'Inbound payment method 2',
            'payment_type': 'inbound',
            'code': 'manual',
        })

        cls.partner_a.property_inbound_payment_method_id = cls.inbound_payment_method_1
        cls.partner_b.property_inbound_payment_method_id = cls.inbound_payment_method_2

        cls.move_partner_a = cls.init_invoice(move_type='out_invoice', partner=cls.partner_a, products=cls.product_a, post=True)
        cls.move_partner_b = cls.init_invoice(move_type='out_invoice', partner=cls.partner_b, products=cls.product_a, post=True)

    def assertRegisterPayment(self, expected_payment_method, move_partner, preferred_payment_method=False):
        if preferred_payment_method and expected_payment_method:
            move_partner.preferred_payment_method_id = expected_payment_method

        payment = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=move_partner.ids,
        ).create({})

        if not expected_payment_method:
            expected_payment_method = payment.available_payment_method_ids[0]

        self.assertRecordValues(payment, [{
            'payment_method_id': expected_payment_method.id,
        }])

    def test_move_register_payment_wizard(self):
        """
            This test will do a basic flow where we do a register payment from an invoice by using the register payment
            wizard. If we have a payment method set on the partner, the preferred payment method will be the one from
            the partner and so the wizard will have the payment method from the partner. However, we can modify the
            preferred payment on the move and so the payment method and journal of the wizard will be changed.
        """
        # The preferred payment method will be the one set on the partner
        self.assertRegisterPayment(
            self.inbound_payment_method_1,
            self.move_partner_a,
        )
        # We then modify it from the move and check if that still works
        self.assertRegisterPayment(
            self.inbound_payment_method_2,
            self.move_partner_a,
            True,
        )

    def test_multiple_moves_register_payment(self):
        """
            This will test the register payment wizard when selecting multiple move with different partner to see if the
            payment methods are set correctly.
        """
        # Test with two moves with same payment methods and same partners
        move_partner_a_copy = self.move_partner_a.copy()
        move_partner_a_copy.action_post()
        self.assertRegisterPayment(
            self.inbound_payment_method_1,
            self.move_partner_a + move_partner_a_copy,
        )

        # Test with two moves with same payment methods but different partners
        self.partner_c = self.partner_a.copy()
        move_partner_c = self.init_invoice(move_type='out_invoice', partner=self.partner_c, products=self.product_a, post=True)
        self.assertRegisterPayment(
            self.inbound_payment_method_1,
            self.move_partner_a + move_partner_c,
        )

        # Test with two moves with different partners and different payment methods
        self.assertRegisterPayment(
            None,  # We will get in the assertRegisterPayment the default payment method
            self.move_partner_a + self.move_partner_b,
        )

    def test_move_register_payment_view(self):
        """
            This test will check the payment method on a payment from the account payment view.
            When setting a partner with a preferred method set then the payment method must change.
        """
        with Form(self.env['account.payment'].with_context(default_partner_id=self.partner_a)) as pay_form:
            self.assertEqual(pay_form.payment_method_id.id, self.inbound_payment_method_1.id)

            pay_form.partner_id = self.partner_b
            self.assertEqual(pay_form.payment_method_id.id, self.inbound_payment_method_2.id)
