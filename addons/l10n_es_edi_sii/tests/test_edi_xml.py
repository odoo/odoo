# coding: utf-8
from .common import TestEsEdiCommon, mocked_l10n_es_edi_call_web_service_sign


from freezegun import freeze_time
from unittest.mock import patch
from lxml import etree

from odoo import Command
from odoo.tools import misc
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiXmls(TestEsEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('USD')

        cls.certificate.write({
            'date_start': '2019-01-01 01:00:00',
            'date_end': '2021-01-01 01:00:00',
        })

    def assertXmlEqual(self, xml1, xml2):
        def xml_to_dict(element):
            result = {
                'tag': element.tag,
                'text': (element.text or '').strip(),
                'children': sorted([xml_to_dict(c) for c in element], key=str),
            }
            return result
        self.assertEqual(
           xml_to_dict(etree.fromstring(xml1)),
           xml_to_dict(etree.fromstring(xml2)),
            )

    def test_010_out_invoice_s_iva10b_s_iva21s(self):
        """ Invoice with goods and services as they need to be reported in different sections for customer invoices. """
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva21s').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_010_out_invoice_s_iva10b_s_iva21s.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_020_out_invoice_s_iva10b_s_iva0_ns(self):
        """ The ns tax is a special case with l10n_es_type ignore and should not appear in what we send"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_b.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_ns').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_020_out_invoice_s_iva10b_s_iva0_ns.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_030_out_invoice_s_iva10b_s_req014_s_iva21s_s_req52(self):
        """Recargo de Equivalencia with 2 different taxes and 2 different IVAs as it is reported in the same tag as the IVA"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [Command.set((self._get_tax_by_xml_id('s_iva10b') + self._get_tax_by_xml_id('s_req014')).ids)],
                    },
                    {
                        'price_unit': 50.0,
                        'tax_ids': [Command.set((self._get_tax_by_xml_id('s_iva10b') + self._get_tax_by_xml_id('s_req014')).ids)],
                    },
                    {
                        'price_unit': 200.0,
                        'tax_ids': [Command.set((self._get_tax_by_xml_id('s_iva21s') + self._get_tax_by_xml_id('s_req52')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_030_out_invoice_s_iva10b_s_req014_s_iva21s_s_req52.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_040_out_refund_s_iva10b_s_iva10b_s_iva21s(self):
        """For a customer refund, the amounts need to be reported as negative and also have goods and services separate"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva10b').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva21s').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_040_out_refund_s_iva10b_s_iva10b_s_iva21s.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_050_out_invoice_s_iva0_sp_i_s_iva0_g_i(self):
        """An intra-community sale needs to be reported as exempt and intra-community services as no sujeto por reglas de localizacion (no_sujeto_loc)"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_i').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_050_out_invoice_s_iva0_sp_i_s_iva0_g_i.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_060_out_refund_s_iva0_sp_i_s_iva0_g_i(self):
        """ Intra-community refund of service and good"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_i').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_060_out_refund_s_iva0_sp_i_s_iva0_g_i.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_070_out_invoice_s_iva_e_s_iva0_g_e(self):
        """ Export of service (no sujeto por reglas de localization) and export of goods (exempt)"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva_e').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_e').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_070_out_invoice_s_iva_e_s_iva0_g_e.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_080_out_refund_s_iva0_sp_i_s_iva0_g_i(self):
        """Customer refund of an intracom good and service"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_i').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_080_out_refund_s_iva0_sp_i_s_iva0_g_i.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_085_out_refund_s_iva0_sp_i_s_iva0_g_i_multi_currency(self):
        """ Same as test_080 but in multi-currency"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                currency_id=self.other_currency.id,
                invoice_line_ids=[
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_sp_i').ids)]},
                    {'price_unit': 400.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva0_g_i').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_085_out_refund_s_iva0_sp_i_s_iva0_g_i_multi_currency.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_090_in_invoice_p_iva10_bc_p_irpf19_p_iva21_sc_p_irpf19(self):
        """ Vendor bill 10% IVA 19% retention, 21% IVA 19% retention
        The retention just needs to be ignored basically, but in the ImporteTotal,
        we need the amount before retention (withholding). """
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf19')).ids)],
                    },
                    {
                        'price_unit': 200.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva21_sc') + self._get_tax_by_xml_id('p_irpf19')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_090_in_invoice_p_iva10_bc_p_irpf19_p_iva21_sc_p_irpf19.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_100_in_refund_p_iva10_bc(self):
        """Vendor bill refund of VAT 10% goods"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_refund',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva10_bc').ids)]}],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_100_in_refund_p_iva10_bc.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_110_in_invoice_p_iva10_bc_p_req014_p_iva21_sc_p_req52(self):
        """Vendor bill with recargo de equivalencia that needs to be reported within the VAT tax"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_req014')).ids)],
                    },
                    {
                        'price_unit': 200.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva21_sc') + self._get_tax_by_xml_id('p_req52')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_110_in_invoice_p_iva10_bc_p_req014_p_iva21_sc_p_req52.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_120_in_invoice_p_iva21_sp_ex(self):
        """ Extra-community vendor bill with reverse charge (-100 line which changes importetotal)"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_sp_ex').ids)]}],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_120_in_invoice_p_iva21_sp_ex.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_130_in_invoice_p_iva0_ns_p_iva10_bc(self):
        """Vendor bill with a line of no sujeto services and a line of 10% goods.  Here, there is no separation between goods and services"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva0_ns').ids)]},
                    {'price_unit': 200.0, 'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva10_bc').ids)]},
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_130_in_invoice_p_iva0_ns_p_iva10_bc.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_140_out_invoice_s_iva10b_s_irpf1(self):
        """Customer invoice with a 10% VAT and a retention.  The retention should not be deducted from the importetotal."""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                partner_id=self.partner_b.id,
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('s_iva10b') + self._get_tax_by_xml_id('s_irpf1')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_140_out_invoice_s_iva10b_s_irpf1.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_150_in_invoice_p_iva10_bc_p_irpf1(self):
        """Same as test_140 but for vendor bills"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf1')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_150_in_invoice_p_iva10_bc_p_irpf1.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_160_in_refund_p_iva10_bc_p_irpf1(self):
        """Same as 150 but for supplier refunds.  The amounts need to be negative. """
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_refund',
                ref='sup0001',
                partner_id=self.partner_b.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf1')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_160_in_refund_p_iva10_bc_p_irpf1.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_165_in_refund_p_iva10_bc_p_irpf1_multi_currency(self):
        """Same as test_160, but with another currency.  With double the amounts, the result is the same. """
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_refund',
                ref='sup0001',
                partner_id=self.partner_b.id,
                currency_id=self.other_currency.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 200.0,
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva10_bc') + self._get_tax_by_xml_id('p_irpf1')).ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_165_in_refund_p_iva10_bc_p_irpf1_multi_currency.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_170_in_invoice_dua(self):
        """DUA invoice.  The TipoFactura needs to change as well as the importetotal needs to include the base. """
        with freeze_time(self.frozen_today), patch(
                'odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                new=mocked_l10n_es_edi_call_web_service_sign
        ):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='fakedua',
                partner_id=self.partner_b.id,
                currency_id=self.other_currency.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'tax_ids': [(6, 0, (self._get_tax_by_xml_id('p_iva21_ibc_group').ids))],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_170_in_invoice_dua.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_180_in_invoice_iva21_sp_in_iva21_ic_bc(self):
        """ For intra-community purchase of services and goods, the -100 needs to be taken into account in the importe total.
        The clave should also change to 09. """
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_a.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_sp_in').ids)],
                    },
                    {
                        'price_unit': 200.0,
                        'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_ic_bc').ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_180_in_invoice_iva21_sp_in_iva21_ic_bc.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_190_in_refund_iva21_sp_in_iva21_ic_bc(self):
        """ For intra-community purchase return services and goods, the -100 needs to be taken into account in the importe total.
        For a refund, the type should change to R4"""
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_refund',
                ref='sup0001',
                partner_id=self.partner_a.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 100.0,
                        'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_sp_in').ids)],
                    },
                    {
                        'price_unit': 200.0,
                        'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_ic_bc').ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_190_in_refund_iva21_sp_in_iva21_ic_bc.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_200_in_invoice_p_iva12_agr(self):
        """ For bills with the 12% agricuture tax the Clave Regime Special should be E2
        """
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            invoice = self.create_invoice(
                move_type='in_invoice',
                ref='sup0001',
                partner_id=self.partner_a.id,
                l10n_es_registration_date='2019-01-02',
                invoice_line_ids=[
                    {
                        'price_unit': 200.0,
                        'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva12_agr').ids)],
                    },
                ],
            )
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)
            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_200_in_invoice_p_iva12_agr.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)

    def test_out_invoice_period_match_tax_periodicity(self):
        """
        Test that an invoice in April correctly reflects the '2T' period
        when the company's tax periodicity is set to 'trimester'
        and '0A' when the tax periodicity is set to 'year
        """
        self.ensure_installed('account_reports')
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_es_edi_sii.models.account_edi_format.AccountEdiFormat._l10n_es_edi_call_web_service_sign',
                   new=mocked_l10n_es_edi_call_web_service_sign):
            self.env.company.account_tax_periodicity = 'trimester'
            invoice = self._create_invoice(
                date='2019-04-02',
                post=True,
            )

            generated_files = self._process_documents_web_services(invoice, {'es_sii'})
            self.assertTrue(generated_files)

            with misc.file_open('l10n_es_edi_sii/tests/expected_xml/test_out_invoice_period_match_tax_periodicity.xml', 'rb') as f:
                expected_xml = f.read()
            self.assertXmlEqual(generated_files[0], expected_xml)
