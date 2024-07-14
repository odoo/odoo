# -*- coding: utf-8 -*-
import os

from freezegun import freeze_time
from unittest.mock import patch


from odoo.tools import misc
from odoo.tests import tagged
from .common import TestL10nClEdiCommon, _check_with_xsd_patch


@tagged('post_install_l10n', 'post_install', '-at_install')
@patch('odoo.tools.xml_utils._check_with_xsd', _check_with_xsd_patch)
class TestL10nClDte(TestL10nClEdiCommon):
    """
    Summary of the document types to test:
        - 33:
            - A invoice with tax in each line
            - A invoice with references_ids and tax in each line
            - A invoice with holding taxes
            - A invoice with discounts
        - 34:
            - A invoice with two lines
        - 56:
            - A  invoice with line discounts
        - 110:
            - An exportation invoice for services
    """

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_dte_33(self):
        self.tax_19 = self.env['account.tax'].search([
            ('name', '=', '19%'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': self.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_date_due': '2019-10-23',
            'invoice_date': '2019-10-23',
            'currency_id': self.env.ref('base.CLP').id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_a_f_dte').id,
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Tapa Ranurada UL FM 300 6"',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 26,
                'price_unit': 2391.0,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': 'Copla Flexible 1NS 6"',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 80,
                'price_unit': 2914.0,
                'tax_ids': [self.tax_19.id],
            })],
        })

        invoice.with_context(skip_xsd=True).action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')
        xml_expected_dte = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'expected_dtes', 'dte_33.xml')).read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_sii_send_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode())
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_dte_33_with_reference_ids(self):
        self.tax_19 = self.env['account.tax'].search([
            ('name', '=', '19%'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': self.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_date': '2019-10-23',
            'invoice_date_due': '2019-10-23',
            'currency_id': self.env.ref('base.CLP').id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_a_f_dte').id,
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Tapa Ranurada UL FM 300 6"',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 26,
                'price_unit': 2391.0,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': 'Copla Flexible 1NS 6"',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 80,
                'price_unit': 2914.0,
                'tax_ids': [self.tax_19.id],
            })],
        })
        invoice.write({
            'l10n_cl_reference_ids': [(0, 0, {
                'origin_doc_number': 'PO00273',
                'l10n_cl_reference_doc_type_id': self.env.ref('l10n_cl.dc_odc').id,
                'reason': 'Test',
                'move_id': invoice.id,
                'date': '2019-10-18'
            }), (0, 0, {
                'origin_doc_number': '996327',
                'l10n_cl_reference_doc_type_id': self.env.ref('l10n_cl.dc_gd_dte').id,
                'reason': 'Test',
                'move_id': invoice.id,
                'date': '2019-10-18'
            })],
        })

        invoice.with_context(skip_xsd=True)._post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'expected_dtes', 'dte_33_with_reference_ids.xml')).read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_sii_send_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode()),
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_dte_33_withholding_taxes(self):
        self.tax_19 = self.env['account.tax'].search([
            ('name', '=', '19%'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])
        self.tax_205 = self.env['account.tax'].search([
            ('name', '=', '20.5% ILA'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])
        self.tax_100 = self.env['account.tax'].search([
            ('name', '=', '10% ILA'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])

        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': self.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_date': '2019-10-23',
            'invoice_date_due': '2019-10-23',
            'currency_id': self.env.ref('base.CLP').id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_a_f_dte').id,
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'FALERNIA CABERNET SAUVIGNON RESERVA 2018 750ML 14',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 31110.0,
                'tax_ids': [self.tax_19.id, self.tax_205.id],
            }), (0, 0, {
                'name': 'FALERNIA CARMENERE 2017 RESERVA 14 750ML',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 31110.0,
                'tax_ids': [self.tax_19.id, self.tax_205.id],
            }), (0, 0, {
                'name': 'FAL CARMENERE 2017 375CC',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 36210.0,
                'tax_ids': [self.tax_19.id, self.tax_205.id],
            }), (0, 0, {
                'name': 'FALERNIA CARMENERE GRAN RESERVA 2016 750ML 15',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 26138.0,
                'tax_ids': [self.tax_19.id, self.tax_205.id],
            }), (0, 0, {
                'name': 'FALERNIA C. SAUVIGNON GR.RESERVA 2017 750ML 14,5',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 26138.0,
                'tax_ids': [self.tax_19.id, self.tax_205.id],
            }), (0, 0, {
                'name': 'COCA COLA NO RETORNABLE 2L',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 12,
                'price_unit': 800.0,
                'tax_ids': [self.tax_19.id, self.tax_100.id],
            }), (0, 0, {
                'name': 'COSTO LOGISTICO',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 7143.0,
                'tax_ids': [self.tax_19.id],
            }), ],
        })

        invoice.with_context(skip_xsd=True).action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'expected_dtes', 'dte_33_with_holding_taxes.xml')).read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_sii_send_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode()),
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_dte_33_with_discounts(self):
        self.tax_19 = self.env['account.tax'].search([
            ('name', '=', '19%'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': self.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_date': '2019-10-23',
            'invoice_date_due': '2019-10-23',
            'currency_id': self.env.ref('base.CLP').id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_a_f_dte').id,
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Tapa Ranurada UL FM 300 6"',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 200,
                'price_unit': 5.0,
                'discount': 5.99,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': 'Copla Flexible 1NS 6"',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 300,
                'price_unit': 800.0,
                'discount': 9.77,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': 'Desk Combination',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 5,
                'price_unit': 40000.0,
                'discount': 10.00,
                'tax_ids': [self.tax_19.id],
            })],
        })

        invoice.with_context(skip_xsd=True).action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'expected_dtes', 'dte_33_with_discounts.xml')).read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_sii_send_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode()),
        )

    @freeze_time('2022-11-24T12:45:37', tz_offset=3)
    def test_l10n_cl_dte_33_usd_with_discounts(self):
        self.tax_19 = self.env['account.tax'].search([
            ('name', '=', '19%'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])
        currency_usd = self.env.ref('base.USD')
        currency_usd.active = True
        self.env['res.currency.rate'].create({
            'name': '2022-11-24',
            'company_id': self.company_data['company'].id,
            'currency_id': currency_usd.id,
            'rate': 0.001069187097})
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': self.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_date': '2022-11-24',
            'currency_id': self.env.ref('base.USD').id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_a_f_dte').id,
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Tapa Ranurada UL FM 300 6"',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 2,
                'price_unit': 123.45,
                'discount': 10,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': 'Copla Flexible 1NS 6"',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 12.31,
                'discount': 5,
                'tax_ids': [self.tax_19.id],
            })],
        })

        invoice.action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open('l10n_cl_edi/tests/expected_dtes/dte_33_usd_with_discounts.xml').read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_sii_send_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode()),
        )

    @freeze_time('2019-10-22T20:23:27', tz_offset=3)
    def test_l10n_cl_dte_34(self):
        self.product_a.write({
            'name': 'Desk Combination',
            'default_code': 'FURN_7800'
        })

        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': self.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_date': '2019-10-22',
            'invoice_date_due': '2019-10-22',
            'currency_id': self.env.ref('base.CLP').id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_y_f_dte').id,
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Desk Combination',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 1200000.0,
                'tax_ids': [],
            }), (0, 0, {
                'name': 'Desk Combination',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 2400000.0,
                'tax_ids': [],
            })],
        })

        invoice.with_context(skip_xsd=True).action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'expected_dtes', 'dte_34.xml')).read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_sii_send_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode()),
        )

    @freeze_time('2019-10-24T20:00:00', tz_offset=3)
    def test_l10n_cl_dte_56(self):
        self.tax_19 = self.env['account.tax'].search([
            ('name', '=', '19%'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])

        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': self.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_date': '2019-10-23',
            'invoice_date_due': '2019-10-23',
            'currency_id': self.env.ref('base.CLP').id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_nd_f_dte').id,
            'l10n_latam_document_number': '122',
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'name': '[WUS-0558538] Conjunto De Control Electrónico Ps3.39',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'discount': 10.00,
                'price_unit': 497804.44,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': '[WUS-0558424A] Vastago Ps 3.39',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 171375.56,
                'discount': 10.00,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': '[WUS-0555217] Filtro Malla Acero',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 6801.11,
                'discount': 10.00,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': '[WUS-0524421] Retenedor Wagner 339',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 19722.22,
                'discount': 10.00,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': '[INSUMO] Insumos Varios',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 2,
                'price_unit': 4760.00,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': '[SERVICIO03] Servicio de Reparación Equipo Airless (Fieldlazer, 695-MarkV, PS3.29-3.39)',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 114250.00,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': '[WUS-0558587] Kit Reparación Ps3 .39',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 150973.33,
                'discount': 10.00,
                'tax_ids': [self.tax_19.id],
            }), ],
        })

        invoice.write({
            'l10n_cl_reference_ids': [[0, 0, {
                'move_id': invoice.id,
                'origin_doc_number': 1961,
                'l10n_cl_reference_doc_type_id': self.env.ref('l10n_cl.dc_nc_f_dte').id,
                'reference_doc_code': '1',
                'reason': 'Anulación NC por aceptación con reparo (N/C 001961)',
                'date': invoice.invoice_date, }, ], ]
        })

        invoice.with_context(skip_xsd=True).action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open(os.path.join(
            'l10n_cl_edi', 'tests', 'expected_dtes', 'dte_56.xml')).read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_dte_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode()),
        )
