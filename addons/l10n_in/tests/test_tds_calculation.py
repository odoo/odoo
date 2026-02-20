from odoo.tests import tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTdsCalculation(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template']
        cls.tax_194c_20 = ChartTemplate.ref('tds_20_us_194c')

    def test_tds_rounding(self):
        """
            This test case is based on a practical scenario where the invoice total is 1000.51 (non-rounded).
            After applying rounding, the total becomes 1001.00.

            In this situation:
            - If TDS is calculated on the base amount (1000.51), the TDS is 200.102.
            - However, since the invoice total is rounded, the TDS should follow the rounding up.
            Therefore, the TDS must also be rounded to 201.00.

            We use round-up for TDS to ensure that the payment to the government is never lower than the calculated amount.

            As a result, the residual amount becomes 800.00 instead of 799.898.

            Note:
            There is an additional rule where TDS payment to the government (challan)
            must be rounded to the nearest 10 rupees. This rounding is handled during
            the reconciliation process, not during TDS calculation.

            Hence, we must ensure that the TDS amount is properly rounded before
            entering the reconciliation process.
        """
        # Create invoice where base is not rounded and it's use case base so residual amount is rounded
        invoice = self.init_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            amounts=[1000.51],
        )
        cash_rounding_in_half_up = self.env.ref('l10n_in.cash_rounding_in_half_up')
        invoice.write({
            'invoice_cash_rounding_id': cash_rounding_in_half_up.id,
        })
        invoice.action_post()
        self.assertEqual(invoice.amount_total, 1001.00)
        tds_entry = self.tds_wizard_entry(move=invoice, lines=[(self.tax_194c_20, 1000.51)])
        self.assertEqual(tds_entry.line_ids.filtered(lambda l: l.tax_line_id == self.tax_194c_20).credit, 201.00)
        self.assertEqual(invoice.amount_residual, 800.00)
