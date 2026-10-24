from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFrTaxReport(AccountTestInvoicingCommon):

    def test_bill_invoice_refund_net_vat_due(self):
        vat_tax = self.env['account.tax'].create({
            'name': 'VAT 10%',
            'amount_type': 'percent',
            'amount': 10,
            'company_id': self.env.company.id,
            'type_tax_use': 'sale',
        })

        bill = self.init_invoice('in_invoice', self.partner_a, '2024-01-01', amounts=[1000], taxes=[vat_tax], post=True)
        invoice = self.init_invoice('out_invoice', self.partner_a, '2024-01-01', amounts=[1000], taxes=[vat_tax], post=True)
        refund = self.init_invoice('out_refund', self.partner_a, '2024-01-01', amounts=[1000], taxes=[vat_tax], post=True)

        bill_tax = abs(bill.amount_tax)
        invoice_tax = abs(invoice.amount_tax)
        refund_tax = abs(refund.amount_tax)

        self.assertEqual(bill_tax, 100)
        self.assertEqual(invoice_tax, 100)
        self.assertEqual(refund_tax, 100)

        tax_due = max(0, invoice_tax + refund_tax - bill_tax)
        tax_credit = max(0, bill_tax - invoice_tax - refund_tax)
        self.assertEqual(tax_due, 100)
        self.assertEqual(tax_credit, 0)
