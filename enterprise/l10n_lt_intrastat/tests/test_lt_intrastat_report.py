# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests.common import test_xsd


class TestLTIntrastatReportCommon(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('lt')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].company_registry = '0123456789'
        italy = cls.env.ref('base.it')
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
        <INSTAT>
            <Envelope>
                <envelopeId>___ignore___</envelopeId>
                <DateTime>
                    <date>2024-01-04</date>
                    <time>13:54:34</time>
                </DateTime>
                <Party partyType="PSI" partyRole="sender">
                    <partyName>company_1_data</partyName>
                    <Address> </Address>
                    <ContactPerson>
                        <contactPersonName>Because I am accountman!</contactPersonName>
                        <e-mail>accountman@test.com</e-mail>
                    </ContactPerson>
                </Party>
                <Party partyType="CC" partyRole="receiver">
                    <partyId>MM39</partyId>
                    <partyName>MD STATISTIKOS ANALIZ&#278;S SKYRIUS</partyName>
                </Party>
                <softwareUsed>___ignore___</softwareUsed>
                <Declaration>
                    <DateTime>
                        <date>2024-01-04</date>
                        <time>13:54:34</time>
                    </DateTime>
                    <referencePeriod>2022-05</referencePeriod>
                    <Function>
                        <functionCode>O</functionCode>
                    </Function>
                    <flowCode>A</flowCode>
                    <currencyCode>EUR</currencyCode>
                    <totalInvoicedAmount>959328</totalInvoicedAmount>
                    <Item>
                        <itemNumber>2</itemNumber>
                        <CN8>
                            <CN8Code>25309050</CN8Code>
                        </CN8>
                        <goodsDescription />
                        <MSConsDestCode>LT</MSConsDestCode>
                        <countryOfOriginCode>QV</countryOfOriginCode>
                        <netMass>798000</netMass>
                        <invoicedAmount>23328</invoicedAmount>
                        <partnerId>QV999999999999</partnerId>
                        <NatureOfTransaction>
                            <natureOfTransactionACode>1</natureOfTransactionACode>
                            <natureOfTransactionBCode>1</natureOfTransactionBCode>
                        </NatureOfTransaction>
                    </Item>
                    <totalNumberDetailedLines>1</totalNumberDetailedLines>
                </Declaration>
                <Declaration>
                    <DateTime>
                        <date>2024-01-04</date>
                        <time>13:54:34</time>
                    </DateTime>
                    <referencePeriod>2022-05</referencePeriod>
                    <Function>
                        <functionCode>O</functionCode>
                    </Function>
                    <flowCode>D</flowCode>
                    <currencyCode>EUR</currencyCode>
                    <totalInvoicedAmount>959328</totalInvoicedAmount>
                    <Item>
                        <itemNumber>1</itemNumber>
                        <CN8>
                            <CN8Code>88023000</CN8Code>
                            <SUCode>4.0</SUCode>
                        </CN8>
                        <goodsDescription />
                        <MSConsDestCode>IT</MSConsDestCode>
                        <countryOfOriginCode>QV</countryOfOriginCode>
                        <netMass>14956000</netMass>
                        <invoicedAmount>936000</invoicedAmount>
                        <partnerId>QV999999999999</partnerId>
                        <NatureOfTransaction>
                            <natureOfTransactionACode>1</natureOfTransactionACode>
                            <natureOfTransactionBCode>1</natureOfTransactionBCode>
                        </NatureOfTransaction>
                    </Item>
                    <totalNumberDetailedLines>1</totalNumberDetailedLines>
                </Declaration>
                <numberOfDeclarations>2</numberOfDeclarations>
            </Envelope>
        </INSTAT>
        '''

    def _generate_xml(self):
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')
        arrivals, dispatches = options['intrastat_type']
        arrivals['selected'], dispatches['selected'] = False, False
        options = self.report.get_options(options)

        return self.report_handler.lt_intrastat_export_to_xml(options)['file_content']


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLTIntrastatReport(TestLTIntrastatReportCommon):

    @freeze_time("2024-01-04 13:54:34")
    def test_full_export(self):
        self.inwards_vendor_bill.action_post()
        self.outwards_customer_invoice.action_post()
        self.env.cr.flush()

        full_export_tree = etree.fromstring(self._generate_xml())
        expected_tree = etree.fromstring(self.expected_content_all)
        self.assertXmlTreeEqual(full_export_tree, expected_tree)


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestLTIntrastatReportXmlValidity(TestLTIntrastatReportCommon):

    # The XSD validator on the website is not correct. For such reason, the
    # content has been added and updated in a file meanwhile:
    # 150: - <xsd:element ref="fillingTimeHours" minOccurs="0"/>
    # 150: + <xsd:element name="fillingTimeHours" type="xsd:integer"/>
    # 151: - <xsd:element ref="fillingTimeMinutes" minOccurs="0"/>
    # 151: + <xsd:element name="fillingTimeMinutes" type="xsd:integer"/>
    # @test_xsd(url='https://intrastat.lrmuitine.lt/docs/instat-v20230419.xsd')
    @test_xsd(path='l10n_lt_intrastat/data/intrastat.xsd')
    def test_xml_validity(self):
        self.inwards_vendor_bill.action_post()
        self.outwards_customer_invoice.action_post()
        self.env.cr.flush()
        return self._generate_xml()
