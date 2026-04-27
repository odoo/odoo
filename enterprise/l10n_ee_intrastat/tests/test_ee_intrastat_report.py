from lxml import etree
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEEIntrastatReport(TestAccountReportsCommon):

    @classmethod
    @AccountSalesReportCommon.setup_country('ee')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].country_id = cls.env.ref('base.ee')
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

    @freeze_time("2024-01-04 13:54:34")
    def test_xml_export(self):
        self.inwards_vendor_bill.action_post()
        self.outwards_customer_invoice.action_post()
        self.env.cr.flush()
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')

        # This tree represents the export with both kinds of reports (the extended version)
        expected_content_all = b'''
        <INSTAT>
            <Envelope>
                <envelopeId>___ignore___</envelopeId>
                <DateTime>
                    <date>2024-01-04</date>
                    <time>13:54:34</time>
                </DateTime>
                <Party partyRole="sender" partyType="PSI">
                    <partyName>company_1_data</partyName>
                    <Address>
                    </Address>
                    <ContactPerson>
                        <contactPersonName>Because I am accountman!</contactPersonName>
                        <e-mail>accountman@test.com</e-mail>
                    </ContactPerson>
                </Party>
                <Party partyRole="receiver" partyType="CC">
                    <partyId>estat</partyId>
                    <partyName>STATISTICS ESTONIA</partyName>
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
                    <flowCode>1</flowCode>
                    <currencyCode>EUR</currencyCode>
                    <totalNetMass>798.0</totalNetMass>
                    <totalGoodsValue>23328.48</totalGoodsValue>
                    <Item>
                        <itemNumber>1</itemNumber>
                        <CN8>
                            <CN8Code>25309050</CN8Code>
                        </CN8>
                        <goodsDescription></goodsDescription>
                        <MSConsDestCode>EE</MSConsDestCode>
                        <countryOfOriginCode>QV</countryOfOriginCode>
                        <netMass>798.0</netMass>
                        <quantityInSu>42.0</quantityInSu>
                        <goodsValue>23328.48</goodsValue>
                        <partnerId>QV999999999999</partnerId>
                        <NatureOfTransaction>
                            <natureOfTransactionACode>1</natureOfTransactionACode>
                            <natureOfTransactionBCode>1</natureOfTransactionBCode>
                        </NatureOfTransaction>
                    </Item>
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
                    <flowCode>2</flowCode>
                    <currencyCode>EUR</currencyCode>
                    <totalNetMass>14956.0</totalNetMass>
                    <totalGoodsValue>936000.0</totalGoodsValue>
                    <Item>
                        <itemNumber>2</itemNumber>
                        <CN8>
                            <CN8Code>88023000</CN8Code>
                            <SUCode>p/st</SUCode>
                        </CN8>
                        <goodsDescription></goodsDescription>
                        <MSConsDestCode>IT</MSConsDestCode>
                        <countryOfOriginCode>QV</countryOfOriginCode>
                        <netMass>14956.0</netMass>
                        <quantityInSu>16.0</quantityInSu>
                        <goodsValue>936000.0</goodsValue>
                        <partnerId>QV999999999999</partnerId>
                        <NatureOfTransaction>
                            <natureOfTransactionACode>1</natureOfTransactionACode>
                            <natureOfTransactionBCode>1</natureOfTransactionBCode>
                        </NatureOfTransaction>
                    </Item>
                </Declaration>
                <numberOfDeclarations>2</numberOfDeclarations>
            </Envelope>
        </INSTAT>
        '''

        self.assertXmlTreeEqual(
            etree.fromstring(self.report_handler.ee_intrastat_export_to_xml(options)['file_content']),
            etree.fromstring(expected_content_all)
        )

    def test_ee_intrastat_arrivals_xlsx(self):
        """ Test that data provided for the xlsx export of intrastat report with Estonian
        company will correspond to the expected format in case only arrivals are requested
        """
        self.inwards_vendor_bill.action_post()
        self.env.cr.flush()
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')

        options_arrivals = self.report_handler._ee_prepare_options_for_xlsx_export(options, 'arrivals')
        arrivals_only_lines = self.report_handler._ee_intrastat_xlsx_get_data(options_arrivals)

        expected_lines = [
            [
                'Code of economic entity', 'Questionnaire code', 'Periodicity', 'EU Member State', 'Transaction',
                'Country of Origin', 'CN8 goods code', 'Net mass (kg)', 'Supplementary quantity', 'Unit', 'Value of goods in euros',
                'Description of goods', 'Remark'
            ],
            [
                '0123456789', '1204', '2022-05', 'IT', '11',
                'QV', '25309050', '798.0', '', '', '23328.48',
                '', ''
            ],
        ]

        self.assertListEqual(arrivals_only_lines, expected_lines)

    def test_ee_intrastat_dispatches_xlsx(self):
        """ Test that data provided for the xlsx export of intrastat report with Estonian
        company will correspond to the expected format in case only dispatches are requested
        """
        self.outwards_customer_invoice.action_post()
        self.env.cr.flush()
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')

        options_arrivals = self.report_handler._ee_prepare_options_for_xlsx_export(options, 'dispatches')
        dispatches_only_lines = self.report_handler._ee_intrastat_xlsx_get_data(options_arrivals)

        expected_lines = [
            [
                'Code of economic entity', 'Questionnaire code', 'Periodicity', 'EU Member State', 'VAT number of the purchaser of the commodity in another Member State',
                'Transaction', 'Country of Origin', 'CN8 goods code', 'Net mass (kg)', 'Supplementary quantity', 'Unit',
                'Value of goods in euros', 'Description of goods', 'Remark'
            ],
            [
                '0123456789', '1203', '2022-05', 'IT', 'QV999999999999',
                '11', 'QV', '88023000', '14956.0', '4.0', 'p/st',
                '936000.0', '', ''
            ],
        ]

        self.assertListEqual(dispatches_only_lines, expected_lines)
