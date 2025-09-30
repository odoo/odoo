from odoo.tests import tagged
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTRAccountMoveSend(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('tr')
    def setUpClass(cls):
        super().setUpClass()

    def test_invoice_names_valid_for_nilvera(self):
        valid_names = [
            'INV-2025-00001',
            'R01/2025/00001',
            '123/2025/00001',
            'res.2025.00001',
            'RES2025/00001',
        ]
        invoices = self.env['account.move']
        for name in valid_names:
            invoice = self.init_invoice('out_invoice', invoice_date='2025-11-28', amounts=[1000])
            invoice.name = name
            invoice.action_post()
            invoices |= invoice

        wizard = self.create_send_and_print(invoices)
        self.assertNotIn('tr_moves_with_invalid_name', wizard.alerts)

    def test_invoice_names_invalid_for_nilvera(self):
        invalid_names = [
            'INV/2025/0',
            'INV/25/1012',
            'RESXYZ00001',
            'res2025ABCDE',
            'RES-XYZ-00001',
            'INVOICE/2025/00010',
        ]
        for name in invalid_names:
            invoice = self.init_invoice('out_invoice', invoice_date='2025-11-28', amounts=[1000])
            invoice.name = name
            invoice.action_post()

            wizard = self.create_send_and_print(invoice)
            self.assertIn('tr_moves_with_invalid_name', wizard.alerts)
