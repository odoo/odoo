from lxml import etree
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDEIntrastatReport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_chart_template('de_skr03')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].country_id = cls.env.ref('base.de')
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
                    <envelopeId>XGT-202205-20240104-1354</envelopeId>
                    <DateTime>
                        <date>2024-01-04</date>
                        <time>13:54:34</time>
                    </DateTime>
                    <Party partyType="CC" partyRole="receiver">
                        <partyId>00</partyId>
                        <partyName>Statistisches Bundesamt</partyName>
                        <Address>
                            <streetName>Gustav - Stresemann - Ring 11</streetName>
                            <postalCode>65189</postalCode>
                            <cityName>Wiesbaden</cityName>
                        </Address>
                    </Party>
                    <Party partyType="PSI" partyRole="sender">
                        <partyName>company_1_data</partyName>
                        <Address>
                            <countryName>Germany</countryName>
                        </Address>
                        <ContactPerson>
                            <contactPersonName>Because I am accountman!</contactPersonName>
                            <e-mail>accountman@test.com</e-mail>
                        </ContactPerson>
                    </Party>
                    <softwareUsed>___ignore___</softwareUsed>
                    <Declaration>
                        <declarationId>2022-05</declarationId>
                        <DateTime>
                            <date>2024-01-04</date>
                            <time>13:54:34</time>
                        </DateTime>
                        <referencePeriod>2022-05</referencePeriod>
                        <Function>
                            <functionCode>O</functionCode>
                        </Function>
                        <declarationTypeCode></declarationTypeCode>
                        <flowCode>A</flowCode>
                        <currencyCode>EUR</currencyCode>
                        <totalNetMass>798.0</totalNetMass>
                        <totalInvoicedAmount>23328.48</totalInvoicedAmount>
                        <Item>
                            <itemNumber>2</itemNumber>
                            <CN8>
                                <CN8Code>25309050</CN8Code>
                            </CN8>
                            <goodsDescription></goodsDescription>
                            <MSConsDestCode>DE</MSConsDestCode>
                            <countryOfOriginCode>QV</countryOfOriginCode>
                            <netMass>798.0</netMass>
                            <quantityInSu>42.0</quantityInSu>
                            <invoicedAmount>23328.48</invoicedAmount>
                            <NatureOfTransaction>
                                <natureOfTransactionACode>1</natureOfTransactionACode>
                                <natureOfTransactionBCode>1</natureOfTransactionBCode>
                            </NatureOfTransaction>
                            <partnerId>QN999999999999</partnerId>
                        </Item>
                        <totalNumberLines>1</totalNumberLines>
                    </Declaration>
                    <Declaration>
                        <declarationId>2022-05</declarationId>
                        <DateTime>
                            <date>2024-01-04</date>
                            <time>13:54:34</time>
                        </DateTime>
                        <referencePeriod>2022-05</referencePeriod>
                        <Function>
                            <functionCode>O</functionCode>
                        </Function>
                        <declarationTypeCode></declarationTypeCode>
                        <flowCode>D</flowCode>
                        <currencyCode>EUR</currencyCode>
                        <totalNetMass>14956.0</totalNetMass>
                        <totalInvoicedAmount>936000.0</totalInvoicedAmount>
                        <Item>
                            <itemNumber>1</itemNumber>
                            <CN8>
                                <CN8Code>88023000</CN8Code>
                                <SUCode>p/st</SUCode>
                            </CN8>
                            <goodsDescription></goodsDescription>
                            <MSConsDestCode>IT</MSConsDestCode>
                            <countryOfOriginCode>QV</countryOfOriginCode>
                            <netMass>14956.0</netMass>
                            <quantityInSu>16.0</quantityInSu>
                            <invoicedAmount>936000.0</invoicedAmount>
                            <NatureOfTransaction>
                                <natureOfTransactionACode>1</natureOfTransactionACode>
                                <natureOfTransactionBCode>1</natureOfTransactionBCode>
                            </NatureOfTransaction>
                            <partnerId>QN999999999999</partnerId>
                        </Item>
                        <totalNumberLines>1</totalNumberLines>
                    </Declaration>
                    <numberOfDeclarations>2</numberOfDeclarations>
                </Envelope>
            </INSTAT>
        '''

    @freeze_time("2024-01-04 13:54:34")
    def test_xml_export(self):
        self.inwards_vendor_bill.action_post()
        self.outwards_customer_invoice.action_post()
        self.env.cr.flush()
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31', default_options={'export_mode': 'file'})

        self.assertXmlTreeEqual(
            etree.fromstring(self.report_handler.de_intrastat_export_to_xml(options)['file_content']),
            etree.fromstring(self.expected_content_all)
        )
