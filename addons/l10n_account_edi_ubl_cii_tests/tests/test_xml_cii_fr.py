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
            'ref': 'seller_ref',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Rue Charles de Gaulle",
            'zip': "52330",
            'city': "Colombey-les-Deux-Églises",
            'vat': 'FR35562153452',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR90735788866632'})],
            'ref': 'buyer_ref',
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.fr').id,
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

    ####################################################
    # Test import
    ####################################################

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
            amount_total=90, amount_tax=0, list_line_subtotals=[-5, 10, 60, 30, 5, 0, -10], move_type='in_refund')
