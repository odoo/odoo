# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBEIntrastatReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.be')
        italy = cls.env.ref('base.it')
        cls.company_data['company'].company_registry = '0123456789'
        cls.report = cls.env.ref('account_intrastat.intrastat_report')
        cls.report_handler = cls.env['account.intrastat.report.handler']
        cls.partner_a = cls.env['res.partner'].create({
            'name': "Miskatonic University",
            'country_id': italy.id,
        })

        cls.product_aeroplane = cls.env['product.product'].create({
            'name': 'Dornier Aeroplane',
            'intrastat_code_id': cls.env.ref('account_intrastat.commodity_code_2018_88023000').id,
            'intrastat_supplementary_unit_amount': 1,
            'weight': 3739,
        })
        cls.product_samples = cls.env['product.product'].create({
            'name': 'Interesting Antarctic Rock and Soil Specimens',
            'intrastat_code_id': cls.env.ref('account_intrastat.commodity_code_2023_25309050').id,
            'weight': 19,
        })
        cls.inwards_vendor_bill = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-05-15',
            'date': '2022-05-15',
            'intrastat_country_id': italy.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                'product_id': cls.product_samples.id,
                'quantity': 42,
                'price_unit': 555.44,
            })]
        })
        cls.outwards_customer_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-05-15',
            'date': '2022-05-15',
            'intrastat_country_id': italy.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'product_id': cls.product_aeroplane.id,
                'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                'quantity': 4,
                'price_unit': 234000,
            })]
        })

        # This tree represents the export with both kinds of reports (the extended version)
        cls.expected_content_all = b'''
        <DeclarationReport xmlns="http://www.onegate.eu/2010-01-01">
            <Administration>
                <From declarerType="KBO">0123456789</From>
                <To>NBB</To>
                <Domain>SXX</Domain>
            </Administration>
            <Report action="replace" code="EX19E" date="2022-05">
                <Data close="true" form="EXF19E">
                    <Item>
                        <Dim prop="EXTRF">19</Dim>
                        <Dim prop="EXCNT">IT</Dim>
                        <Dim prop="EXTTA">11</Dim>
                        <Dim prop="EXTGO">25309050</Dim>
                        <Dim prop="EXTXVAL">23328.48</Dim>
                        <Dim prop="EXWEIGHT">798.00</Dim>
                        <Dim prop="EXTPC"></Dim>
                        <Dim prop="EXDELTRM"></Dim>
                    </Item>
                </Data>
            </Report>
            <Report action="replace" code="INTRASTAT_X_E" date="2022-05">
                <Data close="true" form="INTRASTAT_X_EF">
                    <Item>
                        <Dim prop="EXTRF">29</Dim>
                        <Dim prop="EXCNT">IT</Dim>
                        <Dim prop="EXTTA">11</Dim>
                        <Dim prop="EXTGO">88023000</Dim>
                        <Dim prop="EXTXVAL">936000.00</Dim>
                        <Dim prop="EXWEIGHT">14956.00</Dim>
                        <Dim prop="EXUNITS">4.0</Dim>
                        <Dim prop="EXCNTORI">QU</Dim>
                        <Dim prop="PARTNERID">QV999999999999</Dim>
                        <Dim prop="EXTPC"></Dim>
                        <Dim prop="EXDELTRM"></Dim>
                   </Item>
                </Data>
            </Report>
        </DeclarationReport>
        '''

    def test_dispatches_only(self):
        """ Test generating an XML export containing only dispatches (when only the dispatches options is checked) """
        self.inwards_vendor_bill.action_post()
        self.outwards_customer_invoice.action_post()

        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')
        arrivals, dispatches = options['intrastat_type']
        arrivals['selected'], dispatches['selected'] = False, True
        options = self.report.get_options(options)

        dispatches_only_tree = etree.fromstring(self.report_handler.be_intrastat_export_to_xml(options)['file_content'])
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.expected_content_all),
            '''
            <xpath expr="//{http://www.onegate.eu/2010-01-01}Report[@code='EX19E']" position="replace"></xpath>
            '''
        )
        self.assertXmlTreeEqual(dispatches_only_tree, expected_tree)

    def test_arrivals_only(self):
        """ Test generating an XML export containing only arrivals (when only the arrivals options is checked)  """
        self.inwards_vendor_bill.action_post()
        self.outwards_customer_invoice.action_post()

        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')
        arrivals, dispatches = options['intrastat_type']
        arrivals['selected'], dispatches['selected'] = True, False
        options = self.report.get_options(options)
        arrivals_only_tree = etree.fromstring(self.report_handler.be_intrastat_export_to_xml(options)['file_content'])
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.expected_content_all),
            '''
            <xpath expr="//{http://www.onegate.eu/2010-01-01}Report[@code='INTRASTAT_X_E']" position="replace"></xpath>
            '''
        )
        self.assertXmlTreeEqual(arrivals_only_tree, expected_tree)

    def test_full_export(self):
        """ Test generating an XML export for the whole  """
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')
        arrivals, dispatches = options['intrastat_type']
        arrivals['selected'], dispatches['selected'] = False, False
        options = self.report.get_options(options)

        # Both reports should be present, but they should be absent of items (until we post)
        full_export_tree = etree.fromstring(self.report_handler.be_intrastat_export_to_xml(options)['file_content'])
        expected_tree = self.with_applied_xpath(
            etree.fromstring(self.expected_content_all),
            '''
            <xpath expr="//{http://www.onegate.eu/2010-01-01}Report[@code='INTRASTAT_X_E']" position="attributes">
                <attribute name="action">nihil</attribute>
            </xpath>
            <xpath expr="//{http://www.onegate.eu/2010-01-01}Data[@form='INTRASTAT_X_EF']/*" position="replace"></xpath>
            <xpath expr="//{http://www.onegate.eu/2010-01-01}Report[@code='EX19E']" position="attributes">
                <attribute name="action">nihil</attribute>
            </xpath>
            <xpath expr="//{http://www.onegate.eu/2010-01-01}Data[@form='EXF19E']/*" position="replace"></xpath>
            '''
        )
        self.assertXmlTreeEqual(full_export_tree, expected_tree)

        self.inwards_vendor_bill.action_post()
        self.outwards_customer_invoice.action_post()

        self.assertXmlTreeEqual(
            etree.fromstring(self.report_handler.be_intrastat_export_to_xml(options)['file_content']),
            etree.fromstring(self.expected_content_all),
        )
