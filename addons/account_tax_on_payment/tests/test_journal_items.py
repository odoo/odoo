# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiJson(AccountTestInvoicingCommon):


    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        company = cls.company_data["company"]
        cls.account_advance_payment_tax_account_id = cls.env['account.account'].create({
            'name': 'Tax On Advance',
            'code': '1350',
            'account_type': 'asset_current',
            'company_id': company.id,
        })
        cls.tax_account_id = cls.env['account.account'].create({
            'name': 'Tax',
            'code': '1360',
            'account_type': 'asset_current',
            'company_id': company.id,
        })
        cls.tax_adjustment_journal = cls.env['account.journal'].create({'name': 'Tax Adjustment', 'type': 'general', 'code': 'TAXAD', 'company_id': company.id})
        company.write({
            'account_advance_payment_tax_account_id': cls.account_advance_payment_tax_account_id.id,
            'account_advance_payment_tax_adjustment_journal_id': cls.tax_adjustment_journal.id
        })
        cls.tax_12 = cls.env['account.tax'].create({
            'name': "tax_12",
            'amount_type': 'percent',
            'amount': 12.0,
            'company_id': company.id,
            'invoice_repartition_line_ids': [
                    (0, 0, {
                        'repartition_type': 'base',
                    }),
                    (0, 0, {
                        'repartition_type': 'tax',
                        'account_id': cls.tax_account_id.id,
                    }),
                ],
            'refund_repartition_line_ids': [
                    (0, 0, {
                        'repartition_type': 'base',
                    }),

                    (0, 0, {
                        'repartition_type': 'tax',
                        'account_id': cls.tax_account_id.id,
                    }),
                ],
        })
        cls.negative_tax_10 = cls.tax_12.copy({'amount': -10.00})

    def _create_payment(self, amount, partner_type, partner, tax_ids=None, payment_type='inbound'):
        payment = self.env['account.payment'].create({
            'amount': amount,
            'payment_type': payment_type,
            'partner_type': partner_type,
            'partner_id': partner.id,
            'tax_ids': [(6, 0, tax_ids or [])]
        })
        payment.action_post()
        return payment

    def test_customer_advance_payment_with_gst(self):
        payment = self._create_payment(1000, 'customer', self.partner_a, tax_ids=[self.tax_12.id])
        expected_line_values = [
            {
                'account_id': payment.outstanding_account_id.id,
                'credit': 0.00,
                'debit': 1000.00,
            },
            {
                'account_id': payment.destination_account_id.id,
                'credit': 1000.00,
                'debit': 0.00,
            },
            {
                'account_id': self.tax_account_id.id,
                'credit': 107.14,
                'debit': 0.00,
            },
            {
                'account_id': self.account_advance_payment_tax_account_id.id,
                'credit': 0.00,
                'debit': 107.14,
            }
        ]
        self.assertRecordValues(payment.move_id.line_ids, expected_line_values)
        invoice = self.init_invoice(move_type='out_invoice', amounts=[1000], post=True)
        counterpart_lines = payment._seek_for_lines()[1]
        (counterpart_lines + invoice.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')).reconcile()

        adjustmen_entry = payment.move_id.advanced_payment_tax_created_move_ids
        adjustmen_expected_line_values = [
            {
                'account_id': self.tax_account_id.id,
                'credit': 0.00,
                'debit': 107.14,
            },
            {
                'account_id': self.account_advance_payment_tax_account_id.id,
                'credit': 107.14,
                'debit': 0.00,
            }
        ]
        self.assertRecordValues(adjustmen_entry.line_ids, adjustmen_expected_line_values)
        self.assertEqual(adjustmen_entry.journal_id, self.tax_adjustment_journal)


    def test_customer_advance_payment_with_nagative(self):
        payment = self._create_payment(900, 'customer', self.partner_a, tax_ids=[self.negative_tax_10.id])
        expected_line_values = [
            {
                'account_id': payment.outstanding_account_id.id,
                'credit': 0.00,
                'debit': 900.00,
            },
            {
                'account_id': payment.destination_account_id.id,
                'credit': 900.00,
                'debit': 0.00,
            },
            {
                'account_id': self.tax_account_id.id,
                'credit': 0.00,
                'debit': 100.00,
            },
            {
                'account_id': self.account_advance_payment_tax_account_id.id,
                'credit': 100.00,
                'debit': 0.00,
            }
        ]
        self.assertRecordValues(payment.move_id.line_ids, expected_line_values)
        invoice = self.init_invoice(move_type='out_invoice', amounts=[880], post=True)
        counterpart_lines = payment._seek_for_lines()[1]
        (counterpart_lines + invoice.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')).reconcile()

        adjustmen_entry = payment.move_id.advanced_payment_tax_created_move_ids
        adjustmen_expected_line_values = [
            {
                'account_id': self.tax_account_id.id,
                'credit': 100.00,
                'debit': 0.00,
            },
            {
                'account_id': self.account_advance_payment_tax_account_id.id,
                'credit': 0.00,
                'debit': 100.00,
            }
        ]
        self.assertRecordValues(adjustmen_entry.line_ids, adjustmen_expected_line_values)
        self.assertEqual(adjustmen_entry.journal_id, self.tax_adjustment_journal)
