# -*- coding: utf-8 -*-
from .common import TestMxEdiCommonExternal
from odoo.tests import tagged


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestCFDIInvoiceExternal(TestMxEdiCommonExternal):

    def _test_invoice_cfdi(self, pac_name):
        self.env.company.l10n_mx_edi_pac = pac_name
        invoice = self._create_invoice(partner_id=self.partner_us.id)
        invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertEqual(invoice.l10n_mx_edi_cfdi_state, 'sent', f'Error: {invoice.l10n_mx_edi_document_ids.message}')

    def test_invoice_cfdi_solfact(self):
        self._test_invoice_cfdi('solfact')

    def test_invoice_cfdi_finkok(self):
        self._test_invoice_cfdi('finkok')
