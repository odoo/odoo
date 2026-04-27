# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, Command
from odoo.tests import tagged
from odoo.exceptions import UserError
from odoo.addons.l10n_ke_edi_oscu.tests.common import TestKeEdiCommon


class TestKeEdi(TestKeEdiCommon):
    def _test_get_items(self):
        self.env['ir.config_parameter'].set_param('l10n_ke_oscu.last_fetch_items_request_date', '20180101000000')
        with self.assertRaises(UserError):
            self.env.company.action_l10n_ke_get_items()

    def _test_get_stock_moves(self):
        with self.assertRaises(UserError):
            self.env.company.action_l10n_ke_get_stock_moves()

    def _test_update_codes(self):
        self.env['ir.config_parameter'].set_param('l10n_ke_oscu.last_code_request_date', '20180101000000')
        self.env['l10n_ke_edi_oscu.code']._cron_get_codes_from_device()

    def _test_update_customer(self):
        with self.assertRaises(UserError):
            self.partner_a.action_l10n_ke_oscu_fetch_bhf_customer()

    def _test_update_notices(self):
        self.env['ir.config_parameter'].set_param('l10n_ke_oscu.last_notice_request_date', '20180101000000')
        self.env.ref('l10n_ke_edi_oscu.ir_cron_fetch_notice').method_direct_trigger()

    def _test_update_unspsc_codes(self):
        self.env['ir.config_parameter'].set_param('l10n_ke_oscu.last_unspsc_code_request_date', '20180101000000')
        self.env.ref('l10n_ke_edi_oscu.ir_cron_fetch_unspsc').method_direct_trigger()

    def _test_save_customer(self):
        self.partner_a.action_l10n_ke_oscu_register_bhf_customer()

    def _test_save_insurance(self):
        self.env.company.action_l10n_ke_send_insurance()

    def _test_save_item(self):
        self.product_service.action_l10n_ke_oscu_save_item()

    def _test_save_user(self):
        self.env.user.action_l10n_ke_create_branch_user()

    def _test_send_invoice_and_credit_note(self):
        """ Test that we're able to send an invoice and a credit note """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-01-28',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_service.id,
                'discount': 10.0,
            })],
        })
        self.assertFalse(invoice.l10n_ke_validation_message)

        invoice.action_post()
        send_and_print = self.create_send_and_print(invoice)
        self.assertTrue(send_and_print.extra_edi_checkboxes.get('ke_oscu', {}).get('checked'))
        with self.set_invoice_number(invoice):
            send_and_print.action_send_and_print()

        self.assertTrue(invoice.l10n_ke_oscu_invoice_number)
        self.assertTrue(invoice.l10n_ke_oscu_receipt_number)
        self.assertTrue(invoice.l10n_ke_oscu_internal_data)

        credit_note = self.create_reversal(invoice)
        self.assertFalse(credit_note.l10n_ke_validation_message)
        credit_note.action_post()
        send_and_print = self.create_send_and_print(credit_note)
        self.assertTrue(send_and_print.extra_edi_checkboxes.get('ke_oscu', {}).get('checked'))
        with self.set_invoice_number(credit_note):
            send_and_print.action_send_and_print()

        self.assertTrue(credit_note.l10n_ke_oscu_invoice_number)
        self.assertTrue(credit_note.l10n_ke_oscu_receipt_number)
        self.assertTrue(credit_note.l10n_ke_oscu_internal_data)

    def _test_send_invoice_complex(self):
        """ Test that the invoice JSON generation correctly handles an invoice with:
            - a currency (EUR) different from KSh
            - an UoM on the invoice line that differs from the UoM on the product
            - a round_globally tax setting
            - an excise tax included in price, that applies before the VAT, and a withholding tax.

        The excise tax amount should appear as part of the base amount, while the withholding tax should not
        be reported.
        """
        wh_tax = self.env['account.chart.template'].ref('SWT10')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.today(),
            'journal_id': self.company_data['default_journal_sale'].id,
            'currency_id': self.env.ref('base.EUR').id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_service.id,
                    'price_unit': 1300.00,  # 1000 base + 300 excise = 1300 EUR.
                    'quantity': 2,
                    'tax_ids': [Command.set((self.excise_tax | self.standard_rate_sales_tax | wh_tax).ids)],
                })
            ],
        })

        self.assertFalse(invoice.l10n_ke_validation_message)

        invoice.action_post()
        send_and_print = self.create_send_and_print(invoice)
        self.assertTrue(send_and_print.extra_edi_checkboxes.get('ke_oscu', {}).get('checked'))
        with self.set_invoice_number(invoice):
            send_and_print.action_send_and_print()

        self.assertTrue(invoice.l10n_ke_oscu_invoice_number)
        self.assertTrue(invoice.l10n_ke_oscu_receipt_number)
        self.assertTrue(invoice.l10n_ke_oscu_internal_data)

    def _test_get_vendor_bill(self):
        # Step 1: Get vendor bill
        vendor_bill = self.env['account.move']._l10n_ke_oscu_fetch_purchases(self.company_data['company'])
        expected_vendor_bill = {
            'partner_id': self.partner_a.id,
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2023-12-12'),
        }
        expected_vendor_bill_lines = [
            {
                'name': 'Fiscal Optimization Consultancy',
                'product_id': self.product_service.id,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'quantity': 1,
                'tax_ids': [self.standard_rate_purchase_tax.id],
                'balance': 17499,
            }, {
                'name': '16%',
                'product_id': None,
                'product_uom_id': None,
                'quantity': 0,
                'tax_ids': [],
                'balance': 2799.84,
            }, {
                'name': False,
                'product_id': None,
                'product_uom_id': None,
                'quantity': 0,
                'tax_ids': [],
                'balance': -20298.84,
            }
        ]
        self.assertInvoiceValues(vendor_bill, expected_vendor_bill_lines, expected_vendor_bill)
        return vendor_bill

    def _test_confirm_vendor_bill(self, vendor_bill):
        # Step 2: send vendor bill confirmation
        vendor_bill.l10n_ke_payment_method_id = self.env.ref('l10n_ke_edi_oscu.code_07_05')
        self.assertFalse(vendor_bill.l10n_ke_validation_message)
        vendor_bill.action_post()
        vendor_bill.action_l10n_ke_oscu_confirm_vendor_bill()
        self.assertTrue(vendor_bill.l10n_ke_oscu_invoice_number)


@tagged('external', 'external_l10n', 'post_install', '-post_install_l10n', '-at_install', '-standard')
class TestKeEdiLive(TestKeEdi):
    @TestKeEdiCommon.setup_country('ke')
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.is_live_test = True

    def test_get_items(self):
        self._test_get_items()

    def test_get_stock_moves(self):
        self._test_get_stock_moves()

    def test_update_codes(self):
        self._test_update_codes()

    def test_update_customer(self):
        self._test_update_customer()

    def test_update_notices(self):
        self._test_update_notices()

    def test_update_unspsc_codes(self):
        self._test_update_unspsc_codes()

    def test_save_customer(self):
        self._test_save_customer()

    def test_save_insurance(self):
        self._test_save_insurance()

    def test_save_item(self):
        self._test_save_item()

    def test_save_user(self):
        self._test_save_user()

    def test_create_branches(self):
        self._test_create_branches()

    def test_send_invoice_and_credit_note(self):
        self._test_send_invoice_and_credit_note()

    def test_send_invoice_complex(self):
        self._test_send_invoice_complex()

    def test_confirm_vendor_bill(self):
        # This is mocked because there are no purchases on the test server to retrieve.
        with self.patch_session([
            ('selectTrnsPurchaseSalesList', 'get_purchases', 'get_purchases_1'),
        ]):
            vendor_bill = self._test_get_vendor_bill()
        self._test_confirm_vendor_bill(vendor_bill)
