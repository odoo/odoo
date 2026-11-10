from lxml import html

from odoo import Command
from odoo.tests import tagged

from .common import L10nInTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestInvoiceReport(L10nInTestInvoicingCommon):

    def _render_invoice(self, invoice, report='account.account_invoices'):
        content, _ = self.env['ir.actions.report']._render_qweb_html(report, invoice.ids)
        return html.fromstring(content)

    def test_party_details_in_all_layouts(self):
        self.env.user.group_ids = [Command.link(self.env.ref('account.group_delivery_invoice_address').id)]
        self.invoice_a.partner_shipping_id = self.partner_b
        for layout in self.env['report.layout'].search([]):
            with self.subTest(layout=layout.name):
                self.default_company.external_report_layout_id = layout.view_id
                document = self._render_invoice(self.invoice_a)
                parties = document.xpath('//table[@name="l10n_in_party_details"]')
                self.assertEqual(len(parties), 1)
                self.assertIn('Bill To (Buyer)', parties[0].text_content())
                self.assertIn('Ship To (Consignee)', parties[0].text_content())
                self.assertIn(self.partner_a.vat, parties[0].text_content())
                self.assertIn(self.partner_b.vat, parties[0].text_content())
                self.assertEqual(len(document.xpath('//div[@id="partner_vat_address_not_same_as_shipping"]')), 1)
                self.assertTrue(document.xpath('//div[@name="l10n_in_place_of_supply"]'))
                references = document.xpath('//td[@name="l10n_in_header_references"]')
                self.assertEqual(len(references), 1)
                self.assertEqual(len(references[0].xpath('.//table[@name="l10n_in_reference_table"]')), 1)
                self.assertFalse(references[0].xpath('.//div[@id="informations"]'))
                self.assertEqual(len(document.xpath('//div[@id="informations"]')), 1)
                self.assertIn('Invoice No.', references[0].text_content())
                self.assertTrue(references[0].xpath('.//td[@name="invoice_date"]'))
                self.assertFalse(document.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " header ")]'))
                supplier = document.xpath('//div[@name="l10n_in_supplier"]')
                self.assertEqual(len(supplier), 1)
                self.assertIn(self.default_company.vat, supplier[0].text_content())
                self.assertTrue(supplier[0].xpath('ancestor::tr[1]/td[@name="l10n_in_header_references"]'))
                self.assertEqual(len(document.xpath('//h2')), 1)
                self.assertEqual(document.get('data-report-margin-top'), '12')
                layout_name = layout.view_id.key.split('external_layout_')[-1]
                artwork = document.xpath('//div[@name="l10n_in_header_design"]/*[local-name()="svg"]')
                if layout_name in ('bubble', 'wave', 'folder', 'dual', 'lines'):
                    self.assertEqual(len(artwork), 1)
                    self.assertEqual(artwork[0].get('name'), f'l10n_in_art_{layout_name}')
                else:
                    self.assertFalse(artwork)
                # The HSN summary belongs before totals, independently of the company layout.
                summary = document.xpath('//div[@name="l10n_in_hsn_summary"]')[0]
                self.assertTrue(summary.xpath('following-sibling::div[@id="right-elements"]'))

    def test_commercial_reference_positions(self):
        self.invoice_a.write({'ref': 'BUYER-PO-42', 'invoice_origin': 'SUPPLIER-SO-19'})
        document = self._render_invoice(self.invoice_a)
        table = document.xpath('//table[@name="l10n_in_reference_table"]')[0]
        self.assertEqual([row.get('name') for row in table.xpath('tbody/tr')], [
            'l10n_in_invoice_reference_row', 'l10n_in_delivery_payment_row',
            'l10n_in_supplier_reference_row', 'l10n_in_buyer_order_row',
            'l10n_in_dispatch_reference_row', 'l10n_in_dispatch_destination_row',
            'l10n_in_delivery_terms_row',
        ])
        self.assertIn('SUPPLIER-SO-19', table.xpath('.//td[@name="l10n_in_supplier_reference"]')[0].text_content())
        self.assertIn('BUYER-PO-42', table.xpath('.//td[@name="l10n_in_buyer_order"]')[0].text_content())
        # Unknown delivery references and buyer PO dates retain their cells, without guessed values.
        for name in ('l10n_in_delivery_note', 'l10n_in_buyer_order_date', 'l10n_in_dispatch_document'):
            self.assertFalse(table.xpath(f'.//td[@name="{name}"]/div')[0].text_content().strip())
        self.assertEqual(table.xpath('.//td[@name="l10n_in_payment_terms"]/strong/text()'), ['Mode/Terms of Payment'])

    def test_vendor_reference_is_not_a_buyer_order(self):
        bill = self.init_invoice('in_invoice', partner=self.partner_a, amounts=[100])
        bill.ref = 'VENDOR-INVOICE-42'
        values = bill._l10n_in_get_invoice_report_header_values()
        self.assertEqual(values['supplier_reference'], 'VENDOR-INVOICE-42')
        self.assertFalse(values['buyer_order_no'])

    def test_credit_note_keeps_original_buyer_order(self):
        self.invoice_a.write({'ref': 'BUYER-PO-42', 'invoice_origin': 'SUPPLIER-SO-19'})
        self.invoice_a.action_post()
        credit = self.invoice_a._reverse_moves(default_values_list=[{'ref': 'Damaged items'}])
        values = credit._l10n_in_get_invoice_report_header_values()
        self.assertEqual(values['buyer_order_no'], 'BUYER-PO-42')
        self.assertEqual(values['supplier_reference'], 'SUPPLIER-SO-19')
        self.assertEqual(values['other_references'], 'Damaged items')

    def test_standard_report_keeps_layout_header(self):
        for layout in self.env['report.layout'].search([]):
            with self.subTest(layout=layout.name):
                self.default_company.external_report_layout_id = layout.view_id
                content = self.env['ir.qweb']._render('account.report_invoice_document', {
                    'o': self.invoice_a, 'lang': 'en_US', 'report_type': 'html', 'print_with_payments': False,
                })
                document = html.fromstring(content)
                self.assertEqual(len(document.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " header ")]')), 1)
                self.assertFalse(document.xpath('//div[@name="l10n_in_supplier"]'))

    def test_sections_and_serial_numbers(self):
        self.invoice_a.invoice_line_ids = [
            Command.clear(),
            Command.create({'display_type': 'line_section', 'name': 'Components', 'sequence': 1}),
            Command.create({'product_id': self.product_a.id, 'quantity': 2, 'price_unit': 100, 'sequence': 2,
                            'tax_ids': [Command.set(self.sgst_sale_18.ids)]}),
            Command.create({'display_type': 'line_note', 'name': 'Checked before dispatch', 'sequence': 3}),
            Command.create({'product_id': self.product_b.id, 'quantity': 1, 'price_unit': 200, 'sequence': 4,
                            'tax_ids': [Command.set(self.sgst_sale_18.ids)]}),
        ]
        document = self._render_invoice(self.invoice_a)
        serials = document.xpath('//td[@name="td_l10n_in_serial"]/span/text()')
        self.assertEqual(serials, ['1', '2'])
        table = document.xpath('//table[@name="invoice_line_table"]')[0]
        column_count = len(table.xpath('thead/tr/th'))
        section = table.xpath('.//td[@name="line_name_td"]')[0]
        self.assertEqual(int(section.get('colspan')) + 1, column_count)

    def test_copy_labels(self):
        document = self._render_invoice(self.invoice_a, 'l10n_in.l10n_in_account_invoices_triplicate')
        copies = document.xpath('//div[@name="l10n_in_copy_title"]')
        self.assertEqual([copy.text_content().strip() for copy in copies], [
            'ORIGINAL FOR RECIPIENT', 'DUPLICATE FOR TRANSPORTER', 'TRIPLICATE FOR SUPPLIER',
        ])
