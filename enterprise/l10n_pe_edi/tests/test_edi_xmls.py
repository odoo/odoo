# -*- coding: utf-8 -*
from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open
from .common import TestPeEdiCommon, mocked_l10n_pe_edi_post_invoice_web_service
from unittest.mock import patch

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiXmls(TestPeEdiCommon):

    def test_price_amount_rounding(self):
        with freeze_time(self.frozen_today), \
            patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice(invoice_line_ids=[(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 83.6,  # We will compute 250.8 / 3, which results in 83.60000000000001. It must be rounded.
                'quantity': 3,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })])
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            etree = self.get_xml_tree_from_string(edi_xml)
            price_amount = etree.find('.//{*}InvoiceLine/{*}Price/{*}PriceAmount')
            self.assertEqual(price_amount.text, '83.6')

    def test_invoice_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice()
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_invoice_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_refund_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_refund()
            (move.reversed_entry_id + move).action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_refund_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_debit_note_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_debit_note()
            (move.debit_origin_id + move).action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_debit_note_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_payment_term_detraction_case(self):
        """ Invoice in USD with detractions and multiple payment term lines"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '001'
        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            update_vals_dict = {"l10n_pe_edi_operation_type": "1001",
                                "invoice_payment_term_id": self.env.ref("account.account_payment_term_advance_60days").id}
            invoice = self._create_invoice(**update_vals_dict).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/invoice_detraction_payment_terms.xml', 'rb') as expected_file:
            expected_etree = self.get_xml_tree_from_string(expected_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_detraction_with_decimal(self):
        """ Invoice in PEN with detraction containing decimal digits"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '019'

        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'invoice_payment_term_id': self.env.ref("account.account_payment_term_end_following_month").id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
                'l10n_pe_edi_operation_type': '1001',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'price_unit': 990.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/invoice_detraction_with_decimal.xml', 'rb') as expected_invoice_file:
            expected_etree = self.get_xml_tree_from_string(expected_invoice_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_detraction_with_decimal_foreign_currency(self):
        """ Invoice in USD with detraction containing decimal digits"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '019'

        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'currency_id': self.other_currency.id,
                'invoice_payment_term_id': self.env.ref("account.account_payment_term_end_following_month").id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
                'l10n_pe_edi_operation_type': '1001',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'price_unit': 990.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/invoice_detraction_with_decimal_foreign_currency.xml', 'rb') as expected_invoice_file:
            expected_etree = self.get_xml_tree_from_string(expected_invoice_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_low_unit_price_with_higher_decimal_precision(self):
        """ Invoice with a decimal precition of 4 digits for the product price
            and a non-zero unit price that is rounded to 0.00 in the decimal
            precision of the currency.
        """
        self.env.ref('product.decimal_price').digits = 4
        self.currency.rounding = 0.01
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            invoice_line_vals = {
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 0.0045,
                        'quantity': 100,
                        'tax_ids': [Command.set(self.tax_18.ids)],
                    })
                ],
            }
            move = self._create_invoice(**invoice_line_vals)
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)

            with file_open('l10n_pe_edi/tests/test_files/invoice_low_unit_price.xml', 'rb') as expected_file:
                expected_etree = self.get_xml_tree_from_string(expected_file.read())

            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_free(self):
        """ Test the UBL generated for an invoice that uses the '18% Free' tax
        (feature introduced in enterprise#56767)
        """
        tax_18_free = self.env['account.chart.template'].ref('tax_free_group')
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice(
                l10n_pe_edi_legend='1002',
                invoice_line_ids=[(0, 0, {
                    'product_id': self.product.id,
                    'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                    'price_unit': 2000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [(6, 0, tax_18_free.ids)],
                })],
            )
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)

            with file_open('l10n_pe_edi/tests/test_files/invoice_free.xml', 'rb') as expected_file:
                expected_etree = self.get_xml_tree_from_string(expected_file.read())

            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_isc(self):
        """ Test the UBL generated for an invoice that uses both the ISC and the IGV taxes.
        (feature introduced in enterprise#35280)
        """
        tax_isc = self.env['account.tax'].create({
            'name': 'tax_ics_20',
            'sequence': -1,  # So it precedes the IGV 18% tax
            'amount_type': 'percent',
            'amount': 20,
            'include_base_amount': True,
            'l10n_pe_edi_tax_code': '2000',
            'l10n_pe_edi_unece_category': 'S',
            'type_tax_use': 'sale',
            'tax_group_id': self.env['account.chart.template'].ref('tax_group_isc').id,
        })
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice(
                invoice_line_ids=[
                    (0, 0, {
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 2000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'tax_ids': [(6, 0, [tax_isc.id, self.tax_18.id])],
                    }),
                    (0, 0, {
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 2000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'tax_ids': [(6, 0, [self.tax_18.id])],
                    })
                ],
            )
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)

            with file_open('l10n_pe_edi/tests/test_files/invoice_isc.xml', 'rb') as expected_file:
                expected_etree = self.get_xml_tree_from_string(expected_file.read())
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_foreign_customer(self):
        """Invoice for a foreign customer"""
        co_identification_type = self.env['l10n_latam.identification.type'].sudo().create({
            "name": "Cédula de ciudadanía (CO)",
            "country_id": self.env.ref('base.co').id,
        })
        self.partner_a.write({
            "l10n_latam_identification_type_id": co_identification_type.id,
            "country_id": self.env.ref('base.co').id,
        })
        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'currency_id': self.other_currency.id,
                'invoice_payment_term_id': self.env.ref("account.account_payment_term_end_following_month").id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type02').id,
                'l10n_pe_edi_operation_type': '0200',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'price_unit': 990.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/foreign_customer.xml', 'rb') as expected_invoice_file:
            expected_etree = self.get_xml_tree_from_string(expected_invoice_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)
