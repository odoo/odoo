# -*- coding: utf-8 -*-

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCIIFR(TestUBLCommon):

    @classmethod
    def setUpClass(cls,
                   chart_template_ref="l10n_fr.l10n_fr_pcg_chart_template",
                   edi_format_ref="account_edi_ubl_cii.edi_facturx_1_0_05",
                   ):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Rue Jean Jaurès, 42",
            'zip': "75000",
            'city': "Paris",
            'vat': 'FR05677404089',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR15001559627230'})],
            'phone': '+1 (650) 555-0111',
            'email': "partner1@yourcompany.com",
            'ref': 'ref_partner_1',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Rue Charles de Gaulle",
            'zip': "52330",
            'city': "Colombey-les-Deux-Églises",
            'vat': 'FR35562153452',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR90735788866632'})],
            'ref': 'ref_partner_2',
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.fr').id,
            'sequence': 10,
        })

        cls.tax_12 = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.tax_21_purchase = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.tax_12_purchase = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.tax_5_purchase = cls.env['account.tax'].create({
            'name': 'tax_5',
            'amount_type': 'percent',
            'amount': 5,
            'type_tax_use': 'purchase',
        })

        cls.tax_0_purchase = cls.env['account.tax'].create({
            'name': 'tax_0',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'purchase',
        })

        cls.tax_5 = cls.env['account.tax'].create({
            'name': 'tax_5',
            'amount_type': 'percent',
            'amount': 5,
            'type_tax_use': 'sale',
        })

        cls.tax_5_incl = cls.env['account.tax'].create({
            'name': 'tax_5_incl',
            'amount_type': 'percent',
            'amount': 5,
            'type_tax_use': 'sale',
            'price_include': True,
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template):
        # OVERRIDE
        # to force the company to be french
        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.fr").id,
            phone='+1 (650) 555-0111',  # [BR-DE-6] "Seller contact telephone number" (BT-42) is required
            email="info@yourcompany.com",  # [BR-DE-7] The element "Seller contact email address" (BT-43) is required
        )
        return res

    ####################################################
    # Test export - import
    ####################################################

    def test_export_pdf(self):
        acc_bank = self.env['res.partner.bank'].create({
            'acc_number': 'FR15001559627231',
            'partner_id': self.company_data['company'].partner_id.id,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.journal.id,
            'partner_id': self.partner_1.id,
            'partner_bank_id': acc_bank.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                'price_unit': 275.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, self.tax_21.ids)],
            })],
        })
        invoice.action_post()
        pdf_attachment = invoice._get_edi_attachment(self.edi_format)
        self.assertEqual(pdf_attachment['name'], 'factur-x.xml')

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
        attachment = self._assert_invoice_attachment(
            invoice,
            xpaths='''
                <xpath expr="./*[local-name()='ExchangedDocument']/*[local-name()='ID']" position="replace">
                        <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='IssuerAssignedID']" position="replace">
                        <IssuerAssignedID>___ignore___</IssuerAssignedID>
                </xpath>
                <xpath expr=".//*[local-name()='PaymentReference']" position="replace">
                        <PaymentReference>___ignore___</PaymentReference>
                </xpath>
            ''',
            expected_file='from_odoo/facturx_out_invoice.xml',
        )
        self.assertEqual(attachment.name, "factur-x.xml")
        self._assert_imported_invoice_from_etree(invoice, attachment)

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
        attachment = self._assert_invoice_attachment(
            refund,
            xpaths='''
                <xpath expr="./*[local-name()='ExchangedDocument']/*[local-name()='ID']" position="replace">
                        <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='IssuerAssignedID']" position="replace">
                        <IssuerAssignedID>___ignore___</IssuerAssignedID>
                </xpath>
            ''',
            expected_file='from_odoo/facturx_out_refund.xml'
        )
        self.assertEqual(attachment.name, "factur-x.xml")
        self._assert_imported_invoice_from_etree(refund, attachment)

    def test_export_tax_included(self):
        """
        Tests whether the tax included price_units are correctly converted to tax excluded
        amounts in the exported xml
        """
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [(6, 0, self.tax_5_incl.ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [(6, 0, self.tax_5.ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 200,
                    'discount': 10,
                    'tax_ids': [(6, 0, self.tax_5_incl.ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 200,
                    'discount': 10,
                    'tax_ids': [(6, 0, self.tax_5.ids)],
                },
            ],
        )
        self._assert_invoice_attachment(
            invoice,
            xpaths='''
                <xpath expr="./*[local-name()='ExchangedDocument']/*[local-name()='ID']" position="replace">
                        <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='IssuerAssignedID']" position="replace">
                        <IssuerAssignedID>___ignore___</IssuerAssignedID>
                </xpath>
            ''',
            expected_file='from_odoo/facturx_out_invoice_tax_incl.xml'
        )

    def test_encoding_in_attachment_facturx(self):
        self._test_encoding_in_attachment('facturx_1_0_05', 'factur-x.xml')

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
        self._assert_invoice_attachment(invoice, None, 'from_odoo/facturx_ecotaxes_case1.xml')

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
        self._assert_invoice_attachment(invoice, None, 'from_odoo/facturx_ecotaxes_case2.xml')

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
        self._assert_invoice_attachment(invoice, None, 'from_odoo/facturx_ecotaxes_case3.xml')

    ####################################################
    # Test import
    ####################################################

    def test_import_partner_facturx(self):
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
        new_invoice = self._import_invoice_attachment(invoice, 'facturx_1_0_05', self.company_data['default_journal_sale'])
        self.assertEqual(self.partner_2, new_invoice.partner_id)

        new_invoice = self._import_invoice_attachment(invoice, 'facturx_1_0_05', self.company_data['default_journal_purchase'])
        self.assertEqual(self.partner_1, new_invoice.partner_id)

    def test_import_journal_facturx(self):
        """
        If the context contains the info about the current default journal, we should use it
        instead of infering the journal from the move type.
        """
        journal2 = self.company_data['default_journal_sale'].copy()
        journal2.default_account_id = self.company_data['default_account_revenue'].id
        invoice = self._generate_move(
            seller=self.partner_1,
            buyer=self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[{'product_id': self.product_a.id}],
        )
        edi_attachment = invoice._get_edi_attachment(self.env.ref('account_edi_ubl_cii.edi_facturx_1_0_05')).id

        new_invoice = self.env['account.journal'].with_context(default_move_type='out_invoice')._create_document_from_attachment(edi_attachment)
        self.assertEqual(new_invoice.journal_id, self.company_data['default_journal_sale'])

        new_invoice = self.env['account.journal'].with_context(default_journal_id=journal2.id)._create_document_from_attachment(edi_attachment)
        self.assertEqual(new_invoice.journal_id, journal2)

    def test_import_and_create_partner_facturx(self):
        """ Tests whether the partner is created at import if no match is found when decoding the EDI attachment
        """
        partner_vals = {
            'name': "Buyer",
            'mail': "buyer@yahoo.com",
            'phone': "1111",
            'vat': "FR89215010646",
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
            filename='facturx_test_import_partner.xml',
            invoice=invoice)

        # assert a new partner has been created
        partner_vals['email'] = partner_vals.pop('mail')
        self.assertRecordValues(invoice.partner_id, [partner_vals])

    def test_import_tax_included(self):
        """
        Tests whether the tax included / tax excluded are correctly decoded when
        importing a document. The imported xml represents the following invoice:

        Description         Quantity    Unit Price    Disc (%)   Taxes            Amount
        --------------------------------------------------------------------------------
        Product A                  1           100          0    5% (incl)         95.24
        Product A                  1           100          0    5% (not incl)       100
        Product A                  2           200         10    5% (incl)        171.43
        Product A                  2           200         10    5% (not incl)       180
        -----------------------
        Untaxed Amount: 546.67
        Taxes: 27.334
        -----------------------
        Total: 574.004
        """
        self._assert_imported_invoice_from_file(
            subfolder='tests/test_files/from_odoo',
            filename='facturx_out_invoice_tax_incl.xml',
            amount_total=574.004,
            amount_tax=27.334,
            list_line_subtotals=[95.24, 100, 171.43, 180],
            # /!\ The price_unit are different for taxes with price_include, because all amounts in Factur-X should be
            # tax excluded. At import, the tax included amounts are thus converted into tax excluded ones.
            # Yet, the line subtotals and total will be the same (if an equivalent tax exist with price_include = False)
            list_line_price_unit=[95.24, 100, 190.48, 200],
            # rounding error since for line 3: we round several times...
            # when exporting the invoice, we compute the price tax excluded = 200/1.05 ~= 190.48
            # then, when computing the discount amount: 190.48 * 0.1 ~= 19.05 => price net amount = 171.43
            # Thus, at import: price_unit = 190.48, and discount = 100 * (1 - 171.43 / 190.48) = 10.001049979
            list_line_discount=[0, 0, 10, 10],
            # Again, all taxes in the imported invoice are price_include = False
            list_line_taxes=[self.tax_5_purchase]*4,
            move_type='in_invoice',
            currency_id=self.env['res.currency'].search([('name', '=', 'USD')], limit=1).id,
        )

    def test_import_fnfe_examples(self):
        # Source: official documentation of the FNFE (subdirectory: "5. FACTUR-X 1.0.06 - Examples")
        subfolder = 'tests/test_files/from_factur-x_doc'
        # the 2 following files have the same pdf but one is labelled as an invoice and the other as a refund
        # source: Avoir_FR_type380_EN16931.pdf
        self._assert_imported_invoice_from_file(subfolder=subfolder, filename='facturx_credit_note_type380.xml',
            amount_total=233.47, amount_tax=14.99, list_line_subtotals=[20.48, 198], move_type='in_refund')
        # source: Avoir_FR_type381_EN16931.pdf
        self._assert_imported_invoice_from_file(subfolder=subfolder, filename='facturx_credit_note_type381.xml',
            amount_total=233.47, amount_tax=14.99, list_line_subtotals=[20.48, 198], move_type='in_refund')
        # source: Facture_F20220024_EN_16931_basis_quantity, basis quantity != 1 for one of the lines
        self._assert_imported_invoice_from_file(subfolder=subfolder, filename='facturx_invoice_basis_quantity.xml',
            amount_total=108, amount_tax=8, list_line_subtotals=[-5, 10, 60, 28, 7])
        # source: Facture_F20220029_EN_16931_K.pdf, credit note labelled as an invoice with negative amounts
        self._assert_imported_invoice_from_file(subfolder=subfolder, filename='facturx_invoice_negative_amounts.xml',
            amount_total=100, amount_tax=0, list_line_subtotals=[-5, 10, 60, 30, 5], move_type='in_refund')

    def test_import_fixed_taxes(self):
        """ Tests whether we correctly decode the xml attachments created using fixed taxes.
        See the tests above to create these xml attachments ('test_export_with_fixed_taxes_case_[X]').
        NB: use move_type = 'out_invoice' s.t. we can retrieve the taxes used to create the invoices.
        """
        subfolder = "tests/test_files/from_odoo"
        self._assert_imported_invoice_from_file(
            subfolder=subfolder, filename='facturx_ecotaxes_case1.xml', amount_total=121, amount_tax=22,
            list_line_subtotals=[99], currency_id=self.currency_data['currency'].id, list_line_price_unit=[99],
            list_line_discount=[0], list_line_taxes=[self.tax_21+self.recupel], move_type='out_invoice',
        )
        self._assert_imported_invoice_from_file(
            subfolder=subfolder, filename='facturx_ecotaxes_case2.xml', amount_total=121, amount_tax=23,
            list_line_subtotals=[98], currency_id=self.currency_data['currency'].id, list_line_price_unit=[98],
            list_line_discount=[0], list_line_taxes=[self.tax_21+self.recupel+self.auvibel], move_type='out_invoice',
        )
        self._assert_imported_invoice_from_file(
            subfolder=subfolder, filename='facturx_ecotaxes_case3.xml', amount_total=121, amount_tax=22,
            list_line_subtotals=[99], currency_id=self.currency_data['currency'].id, list_line_price_unit=[99],
            list_line_discount=[0], list_line_taxes=[self.tax_21+self.recupel], move_type='out_invoice',
        )
