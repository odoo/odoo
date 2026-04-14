from odoo import Command

from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBEPurchaseMatching(TestUblImportBis3InvoiceBE):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ensure_installed('purchase')
        cls.tax_21 = cls.percent_tax(cls, 21.0, type_tax_use='purchase')
        cls.product_c = cls.env['product.product'].create({
            'name': 'product_c',
            'standard_price': 300.0,
            'supplier_taxes_id': False
        })
        cls.po = cls.env['purchase.order'].create({  # noqa: OLS03001
            'name': 'TEST_PURCHASE_ORDER',
            'company_id': cls.company_data['company'].id,
            'partner_id': cls.partner_a.id,
            'order_line': [Command.create({
                'product_id': cls.product_a.id,
                'price_unit': 100,
                'product_qty': 1,
                'taxes_id': cls.tax_21.ids,
            }),
            Command.create({
                'product_id': cls.product_b.id,
                'price_unit': 200,
                'product_qty': 1,
                'taxes_id': cls.tax_21.ids,
            }),
            Command.create({
                'product_id': cls.product_c.id,
                'price_unit': 300,
                'product_qty': 1,
                'taxes_id': cls.tax_21.ids,
            })],
        })
        cls.po.button_confirm()

    def test_import_invoice_purchase_order_full_match(self):
        self.ensure_installed('purchase')
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_purchase_order_full_match',
            journal=self.company_data['default_journal_purchase'],
        )
        po_line_ids = self.po.order_line.ids

        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'display_type': 'line_section',
                'purchase_line_id': False,
            },
            {
                'display_type': 'product',
                'purchase_line_id': po_line_ids[0],
            },
            {
                'display_type': 'product',
                'purchase_line_id': po_line_ids[1],
            },
            {
                'display_type': 'product',
                'purchase_line_id': po_line_ids[2],
            },
        ])

    def test_import_invoice_purchase_order_submatch(self):
        self.ensure_installed('purchase')

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_purchase_order_submatch',
            journal=self.company_data['default_journal_purchase'],
        )
        po_line_ids = self.po.order_line.ids

        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'display_type': 'line_section',
                'purchase_line_id': False,
            },
            {
                'display_type': 'product',
                'purchase_line_id': po_line_ids[0],
            },
            {
                'display_type': 'product',
                'purchase_line_id': po_line_ids[2],
            },
        ])

    def test_import_invoice_purchase_order_overmatch(self):
        self.ensure_installed('purchase')

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_purchase_order_overmatch',
            journal=self.company_data['default_journal_purchase'],
        )
        po_line_ids = self.po.order_line.ids

        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'display_type': 'product',
                'purchase_line_id': False,
            },
            {
                'display_type': 'line_section',  # FROM PO
                'purchase_line_id': False,
            },
            {
                'display_type': 'product',
                'purchase_line_id': po_line_ids[0],
            },
            {
                'display_type': 'product',
                'purchase_line_id': po_line_ids[1],
            },
            {
                'display_type': 'product',
                'purchase_line_id': po_line_ids[2],
            },
            {
                'display_type': 'line_section',  # FROM EDI but sequence = -1 so in the ui it'll be the first line
                'purchase_line_id': False,
            },
        ])
