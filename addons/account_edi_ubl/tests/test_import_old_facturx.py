# -*- coding: utf-8 -*-
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestImportOldFacturX(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref='account_edi_ubl.edi_ubl_bis3'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

    ####################################################
    # Test import
    ####################################################

    def test_invoice_edi_pdf(self):
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file(invoice, 'account_edi_ubl', 'tests', 'test_files', 'test_facturx.pdf')

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 525)

        self.create_invoice_from_file('account_edi_ubl', 'tests', 'test_files', 'test_facturx.pdf')

        self.assertEqual(invoice.amount_total, 525)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    def test_invoice_edi_xml(self):
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file(invoice, 'account_edi_ubl', 'tests', 'test_files', 'test_facturx.xml')

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 4610)

        self.create_invoice_from_file('account_edi_ubl', 'tests', 'test_files', 'test_facturx.xml')

        self.assertEqual(invoice.amount_total, 4610)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)
