# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.account_reports.tests.test_general_ledger_report import TestAccountReportsCommon
from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon

@tagged('post_install', 'post_install_l10n', '-at_install')
class AccountXmlPolizasWizard(TestMxEdiCommon, TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        """ Set up the test class for its own tests """
        super().setUpClass()

        # Setup the company
        cls.company = cls.company_data['company']
        cls.company_2 = cls.company_data_2['company']
        # Enforce old default expence account
        cls.company_data['default_account_expense'] = cls.env.ref(f'account.{cls.company.id}_cuenta601_84')
        cls.company_data_2['default_account_expense'] = cls.env.ref(f'account.{cls.company_2.id}_cuenta601_84')

        cls.company.vat = 'AAAA611013AAA'
        cls.company_2.vat = 'P&G851223B24'
        cls.wizard = cls.env['l10n_mx_xml_polizas.xml_polizas_wizard'].create({
            "export_type": 'AF',
            "order_number": "ABC6987654/99",
        })
        cls.tax_16.tax_exigibility = 'on_invoice'

        # Create moves to check the export
        cls.moves_company_1 = cls.env['account.move'].create([{
                'move_type': 'entry',
                'date': date(2016, 1, 1),
                'journal_id': cls._get_id('journal_misc'),
                'line_ids': [
                    (0, 0, {'debit': 100.0, 'credit': 0.0, 'name': '2016_1_1', 'account_id': cls._get_id('account_payable')}),
                    (0, 0, {'debit': 200.0, 'credit': 0.0, 'name': '2016_1_2', 'account_id': cls._get_id('account_expense')}),
                    (0, 0, {'debit': 0.0, 'credit': 300.0, 'name': '2016_1_3', 'account_id': cls._get_id('account_revenue')}),
                ],
            }, {
                'move_type': 'entry',
                'date': date(2016, 6, 15),
                'journal_id': cls._get_id('journal_misc'),
                'line_ids': [
                    (0, 0, {'debit': 40.0, 'credit': 0.0, 'name': '2016_1b_1', 'account_id': cls._get_id('account_payable')}),
                    (0, 0, {'debit': 0.0, 'credit': 40.0, 'name': '2016_1b_1', 'account_id': cls._get_id('account_revenue')}),
                ],
            }, {
                'move_type': 'entry',
                'date': date(2017, 1, 1),
                'journal_id': cls._get_id('journal_misc'),
                'line_ids': [
                    (0, 0, {'debit': 1000.0, 'credit': 0.0, 'name': '2017_1_1', 'account_id': cls._get_id('account_receivable')}),
                    (0, 0, {'debit': 2000.0, 'credit': 0.0, 'name': '2017_1_2', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 3000.0, 'credit': 0.0, 'name': '2017_1_3', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 4000.0, 'credit': 0.0, 'name': '2017_1_4', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 5000.0, 'credit': 0.0, 'name': '2017_1_5', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 6000.0, 'credit': 0.0, 'name': '2017_1_6', 'account_id': cls._get_id('account_revenue')}),
                    (0, 0, {'debit': 0.0, 'credit': 6000.0, 'name': '2017_1_7', 'account_id': cls._get_id('account_expense')}),
                    (0, 0, {'debit': 0.0, 'credit': 7000.0, 'name': '2017_1_8', 'account_id': cls._get_id('account_expense')}),
                    (0, 0, {'debit': 0.0, 'credit': 8000.0, 'name': '2017_1_9', 'account_id': cls._get_id('account_expense')}),
                ],
            }
        ])
        cls.moves_company_1.action_post()

        cls.moves_company_2 = cls.env["account.move"].create([
            {
                'move_type': 'entry',
                'date': date(2016, 1, 1),
                'journal_id': cls._get_id('journal_misc', 2),
                'line_ids': [
                    (0, 0, {'debit': 100.0, 'credit': 0.0, 'name': '2016_2_1', 'account_id': cls._get_id('account_payable', 2)}),
                    (0, 0, {'debit': 0.0, 'credit': 100.0, 'name': '2016_2_2', 'account_id': cls._get_id('account_revenue', 2)}),
                ],
            }, {
                'move_type': 'entry',
                'date': date(2017, 6, 1),
                'journal_id': cls._get_id('journal_bank', 2),
                'line_ids': [
                    (0, 0, {'debit': 400.0, 'credit': 0.0, 'name': '2017_2_1', 'account_id': cls._get_id('account_expense', 2)}),
                    (0, 0, {'debit': 0.0, 'credit': 400.0, 'name': '2017_2_2', 'account_id': cls._get_id('account_revenue', 2)}),
                ],
            }
        ])
        cls.moves_company_2.action_post()

    @classmethod
    def _get_id(cls, name, company_no=1):
        """ Syntactic sugar method to simplify access to default accounts/journals """
        company_data = cls.company_data if company_no == 1 else cls.company_data_2
        return company_data['default_%s' % name].id

    def _get_xml_data(self, date_from, date_to, company=None):
        """ Fire the export wizard and get the generated XML and metadata (year, month, filename) """
        options = self._generate_options(self.env.ref('account_reports.general_ledger_report'), date_from, date_to)
        wizard = self.wizard.with_context(l10n_mx_xml_polizas_generation_options=options)
        if company:
            wizard = wizard.with_company(company)
        return wizard._get_xml_data()

    def _assert_export_equal(self, year, month, filename, expected_xml, actual_data):
        """ Compare that the given export output file corresponds to what is expected """
        actual_xml_tree = self.get_xml_tree_from_string(actual_data['content'])
        expected_xml_tree = self.get_xml_tree_from_string(expected_xml.encode())
        self.assertEqual(actual_data['year'], "%04d" % year)
        self.assertEqual(actual_data['month'], "%02d" % month)
        self.assertEqual(actual_data['filename'], filename)
        self.assertXmlTreeEqual(actual_xml_tree, expected_xml_tree)

    def test_xml_polizas_simple(self):
        """ Test a simple entry """
        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2017" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2017/01/0001">
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_1" DesCta="___ignore___" NumCta="105.01.01" Haber="0.00" Debe="1000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_2" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="2000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_3" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="3000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_4" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="4000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_5" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="5000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_6" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="6000.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_7" DesCta="___ignore___" NumCta="601.84.01" Haber="6000.00" Debe="0.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_8" DesCta="___ignore___" NumCta="601.84.01" Haber="7000.00" Debe="0.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_9" DesCta="___ignore___" NumCta="601.84.01" Haber="8000.00" Debe="0.00"></PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>"""
        exported_file = self._get_xml_data(date(2017, 1, 1), date(2017, 12, 31))[0]
        self._assert_export_equal(year=2017, month=1, filename='AAAA611013AAA201701PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)

    def test_xml_polizas_multicompany(self):
        """ For the same period, different move lines are exported for different companies"""
        date_from, date_to = date(2016, 1, 1), date(2016, 1, 31)

        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                         xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                         Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2016" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2016-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2016/01/0001">
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_1" DesCta="___ignore___" NumCta="201.01.01" Haber="0.00" Debe="100.00"></PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_2" DesCta="___ignore___" NumCta="601.84.01" Haber="0.00" Debe="200.00"></PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_3" DesCta="___ignore___" NumCta="401.01.01" Haber="300.00" Debe="0.00"></PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>"""
        exported_file = self._get_xml_data(date_from, date_to)[0]
        self._assert_export_equal(year=2016, month=1, filename='AAAA611013AAA201601PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)

        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                         xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                         Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2016" Mes="01" RFC="P&amp;G851223B24">
                 <PLZ:Poliza Fecha="2016-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2016/01/0001">
                      <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_2_1" DesCta="___ignore___" NumCta="201.01.01" Haber="0.00" Debe="100.00"></PLZ:Transaccion>
                      <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_2_2" DesCta="___ignore___" NumCta="401.01.01" Haber="100.00" Debe="0.00"></PLZ:Transaccion>
                 </PLZ:Poliza>
            </PLZ:Polizas>"""
        exported_file = self._get_xml_data(date_from, date_to, company=self.company_2)[0]
        self._assert_export_equal(year=2016, month=1, filename='P&G851223B24201601PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)

    def test_xml_polizas_split_by_date(self):
        """ Test that the moves are split by date into different files """
        exported_files = self._get_xml_data(date(2016, 1, 1), date(2016, 12, 31))
        expected_xml_jan = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                         xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                         Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2016" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2016-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2016/01/0001">
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_1" DesCta="___ignore___" NumCta="201.01.01" Haber="0.00" Debe="100.00"></PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_2" DesCta="___ignore___" NumCta="601.84.01" Haber="0.00" Debe="200.00"></PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1_3" DesCta="___ignore___" NumCta="401.01.01" Haber="300.00" Debe="0.00"></PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>"""
        jan_filename = 'AAAA611013AAA201601PL.XML'
        exported_jan_file = next((x for x in exported_files if x['filename'] == jan_filename), None)
        self.assertIsNotNone(exported_jan_file)
        self._assert_export_equal(year=2016, month=1, filename=jan_filename,
                                  expected_xml=expected_xml_jan, actual_data=exported_jan_file)

        expected_xml_jun = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
                         xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
                         Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2016" Mes="06" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2016-06-15" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2016/06/0001">
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1b_1" DesCta="___ignore___" NumCta="201.01.01" Haber="0.00" Debe="40.00"></PLZ:Transaccion>
                     <PLZ:Transaccion Concepto="Miscellaneous Operations - 2016_1b_1" DesCta="___ignore___" NumCta="401.01.01" Haber="40.00" Debe="0.00"></PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>"""
        jun_filename = 'AAAA611013AAA201606PL.XML'
        exported_jun_file = next((x for x in exported_files if x['filename'] == jun_filename), None)
        self.assertIsNotNone(exported_jun_file)
        self._assert_export_equal(year=2016, month=6, filename=jun_filename,
                                  expected_xml=expected_xml_jun, actual_data=exported_jun_file)

    def _get_xml_polizas_data(self, date_from, date_to, company=None):
        """ Fire the export wizard and get the generated XML and metadata (year, month, filename) """
        wizard = self.env['l10n_mx_xml_polizas.xml_polizas_wizard'].create({
            "export_type": 'AF',
            "order_number": "ABC6987654/99",
        })

        options = self._init_options(self.env['account.general.ledger'], date_from, date_to)
        wizard = wizard.with_context(l10n_mx_xml_polizas_generation_options=options)
        if company:
            wizard = wizard.with_company(company)
        return wizard._get_xml_data()

    def _fake_cfdi_values(self, moves):
        for move in moves:
            move.write({
                'l10n_mx_edi_cfdi_uuid': "AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA",
                'l10n_mx_edi_cfdi_supplier_rfc': "AAAA611013AAA",
                'l10n_mx_edi_cfdi_customer_rfc': "XEXX010101000",
                'l10n_mx_edi_cfdi_amount': 10.0,
            })
        moves.flush_recordset()

    def test_xml_edi_polizas_simple(self):
        """ Test XML Polizas is exported with CompNal info """

        invoice_a = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.company_data['currency'].id,
            'invoice_incoterm_id': self.env.ref('account.incoterm_FCA').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, (self.tax_16 + self.tax_10_ret_isr).ids)],
            })],
        })

        with freeze_time(self.frozen_today):
            invoice_a.action_post()
            self._fake_cfdi_values(invoice_a)
        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo" xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd" Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2017" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2017/01/0001">
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_1" DesCta="___ignore___" NumCta="105.01.01" Haber="0.00" Debe="1000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_2" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="2000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_3" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="3000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_4" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="4000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_5" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="5000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_6" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="6000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_7" DesCta="___ignore___" NumCta="601.84.01" Haber="6000.00" Debe="0.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_8" DesCta="___ignore___" NumCta="601.84.01" Haber="7000.00" Debe="0.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_9" DesCta="___ignore___" NumCta="601.84.01" Haber="8000.00" Debe="0.00">
                      </PLZ:Transaccion>
                </PLZ:Poliza>
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Customer Invoices" NumUnIdenPol="INV/2017/00001">
                    <PLZ:Transaccion Concepto="Customer Invoices - 10% WH L I" DesCta="___ignore___" NumCta="216.03.01" Haber="0.00" Debe="800.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="800.00"></PLZ:CompNal>
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - 16%" DesCta="___ignore___" NumCta="208.01.01" Haber="1280.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-1280.00"></PLZ:CompNal>
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - INV/2017/00001" DesCta="___ignore___" NumCta="105.01.01" Haber="0.00" Debe="8480.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="8480.00"></PLZ:CompNal>
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - [product_mx] product_mx" DesCta="___ignore___" NumCta="401.01.01" Haber="8000.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-8000.00"></PLZ:CompNal>
                      </PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>
            """

        exported_file = self._get_xml_data(date(2017, 1, 1), date(2017, 12, 31))[0]
        self._assert_export_equal(year=2017, month=1, filename='AAAA611013AAA201701PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)

    def test_xml_edi_polizas_vendor_bill(self):
        """ Test XML Polizas is exported with CompNal info """

        self.partner_a.write({
            'country_id': self.env.ref('base.mx').id,
            'l10n_mx_type_of_operation': '85',
            'vat': 'XAXX010101000'
        })
        self.partner_a.flush_recordset()
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.company_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [],
                'account_id': self.company_data['default_account_expense'].id,
            })],
        })

        with freeze_time(self.frozen_today):
            bill.action_post()
            self._fake_cfdi_values(bill)
        bill.line_ids.flush_recordset()
        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo" xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd" Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2017" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2017/01/0001">
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_1" DesCta="___ignore___" NumCta="105.01.01" Haber="0.00" Debe="1000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_2" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="2000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_3" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="3000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_4" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="4000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_5" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="5000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_6" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="6000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_7" DesCta="___ignore___" NumCta="601.84.01" Haber="6000.00" Debe="0.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_8" DesCta="___ignore___" NumCta="601.84.01" Haber="7000.00" Debe="0.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_9" DesCta="___ignore___" NumCta="601.84.01" Haber="8000.00" Debe="0.00">
                      </PLZ:Transaccion>
                </PLZ:Poliza>
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Vendor Bills" NumUnIdenPol="BILL/2017/01/0001">
                    <PLZ:Transaccion Concepto="Vendor Bills" DesCta="___ignore___" NumCta="201.01.01" Haber="8000.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XAXX010101000" MontoTotal="-8000.00"></PLZ:CompNal>
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Vendor Bills - [product_mx] product_mx" DesCta="___ignore___" NumCta="601.84.01" Haber="0.00" Debe="8000.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XAXX010101000" MontoTotal="8000.00"></PLZ:CompNal>
                      </PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>
            """

        exported_file = self._get_xml_data(date(2017, 1, 1), date(2017, 12, 31))[0]
        self._assert_export_equal(year=2017, month=1, filename='AAAA611013AAA201701PL.XML',
                expected_xml=expected_xml, actual_data=exported_file)

    def test_xml_edi_polizas_multicurrency(self):
        """ Test XML Polizas is exported with CompNal info (multicurrency data)"""
        cur_eur = self.env.ref('base.EUR')
        cur_eur.active = True
        self.env['res.currency.rate'].create({
            'name': '2017-01-01',
            'rate': 0.05,
            'currency_id': cur_eur.id,
            'company_id': self.env.company.id,
        })

        self.env['res.currency.rate'].create({
            'name': '2017-01-02',
            'rate': 0.055,
            'currency_id': cur_eur.id,
            'company_id': self.env.company.id,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': cur_eur.id,
            'invoice_incoterm_id': self.env.ref('account.incoterm_FCA').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'tax_ids': [(6, 0, (self.tax_16 + self.tax_10_ret_isr).ids)],
            })],
        })

        with freeze_time(self.frozen_today):
            invoice.action_post()
            payment = self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({
                    'currency_id': self.company_data['currency'].id,
                    'amount': 1820.0,
                    'payment_date': '2017-01-02',
                })\
                ._create_payments()
            self._fake_cfdi_values(invoice + payment.move_id)

        expected_xml = """<?xml version='1.0' encoding='utf-8'?>
            <PLZ:Polizas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:PLZ="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo" xsi:schemaLocation="http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd" Version="1.3" TipoSolicitud="AF" NumOrden="ABC6987654/99" Anio="2017" Mes="01" RFC="AAAA611013AAA">
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Miscellaneous Operations" NumUnIdenPol="MISC/2017/01/0001">
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_1" DesCta="___ignore___" NumCta="105.01.01" Haber="0.00" Debe="1000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_2" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="2000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_3" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="3000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_4" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="4000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_5" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="5000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_6" DesCta="___ignore___" NumCta="401.01.01" Haber="0.00" Debe="6000.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_7" DesCta="___ignore___" NumCta="601.84.01" Haber="6000.00" Debe="0.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_8" DesCta="___ignore___" NumCta="601.84.01" Haber="7000.00" Debe="0.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Miscellaneous Operations - 2017_1_9" DesCta="___ignore___" NumCta="601.84.01" Haber="8000.00" Debe="0.00">
                      </PLZ:Transaccion>
                </PLZ:Poliza>
                <PLZ:Poliza Fecha="2017-01-01" Concepto="Customer Invoices" NumUnIdenPol="INV/2017/00001">
                    <PLZ:Transaccion Concepto="Customer Invoices - 10% WH L I" DesCta="___ignore___" NumCta="216.03.01" Haber="0.00" Debe="10000.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="500.00" Moneda="EUR" TipCamb="20.00000"/>
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - 16%" DesCta="___ignore___" NumCta="208.01.01" Haber="16000.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-800.00" Moneda="EUR" TipCamb="20.00000"/>
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - INV/2017/00001" DesCta="___ignore___" NumCta="105.01.01" Haber="0.00" Debe="106000.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="5300.00" Moneda="EUR" TipCamb="20.00000"/>
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Customer Invoices - [product_mx] product_mx" DesCta="___ignore___" NumCta="401.01.01" Haber="100000.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-5000.00" Moneda="EUR" TipCamb="20.00000"/>
                      </PLZ:Transaccion>
                </PLZ:Poliza>
                <PLZ:Poliza Fecha="2017-01-02" Concepto="Bank" NumUnIdenPol="PBNK1/2017/00001">
                    <PLZ:Transaccion Concepto="Bank - Manual Payment: INV/2017/00001" DesCta="___ignore___" NumCta="102.01.04" Haber="0.00" Debe="1820.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="1820.00"/>
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Bank - Manual Payment: INV/2017/00001" DesCta="___ignore___" NumCta="105.01.01" Haber="1820.00" Debe="0.00">
                        <PLZ:CompNal UUID_CFDI="AAAAAAAA-ABCD-ABCD-ABCD-AAAAAAAAAAAA" RFC="XEXX010101000" MontoTotal="-1820.00"/>
                      </PLZ:Transaccion>
                </PLZ:Poliza>
                <PLZ:Poliza Fecha="2017-01-31" Concepto="Exchange Difference" NumUnIdenPol="EXCH/2017/01/0001">
                    <PLZ:Transaccion Concepto="Exchange Difference - Currency exchange rate difference" DesCta="___ignore___" NumCta="105.01.01" Haber="182.00" Debe="0.00">
                      </PLZ:Transaccion>
                    <PLZ:Transaccion Concepto="Exchange Difference - Currency exchange rate difference" DesCta="___ignore___" NumCta="701.01.01" Haber="0.00" Debe="182.00">
                      </PLZ:Transaccion>
                </PLZ:Poliza>
            </PLZ:Polizas>
        """
        exported_file = self._get_xml_data(date(2017, 1, 1), date(2017, 12, 31))[0]
        self._assert_export_equal(year=2017, month=1, filename='AAAA611013AAA201701PL.XML',
                                  expected_xml=expected_xml, actual_data=exported_file)
