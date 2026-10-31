# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.tests.common import tagged
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nHuEdiInvoiceLayouts(L10nHuEdiTestCommon):

    LAYOUTS = ('standard', 'bubble', 'wave', 'folder', 'center', 'dual', 'lines', 'compact')

    def _render_texts(self, move):
        """ Return the text of the layout header and of the whole report. """
        report = html.fromstring(self.env['ir.actions.report']._render_qweb_html('account.account_invoices', move.ids)[0])
        header = report.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' header ')]")
        header_text = ' '.join(' '.join(node.text_content() for node in header).split())
        return header_text, ' '.join(report.text_content().split())

    def test_invoice_company_details_in_layout_header(self):
        """ The Hungarian company details replace the company address of every document layout,
        which keeps its own header, and the customer is printed whatever the layout. """
        customer = self.env['res.partner'].create({
            'name': 'Client Francais SARL',
            'is_company': True,
            'street': '3 Rue du Test',
            'zip': '37130',
            'city': 'Langeais',
            'country_id': self.env.ref('base.fr').id,
        })
        bank_account = self.env['res.partner.bank'].create({
            'account_number': 'HU23 1176 3419 0608 7887 0000 0000',
            'partner_id': self.company_data['company'].partner_id.id,
            'allow_out_payment': True,
        })
        invoice = self.create_invoice_simple()
        invoice.write({'partner_id': customer.id, 'partner_bank_id': bank_account.id})
        invoice.action_post()

        for layout in self.LAYOUTS:
            with self.subTest(layout=layout):
                self.env.company.external_report_layout_id = self.env.ref(f'web.external_layout_{layout}')
                header_text, report_text = self._render_texts(invoice)
                self.assertIn('EU Tax ID: HU27725414', header_text)
                self.assertIn('Bank Account: HU23 1176 3419 0608 7887 0000 0000', header_text)
                self.assertIn('3 Rue du Test', report_text)
                self.assertNotIn('Supplier:', report_text)

    def test_bill_keeps_party_labels(self):
        """ On a vendor bill the company in the header is the customer: keep the labels. """
        bill = self.create_bill_simple()
        bill.action_post()
        for layout in ('standard', 'center'):
            with self.subTest(layout=layout):
                self.env.company.external_report_layout_id = self.env.ref(f'web.external_layout_{layout}')
                header_text, report_text = self._render_texts(bill)
                self.assertIn('Customer:', header_text)
                self.assertIn('Supplier:', report_text)
