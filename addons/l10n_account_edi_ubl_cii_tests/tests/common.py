# -*- coding: utf-8 -*-
import base64

from freezegun import freeze_time
from collections import Counter
from os.path import join as opj

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields
from odoo.tools import misc

from lxml import etree


class TestUBLCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

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

        cls.move_template = cls.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>TemplateBody for <t t-out="object.name"></t><t t-out="object.invoice_user_id.signature or \'\'"></t></p>',
            'description': 'Sent to customers with their invoices in attachment',
            'email_from': "{{ (object.invoice_user_id.email_formatted or user.email_formatted) }}",
            'model_id': cls.env['ir.model']._get_id('account.move'),
            'name': "Invoice: Test Sending",
            'partner_to': "{{ object.partner_id.id }}",
            'subject': "{{ object.company_id.name }} Invoice (Ref {{ object.name or 'n/a' }})",
            'report_template_ids': [(4, cls.env.ref('account.account_invoices').id)],
            'lang': "{{ object.partner_id.lang }}",
        })

        # Fixed Taxes
        cls.recupel = cls.env['account.tax'].create({
            'name': "RECUPEL",
            'amount_type': 'fixed',
            'amount': 1,
            'include_base_amount': True,
            'sequence': 1,
        })
        cls.auvibel = cls.env['account.tax'].create({
            'name': "AUVIBEL",
            'amount_type': 'fixed',
            'amount': 1,
            'include_base_amount': True,
            'sequence': 2,
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        # OVERRIDE to force the company with EUR currency.
        eur = cls.env.ref('base.EUR')
        if not eur.active:
            eur.active = True

        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].write({
            'currency_id': eur.id,
            'invoice_is_ubl_cii': True,  # check the ubl_cii format by default in the send & print wizard
        })
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

    def _update_invoice_from_file(self, module_name, subfolder, filename, invoice):
        """ Create an attachment from a file and post it on the invoice
        """
        file_path = opj(module_name, subfolder, filename)
        with misc.file_open(file_path, 'rb', filter_ext=('.xml',)) as file:
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': base64.encodebytes(file.read()),
                'res_id': invoice.id,
                'res_model': 'account.move',
            })
            invoice.message_post(attachment_ids=[attachment.id])

    def _assert_imported_invoice_from_file(self, subfolder, filename, amount_total, amount_tax, list_line_subtotals,
                                           list_line_price_unit=None, list_line_discount=None, list_line_taxes=None,
                                           list_line_quantity=None,
                                           move_type='in_invoice', currency_id=None):
        """
        Create an empty account.move, update the file to fill its fields, asserts the currency, total and tax amounts
        are as expected.
        """
        if not currency_id:
            currency_id = self.env.ref('base.EUR').id

        # Create empty account.move, then update a file
        if move_type in self.env['account.move'].get_purchase_types():
            journal = self.company_data['default_journal_purchase']
        else:
            journal = self.company_data['default_journal_sale']

        invoice = self.env['account.move'].create({
            'move_type': move_type,
            'journal_id': journal.id,
        })

        invoice_count = len(self.env['account.move'].search([]))

        self._update_invoice_from_file(
            module_name='l10n_account_edi_ubl_cii_tests',
            subfolder=subfolder,
            filename=filename,
            invoice=invoice,
        )

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
        if list_line_quantity:
            self.assertEqual(invoice.invoice_line_ids.mapped('quantity'), list_line_quantity)

    # -------------------------------------------------------------------------
    # EXPORT HELPERS
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def _generate_move(self, seller, buyer, send=True, **invoice_kwargs):
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
            'invoice_payment_term_id': invoice_kwargs.get('invoice_payment_term_id', self.pay_terms_b.id),
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'narration': 'test narration',
            'ref': 'ref_move',
            **invoice_kwargs,
            'invoice_line_ids': [
                (0, 0, {
                    'sequence': i,
                    **invoice_line_kwargs,
                })
                for i, invoice_line_kwargs in enumerate(invoice_kwargs.get('invoice_line_ids', []))
            ],
        })

        account_move.action_post()
        if send:
            account_move._generate_pdf_and_send_invoice(self.move_template)
        return account_move

    def _assert_invoice_attachment(self, attachment, xpaths, expected_file_path):
        """
        Get attachment from a posted account.move, and asserts it's the same as the expected xml file.
        """
        self.assertTrue(attachment)

        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        xml_etree = self.get_xml_tree_from_string(xml_content)

        expected_file_full_path = misc.file_path(f'{self.test_module}/tests/test_files/{expected_file_path}')
        expected_etree = etree.parse(expected_file_full_path).getroot()

        modified_etree = self.with_applied_xpath(
            expected_etree,
            xpaths
        )

        self.assertXmlTreeEqual(
            xml_etree,
            modified_etree,
        )

        return attachment

    def _test_import_partner(self, attachment, seller, buyer):
        """
        Given a buyer and seller in an EDI attachment.
        * Uploading the attachment as an invoice should create an invoice with the partner = buyer.
        * Uploading the attachment as a vendor bill should create a bill with the partner = seller.
        """
        # Import attachment as an invoice
        new_invoice = self.company_data['default_journal_sale']._create_document_from_attachment(attachment.ids)
        self.assertEqual(buyer, new_invoice.partner_id)

        # Import attachment as a vendor bill
        new_invoice = self.company_data['default_journal_purchase']._create_document_from_attachment(attachment.ids)
        self.assertEqual(seller, new_invoice.partner_id)

    def _test_import_in_journal(self, attachment):
        """
        If the context contains the info about the current default journal, we should use it
        instead of infering the journal from the move type.
        """
        journal2 = self.company_data['default_journal_sale'].copy()
        journal2.default_account_id = self.company_data['default_account_revenue'].id
        journal3 = journal2.copy()
        journal3.default_account_id = self.company_data['default_account_revenue'].id  # Not copied

        # Use the journal if it's set
        new_invoice = journal2._create_document_from_attachment(attachment.id)
        self.assertEqual(new_invoice.journal_id, journal2)

        # If no journal, fallback on the context
        new_invoice2 = self.env['account.journal'].with_context(default_journal_id=journal3.id)._create_document_from_attachment(attachment.id)
        self.assertEqual(new_invoice2.journal_id, journal3)

        # If no journal and no journal in the context, fallback on the move type
        new_invoice3 = self.env['account.journal'].with_context(default_move_type='out_invoice')._create_document_from_attachment(attachment.id)
        self.assertEqual(new_invoice3.journal_id, self.company_data['default_journal_sale'])

    def _test_encoding_in_attachment(self, attachment, filename):
        """
        Generate an invoice, assert that the tag '<?xml version='1.0' encoding='UTF-8'?>' is present in the attachment
        """
        self.assertTrue(filename in attachment.name)
        self.assertIn(b"<?xml version='1.0' encoding='UTF-8'?>", attachment.raw)
