# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from io import BytesIO
from zipfile import ZipFile

from lxml import etree
from unittest.mock import patch
from odoo import fields, Command
from odoo.tests import HttpCase, tagged
from odoo.tools import file_open, misc
from odoo.tools.safe_eval import datetime

from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiCommon


@tagged('post_install', '-at_install')
class TestAccountEdiUblCii(TestUblCiiCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

        cls.uom_units = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozens = cls.env.ref('uom.product_uom_dozen')

        cls.displace_prdct = cls.env['product.product'].create({
            'name': 'Displacement',
            'uom_id': cls.uom_units.id,
            'standard_price': 90.0,
        })

        cls.place_prdct = cls.env['product.product'].create({
            'name': 'Placement',
            'uom_id': cls.uom_units.id,
            'standard_price': 80.0,
        })

        cls.namespaces = {
            'rsm': "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            'ram': "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
            'udt': "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
            'qdt': "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
            'xsi': "http://www.w3.org/2001/XMLSchema-instance",
        }

        cls.ubl_namespaces = {
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }

        cls.reverse_charge_tax = cls.company_data['default_tax_sale'].copy({
            'name': 'Reverse charge tax',
            'ubl_cii_tax_category_code': 'AE',
            'ubl_cii_tax_exemption_reason_code': 'VATEX-EU-AE'
        })
        cls.zero_rated_tax = cls.company_data['default_tax_sale'].copy({
            'name': 'Zero rated tax',
            'ubl_cii_tax_category_code': 'Z'
        })
        cls.prod_tax = cls.company_data['default_tax_sale'].copy({
            'name': 'Production tax',
            'ubl_cii_tax_category_code': 'M'
        })
        cls.free_export_tax = cls.company_data['default_tax_sale'].copy({
            'name': 'Free export tax',
            'ubl_cii_tax_category_code': 'G',
            'ubl_cii_tax_exemption_reason_code': 'VATEX-EU-132-1G'
        })

    def test_export_import_product(self):
        products = self.env['product.product'].create([{
            'name': 'XYZ',
            'default_code': '1234',
        }, {
            'name': 'XYZ',
            'default_code': '5678',
        }, {
            'name': 'XXX',
            'default_code': '1111',
            'barcode': '00001',
        }, {
            'name': 'YYY',
            'default_code': '1111',
            'barcode': '00002',
        }])
        line_vals = [
            {
                'product_id': self.place_prdct.id,
                'name': 'Placement',
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id]
            }, {
                'product_id': self.displace_prdct.id,
                'name': 'Displacement',
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id]
            }, {
                'product_id': self.displace_prdct.id,
                'name': 'Displacement',
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id]
            }, {
                'product_id': self.displace_prdct.id,
                'name': 'Displacement',
                'product_uom_id': self.uom_dozens.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id]
            }, {
                'product_id': products[0].id,
                'name': 'Awesome Product',
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id],
            }, {
                'product_id': products[1].id,
                'name': 'XYZ',
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id],
            }, {
                'product_id': products[2].id,
                'name': 'XXX',
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id],
            }, {
                'product_id': products[3].id,
                'name': 'YYY',
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id],
            },
        ]
        company = self.company_data_2['company']
        company.country_id = self.env['res.country'].search([('code', '=', 'FR')])
        company.vat = 'FR23334175221'
        company.email = 'company@site.ext'
        company.phone = '+33499999999'
        company.zip = '78440'
        company.partner_id.bank_ids = [Command.create({
            'acc_number': '999999',
            'partner_id': company.partner_id.id,
            'acc_holder_name': 'The Chosen One',
            'allow_out_payment': True,
        })]

        for ubl_cii_format in ['facturx', 'ubl_bis3']:
            with self.subTest(sub_test_name=f"format: {ubl_cii_format}"):
                company.partner_id.with_company(company).invoice_edi_format = ubl_cii_format

                invoice = self.env['account.move'].create({
                    'company_id': company.id,
                    'partner_id': company.partner_id.id,
                    'move_type': 'out_invoice',
                    'journal_id': self.company_data_2['default_journal_sale'].id,
                    'invoice_line_ids': [Command.create(vals) for vals in line_vals],
                })
                invoice.action_post()

                print_wiz = self.env['account.move.send.wizard'].create({
                    'move_id': invoice.id,
                    'sending_methods': ['manual'],
                })
                self.assertEqual(print_wiz.invoice_edi_format, ubl_cii_format)
                print_wiz.action_send_and_print()

                attachment = invoice.ubl_cii_xml_id
                xml_tree = etree.fromstring(attachment.raw)

                if ubl_cii_format == 'facturx':
                    # Testing the case where a product on the invoice has a UoM with a different category than the one in the DB
                    wrong_uom_line = xml_tree.findall('./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem')[1]
                    wrong_uom_line.find('./{*}SpecifiedLineTradeDelivery/{*}BilledQuantity').attrib['unitCode'] = 'HUR'
                    last_line_product = xml_tree.find('./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem[8]/{*}SpecifiedTradeProduct')
                    self.assertEqual(last_line_product.find('./{*}GlobalID').text, '00002')
                    self.assertEqual(last_line_product.find('./{*}SellerAssignedID').text, '1111')
                    self.assertEqual(last_line_product.find('./{*}Name').text, 'YYY')
                elif ubl_cii_format == 'ubl_bis3':
                    last_line_product = xml_tree.find('./{*}InvoiceLine[8]/{*}Item')
                    barcode_node = last_line_product.find('./{*}StandardItemIdentification/{*}ID')
                    self.assertEqual(barcode_node.text, '00002')
                    self.assertEqual(barcode_node.attrib['schemeID'], '0160')
                    self.assertEqual(last_line_product.find('./{*}SellersItemIdentification/{*}ID').text, '1111')
                    self.assertEqual(last_line_product.find('./{*}Name').text, 'YYY')

                attachment.raw = etree.tostring(xml_tree)
                new_invoice = invoice.journal_id._create_document_from_attachment(attachment.ids)
                self.assertRecordValues(new_invoice.invoice_line_ids, line_vals)

    def test_import_tax_prediction(self):
        """ We are going to create 2 tax and import the e-invoice twice.

        On the first attempt, as there isn't any data to leverage, the classic 'search' will be called and we expect
        the first tax created to be the selected one as the retrieval order is `sequence, id`.

        We will set the second tax on the bill and post it which make it the most probable one.

        On the second attempt, we expect that second tax to be retrieved.
        """
        self.env.ref('base.EUR').active = True  # EUR might not be active and is used in the xml testing file
        if not hasattr(self.env["account.move.line"], '_predict_specific_tax'):
            self.skipTest("The predictive bill module isn't install and thus prediction with edi can't be tested.")
        # create 2 new taxes for the test seperatly to ensure the first gets the smaller id
        new_tax_1 = self.env["account.tax"].create({
            'name': 'tax with lower id could be retrieved first',
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'amount': 16.0,
        })
        new_tax_2 = self.env["account.tax"].create({
            'name': 'tax with higher id could be retrieved second',
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'amount': 16.0,
        })

        file_path = "bis3_bill_example.xml"
        file_path = f"{self.test_module}/tests/test_files/{file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_invoice.xml',
                'raw': file.read(),
            })

        # Import the document for the first time
        bill = self._import_as_attachment_on(attachment=xml_attachment)

        # Ensure the first tax is retrieved as there isn't any prediction that could be leverage
        self.assertEqual(bill.invoice_line_ids.tax_ids, new_tax_1)

        # Set the second tax on the line to make it the most probable one
        bill.invoice_line_ids.tax_ids = new_tax_2
        bill.action_post()

        # Import the bill again and ensure the prediction did his work
        bill = self._import_as_attachment_on(attachment=xml_attachment)
        self.assertEqual(bill.invoice_line_ids.tax_ids, new_tax_2)

    def test_peppol_eas_endpoint_compute(self):
        partner = self.partner_a
        partner.vat = 'DE123456788'
        partner.country_id = self.env.ref('base.de')

        self.assertRecordValues(partner, [{
            'peppol_eas': '9930',
            'peppol_endpoint': 'DE123456788',
        }])

        partner.country_id = self.env.ref('base.fr')
        partner.vat = 'FR23334175221'

        self.assertRecordValues(partner, [{
            'peppol_eas': '9957',
            'peppol_endpoint': 'FR23334175221',
        }])

        partner.vat = '23334175221'

        self.assertRecordValues(partner, [{
            'peppol_eas': '9957',
            'peppol_endpoint': '23334175221',
        }])

        partner.write({
            'vat': 'BE0477472701',
            'company_registry': '0477472701',
            'country_id': self.env.ref('base.be'),
        })

        self.assertRecordValues(partner, [{
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
        }])

    def test_export_company_registry_in_party_nodes(self):
        """Check that company_registry is used for PartyIdentification and CompanyID."""
        self.partner_be.company_registry = '1234567890'
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_be.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})]
        })
        invoice.action_post()

        xml_tree = etree.fromstring(self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0])
        customer_nodes = xml_tree.xpath('//cac:AccountingCustomerParty/cac:Party', namespaces=self.ubl_namespaces)
        self.assertEqual(customer_nodes[0].find('.//{*}PartyIdentification/{*}ID').text, '1234567890')
        self.assertEqual(customer_nodes[0].find('.//{*}PartyLegalEntity/{*}CompanyID').text, '1234567890')

    def test_import_partner_peppol_fields(self):
        """ Check that the peppol fields are used to retrieve the partner when importing a Bis 3 xml. """
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_be.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})]
        })
        invoice.action_post()
        xml_attachment = self.env['ir.attachment'].create({
            'raw': self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0],
            'name': 'test_invoice.xml',
        })

        # There is a duplicated partner (with the same name and email)
        self.env['res.partner'].create({
            'name': "My Belgian Partner",
            'email': "mypartner@email.com",
        })
        # Change the fields of the partner, keep the peppol fields
        self.partner_be.update({
            'name': "Turlututu",
            'email': False,
            'vat': False,
        })
        # The partner should be retrieved based on the peppol fields
        imported_invoice = self._import_as_attachment_on(attachment=xml_attachment, journal=self.company_data["default_journal_sale"])
        self.assertEqual(imported_invoice.partner_id, self.partner_be)

    def test_import_partner_postal_address(self):
        " Test importing postal address when creating new partner from UBL xml."
        file_path = "bis3_bill_example.xml"
        file_path = f"{self.test_module}/tests/test_files/{file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_invoice.xml',
                'raw': file.read(),
            })

        partner_vals = {
            'name': "ALD Automotive LU",
            'email': "adl@test.com",
            'vat': "LU12977109",
        }
        # assert there is no matching partner
        partner_match = self.env['res.partner']._retrieve_partner(**partner_vals)
        self.assertFalse(partner_match)

        bill = self._import_as_attachment_on(attachment=xml_attachment)

        self.assertRecordValues(bill.partner_id, [partner_vals])
        self.assertEqual(bill.partner_id.contact_address,
                         "ALD Automotive LU\n270 rte d'Arlon\n\n8010 Strassen \nLuxembourg")

    def test_actual_delivery_date_in_cii_xml(self):

        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
            'delivery_date': "2024-12-31",
        })
        invoice.action_post()

        xml_attachment = self.env['ir.attachment'].create({
            'raw': self.env['account.edi.xml.cii']._export_invoice(invoice)[0],
            'name': 'test_invoice.xml',
        })
        xml_tree = etree.fromstring(xml_attachment.raw)
        actual_delivery_date = xml_tree.find('.//ram:ActualDeliverySupplyChainEvent/ram:OccurrenceDateTime/udt:DateTimeString', self.namespaces)
        self.assertEqual(actual_delivery_date.text, '20241231')

    def test_get_invoice_legal_documents_fallback(self):
        company = self.company_data['company']
        company.phone = '11111111111'
        company.email = 'test@test.odoo.com'
        german_partner = self.env['res.partner'].create({
            'name': 'German partner',
            'country_id': self.env.ref('base.de').id,
        })
        us_partner = self.env['res.partner'].create({
            'name': 'US partner',
            'country_id': self.env.ref('base.us').id,
        })
        belgian_partner = self.env['res.partner'].create({
            'name': 'Belgian partner',
            'country_id': self.env.ref('base.be').id,
        })
        invoice_de = self.init_invoice('out_invoice', partner=german_partner, amounts=[100], taxes=[self.tax_sale_a], post=True)
        invoice_be = self.init_invoice('out_invoice', partner=belgian_partner, amounts=[100], taxes=[self.tax_sale_a], post=True)
        invoice_us = self.init_invoice('out_invoice', partner=us_partner, amounts=[100], taxes=[self.tax_sale_a], post=True)
        res = [invoice._get_invoice_legal_documents('ubl', allow_fallback=True) for invoice in (invoice_de + invoice_be + invoice_us)]
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0].get('filename'), 'INV_2019_00001_ubl_de.xml')
        self.assertEqual(res[1].get('filename'), 'INV_2019_00002_ubl_bis3.xml')
        self.assertFalse(res[2])
        invoice_be_failing = self.init_invoice('out_invoice', partner=belgian_partner, amounts=[100], post=True)
        res_errors = invoice_be_failing._get_invoice_legal_documents('ubl', allow_fallback=True)
        self.assertIn("Each invoice line should have at least one tax.", res_errors.get('errors'))

    def test_billing_date_in_cii_xml(self):
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_date': "2024-12-01",
            'invoice_date_due': "2024-12-31",
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        invoice.action_post()
        invoice.invoice_date_due = fields.Date.from_string('2024-12-31')

        xml_attachment = self.env['ir.attachment'].create({
            'raw': self.env['account.edi.xml.cii']._export_invoice(invoice)[0],
            'name': 'test_invoice.xml',
        })
        xml_tree = etree.fromstring(xml_attachment.raw)
        start_date = xml_tree.find('.//ram:ApplicableHeaderTradeSettlement/ram:BillingSpecifiedPeriod/ram:StartDateTime/udt:DateTimeString', self.namespaces)
        end_date = xml_tree.find('.//ram:ApplicableHeaderTradeSettlement/ram:BillingSpecifiedPeriod/ram:EndDateTime/udt:DateTimeString', self.namespaces)
        self.assertEqual(start_date.text, '20241201')
        self.assertEqual(end_date.text, '20241231')

    def test_export_import_billing_dates(self):
        if self.env.ref('base.module_accountant').state != 'installed':
            self.skipTest("payment_custom module is not installed")

        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_date': "2024-12-01",
            'invoice_date_due': "2024-12-31",
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'deferred_start_date': "2024-11-19",
                    'deferred_end_date': "2024-12-11",
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'deferred_end_date': "2024-12-26",
                }),
                Command.create({
                    'product_id': self.product_a.id,
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'deferred_start_date': "2024-11-29",
                    'deferred_end_date': "2024-12-15",
                }),
            ],
        })
        invoice.action_post()

        xml_attachment = self.env['ir.attachment'].create({
            'raw': self.env['account.edi.xml.cii']._export_invoice(invoice)[0],
            'name': 'test_invoice.xml',
        })
        xml_tree = etree.fromstring(xml_attachment.raw)

        line_start_dates = xml_tree.findall('.//ram:SpecifiedLineTradeSettlement/ram:BillingSpecifiedPeriod/ram:StartDateTime/udt:DateTimeString', self.namespaces)
        self.assertEqual([date.text for date in line_start_dates], ['20241119', '20241201', '20241129'])

        line_end_dates = xml_tree.findall('.//ram:SpecifiedLineTradeSettlement/ram:BillingSpecifiedPeriod/ram:EndDateTime/udt:DateTimeString', self.namespaces)
        self.assertEqual([value.text for value in line_end_dates], ['20241211', '20241226', '20241215'])

        global_start_date = xml_tree.find('.//ram:ApplicableHeaderTradeSettlement/ram:BillingSpecifiedPeriod/ram:StartDateTime/udt:DateTimeString', self.namespaces)
        self.assertEqual(global_start_date.text, '20241119')

        global_end_date = xml_tree.find('.//ram:ApplicableHeaderTradeSettlement/ram:BillingSpecifiedPeriod/ram:EndDateTime/udt:DateTimeString', self.namespaces)
        self.assertEqual(global_end_date.text, '20241226')

        line_vals = [
            {
                'product_id': self.product_a.id,
                'deferred_start_date': datetime.date(2024, 11, 19),
                'deferred_end_date': datetime.date(2024, 12, 11),
            },
            {
                'product_id': self.product_a.id,
                'deferred_start_date': datetime.date(2024, 12, 1),
                'deferred_end_date': datetime.date(2024, 12, 26),
            },
            {
                'product_id': self.product_a.id,
                'deferred_start_date': False,
                'deferred_end_date': False,
            },
            {
                'product_id': self.product_a.id,
                'deferred_start_date': datetime.date(2024, 11, 29),
                'deferred_end_date': datetime.date(2024, 12, 15),
            },
        ]
        new_invoice = invoice.journal_id._create_document_from_attachment(xml_attachment.ids)
        self.assertRecordValues(new_invoice.invoice_line_ids, line_vals)

    def test_import_partner_fields(self):
        """ We are going to import the e-invoice and check partner is correctly imported."""
        self.env.ref('base.EUR').active = True  # EUR might not be active and is used in the xml testing file
        file_path = "bis3_bill_example.xml"
        file_path = f"{self.test_module}/tests/test_files/{file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_invoice.xml',
                'raw': file.read(),
            })

        bill = self._import_as_attachment_on(attachment=xml_attachment)

        self.assertRecordValues(bill.partner_id, [{
            'name': "ALD Automotive LU",
            'phone': False,
            'email': 'adl@test.com',
            'vat': 'LU12977109',
            'street': '270 rte d\'Arlon',
            'street2': False,
            'city': 'Strassen',
            'zip': '8010',
        }])

    def test_import_bill(self):
        partner = self.env['res.partner'].create({
            'name': "My Belgian Partner",
            'vat': "BE0477472701",
            'email': "mypartner@email.com",
        })
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})]
        })
        invoice.action_post()
        my_invoice_raw = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        my_invoice_root = etree.fromstring(my_invoice_raw)
        modifying_xpath = """<xpath expr="(//*[local-name()='LegalMonetaryTotal']/*[local-name()='TaxExclusiveAmount'])" position="replace">
        <TaxExclusiveAmount currencyID="EUR"><!--Some valid XML
comment-->1000.0</TaxExclusiveAmount></xpath>"""
        xml_attachment = self.env['ir.attachment'].create({
            'raw': etree.tostring(self.with_applied_xpath(my_invoice_root, modifying_xpath)),
            'name': 'test_invoice.xml',
        })
        imported_invoice = self._import_as_attachment_on(attachment=xml_attachment, journal=self.company_data["default_journal_purchase"])
        self.assertRecordValues(imported_invoice.invoice_line_ids, [{
            'amount_currency': 1000.00,
            'quantity': 1.0}])

    def test_import_discount(self):
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 3,
                    'price_unit': 11.34,
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.65,
                    'price_unit': 29.9,
                }),
            ],
        })
        xml_attachment = self.env['ir.attachment'].create({
            'raw': self.env['account.edi.xml.cii']._export_invoice(invoice)[0],
            'name': 'test_invoice.xml',
        })
        imported_invoice = self._import_as_attachment_on(attachment=xml_attachment, journal=self.company_data["default_journal_sale"])
        for line in imported_invoice.invoice_line_ids:
            self.assertFalse(line.discount, "A discount on the imported lines signals a rounding error in the discount computation")

    def test_export_xml_with_multiple_invoices(self):
        partner = self._create_partner_be(invoice_edi_format='ubl_bis3')
        self.company_data['company'].partner_id.write({
            'peppol_eas': '0230',
            'peppol_endpoint': 'C2584563200',
        })
        invoices = self.env['account.move'].create([
            {
                'partner_id': partner.id,
                'move_type': 'out_invoice',
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'quantity': qty,
                        'price_unit': price,
                    }),
                ],
            }
            for qty, price in [(1, 100), (2, 200), (3, 300)]
        ])
        invoices[:2].action_post()
        invoices[:2]._generate_and_send()
        xml_print_url = next(item for item in invoices.get_extra_print_items() if item['key'] == 'download_ubl')['url']
        self.assertEqual(
            xml_print_url,
            f'/account/download_invoice_documents/{invoices[0].id},{invoices[1].id}/ubl?allow_fallback=true',
            'Only posted invoices should be called in the URL',
        )
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(xml_print_url)
        self.assertEqual(res.status_code, 200)
        with ZipFile(BytesIO(res.content)) as zip_file:
            self.assertEqual(
                zip_file.namelist(),
                (invoices[:2]).ubl_cii_xml_id.mapped('name'),
            )

    def test_payment_means_code_in_facturx_xml(self):
        bank_ing = self.env['res.bank'].create({'name': 'ING', 'bic': 'BBRUBEBB'})
        partner_bank = self.env['res.partner.bank'].create({
                'acc_number': 'BE15001559627230',
                'partner_id': self.partner_a.id,
                'bank_id': bank_ing.id,
                'company_id': self.env.company.id,
                'allow_out_payment': True,
            })
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
            'delivery_date': "2024-12-31",
            'partner_bank_id': partner_bank.id,
        })
        invoice.action_post()

        xml_attachment = self.env['ir.attachment'].create({
            'raw': self.env['account.edi.xml.cii']._export_invoice(invoice)[0],
            'name': 'test_invoice.xml',
        })
        xml_tree = etree.fromstring(xml_attachment.raw)
        code = xml_tree.find('.//ram:SpecifiedTradeSettlementPaymentMeans/ram:TypeCode', self.namespaces)
        self.assertEqual(code.text, '42')

        if self.env['ir.module.module']._get('account_sepa_direct_debit').state == 'installed':
            company = self.env.company
            company.sdd_creditor_identifier = 'BE30ZZZ300D000000042'
            company_bank_journal = self.company_data['default_journal_bank']
            company_bank_journal.bank_acc_number = 'CH9300762011623852957'
            self.partner_a.country_id = self.env.ref('base.nl').id
            company_bank_journal.bank_account_id.write({
                'bank_id': bank_ing.id,
                'allow_out_payment': True,
            })

            mandate = self.env['sdd.mandate'].create({
                'name': 'mandate ' + (self.partner_a.name or ''),
                'partner_bank_id': partner_bank.id,
                'one_off': True,
                'start_date': fields.Date.today(),
                'partner_id': self.partner_a.id,
                'company_id': company.id,
            })
            mandate.action_validate_mandate()
            invoice = self.env['account.move'].create({
                'partner_id': self.partner_a.id,
                'move_type': 'out_invoice',
                'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
                'delivery_date': "2024-12-31",
            })
            invoice.action_post()
            sdd_method_line = company_bank_journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'sdd')
            sdd_method_line.payment_account_id = self.inbound_payment_method_line.payment_account_id
            self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
                'payment_date': invoice.invoice_date,
                'journal_id': company_bank_journal.id,
                'payment_method_line_id': sdd_method_line.id,
            })._create_payments()

            xml_attachment = self.env['ir.attachment'].create({
                'raw': self.env['account.edi.xml.cii']._export_invoice(invoice)[0],
                'name': 'test_invoice.xml',
            })
            xml_tree = etree.fromstring(xml_attachment.raw)
            code = xml_tree.find('.//ram:SpecifiedTradeSettlementPaymentMeans/ram:TypeCode', self.namespaces)
            self.assertEqual(code.text, '59')

    def test_tax_subtotal(self):
        ubl_taxes = (self.reverse_charge_tax + self.zero_rated_tax + self.prod_tax + self.free_export_tax)
        # test tax by tax then with multiple taxes
        tax_list = list(ubl_taxes) + [ubl_taxes]
        for taxes in tax_list:
            invoice = self.env["account.move"].create({
                "partner_id": self.partner_a.id,
                "move_type": "out_invoice",
                "invoice_line_ids": [Command.create({"name": "Test product", "price_unit": 100, "tax_ids": [Command.set(taxes.ids)]})],
            })
            invoice.action_post()
            xml = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
            root = etree.fromstring(xml)
            for tax, node in zip(taxes, root.findall('.//{*}TaxTotal/{*}TaxSubtotal/{*}TaxCategory')):
                self.assertEqual(node.findtext('.//{*}ID') or False, tax.ubl_cii_tax_category_code)
                self.assertEqual(node.findtext('.//{*}TaxExemptionReasonCode') or False, tax.ubl_cii_tax_exemption_reason_code)

    def test_import_discount_3(self):
        """
        This test ensures that the subtotal and the sum of prices and charges are compared
        correctly and there's no regression on floating point issues when the price is 0.0
        """
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 0,
                }),
            ],
        })
        my_invoice_raw = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        my_invoice_root = etree.fromstring(my_invoice_raw)
        modifying_xpath = """
            <xpath expr="(//*[local-name()='InvoiceLine']/*[local-name()='LineExtensionAmount'])" position="replace">
                <LineExtensionAmount currencyID="EUR">0.30</LineExtensionAmount>
            </xpath>
            <xpath expr="(//*[local-name()='InvoiceLine']/*[local-name()='LineExtensionAmount'])" position="after">
                <AllowanceCharge>
                    <ChargeIndicator>true</ChargeIndicator>
                    <AllowanceChargeReason>FREIGHT</AllowanceChargeReason>
                    <Amount currencyID="EUR">0.20</Amount>
                </AllowanceCharge>
                <AllowanceCharge>
                    <ChargeIndicator>true</ChargeIndicator>
                    <AllowanceChargeReason>FUEL SURCHARGE</AllowanceChargeReason>
                    <Amount currencyID="EUR">0.10</Amount>
                </AllowanceCharge>
            </xpath>"""
        xml_attachment = self.env['ir.attachment'].create({
            'raw': etree.tostring(self.with_applied_xpath(my_invoice_root, modifying_xpath)),
            'name': 'test_invoice.xml',
        })

        imported_invoice = self._import_as_attachment_on(attachment=xml_attachment, journal=self.company_data["default_journal_sale"])
        self.assertRecordValues(imported_invoice.invoice_line_ids, [
            {'name': self.product_a.name, 'price_subtotal': 0.00},
            {'name': ' FREIGHT', 'price_subtotal': 0.20},
            {'name': ' FUEL SURCHARGE', 'price_subtotal': 0.10},
        ])

    def test_oin_code(self):
        partner = self.partner_a
        partner.peppol_endpoint = '00000000001020304050'
        partner.country_id = self.env.ref('base.nl').id
        partner.bank_ids = [Command.create({'acc_number': "0123456789", 'allow_out_payment': True})]
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'invoice_date': "2024-12-01",
            'invoice_date_due': "2024-12-31",
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })

        invoice.partner_id.commercial_partner_id.invoice_edi_format = 'nlcius'
        invoice.action_post()
        invoice.invoice_date_due = fields.Date.from_string('2024-12-31')
        builder = invoice.partner_id.commercial_partner_id._get_edi_builder('nlcius')
        xml_content = builder._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)
        scheme_ID = xml_tree.find('.//cac:PartyLegalEntity/cbc:CompanyID[@schemeID]', self.ubl_namespaces)
        self.assertEqual(scheme_ID.attrib.get("schemeID"), "0190")

    def test_facturx_use_correct_vat(self):
        """Test that Factur-X uses the foreign VAT when available, else the company VAT."""
        germany = self.env.ref("base.de")

        self.company.vat = '931736581'
        self.partner_a.country_id = germany.id
        self.partner_a.invoice_edi_format = 'facturx'
        self.partner_b.country_id = self.company.country_id.id
        self.partner_b.invoice_edi_format = 'facturx'

        tax_group = self.env['account.tax.group'].create({
            'name': 'German Taxes',
            'company_id': self.company.id,
            'country_id': germany.id,
        })
        tax = self.env['account.tax'].create({
            'name': 'DE VAT 19%',
            'amount': 19,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'country_id': germany.id,
            'tax_group_id': tax_group.id,
        })

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'German FP',
            'vat_required': True,
            'foreign_vat': 'DE123456788',
            'country_id': germany.id,
        })

        invoice_with_fp = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'fiscal_position_id': fiscal_position.id,
            'invoice_date': fields.Date.from_string('2025-12-22'),
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'tax_ids': [Command.set(tax.ids)],
            })],
        })
        local_invoice = self.env['account.move'].create({
            'partner_id': self.partner_b.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.from_string('2025-12-22'),
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
            })],
        })
        invoice_with_fp.action_post()
        local_invoice.action_post()

        # Check XML for foreign VAT
        xml_bytes = self.env["account.edi.xml.cii"]._export_invoice(invoice_with_fp)[0]
        xml_tree = etree.fromstring(xml_bytes)
        node = xml_tree.xpath("//ram:ID[@schemeID='VA']", namespaces={
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        })
        self.assertEqual(node[0].text, fiscal_position.foreign_vat, "Foreign Fiscal Position VAT")

        # Check XML for company VAT fallback
        xml_bytes = self.env["account.edi.xml.cii"]._export_invoice(local_invoice)[0]
        xml_tree = etree.fromstring(xml_bytes)
        node = xml_tree.xpath("//ram:ID[@schemeID='VA']", namespaces={
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        })
        self.assertEqual(node[0].text, self.company.vat, "Company VAT fallback")

    def test_import_vendor_bill_empty_description(self):
        with misc.file_open(f'{self.test_module}/tests/test_files/bis3/test_vendor_bill_empty_description.xml', 'rb') as file:
            file_read = file.read()
        attachment_id = self.env['ir.attachment'].create({
            'name': 'test_file_no_item_description.xml',
            'raw': file_read,
        }).id
        imported_bill = self.company_data['default_journal_purchase']._create_document_from_attachment(attachment_id)
        self.assertTrue(imported_bill)

    def test_generate_pdf_when_xml_does_not_provide_one(self):
        def _run_wkhtmltopdf(*args, **kwargs):
            return file_open(f'{self.test_module}/tests/test_files/invoice_example.pdf', 'rb').read()

        file_path = f"{self.test_module}/tests/test_files/bis3_bill_example_without_embedded_attachment.xml"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_invoice.xml',
                'raw': file.read(),
            })

        # Import the document that doesn't contain an embedded PDF
        with patch.object(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', _run_wkhtmltopdf):
            bill = self._import_as_attachment_on(
                journal=self.company_data["default_journal_purchase"].with_context(force_report_rendering=True),
                attachment=xml_attachment,
            )

        self.assertTrue(bill)

        # Ensure the created move has 2 attachments: the original XML and a generated PDF
        self.assertEqual(len(bill.attachment_ids), 2)
        self.assertTrue(any('pdf' in attachment.mimetype for attachment in bill.attachment_ids))
