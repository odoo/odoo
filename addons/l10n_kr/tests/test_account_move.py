# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

MISMATCH = 'l10n_kr_issuance_type_mismatch'
MIXED = 'l10n_kr_mixed_tax_nature'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nKrAccountMove(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('kr')
    def setUpClass(cls):
        super().setUpClass()

    def test_issuance_type_protected_by_tax_lock_date(self):
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_date='2024-01-15',
            l10n_kr_issuance_type='tax_invoice',
            invoice_line_ids=[self._prepare_invoice_line(
                price_unit=1000.0,
                tax_ids=self.env['account.chart.template'].ref('l10n_kr_Purchase_10'),
            )],
            post=True,
        )
        bill.company_id.tax_lock_date = fields.Date.from_string('2024-01-31')

        # The proof of issuance decides the VAT report box: it can't change once the period is locked.
        with self.assertRaisesRegex(UserError, "already issued tax statement"):
            bill.l10n_kr_issuance_type = 'card_payment'

        # Writing the same value is not a change.
        bill.l10n_kr_issuance_type = 'tax_invoice'

    def test_edocument_number_not_copied(self):
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_date='2024-01-15',
            l10n_kr_edocument_number='202401154100000012345678',
            post=True,
        )

        self.assertFalse(invoice.copy().l10n_kr_edocument_number)
        self.assertFalse(invoice._reverse_moves().l10n_kr_edocument_number)

    def _get_kr_alerts(self, move_type, issuance_type, tax_xmlids):
        ChartTemplate = self.env['account.chart.template']
        invoice = self._create_invoice(
            move_type=move_type,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100.0, tax_ids=ChartTemplate.ref(xmlid))
                for xmlid in tax_xmlids
            ],
        )
        invoice.l10n_kr_issuance_type = issuance_type
        return {key for key in invoice.alerts or {} if key in (MISMATCH, MIXED)}

    def _assert_alerts(self, move_type, cases):
        for issuance_type, tax_xmlids, expected in cases:
            with self.subTest(move_type=move_type, issuance_type=issuance_type, taxes=tax_xmlids):
                self.assertEqual(self._get_kr_alerts(move_type, issuance_type, tax_xmlids), expected)

    def test_customer_invoice_issuance_type_alerts(self):
        self._assert_alerts('out_invoice', [
            # VAT 10%
            ('tax_invoice', ['l10n_kr_Sales_10'], set()),
            ('tax_exempt_invoice', ['l10n_kr_Sales_10'], {MISMATCH}),
            ('card_payment', ['l10n_kr_Sales_10'], set()),
            # VAT 0%
            ('tax_invoice', ['l10n_kr_Sales_0'], set()),
            ('tax_exempt_invoice', ['l10n_kr_Sales_0'], {MISMATCH}),
            ('purchaser_tax_invoice', ['l10n_kr_Sales_0'], {MISMATCH}),
            ('other', ['l10n_kr_Sales_0'], set()),
            # Tax Exempt
            ('tax_exempt_invoice', ['l10n_kr_Sales_tf'], set()),
            ('tax_invoice', ['l10n_kr_Sales_tf'], {MISMATCH}),
            ('purchaser_tax_invoice', ['l10n_kr_Sales_tf'], {MISMATCH}),
            ('cash_receipt', ['l10n_kr_Sales_tf'], set()),
            # Mixed tax types
            ('tax_invoice', ['l10n_kr_Sales_10', 'l10n_kr_Sales_tf'], {MIXED}),
            ('tax_invoice', ['l10n_kr_Sales_10', 'l10n_kr_Sales_0'], {MIXED}),
            ('tax_invoice', ['l10n_kr_Sales_10', 'l10n_kr_Sales_0', 'l10n_kr_Sales_tf'], {MIXED}),
            ('tax_exempt_invoice', ['l10n_kr_Sales_0', 'l10n_kr_Sales_tf'], {MIXED}),
            ('purchaser_tax_invoice', ['l10n_kr_Sales_10', 'l10n_kr_Sales_tf'], {MIXED}),
            ('card_payment', ['l10n_kr_Sales_10', 'l10n_kr_Sales_tf'], set()),
            ('card_payment', ['l10n_kr_Sales_10', 'l10n_kr_Sales_0'], set()),
        ])

    def test_vendor_bill_issuance_type_alerts(self):
        self._assert_alerts('in_invoice', [
            # VAT 10%
            ('tax_invoice', ['l10n_kr_Purchase_10'], set()),
            ('tax_exempt_invoice', ['l10n_kr_Purchase_10'], {MISMATCH}),
            ('other', ['l10n_kr_Purchase_10'], {MISMATCH}),
            # VAT 0%
            ('tax_invoice', ['l10n_kr_Purchase_0'], set()),
            ('tax_exempt_invoice', ['l10n_kr_Purchase_0'], {MISMATCH}),
            ('purchaser_tax_invoice', ['l10n_kr_Purchase_0'], {MISMATCH}),
            ('card_payment', ['l10n_kr_Purchase_0'], {MISMATCH}),
            ('cash_receipt', ['l10n_kr_Purchase_0'], {MISMATCH}),
            ('other', ['l10n_kr_Purchase_0'], {MISMATCH}),
            # Tax Exempt
            ('tax_exempt_invoice', ['l10n_kr_Purchase_tf'], set()),
            ('tax_invoice', ['l10n_kr_Purchase_tf'], {MISMATCH}),
            ('purchaser_tax_invoice', ['l10n_kr_Purchase_tf'], {MISMATCH}),
            # VAT DP
            ('tax_exempt_invoice', ['l10n_kr_Purchase_4_dp'], set()),
            ('tax_invoice', ['l10n_kr_Purchase_4_dp'], {MISMATCH}),
            ('purchaser_tax_invoice', ['l10n_kr_Purchase_4_dp'], {MISMATCH}),
            # VAT RP
            ('other', ['l10n_kr_Purchase_3_dp'], set()),
            ('tax_invoice', ['l10n_kr_Purchase_3_dp'], {MISMATCH}),
            ('tax_exempt_invoice', ['l10n_kr_Purchase_3_dp'], {MISMATCH}),
            ('purchaser_tax_invoice', ['l10n_kr_Purchase_3_dp'], {MISMATCH}),
            # 10% IM is a group tax: its VAT 10% child tax drives the rules
            ('tax_invoice', ['l10n_kr_Purchase_10_im'], set()),
            ('tax_exempt_invoice', ['l10n_kr_Purchase_10_im'], {MISMATCH}),
            ('tax_invoice', ['l10n_kr_Purchase_10_im', 'l10n_kr_Purchase_tf'], {MIXED}),
            ('tax_invoice', ['l10n_kr_Purchase_10_im', 'l10n_kr_Purchase_0'], {MIXED}),
            # Mixed tax types
            ('tax_invoice', ['l10n_kr_Purchase_10', 'l10n_kr_Purchase_tf'], {MIXED}),
            ('tax_invoice', ['l10n_kr_Purchase_10', 'l10n_kr_Purchase_0'], {MIXED}),
            ('tax_invoice', ['l10n_kr_Purchase_10', 'l10n_kr_Purchase_0', 'l10n_kr_Purchase_tf'], {MIXED}),
            ('tax_exempt_invoice', ['l10n_kr_Purchase_0', 'l10n_kr_Purchase_tf'], {MIXED}),
            ('cash_receipt', ['l10n_kr_Purchase_10', 'l10n_kr_Purchase_tf'], set()),
            # VAT DP / RP are outside the single tax type rule
            ('tax_exempt_invoice', ['l10n_kr_Purchase_tf', 'l10n_kr_Purchase_4_dp'], set()),
        ])

    def test_credit_notes_and_receipts_follow_invoice_rules(self):
        for move_type in ('out_refund', 'out_receipt'):
            self._assert_alerts(move_type, [
                ('tax_invoice', ['l10n_kr_Sales_10'], set()),
                ('tax_invoice', ['l10n_kr_Sales_tf'], {MISMATCH}),
                ('tax_invoice', ['l10n_kr_Sales_10', 'l10n_kr_Sales_tf'], {MIXED}),
            ])
        for move_type in ('in_refund', 'in_receipt'):
            self._assert_alerts(move_type, [
                ('tax_invoice', ['l10n_kr_Purchase_0'], set()),
                ('card_payment', ['l10n_kr_Purchase_0'], {MISMATCH}),
                ('tax_invoice', ['l10n_kr_Purchase_0', 'l10n_kr_Purchase_tf'], {MIXED}),
            ])

    def test_empty_issuance_type_only_warns_on_mixed_tax_types(self):
        self._assert_alerts('out_invoice', [
            (False, ['l10n_kr_Sales_tf'], set()),
            (False, ['l10n_kr_Sales_10', 'l10n_kr_Sales_tf'], {MIXED}),
        ])
        self._assert_alerts('in_invoice', [
            (False, ['l10n_kr_Purchase_0'], set()),
            (False, ['l10n_kr_Purchase_10', 'l10n_kr_Purchase_0'], {MIXED}),
        ])

    def test_no_alert_on_cancelled_invoice(self):
        invoice = self._create_invoice(
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100.0, tax_ids=self.env['account.chart.template'].ref('l10n_kr_Sales_tf'))],
        )
        invoice.l10n_kr_issuance_type = 'tax_invoice'
        self.assertIn(MISMATCH, invoice.alerts)
        invoice.button_cancel()
        self.assertNotIn(MISMATCH, invoice.alerts or {})
