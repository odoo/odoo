# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.tests.common import tagged
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class L10nHuEdiTestInvoiceReport(L10nHuEdiTestCommon):

    def _render_invoice_report(self, invoice):
        report_html = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)[0]
        return html.fromstring(report_html)

    @staticmethod
    def _get_texts(nodes):
        return [' '.join(node.text_content().split()) for node in nodes]

    def test_invoice_report_supplier_block_width(self):
        """ The supplier block is rendered inside the information block of web.address_layout,
        which is already a col-6: it must not be wrapped in another col-6. """
        invoice = self.create_invoice_simple()
        report = self._render_invoice_report(invoice)

        supplier_blocks = report.xpath("//div[@name='information_block']/div")
        self.assertEqual(len(supplier_blocks), 1)
        self.assertNotIn('col-6', supplier_blocks[0].get('class') or '')
        self.assertNotIn('float-start', supplier_blocks[0].find_class('company_address')[0].get('class'))

    def test_invoice_report_group_tax_id_labels(self):
        """ l10n_hu_group_vat is the tax number of the VAT group, the partner's own VAT
        is its group member tax number. """
        self.company_data['company'].partner_id.l10n_hu_group_vat = '17781774-5-44'
        invoice = self.create_invoice_simple()
        invoice.partner_id = self.partner_group_company_1
        report = self._render_invoice_report(invoice)

        supplier_texts = self._get_texts(report.xpath("//div[@name='information_block']//li"))
        self.assertIn('Group Tax ID: 17781774-5-44', supplier_texts)
        self.assertIn('Group Member Tax ID: 27725414-2-13', supplier_texts)

        customer_texts = self._get_texts(report.xpath("//div[starts-with(@id, 'partner_vat_')]/../div"))
        self.assertIn('Group Member Tax ID: 10625790-4-44', customer_texts)
        self.assertIn('Group Tax ID: 17781774-5-44', customer_texts)
