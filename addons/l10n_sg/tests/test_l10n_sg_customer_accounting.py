# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nSGCustomerAccounting(AccountTestInvoicingCommon):
    """Test Customer Accounting IRAS message on invoices with SRCA-S tax."""
    _test_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sg')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].vat = '200002150H'

        cls.srca_s_tax = cls.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', cls.company_data['company'].id),
            ('ubl_cii_tax_category_code', '=', 'SRCA-S'),
            ('type_tax_use', '=', 'sale'),
        ], limit=1)
        cls.srca_s_tax.active = True

        cls.sr_tax = cls.env['account.tax'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('ubl_cii_tax_category_code', '=', 'SR'),
            ('type_tax_use', '=', 'sale'),
        ], limit=1)

    def test_customer_accounting_message_invoice(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Mobile Phone',
                    'quantity': 1,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.srca_s_tax.ids)],
                }),
                Command.create({
                    'name': 'Another Phone',
                    'quantity': 1,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.srca_s_tax.ids)],
                }),
            ],
        })
        # 9% of (1000 + 1000) = 180
        self.assertEqual(invoice.l10n_sg_customer_accounting_gst_amount, 180.0)

    def test_customer_accounting_message_credit_note(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Mobile Phone Return',
                    'quantity': 1,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.srca_s_tax.ids)],
                }),
            ],
        })
        # 9% of 1000 = 90
        self.assertEqual(invoice.l10n_sg_customer_accounting_gst_amount, 90.0)

    def test_no_message_without_srca_s(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Regular Service',
                    'quantity': 1,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.sr_tax.ids)],
                }),
            ],
        })
        self.assertEqual(invoice.l10n_sg_customer_accounting_gst_amount, 0.0)
