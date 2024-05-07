# -*- coding: utf-8 -*-
import base64
from lxml import etree

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLBE(TestUBLCommon):

    @classmethod
    def setUpClass(cls,
                   chart_template_ref="l10n_be.l10nbe_chart_template",
                   edi_format_ref="account_edi_ubl_cii.ubl_bis3",
                   ):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # seller
        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Chaussée de Namur 40",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0202239951',
            'country_id': cls.env.ref('base.be').id,
            'bank_ids': [(0, 0, {'acc_number': 'BE15001559627230'})],
            'ref': 'ref_partner_1',
        })

        # buyer
        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
            'bank_ids': [(0, 0, {'acc_number': 'BE90735788866632'})],
            'ref': 'ref_partner_2',
        })

        cls.tax_25 = cls.env['account.tax'].create({
            'name': 'tax_25',
            'amount_type': 'percent',
            'amount': 25,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.be').id,
            'sequence': 10,
        })

        cls.tax_15 = cls.env['account.tax'].create({
            'name': 'tax_15',
            'amount_type': 'percent',
            'amount': 15,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_12 = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_0 = cls.env['account.tax'].create({
            'name': 'tax_0',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.acc_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE15001559627231',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': cls.journal.id,
            'partner_id': cls.partner_1.id,
            'partner_bank_id': cls.acc_bank,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'product_uom_id': cls.env.ref('uom.product_uom_dozen').id,
                'price_unit': 275.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls.tax_21.ids)],
            })],
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template):
        # OVERRIDE
        # to force the company to be belgian
        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.be").id,
            vat="BE0246697724")
        return res

    ####################################################
    # Test export - import
    ####################################################

    def test_export_import_invoice(self):
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
            ],
        )
        xml_etree, xml_filename = self._assert_invoice_attachment(
            invoice,
            xpaths='''
                <xpath expr="./*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][1]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][2]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][3]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
            ''',
            expected_file='from_odoo/bis3_out_invoice.xml',
        )
        self.assertEqual(xml_filename[-12:], "ubl_bis3.xml")  # ensure we test the right format !
        self._assert_imported_invoice_from_etree(invoice, xml_etree, xml_filename)

    def test_export_import_refund(self):
        refund = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_refund',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
            ],
        )
        xml_etree, xml_filename = self._assert_invoice_attachment(
            refund,
            xpaths='''
                <xpath expr="./*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr="./*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][1]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][2]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][3]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
            ''',
            expected_file='from_odoo/bis3_out_refund.xml',
        )
        self.assertEqual(xml_filename[-12:], "ubl_bis3.xml")
        self._assert_imported_invoice_from_etree(refund, xml_etree, xml_filename)

    def test_encoding_in_attachment_ubl(self):
        self._test_encoding_in_attachment('ubl_bis3', 'INV_2017_00002_ubl_bis3.xml')

    def test_sending_to_public_admin(self):
        """ A public administration has no VAT, but has an arbitrary number (see:
        https://pch.gouvernement.lu/fr/peppol.html). When a partner has no VAT, the node PartyTaxScheme should
        not appear.
        NB: The `EndpointID` node should be filled with this arbitrary number, that is why `l10n_lu_peppol_id`
        module was created. However we cannot use it here because it would require adding it to the dependencies of
        `l10n_account_edi_ubl_cii_tests` in stable.
        """
        self.partner_2.vat = None
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2,
                    'price_unit': 100,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                }
            ],
        )
        self._assert_invoice_attachment(
            invoice,
            xpaths='''
                <xpath expr="./*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr="./*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][1]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
            ''',
            expected_file='from_odoo/bis3_out_invoice_public_admin.xml',
        )

    def test_rounding_price_unit(self):
        """ OpenPeppol states that:
        * All document level amounts shall be rounded to two decimals for accounting
        * Invoice line net amount shall be rounded to two decimals
        See: https://docs.peppol.eu/poacc/billing/3.0/bis/#_rounding
        Do not round the unit prices. It allows to obtain the correct line amounts when prices have more than 2
        digits.
        """
        # Set the allowed number of digits for the price_unit
        decimal_precision = self.env['decimal.precision'].search([('name', '=', 'Product Price')], limit=1)
        self.assertTrue(bool(decimal_precision), "The decimal precision for Product Price is required for this test")
        decimal_precision.digits = 4

        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 10000,
                    'price_unit': 0.4567,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                }
            ],
        )
        self._assert_invoice_attachment(invoice, None, 'from_odoo/bis3_out_invoice_rounding.xml')

    def test_export_with_fixed_taxes_case1(self):
        # CASE 1: simple invoice with a recupel tax
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 99,
                    'tax_ids': [(6, 0, [self.recupel.id, self.tax_21.id])],
                }
            ],
        )
        self.assertEqual(invoice.amount_total, 121)
        self._assert_invoice_attachment(invoice, None, 'from_odoo/bis3_ecotaxes_case1.xml')

    def test_export_with_fixed_taxes_case2(self):
        # CASE 2: Same but with several ecotaxes
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 98,
                    'tax_ids': [(6, 0, [self.recupel.id, self.auvibel.id, self.tax_21.id])],
                }
            ],
        )
        self.assertEqual(invoice.amount_total, 121)
        self._assert_invoice_attachment(invoice, None, 'from_odoo/bis3_ecotaxes_case2.xml')

    def test_export_with_fixed_taxes_case3(self):
        # CASE 3: same as Case 1 but taxes are Price Included
        self.recupel.price_include = True
        self.tax_21.price_include = True

        # Price TTC = 121 = (99 + 1 ) * 1.21
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 121,
                    'tax_ids': [(6, 0, [self.recupel.id, self.tax_21.id])],
                }
            ],
        )
        self.assertEqual(invoice.amount_total, 121)
        self._assert_invoice_attachment(invoice, None, 'from_odoo/bis3_ecotaxes_case3.xml')

    def test_export_with_fixed_taxes_case4(self):
        """ CASE 4: simple invoice with a recupel tax + discount
        1) Subtotal (price after discount, without taxes): 99 * 2 * (1-0.9) = 178.2
        2) Taxes:
            - recupel = 2
            - VAT = (178.2 + 2) * 0.21 = 37.842
        3) Total = 178.2 + 2 + 37.842 = 218.042
        """
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2,
                    'discount': 10,
                    'price_unit': 99,
                    'tax_ids': [(6, 0, [self.recupel.id, self.tax_21.id])],
                }
            ],
        )
        self.assertEqual(invoice.amount_total, 218.042)
        self._assert_invoice_attachment(invoice, None, 'from_odoo/bis3_ecotaxes_case4.xml')

    def test_export_rounding_price_amount(self):
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {'quantity': 3, 'price_unit': 102.15},
                {'quantity': 3, 'price_unit': 83.60},
            ],
        )
        attachment = invoice._get_edi_attachment(self.edi_format)
        price_amounts = etree.fromstring(attachment.raw).findall('.//{*}InvoiceLine/{*}Price/{*}PriceAmount')
        self.assertEqual(price_amounts[0].text, '102.15')
        self.assertEqual(price_amounts[1].text, '83.6')

    def test_export_tax_exempt(self):
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'price_unit': 990.0,
                    'tax_ids': [(6, 0, self.tax_0.ids)],
                },
            ],
        )
        self._assert_invoice_attachment(invoice, None, 'from_odoo/bis3_out_invoice_tax_exempt.xml')

    ####################################################
    # Test import
    ####################################################

    def test_import_partner_ubl(self):
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
        new_invoice = self._import_invoice_attachment(invoice, 'ubl_bis3', self.company_data['default_journal_sale'])
        self.assertEqual(self.partner_2, new_invoice.partner_id)

        new_invoice = self._import_invoice_attachment(invoice, 'ubl_bis3', self.company_data['default_journal_purchase'])
        self.assertEqual(self.partner_1, new_invoice.partner_id)

    def test_import_and_create_partner_ubl(self):
        """ Tests whether the partner is created at import if no match is found when decoding the EDI attachment
        """
        partner_vals = {
            'name': "Buyer",
            'mail': "buyer@yahoo.com",
            'phone': "1111",
            'vat': "BE980737405",
        }
        # assert there is no matching partner
        partner_match = self.env['account.edi.format']._retrieve_partner(**partner_vals)
        self.assertFalse(partner_match)

        # Import attachment as an invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        self.update_invoice_from_file(
            module_name='l10n_account_edi_ubl_cii_tests',
            subfolder='tests/test_files/from_odoo',
            filename='ubl_test_import_partner.xml',
            invoice=invoice)

        # assert a new partner has been created
        partner_vals['email'] = partner_vals.pop('mail')
        self.assertRecordValues(invoice.partner_id, [partner_vals])

    def test_import_export_invoice_xml(self):
        """
        Test whether the elements only specific to ubl_be are correctly exported
        and imported in the xml file
        """
        self.invoice.action_post()
        attachment = self.invoice._get_edi_attachment(self.edi_format)
        self.assertTrue(attachment)
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        xml_etree = self.get_xml_tree_from_string(xml_content)

        self.assertEqual(
            xml_etree.find('{*}ProfileID').text,
            'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'
        )
        self.assertEqual(
            xml_etree.find('{*}CustomizationID').text,
            'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0'
        )
        # Export: in bis3, under Country, the Name element should not appear, but IdentificationCode still should
        self.assertIsNotNone(xml_etree.find('.//{*}Country/{*}IdentificationCode'))
        self.assertIsNone(xml_etree.find('.//{*}Country/{*}Name'))

        # Import:
        created_bill = self.env['account.move'].create({'move_type': 'in_invoice'})
        created_bill.message_post(attachment_ids=[attachment.id])
        self.assertTrue(created_bill)

    def test_import_invoice_xml(self):
        kwargs = {
            'subfolder': 'tests/test_files/from_odoo',
            'amount_total': 3164.22,
            'amount_tax': 482.22,
            'list_line_subtotals': [1782, 1000, -100],
            'list_line_price_unit': [990, 100, 100],
            'list_line_discount': [10, 0, 0],
            'currency_id': self.currency_data['currency'].id,
        }
        self._assert_imported_invoice_from_file(filename='bis3_out_invoice.xml', **kwargs)
        # same as the file above, but the <cac:Price> are missing in the invoice lines
        self._assert_imported_invoice_from_file(filename='bis3_out_invoice_no_prices.xml', **kwargs)

    def test_import_invoice_xml_open_peppol_examples(self):
        # Source: https://github.com/OpenPEPPOL/peppol-bis-invoice-3/tree/master/rules/examples
        subfolder = 'tests/test_files/from_peppol-bis-invoice-3_doc'
        # source: Allowance-example.xml
        self._assert_imported_invoice_from_file(subfolder=subfolder, filename='bis3_allowance.xml', amount_total=7125,
            amount_tax=1225, list_line_subtotals=[200, -200, 4000, 1000, 900])
        # source: base-creditnote-correction.xml
        self._assert_imported_invoice_from_file(subfolder=subfolder, filename='bis3_credit_note.xml',
            amount_total=1656.25, amount_tax=331.25, list_line_subtotals=[25, 2800, -1500], move_type='in_refund')
        # source: base-negative-inv-correction.xml
        self._assert_imported_invoice_from_file(subfolder=subfolder, filename='bis3_invoice_negative_amounts.xml',
            amount_total=1656.25, amount_tax=331.25, list_line_subtotals=[25, 2800, -1500], move_type='in_refund')
        # source: vat-category-E.xml
        self._assert_imported_invoice_from_file(subfolder=subfolder, filename='bis3_tax_exempt_gbp.xml',
            amount_total=1200, amount_tax=0, list_line_subtotals=[1200], currency_id=self.env.ref('base.GBP').id)

    def test_import_existing_invoice_flip_move_type(self):
        """ Tests whether the move_type of an existing invoice can be flipped when importing an attachment
        For instance: with an email alias to create account_move, first the move is created (using alias_defaults,
        which contains move_type = 'out_invoice') then the attachment is decoded, if it represents a credit note,
        the move type needs to be changed to 'out_refund'
        """
        invoice = self.env['account.move'].create({'move_type': 'out_invoice'})
        self.update_invoice_from_file(
            'l10n_account_edi_ubl_cii_tests',
            'tests/test_files/from_odoo',
            'bis3_out_refund.xml',
            invoice,
        )
        self.assertRecordValues(invoice, [{'move_type': 'out_refund', 'amount_total': 3164.22}])

    def test_import_fixed_taxes(self):
        """ Tests whether we correctly decode the xml attachments created using fixed taxes.
        See the tests above to create these xml attachments ('test_export_with_fixed_taxes_case_[X]').
        NB: use move_type = 'out_invoice' s.t. we can retrieve the taxes used to create the invoices.
        """
        subfolder = "tests/test_files/from_odoo"
        # The tax 21% from l10n_be is retrieved since it's a duplicate of self.tax_21
        tax_21 = self.env.ref(f'l10n_be.{self.env.company.id}_attn_VAT-OUT-21-L')
        self._assert_imported_invoice_from_file(
            subfolder=subfolder, filename='bis3_ecotaxes_case1.xml', amount_total=121, amount_tax=22,
            list_line_subtotals=[99], currency_id=self.currency_data['currency'].id, list_line_price_unit=[99],
            list_line_discount=[0], list_line_taxes=[tax_21+self.recupel], move_type='out_invoice',
        )
        self._assert_imported_invoice_from_file(
            subfolder=subfolder, filename='bis3_ecotaxes_case2.xml', amount_total=121, amount_tax=23,
            list_line_subtotals=[98], currency_id=self.currency_data['currency'].id, list_line_price_unit=[98],
            list_line_discount=[0], list_line_taxes=[tax_21+self.recupel+self.auvibel], move_type='out_invoice',
        )
        self._assert_imported_invoice_from_file(
            subfolder=subfolder, filename='bis3_ecotaxes_case3.xml', amount_total=121, amount_tax=22,
            list_line_subtotals=[99], currency_id=self.currency_data['currency'].id, list_line_price_unit=[99],
            list_line_discount=[0], list_line_taxes=[tax_21+self.recupel], move_type='out_invoice',
        )
        self._assert_imported_invoice_from_file(
            subfolder=subfolder, filename='bis3_ecotaxes_case4.xml', amount_total=218.042, amount_tax=39.842,
            list_line_subtotals=[178.2], currency_id=self.currency_data['currency'].id, list_line_price_unit=[99],
            list_line_discount=[10], list_line_taxes=[tax_21+self.recupel], move_type='out_invoice',
        )

    def test_inverting_negative_price_unit(self):
        """ We can not have negative unit prices, so we try to invert the unit price and quantity.
        """
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': -25.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                }
            ],
        )
        self._assert_invoice_attachment(invoice, None, 'from_odoo/bis3_out_invoice_negative_unit_price.xml')
