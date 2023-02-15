# -*- coding: utf-8 -*-
import base64

from freezegun import freeze_time
from collections import Counter

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo import fields
from odoo.modules.module import get_resource_path
from odoo.tests import tagged
from lxml import etree


class TestUBLCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # Required for `product_uom_id` to be visible in the form views
        cls.env.user.groups_id += cls.env.ref('uom.group_uom')

        # Ensure the testing currency is using a valid ISO code.
        real_usd = cls.env.ref('base.USD')
        real_usd.name = 'FUSD'
        real_usd.flush_model(['name'])
        cls.currency_data['currency'].name = 'USD'

        # remove this tax, otherwise, at import, this tax with children taxes can be selected and the total is wrong
        cls.tax_armageddon.children_tax_ids.unlink()
        cls.tax_armageddon.unlink()

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        # OVERRIDE to force the company with EUR currency.
        eur = cls.env.ref('base.EUR')
        if not eur.active:
            eur.active = True

        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].currency_id = eur
        return res

    def assert_same_invoice(self, invoice1, invoice2, **invoice_kwargs):
        self.assertEqual(len(invoice1.invoice_line_ids), len(invoice2.invoice_line_ids))
        self.assertRecordValues(invoice2, [{
            'partner_id': invoice1.partner_id.id,
            'invoice_date': fields.Date.from_string(invoice1.date),
            'currency_id': invoice1.currency_id.id,
            'amount_untaxed': invoice1.amount_untaxed,
            'amount_tax': invoice1.amount_tax,
            'amount_total': invoice1.amount_total,
            **invoice_kwargs,
        }])

        default_invoice_line_kwargs_list = [{}] * len(invoice1.invoice_line_ids)
        invoice_line_kwargs_list = invoice_kwargs.get('invoice_line_ids', default_invoice_line_kwargs_list)
        self.assertRecordValues(invoice2.invoice_line_ids, [{
            'quantity': line.quantity,
            'price_unit': line.price_unit,
            'discount': line.discount,
            'product_id': line.product_id.id,
            'product_uom_id': line.product_uom_id.id,
            **invoice_line_kwargs,
        } for line, invoice_line_kwargs in zip(invoice1.invoice_line_ids, invoice_line_kwargs_list)])

    # -------------------------------------------------------------------------
    # IMPORT HELPERS
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def _assert_imported_invoice_from_etree(self, invoice, attachment):
        """
        Create an account.move directly from an xml file, asserts the invoice obtained is the same as the expected
        invoice.
        """
        # /!\ use the same journal as the invoice's one to import the attachment !
        invoice.journal_id.create_document_from_attachment(attachment.ids)
        new_invoice = self.env['account.move'].search([], order='id desc', limit=1)

        self.assertTrue(new_invoice)
        self.assert_same_invoice(invoice, new_invoice)

    def _assert_imported_invoice_from_file(self, subfolder, filename, amount_total, amount_tax, list_line_subtotals,
                                           list_line_price_unit=None, list_line_discount=None, list_line_taxes=None,
                                           move_type='in_invoice', currency_id=None):
        """
        Create an empty account.move, update the file to fill its fields, asserts the currency, total and tax amounts
        are as expected.
        """
        if not currency_id:
            currency_id = self.env.ref('base.EUR').id

        # Create empty account.move, then update a file
        if move_type == 'in_invoice':
            invoice = self._create_empty_vendor_bill()
        else:
            invoice = self.env['account.move'].create({
                'move_type': move_type,
                'journal_id': self.company_data['default_journal_purchase'].id,
            })
        invoice_count = len(self.env['account.move'].search([]))

        # Import the file to fill the empty invoice
        self.update_invoice_from_file('l10n_account_edi_ubl_cii_tests', subfolder, filename, invoice)

        # Checks
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertRecordValues(invoice, [{
            'amount_total': amount_total,
            'amount_tax': amount_tax,
            'currency_id': currency_id,
        }])
        self.assertEqual(
            Counter(invoice.invoice_line_ids.mapped('price_subtotal')),
            Counter(list_line_subtotals),
        )
        if list_line_price_unit:
            self.assertEqual(invoice.invoice_line_ids.mapped('price_unit'), list_line_price_unit)
        if list_line_discount:
            # See test_import_tax_included: sometimes, it's impossible to retrieve the exact discount at import because
            # of rounding during export. The obtained discount might be 10.001 while the expected is 10.
            dp = self.env.ref('product.decimal_discount').precision_get("Discount")
            self.assertEqual([round(d, dp) for d in invoice.invoice_line_ids.mapped('discount')], list_line_discount)
        if list_line_taxes:
            for line, taxes in zip(invoice.invoice_line_ids, list_line_taxes):
                self.assertEqual(line.tax_ids, taxes)

    # -------------------------------------------------------------------------
    # EXPORT HELPERS
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def _generate_move(self, seller, buyer, **invoice_kwargs):
        """
        Create and post an account.move.
        """
        # Setup the seller.
        self.env.company.write({
            'partner_id': seller.id,
            'name': seller.name,
            'street': seller.street,
            'zip': seller.zip,
            'city': seller.city,
            'vat': seller.vat,
            'country_id': seller.country_id.id,
        })

        move_type = invoice_kwargs['move_type']
        account_move = self.env['account.move'].create({
            'partner_id': buyer.id,
            'partner_bank_id': (seller if move_type == 'out_invoice' else buyer).bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_origin': 'test invoice origin',
            'narration': 'test narration',
            **invoice_kwargs,
            'invoice_line_ids': [
                (0, 0, {
                    'sequence': i,
                    **invoice_line_kwargs,
                })
                for i, invoice_line_kwargs in enumerate(invoice_kwargs.get('invoice_line_ids', []))
            ],
        })
        # this is needed for formats not enabled by default on the journal
        account_move.journal_id.edi_format_ids += self.edi_format
        account_move.action_post()
        return account_move

    def _assert_invoice_attachment(self, invoice, xpaths, expected_file):
        """
        Get attachment from a posted account.move, and asserts it's the same as the expected xml file.
        """
        attachment = invoice._get_edi_attachment(self.edi_format)
        self.assertTrue(attachment)
        xml_filename = attachment.name
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        xml_etree = self.get_xml_tree_from_string(xml_content)

        expected_file_path = get_resource_path('l10n_account_edi_ubl_cii_tests', 'tests/test_files', expected_file)
        expected_etree = etree.parse(expected_file_path).getroot()

        modified_etree = self.with_applied_xpath(
            expected_etree,
            xpaths
        )

        self.assertXmlTreeEqual(
            xml_etree,
            modified_etree,
        )

        return attachment

    def _test_import_partner(self, edi_code, filename):
        """
        Given an invoice where partner_1 is the vendor and partner_2 is the customer with an EDI attachment.
        * Uploading the attachment as an invoice should create an invoice with the buyer = partner_2.
        * Uploading the attachment as a vendor bill should create a bill with the vendor = partner_1.
        """
        invoice = self._generate_move(
            seller=self.partner_1,
            buyer=self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[{'product_id': self.product_a.id}],
        )
        edi_attachment = invoice.edi_document_ids.filtered(
            lambda doc: doc.edi_format_id.code == edi_code).attachment_id
        self.assertEqual(edi_attachment.name, filename)
        edi_etree = self.get_xml_tree_from_string(edi_attachment.raw)

        # Import attachment as an invoice
        new_invoice = self.edi_format._create_invoice_from_xml_tree(
            filename='test_filename',
            tree=edi_etree,
            journal=self.env['account.journal'].search(
                [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1)
        )
        self.assertEqual(self.partner_2, new_invoice.partner_id)

        # Import attachment as a vendor bill
        new_invoice = self.edi_format._create_invoice_from_xml_tree(
            filename='test_filename',
            tree=edi_etree,
            journal=self.env['account.journal'].search(
                [('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)], limit=1)
        )
        self.assertEqual(self.partner_1, new_invoice.partner_id)

    def _test_encoding_in_attachment(self, edi_code, filename):
        """
        Generate an invoice, assert that the tag '<?xml version='1.0' encoding='UTF-8'?>' is present in the attachment
        """
        invoice = self._generate_move(
            seller=self.partner_1,
            buyer=self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[{'product_id': self.product_a.id}],
        )
        edi_attachment = invoice.edi_document_ids.filtered(
            lambda doc: doc.edi_format_id.code == edi_code).attachment_id
        self.assertEqual(edi_attachment.name, filename)
        self.assertIn(b"<?xml version='1.0' encoding='UTF-8'?>", edi_attachment.raw)
