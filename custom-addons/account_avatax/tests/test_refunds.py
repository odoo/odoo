from odoo.tests.common import tagged
from .common import TestAccountAvataxCommon


@tagged("-at_install", "post_install")
class TestAccountAvalaraRefunds(TestAccountAvataxCommon):
    """https://developer.avalara.com/certification/avatax/refunds-credit-memos-badge/"""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        res = super().setUpClass(chart_template_ref)
        cls.product = cls.env["product.product"].create({
            'name': "Product",
            'list_price': 15.00,
            'standard_price': 15.00,
            'supplier_taxes_id': None,
            'avatax_category_id': cls.env.ref('account_avatax.DC010000').id,
        })

        with cls._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            cls.invoice = cls.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': cls.partner.id,
                'fiscal_position_id': cls.fp_avatax.id,
                'invoice_date': '2020-01-01',
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': cls.product.id,
                        'price_unit': cls.product.list_price,
                    })
                ]
            })
            cls.invoice.button_external_tax_calculation()
        cls.invoice_captured_arguments = capture.val['json']['createTransactionModel']
        with cls._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            cls.invoice.action_post()

        with cls._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            move_reversal = cls.env['account.move.reversal'].with_context(
                active_model="account.move",
                active_ids=cls.invoice.ids
            ).create({
                'date': '2020-02-01',
                'reason': 'no reason',
                'journal_id': cls.invoice.journal_id.id,
            })
            reversal = move_reversal.refund_moves()
            reverse_move = cls.env['account.move'].browse(reversal['res_id'])
            reverse_move.button_external_tax_calculation()
        cls.refund_captured_arguments = capture.val['json']['createTransactionModel']

        with cls._capture_request(return_value={'lines': [], 'summary': []}) as capture:
            reverse_move.action_post()
        cls.refund_commit_captured_arguments = capture.val['json']['createTransactionModel']
        return res

    def test_post_tax_credit_memento(self):
        """Ensure that returns are committed/posted for reporting appropriately."""
        self.assertEqual(self.refund_captured_arguments['type'], 'ReturnInvoice')
        self.assertTrue(self.refund_commit_captured_arguments['commit'])

    def test_original_invoice_date(self):
        """Send original invoice date as tax calculation date for return orders/credit memos."""
        self.assertTrue('taxOverride' not in self.invoice_captured_arguments)
        self.assertEqual(self.invoice_captured_arguments['date'], '2020-01-01')

        self.assertEqual(
            self.refund_captured_arguments['taxOverride']['taxDate'], '2020-01-01',
            'Refund date should be overridden to match the tax calculation date of the original invoice.'
        )

    def test_current_transaction_date(self):
        """Send current transaction date as document date for return orders/credit memos"""
        self.assertEqual(self.invoice_captured_arguments['date'], '2020-01-01')
        self.assertEqual(self.refund_captured_arguments['date'], '2020-02-01')
