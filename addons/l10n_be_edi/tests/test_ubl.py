# -*- coding: utf-8 -*-
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon


class TestUBL(AccountEdiTestCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template', edi_format_ref='l10n_be_edi.edi_efff_1'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.partner_a.vat = 'BE0123456789'

    def test_invoice_edi_xml(self):
        invoice = self.env['account.move'].with_context(default_move_type='in_invoice').create({})
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('l10n_be_edi', 'test_xml_file', 'efff_test.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 666.50)
        self.assertEqual(invoice.amount_tax, 115.67)
        self.assertEqual(invoice.partner_id, self.partner_a)
