# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.tools.safe_eval import datetime


@tagged('post_install', '-at_install')
class TestAccountEdiUblCii(AccountTestInvoicingCommon):

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

    def import_attachment(self, attachment, journal=None):
        journal = journal or self.company_data["default_journal_purchase"]
        return self.env['account.journal'] \
            .with_context(default_journal_id=journal.id) \
            ._create_document_from_attachment(attachment.id)

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
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id]
            }, {
                'product_id': self.displace_prdct.id,
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id]
            }, {
                'product_id': self.displace_prdct.id,
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id]
            }, {
                'product_id': self.displace_prdct.id,
                'product_uom_id': self.uom_dozens.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id]
            }, {
                'product_id': products[0].id,
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id],
            }, {
                'product_id': products[1].id,
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id],
            }, {
                'product_id': products[2].id,
                'product_uom_id': self.uom_units.id,
                'tax_ids': [self.company_data_2['default_tax_sale'].id],
            }, {
                'product_id': products[3].id,
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
            'acc_holder_name': 'The Chosen One'
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

    def test_export_import_product_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_export_import_product()

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
        bill = self.import_attachment(xml_attachment, self.company_data["default_journal_purchase"])

        # Ensure the first tax is retrieved as there isn't any prediction that could be leverage
        self.assertEqual(bill.invoice_line_ids.tax_ids, new_tax_1)

        # Set the second tax on the line to make it the most probable one
        bill.invoice_line_ids.tax_ids = new_tax_2
        bill.action_post()

        # Import the bill again and ensure the prediction did his work
        bill = self.import_attachment(xml_attachment, self.company_data["default_journal_purchase"])
        self.assertEqual(bill.invoice_line_ids.tax_ids, new_tax_2)

    def test_peppol_eas_endpoint_compute(self):
        partner = self.partner_a
        partner.vat = 'DE123456788'

        self.assertRecordValues(partner, [{
            'peppol_eas': '9930',
            'peppol_endpoint': 'DE123456788',
        }])

        partner.vat = 'FR23334175221'

        self.assertRecordValues(partner, [{
            'peppol_eas': '9957',
            'peppol_endpoint': 'FR23334175221',
        }])

        partner.vat = '23334175221'

        self.assertRecordValues(partner, [{
            'peppol_eas': '9957',
            'peppol_endpoint': 'FR23334175221',
        }])

        partner.write({
            'vat': 'BE0477472701',
            'company_registry': '0477472701',
        })

        self.assertRecordValues(partner, [{
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
        }])

    def test_import_partner_peppol_fields(self):
        """ Check that the peppol fields are used to retrieve the partner when importing a Bis 3 xml. """
        partner = self.env['res.partner'].create({
            'name': "My Belgian Partner",
            'vat': "BE0477472701",
            'peppol_eas': "0208",
            'peppol_endpoint': "0477472701",
            'email': "mypartner@email.com",
        })
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
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
        partner.update({
            'name': "Turlututu",
            'email': False,
            'vat': False,
        })
        # The partner should be retrieved based on the peppol fields
        imported_invoice = self.import_attachment(xml_attachment, self.company_data["default_journal_sale"])
        self.assertEqual(imported_invoice.partner_id, partner)

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

        bill = self.import_attachment(xml_attachment, self.company_data["default_journal_purchase"])

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
        imported_invoice = self.import_attachment(xml_attachment, self.company_data["default_journal_sale"])
        for line in imported_invoice.invoice_line_ids:
            self.assertFalse(line.discount, "A discount on the imported lines signals a rounding error in the discount computation")

    def test_payment_means_code_in_facturx_xml(self):
        bank_ing = self.env['res.bank'].create({'name': 'ING', 'bic': 'BBRUBEBB'})
        partner_bank = self.env['res.partner.bank'].create({
                'acc_number': 'BE15001559627230',
                'partner_id': self.partner_a.id,
                'bank_id': bank_ing.id,
                'company_id': self.env.company.id,
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
            company_bank_journal.bank_account_id.bank_id = bank_ing
            self.partner_a.country_id = self.env.ref('base.nl').id

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
