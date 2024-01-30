# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from lxml import etree
from odoo.addons.l10n_it_edi.tests.common import TestItEdi
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo import tools

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiPa(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Move = cls.env['account.move'].with_company(cls.company)
        journal_code = cls.company_data_2['default_journal_sale'].code
        cls.split_payment_tax = cls.env['account.tax'].with_company(cls.company).search([('name', '=', '22% SP')])
        cls.split_payment_line_data = {
            **cls.standard_line,
            'tax_ids': [(6, 0, [cls.split_payment_tax.id])]
        }

        cls.pa_partner_invoice_data = {
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_b.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, cls.split_payment_line_data),
            ],
            'l10n_it_origin_document_type': 'purchase_order',
            'l10n_it_origin_document_date': datetime.date(2022, 3, 23),
            'l10n_it_origin_document_name': f"{journal_code}/2022/0001",
            'l10n_it_cup': '0123456789',
            'l10n_it_cig': '0987654321'
        }
        cls.pa_partner_invoice = cls.Move.create(cls.pa_partner_invoice_data)
        cls.pa_partner_invoice_2 = cls.Move.create({
            **cls.pa_partner_invoice_data,
            'l10n_it_origin_document_type': False,
        })
        cls.pa_partner_invoice._post()
        cls.split_payment_invoice_content = cls._get_test_file_content('split_payment.xml')

    @classmethod
    def _get_test_file_content(cls, filename):
        """ Get the content of a test file inside this module """
        path = 'l10n_it_edi/tests/expected_xmls/' + filename
        with tools.file_open(path, mode='rb') as test_file:
            return test_file.read()

    def test_send_pa_partner(self):
        res = self.edi_format._l10n_it_post_invoices_step_1(self.pa_partner_invoice)
        self.assertEqual(res[self.pa_partner_invoice], {'attachment': self.pa_partner_invoice.l10n_it_edi_attachment_id, 'success': True})

    def test_send_pa_partner_missing_field(self):
        with self.assertRaises(UserError):
            self.pa_partner_invoice_2._post()

    def test_split_payment(self):
        """ ImportoTotaleDocumento must include VAT
            ImportoPagamento must be without VAT
            EsigibilitaIva of the Split payment tax must be 'S'
            The orgin_document fields must appear in the XML.
            Use reference validator: https://fex-app.com/servizi/inizia
        """
        invoice_etree = self._cleanup_etree(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.pa_partner_invoice))
        expected_etree = etree.fromstring(self.split_payment_invoice_content)
        self.assertXmlTreeEqual(invoice_etree, expected_etree)
