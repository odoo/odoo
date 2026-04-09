# Part of Odoo. See LICENSE file for full copyright and licensing details.


from lxml import etree

from odoo import fields, Command, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

# from unittest.mock import patch


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestEBupot(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('id')
    def setUpClass(cls):

        super().setUpClass()
        cls.company_data['company'].street = "test"
        cls.company_data['company'].phone = "12345"
        cls.company_data['company'].vat = "1234567890123456"
        cls.company_data_2 = cls.setup_other_company()
        cls.partner_a.write({
            "vat": "1234567890123457",
            "country_id": cls.env.ref('base.id').id}
        )

        company_id = cls.company_data['company'].id
        ChartTemplate = cls.env['account.chart.template'].with_company(company_id)
        cls.tax_pph_22 = ChartTemplate.ref(f'account.{company_id}_tax_22-102-01_purchase')
        cls.tax_pph_23 = ChartTemplate.ref(f'account.{company_id}_tax_24-101-01_purchase')
        cls.tax_pph_42 = ChartTemplate.ref(f'account.{company_id}_tax_28-403-04_purchase')

        path = "l10n_id_efaktur_coretax/tests/results/sample_ebupot.xml"
        with tools.file_open(path, mode='rb') as test_file:
            cls.sample_xml = test_file.read()

    def _create_valid_payment(self):
        payment = self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'amount': 1000,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'date': '2026-04-24',
            'company_id': self.company_data['company'].id,
        })
        return payment

    def test_download_ebupot_multi_company_user_error(self):
        payment = self._create_valid_payment()
        payment = payment | payment.with_company(self.company_data_2['company'])

        with self.assertRaises(UserError):
            payment.download_ebupot()

    def test_download_ebupot_company_vat_missing(self):
        payment = self._create_valid_payment()
        payment.company_id.vat = False

        with self.assertRaises(ValidationError) as e:
            payment.download_ebupot()
        self.assertIn("VAT hasn't been configured", str(e.exception))

    def test_download_ebupot_company_not_indonesia(self):
        payment = self._create_valid_payment()
        payment.company_id.country_id = self.env.ref('base.us')

        with self.assertRaises(ValidationError) as e:
            payment.download_ebupot()
        self.assertIn("not located in Indonesia", str(e.exception))

    def test_download_ebupot_partner_vat_missing(self):
        payment = self._create_valid_payment()
        payment.partner_id.vat = False

        with self.assertRaises(ValidationError) as e:
            payment.download_ebupot()
        self.assertIn("VAT for customer", str(e.exception))

    def test_download_ebupot_partner_country_missing(self):
        payment = self._create_valid_payment()
        payment.partner_id.country_id = False

        with self.assertRaises(ValidationError) as e:
            payment.download_ebupot()
        self.assertIn("No country is set", str(e.exception))

    def test_download_ebupot_no_bills(self):
        payment = self._create_valid_payment()

        with self.assertRaises(ValidationError) as e:
            payment.download_ebupot()
        self.assertIn("No vendor bills linked", str(e.exception))

    def test_download_ebupot_bill_without_pph(self):
        payment = self._create_valid_payment()
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2026-04-24',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'quantity': 1,
                'price_unit': 1000,
            })],
        })
        bill.action_post()
        bill.reconciled_payment_ids = payment
        payment.reconciled_bill_ids = bill

        with self.assertRaises(ValidationError) as e:
            payment.download_ebupot()
        self.assertIn("does not contain any PPH taxes", str(e.exception))

    def test_download_ebupot_bill_multiple_pph_type(self):
        payment = self._create_valid_payment()
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2026-04-24',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'quantity': 1,
                'price_unit': 1000,
                'tax_ids': [self.tax_pph_22.id, self.tax_pph_23.id]
            })],
        })
        bill.action_post()
        bill.reconciled_payment_ids = payment
        payment.reconciled_bill_ids = bill

        with self.assertRaises(UserError) as e:
            payment.download_ebupot()
        self.assertIn("has more than one PPh tax", str(e.exception))

    def test_prepare_ebupot_grouping_different_partner_or_month(self):
        payment1 = self._create_valid_payment()
        payment2 = self._create_valid_payment()

        # Different partner
        partner_b = self.env['res.partner'].create({
            'name': 'Partner B',
            'vat': '9999999999999999',
            'country_id': self.env.ref('base.id').id,
        })

        payment2.partner_id = partner_b
        payment2.date = '2026-05-01'  # different month

        bill1 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': payment1.date,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'quantity': 1,
                'price_unit': 1000,
                'tax_ids': [self.tax_pph_22.id],
            })],
        })

        bill2 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': payment2.date,
            'partner_id': partner_b.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'quantity': 1,
                'price_unit': 1000,
                'tax_ids': [self.tax_pph_22.id],
            })],
        })

        bill1.action_post()
        bill2.action_post()

        bill1.reconciled_payment_ids = payment1
        payment1.reconciled_bill_ids = bill1

        bill2.reconciled_payment_ids = payment2
        payment2.reconciled_bill_ids = bill2

        result = (payment1 | payment2).prepare_ebupot_vals()
        self.assertEqual(len(result), 2, "Should split into 2 groups (different partner/month)")

    def test_prepare_ebupot_multiple_payments_ratio_split(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2026-03-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'quantity': 1,
                'price_unit': 100000,
                'tax_ids': [self.tax_pph_22.id],
            })],
        })
        bill.action_post()

        payment1 = self._create_valid_payment()
        payment1.amount = 20000
        payment1.date = '2026-03-01'

        payment2 = self._create_valid_payment()
        payment2.amount = 30000
        payment2.date = '2026-04-01'

        payment3 = self._create_valid_payment()
        payment3.amount = 50000
        payment3.date = '2026-05-01'

        payments = payment1 | payment2 | payment3

        bill.write({
            'reconciled_payment_ids': [(6, 0, payments.ids)],
        })
        payments.write({
            'reconciled_bill_ids': [(6, 0, [bill.id])],
        })

        result = payments.prepare_ebupot_vals()

        bases = [vals['TaxBase'] for vals in result]

        self.assertEqual(len(bases), 3)
        self.assertIn(20000, bases)
        self.assertIn(30000, bases)
        self.assertIn(50000, bases)

    def test_ebupot_generated_xml(self):
        payment1 = self._create_valid_payment()
        bill1 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': 'ABC123',
            'invoice_date': payment1.date,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'quantity': 1,
                'price_unit': 1000,
                'tax_ids': [self.tax_pph_22.id],
            })],
        })
        bill1.action_post()
        payment1.action_post()
        bill1.reconciled_payment_ids = payment1
        payment1.reconciled_bill_ids = bill1

        payment1.download_ebupot()
        result_xml = payment1.l10n_id_ebupot_document_xml._generate_ebupot_invoice()[0]['xml']
        result_tree = etree.fromstring(result_xml)
        withholding_date = fields.Datetime.now().strftime('%Y-%m-%d')

        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.sample_xml),
            f'''
            <xpath expr="//WithholdingDate" position="replace">
                <WithholdingDate>{withholding_date}</WithholdingDate>
            </xpath>
            '''
        )
        self.assertXmlTreeEqual(result_tree, expected_tree)
