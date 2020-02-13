from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

import time


@tagged('post_install', '-at_install')
class PaymentISR(AccountingTestCase):
    """Test grouping of payment by ISR reference"""

    def create_supplier_invoice(self, supplier, ref, currency_to_use='base.CHF', inv_date=None):
        """ Generates a test invoice """
        f = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        f.partner_id = supplier
        f.invoice_payment_ref = ref
        f.currency_id = self.env.ref(currency_to_use)
        f.invoice_date = inv_date or time.strftime('%Y') + '-12-22'
        with f.invoice_line_ids.new() as line:
            line.product_id = self.env.ref("product.product_product_4")
            line.quantity = 1
            line.price_unit = 42

        invoice = f.save()
        invoice.post()
        return invoice

    def create_bank_account(self, number, partner, bank=None):
        """ Generates a test res.partner.bank. """
        return self.env['res.partner.bank'].create({
            'acc_number': number,
            'bank_id': bank.id,
            'partner_id': partner.id,
        })

    def create_isrb_account(self, number, partner):
        """ Generates a test res.partner.bank. """
        return self.env['res.partner.bank'].create({
            'acc_number': partner.name + number,
            'l10n_ch_postal': number,
            'partner_id': partner.id,
        })

    def setUp(self):
        super().setUp()
        abs_bank = self.env['res.bank'].create(
            {
                'name': 'Alternative Bank Schweiz',
                'bic': 'ABSOCH22XXX',
            }
        )

        self.supplier_isrb1 = self.env['res.partner'].create({
            'name': "Supplier ISR 1"
        })
        self.create_isrb_account('01-162-8', self.supplier_isrb1)
        self.supplier_isrb2 = self.env['res.partner'].create({
            'name': "Supplier ISR 2"
        })
        self.create_isrb_account('01-162-8', self.supplier_isrb2)
        self.supplier_iban = self.env['res.partner'].create({
            'name': "Supplier IBAN"
        })
        self.create_bank_account(
            'CH61 0839 0107 6280 0100 0',
            self.supplier_iban,
            abs_bank,
        )

    def test_payment_isr_grouping(self):
        """Create multiple invoices to test grouping by partner and ISR

        """
        invoices = (
            self.create_supplier_invoice(self.supplier_isrb1, '703192500010549027000209403')
            | self.create_supplier_invoice(self.supplier_isrb1, '120000000000234478943216899')
            | self.create_supplier_invoice(self.supplier_isrb1, '120000000000234478943216899', inv_date=time.strftime('%Y') + '-12-23')
            | self.create_supplier_invoice(self.supplier_isrb2, '120000000000234478943216899')
            | self.create_supplier_invoice(self.supplier_iban, '1234')
            | self.create_supplier_invoice(self.supplier_iban, '5678')
        )
        # create an invoice where ref is set instead of invoice_payment_ref
        inv_ref = self.create_supplier_invoice(self.supplier_isrb1, False)
        inv_ref.ref = '120000000000234478943216899'
        invoices |= inv_ref
        inv_no_ref = self.create_supplier_invoice(self.supplier_iban, False)
        invoices |= inv_no_ref
        # create an invoice where ref is set instead of invoice_payment_ref
        PaymentRegister = self.env['account.payment.register']
        register = PaymentRegister.with_context(active_ids=invoices.ids).create({
            'group_payment': True,
        })

        vals = register.get_payments_vals()
        self.assertEqual(len(vals), 4)
        expected_vals = [
            # ref, partner, invoice count, amount
            # 3 invoices #2, #3 and inv_ref grouped in one payment with a single ref
            ('120000000000234478943216899', self.supplier_isrb1.id, 3, 126.0),
            # different partner, different payment
            ('120000000000234478943216899', self.supplier_isrb2.id, 1, 42.0),
            # not ISR, standard grouping
            ('1234 5678 {}'.format(inv_no_ref.name), self.supplier_iban.id, 3, 126.0),
            # different ISR reference, different payment
            ('703192500010549027000209403', self.supplier_isrb1.id, 1, 42.0),
        ]
        self.assertEqual(
            [(v['communication'], v['partner_id'], len(v['invoice_ids'][0][2]),
                v['amount']) for v in sorted(vals, key=lambda i: (i['communication'], i['partner_id']))],
            expected_vals,
        )
