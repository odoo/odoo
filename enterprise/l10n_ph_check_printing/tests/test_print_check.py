from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPrintCheck(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('PH')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].account_check_printing_layout = 'l10n_ph_check_printing.action_print_check'

        bank_journal = cls.company_data['default_journal_bank']

        cls.payment_method_line_check = bank_journal.outbound_payment_method_line_ids\
            .filtered(lambda l: l.code == 'check_printing')

        cls.outstanding_account = cls.env['account.account'].create({
            'name': "Outstanding Payments",
            'code': 'OSTP420',
            'reconcile': False,  # On purpose for testing.
            'account_type': 'asset_current',
        })

    def test_check_with_withholding_tax(self):
        withholding_tax_module = self.env['ir.module.module']._get('l10n_account_withholding_tax')
        if withholding_tax_module.state != 'installed':
            self.skipTest("This test depends on 'Withholding Tax on Payment' module.")

        withholding_tax = self.env['account.chart.template'].ref('l10n_ph_tax_purchase_wi011')
        withholding_tax.is_withholding_tax_on_payment = True

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 3000.0,
                'tax_ids': [withholding_tax.id],
            })]
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register'].with_context(
            lang='en_US',
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'withholding_outstanding_account_id': self.outstanding_account.id,
        })

        payment_register.withholding_line_ids[0].name = "1"
        payment = payment_register._create_payments()
        check_page_info = payment._check_get_pages()[0]

        self.assertEqual(check_page_info['amount_no_currency'], "2,700.00")
        self.assertEqual(check_page_info['amount_in_word'], "Two Thousand Seven Hundred ONLY")
