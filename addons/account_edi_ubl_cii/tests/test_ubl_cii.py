# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from odoo import fields, Command
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiCommon
from odoo.tests import tagged
from odoo.tools.safe_eval import datetime


@tagged('post_install', '-at_install')
class TestAccountEdiUblCii(TestUblCiiCommon):

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

    def setUp(self):
        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_all_caches)
        super().setUp()

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

        company.partner_id.with_company(company).invoice_edi_format = 'facturx'

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
        self.assertEqual(print_wiz.invoice_edi_format, 'facturx')
        print_wiz.action_send_and_print()

        attachment = invoice.ubl_cii_xml_id
        xml_tree = etree.fromstring(attachment.raw)

        # Testing the case where a product on the invoice has a UoM with a different category than the one in the DB
        wrong_uom_line = xml_tree.findall('./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem')[1]
        wrong_uom_line.find('./{*}SpecifiedLineTradeDelivery/{*}BilledQuantity').attrib['unitCode'] = 'HUR'
        last_line_product = xml_tree.find('./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem[8]/{*}SpecifiedTradeProduct')
        self.assertEqual(last_line_product.find('./{*}GlobalID').text, '00002')
        self.assertEqual(last_line_product.find('./{*}SellerAssignedID').text, '1111')
        self.assertEqual(last_line_product.find('./{*}Name').text, 'YYY')

        attachment.raw = etree.tostring(xml_tree)
        new_invoice = invoice.journal_id._create_document_from_attachment(attachment.ids)
        self.assertRecordValues(new_invoice.invoice_line_ids, line_vals)

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
        imported_invoice = self._import_invoice_as_attachment_on(attachment=xml_attachment, journal=self.company_data["default_journal_sale"])
        self.assertEqual(imported_invoice.partner_id, self.partner_be)

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

    def test_import_bill(self):
        self.env['res.partner.bank'].sudo().create({
            'acc_number': 'Test account',
            'partner_id': self.company_data['company'].partner_id.id,
            'allow_out_payment': True,
        })
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
        imported_invoice = self._import_invoice_as_attachment_on(attachment=xml_attachment, journal=self.company_data["default_journal_purchase"])
        self.assertRecordValues(imported_invoice.invoice_line_ids, [{
            'amount_currency': 1000.00,
            'quantity': 1.0}])

    def test_importing_bill_shouldnt_set_current_company_bank_account(self):
        partner = self.env['res.partner'].create({
            'name': "My Belgian Partner",
        })
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})]
        })
        invoice.action_post()
        my_invoice_raw = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        my_invoice_root = etree.fromstring(my_invoice_raw)
        modifying_xpath = """
            <xpath expr="(//*[local-name()='PaymentMeans']/*[local-name()='PaymentID'])" position="after">
                <PayeeFinancialAccount><ID>Test account</ID></PayeeFinancialAccount>
            </xpath>"""
        xml_attachment = self.env['ir.attachment'].create({
            'raw': etree.tostring(self.with_applied_xpath(my_invoice_root, modifying_xpath)),
            'name': 'test_invoice.xml',
        })
        move = self.env['account.journal']\
            .with_context(default_journal_id=self.company_data['default_journal_sale'].id)\
            ._create_document_from_attachment(xml_attachment.id)
        self.assertTrue(any('add your own bank account manually' in message.body for message in move.message_ids))

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

        invoice.partner_id.commercial_partner_id.invoice_edi_format = 'ubl_bis3'
        invoice.action_post()
        invoice.invoice_date_due = fields.Date.from_string('2024-12-31')
        builder = invoice.partner_id.commercial_partner_id._get_edi_builder('ubl_bis3')
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

    def test_bank_details_import(self):
        acc_number = '1234567890'
        partner_bank = self.env['res.partner.bank'].create({
            'active': False,
            'acc_number': acc_number,
            'partner_id': self.partner_a.id
        })
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'in_invoice',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        # will not raise sql constraint because the sql is not commited yet
        self.env['account.edi.common']._import_partner_bank(invoice, [acc_number])
        self.assertFalse(invoice.partner_bank_id)

        partner_bank.active = True
        self.env['account.edi.common']._import_partner_bank(invoice, [acc_number])
        self.assertEqual(invoice.partner_bank_id, partner_bank)

    def test_invoice_optional_fields(self):
        """Test that optional invoice and invoice lines custom fields added by the user are exported correctly"""
        model_id = self.env["ir.model"]._get_id("account.move")
        invoice_fields = [
            ("x_studio_peppol_tax_point_date", "date"),
            ("x_studio_peppol_contract_document_reference_id", "char"),
            ("x_studio_peppol_despatch_document_reference_id", "char"),
            ("x_studio_peppol_accounting_cost", "char"),
            ("x_studio_peppol_project_reference_id", "char"),
            ("x_studio_peppol_order_reference_id", "char"),
            ("x_studio_peppol_invoice_period_start_date", "date"),
            ("x_studio_peppol_invoice_period_end_date", "date"),
        ]

        self.env["ir.model.fields"].create([{
                "name": name,
                "model": "account.move",
                "model_id": model_id,
                "ttype": ttype,
                "state": "manual",
            }
            for name, ttype in invoice_fields
        ])

        model_id = self.env["ir.model"]._get_id("account.move.line")
        invoice_line_fields = [
            ("x_studio_peppol_order_line_reference_id", "char"),
            ("x_studio_peppol_buyers_item_id", "char"),
        ]

        self.env["ir.model.fields"].create([{
                "name": name,
                "model": "account.move.line",
                "model_id": model_id,
                "ttype": ttype,
                "state": "manual",
            }
            for name, ttype in invoice_line_fields
        ])

        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'x_studio_peppol_order_line_reference_id': "order_line1-1234",
                    'x_studio_peppol_buyers_item_id': "item1-1234",
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'x_studio_peppol_order_line_reference_id': "order_line2-1234",
                    'x_studio_peppol_buyers_item_id': "item2-1234",
                })
            ],
            'x_studio_peppol_tax_point_date': "2028-01-01",
            'x_studio_peppol_contract_document_reference_id': "contract-1234",
            'x_studio_peppol_despatch_document_reference_id': "despatch-1234",
            'x_studio_peppol_accounting_cost': "88.5",
            'x_studio_peppol_project_reference_id': "project-1234",
            'x_studio_peppol_order_reference_id': "order-1234",
            'x_studio_peppol_invoice_period_start_date': "2028-01-01",
            'x_studio_peppol_invoice_period_end_date': "2028-02-01",
        })

        invoice.action_post()

        xml_content = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)

        tax_point_date = xml_tree.find('.//cbc:TaxPointDate', self.ubl_namespaces)
        self.assertEqual(tax_point_date.text, '2028-01-01')

        contract_document_reference_id = xml_tree.find('.//cac:ContractDocumentReference/cbc:ID', self.ubl_namespaces)
        self.assertEqual(contract_document_reference_id.text, 'contract-1234')

        despatch_document_reference_id = xml_tree.find('.//cac:DespatchDocumentReference/cbc:ID', self.ubl_namespaces)
        self.assertEqual(despatch_document_reference_id.text, 'despatch-1234')

        accounting_cost = xml_tree.find('.//cbc:AccountingCost', self.ubl_namespaces)
        self.assertEqual(accounting_cost.text, '88.5')

        project_reference_id = xml_tree.find('.//cac:ProjectReference/cbc:ID', self.ubl_namespaces)
        self.assertEqual(project_reference_id.text, 'project-1234')

        order_reference_id = xml_tree.find('.//cac:OrderReference/cbc:ID', self.ubl_namespaces)
        self.assertEqual(order_reference_id.text, 'order-1234')

        invoice_period_start_date = xml_tree.find('.//cac:InvoicePeriod/cbc:StartDate', self.ubl_namespaces)
        self.assertEqual(invoice_period_start_date.text, '2028-01-01')

        invoice_period_end_date = xml_tree.find('.//cac:InvoicePeriod/cbc:EndDate', self.ubl_namespaces)
        self.assertEqual(invoice_period_end_date.text, '2028-02-01')

        order_line_reference_id = xml_tree.findall('.//cac:InvoiceLine/cac:OrderLineReference/cbc:LineID', self.ubl_namespaces)
        self.assertEqual(order_line_reference_id[0].text, 'order_line1-1234')
        self.assertEqual(order_line_reference_id[1].text, 'order_line2-1234')

        buyers_item_id = xml_tree.findall('.//cac:InvoiceLine/cac:Item/cac:BuyersItemIdentification/cbc:ID', self.ubl_namespaces)
        self.assertEqual(buyers_item_id[0].text, 'item1-1234')
        self.assertEqual(buyers_item_id[1].text, 'item2-1234')

    def test_credit_note_optional_fields(self):
        """Test that optional credit note and credit note lines custom fields added by the user are exported correctly"""
        model_id = self.env["ir.model"]._get_id("account.move")

        credit_note_fields = [
            ("x_studio_peppol_tax_point_date", "date"),
            ("x_studio_peppol_contract_document_reference_id", "char"),
            ("x_studio_peppol_despatch_document_reference_id", "char"),
            ("x_studio_peppol_accounting_cost", "char"),
            ("x_studio_peppol_order_reference_id", "char"),
            ("x_studio_peppol_invoice_period_start_date", "date"),
            ("x_studio_peppol_invoice_period_end_date", "date"),
        ]

        self.env["ir.model.fields"].create([{
                "name": name,
                "model": "account.move",
                "model_id": model_id,
                "ttype": ttype,
                "state": "manual",
            }
            for name, ttype in credit_note_fields
        ])

        model_id = self.env["ir.model"]._get_id("account.move.line")
        credit_note_line_fields = [
            ("x_studio_peppol_order_line_reference_id", "char"),
            ("x_studio_peppol_buyers_item_id", "char"),
        ]

        self.env["ir.model.fields"].create([{
                "name": name,
                "model": "account.move",
                "model_id": model_id,
                "ttype": ttype,
                "state": "manual",
            }
            for name, ttype in credit_note_line_fields
        ])

        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_refund',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'x_studio_peppol_order_line_reference_id': "order_line1-1234",
                'x_studio_peppol_buyers_item_id': "item1-1234",
            }),
                Command.create({
                    'product_id': self.product_a.id,
                    'x_studio_peppol_order_line_reference_id': "order_line2-1234",
                    'x_studio_peppol_buyers_item_id': "item2-1234",
                })
            ],
            'x_studio_peppol_tax_point_date': "2028-01-01",
            'x_studio_peppol_contract_document_reference_id': "contract-1234",
            'x_studio_peppol_despatch_document_reference_id': "despatch-1234",
            'x_studio_peppol_accounting_cost': "88.5",
            'x_studio_peppol_order_reference_id': "order-1234",
            'x_studio_peppol_invoice_period_start_date': "2028-01-01",
            'x_studio_peppol_invoice_period_end_date': "2028-02-01",
        })

        invoice.action_post()

        xml_content = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        xml_tree = etree.fromstring(xml_content)

        tax_point_date = xml_tree.find('.//cbc:TaxPointDate', self.ubl_namespaces)
        self.assertEqual(tax_point_date.text, '2028-01-01')

        contract_document_reference_id = xml_tree.find('.//cac:ContractDocumentReference/cbc:ID', self.ubl_namespaces)
        self.assertEqual(contract_document_reference_id.text, 'contract-1234')

        despatch_document_reference_id = xml_tree.find('.//cac:DespatchDocumentReference/cbc:ID', self.ubl_namespaces)
        self.assertEqual(despatch_document_reference_id.text, 'despatch-1234')

        accounting_cost = xml_tree.find('.//cbc:AccountingCost', self.ubl_namespaces)
        self.assertEqual(accounting_cost.text, '88.5')

        order_reference_id = xml_tree.find('.//cac:OrderReference/cbc:ID', self.ubl_namespaces)
        self.assertEqual(order_reference_id.text, 'order-1234')

        invoice_period_start_date = xml_tree.find('.//cac:InvoicePeriod/cbc:StartDate', self.ubl_namespaces)
        self.assertEqual(invoice_period_start_date.text, '2028-01-01')

        invoice_period_end_date = xml_tree.find('.//cac:InvoicePeriod/cbc:EndDate', self.ubl_namespaces)
        self.assertEqual(invoice_period_end_date.text, '2028-02-01')

        order_line_reference_id = xml_tree.findall('.//cac:CreditNoteLine/cac:OrderLineReference/cbc:LineID', self.ubl_namespaces)
        self.assertEqual(order_line_reference_id[0].text, 'order_line1-1234')
        self.assertEqual(order_line_reference_id[1].text, 'order_line2-1234')

        buyers_item_id = xml_tree.findall('.//cac:CreditNoteLine/cac:Item/cac:BuyersItemIdentification/cbc:ID', self.ubl_namespaces)
        self.assertEqual(buyers_item_id[0].text, 'item1-1234')
        self.assertEqual(buyers_item_id[1].text, 'item2-1234')

    def test_payment_terms_immediate_in_cii_xml(self):
        self.partner_a.invoice_edi_format = 'facturx'
        invoice = self._create_invoice_one_line(
            product_id=self.product_a,
            partner_id=self.partner_a,
            invoice_date="2025-12-01",
            post=True,
        )

        xml_tree = etree.fromstring(self.env['account.edi.xml.cii']._export_invoice(invoice)[0])
        description = xml_tree.find('.//ram:SpecifiedTradePaymentTerms/ram:Description', self.namespaces)
        due_date = xml_tree.find('.//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString',
                                 self.namespaces)
        self.assertEqual(description.text, 'Immediate Payment')
        self.assertEqual(due_date.text, '20251201')

    def test_payment_terms_early_payment_discount_in_cii_xml(self):
        pay_terms = self.env['account.payment.term'].create({
            'name': '3% Before 15 Days',
            'note': 'Payment terms: 3% Before 15 Days',
            'early_discount': True,
            'discount_days': 15,
            'discount_percentage': 3.0,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 30,
            })],
        })
        partner = self.partner_a
        partner.invoice_edi_format = 'facturx'
        partner.property_payment_term_id = pay_terms.id
        partner.property_supplier_payment_term_id = pay_terms.id

        invoice = self._create_invoice_one_line(
            product_id=self.product_a,
            partner_id=self.partner_a,
            invoice_date="2025-12-01",
            post=True,
        )

        xml_tree = etree.fromstring(self.env['account.edi.xml.cii']._export_invoice(invoice)[0])
        description = xml_tree.find('.//ram:SpecifiedTradePaymentTerms/ram:Description', self.namespaces)
        due_date = xml_tree.find('.//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString',
                                 self.namespaces)
        days = xml_tree.find(
            './/ram:SpecifiedTradePaymentTerms/ram:ApplicableTradePaymentDiscountTerms/ram:BasisPeriodMeasure',
            self.namespaces)
        percent = xml_tree.find(
            './/ram:SpecifiedTradePaymentTerms/ram:ApplicableTradePaymentDiscountTerms/ram:CalculationPercent',
            self.namespaces)

        self.assertEqual(description.text, '3% Before 15 Days')
        self.assertEqual(due_date.text, '20251231')
        self.assertEqual(days.text, '15')
        self.assertEqual(percent.text, '3.0')
