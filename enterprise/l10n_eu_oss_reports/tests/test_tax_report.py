# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class OSSTaxReportTest(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.country_id = cls.env.ref('base.be')
        cls.env.company.account_fiscal_country_id = cls.env.ref('base.be')
        cls.env.company.vat = 'BE0477472701'
        cls.env.company.currency_id = cls.env.ref('base.EUR')

        account_payable = cls.env['account.account'].create({
            'name': "VAT Payable: VAT Current Account (C/A)",
            'code': "4512",
            'account_type': 'liability_payable',
            'reconcile': True,
            'non_trade': True,
        })
        account_receivable = cls.env['account.account'].create({
            'name': "VAT Recoverable: VAT Current Account (C/A)",
            'code': "4112",
            'account_type': 'asset_receivable',
            'reconcile': True,
            'non_trade': True,
        })

        tax_group = cls.env['account.tax.group'].create({
            'name': 'tax_group',
            'country_id': cls.env.ref('base.be').id,
            'tax_payable_account_id': account_payable.id,
            'tax_receivable_account_id': account_receivable.id,
        })

        tax_21, tax_06 = cls.env['account.tax'].create([
            {
                'name': "tax_21",
                'amount_type': 'percent',
                'amount': 21.0,
                'country_id': cls.env.ref('base.be').id,
                'tax_group_id': tax_group.id,
            },
            {
                'name': "tax_06",
                'amount_type': 'percent',
                'amount': 6.0,
                'country_id': cls.env.ref('base.be').id,
                'tax_group_id': tax_group.id,
            },
        ])
        cls.tax_06 = tax_06
        cls.tax_21 = tax_21

        cls.env.company._map_eu_taxes()

        cls.product_1, cls.product_2 = cls.env['product.product'].create([
            {
                'name': 'product_1',
                'lst_price': 1000.0,
                'taxes_id': [Command.set(cls.tax_21.ids)],
            },
            {
                'name': 'product_2',
                'lst_price': 500.0,
                'taxes_id': [Command.set(cls.tax_06.ids)],
            },
        ])

        cls.partner_be = cls.env['res.partner'].create({
            'name': 'Partner BE',
            'country_id': cls.env.ref('base.be').id,
        })
        cls.partner_fr = cls.env['res.partner'].create({
            'name': 'Partner FR',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.partner_lu = cls.env['res.partner'].create({
            'name': 'Partner LU',
            'country_id': cls.env.ref('base.lu').id,
        })
        cls.partner_nl = cls.env['res.partner'].create({
            'name': 'Partner NL',
            'country_id': cls.env.ref('base.nl').id,
        })
        cls.partner_gr = cls.env['res.partner'].create({
            'name': 'Partner GR',
            'country_id': cls.env.ref('base.gr').id,
        })

        cls.init_invoice('out_invoice', partner=cls.partner_be, products=cls.product_1, invoice_date=fields.Date.from_string('2021-04-01'), post=True)
        cls.init_invoice('out_invoice', partner=cls.partner_fr, products=cls.product_1, invoice_date=fields.Date.from_string('2021-05-23'), post=True)
        cls.init_invoice('out_invoice', partner=cls.partner_lu, products=cls.product_1, invoice_date=fields.Date.from_string('2021-06-12'), post=True)
        cls.init_invoice('out_refund', partner=cls.partner_lu, products=cls.product_2, invoice_date=fields.Date.from_string('2021-06-15'), post=True)
        cls.init_invoice('out_invoice', partner=cls.partner_nl, products=cls.product_1, invoice_date=fields.Date.from_string('2021-05-09'), post=True)
        cls.init_invoice('out_refund', partner=cls.partner_nl, products=cls.product_1, invoice_date=fields.Date.from_string('2021-05-11'), post=True)
        cls.init_invoice('out_refund', partner=cls.partner_gr, products=cls.product_1, invoice_date=fields.Date.from_string('2021-06-26'), post=True)

    def _assert_closing_lines(self, entry, expected_lines_dict):
        for line, expected_line in zip(entry.line_ids, expected_lines_dict):
            for key in expected_line:
                self.assertEqual(line.mapped(key)[0], expected_line[key])

    def test_tax_report_oss(self):
        """ Test tax report's content for 'domestic' foreign VAT fiscal position option.
        """
        report = self.env.ref('l10n_eu_oss_reports.oss_sales_report')
        options = self._generate_options(report, fields.Date.from_string('2021-04-01'), fields.Date.from_string('2021-06-30'))

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                        Net               Tax
            [   0,                            1,                2],
            [
                ("Sales",                    '',               90),
                ("France",                   '',              200),
                ("20.0% FR VAT (20.0%)",   1000,              200),
                ("Total France",             '',              200),
                ("Greece",                   '',             -240),
                ("24.0% GR VAT (24.0%)",  -1000,             -240),
                ("Total Greece",             '',             -240),
                ("Luxembourg",               '',              130),
                ("17.0% LU VAT (17.0%)",   1000,              170),
                ("8.0% LU VAT (8.0%)",     -500,              -40),
                ("Total Luxembourg",         '',              130),
                ("Netherlands",              '',              0.0),
                ("21.0% NL VAT (21.0%)",    0.0,              0.0),
                ("Total Netherlands",        '',              0.0),
                ("Total Sales",              '',               90),
            ],
            options,
        )

    def test_tax_closing_entries_isolation_sales_and_imports(self):
        """
        Check that Sales and Imports OSS reports generate separate tax closing journal entries
        """
        sales_report = self.env.ref('l10n_eu_oss_reports.oss_sales_report')
        options = self._generate_options(sales_report, '2021-04-01', '2021-06-30')
        sales_closing_entries = self.env[sales_report.custom_handler_model_name]._generate_tax_closing_entries(sales_report, options)
        self.assertEqual(len(sales_closing_entries), 1)

        imports_report = self.env.ref('l10n_eu_oss_reports.oss_imports_report')
        options = self._generate_options(imports_report, '2021-06-01', '2021-06-30')
        imports_closing_entries = self.env[imports_report.custom_handler_model_name]._generate_tax_closing_entries(imports_report, options)
        self.assertEqual(len(imports_closing_entries), 1)

        self.assertRecordValues(sales_closing_entries + imports_closing_entries, [
            {'ref': 'OSS Sales: Q2 2021', 'tax_closing_report_id': sales_report.id},
            {'ref': 'OSS Imports: June 2021', 'tax_closing_report_id': imports_report.id},
        ])

    def test_tax_report_oss_closing(self):
        report = self.env.ref('l10n_eu_oss_reports.oss_sales_report')
        options = self._generate_options(report, '2021-04-01', '2021-06-30')
        tax_closing_entries = self.env[report.custom_handler_model_name]._generate_tax_closing_entries(report, options)
        self.assertEqual(len(tax_closing_entries), 1)

        self._assert_closing_lines(
            tax_closing_entries[0],
            [
                {'account_id.code':     '251002',        'debit': 200,       'credit': 0},
                {'account_id.code':     '251002',        'debit': 0,         'credit': 0},
                {'account_id.code':     '251002',        'debit': 0,         'credit': 240},
                {'account_id.code':     '251002',        'debit': 170,       'credit': 0},
                {'account_id.code':     '251002',        'debit': 0,         'credit': 40},
                {'account_id.code':     '252000',        'debit': 0,         'credit': 90},
            ]
        )

    def test_oss_import_report(self):
        self.product_1.account_tag_ids += self.env.ref('l10n_eu_oss.tag_eu_import')
        self.init_invoice('out_invoice', partner=self.partner_fr, products=self.product_1, invoice_date='2021-04-01', post=True)

        report = self.env.ref('l10n_eu_oss_reports.oss_imports_report')
        options = self._generate_options(report, '2021-04-01', '2021-06-30')

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                        Net               Tax
            [   0,                            1,                2],
            [
                ("Sales",                    '',              200),
                ("France",                   '',              200),
                ("20.0% FR VAT (20.0%)",   1000,              200),
                ("Total France",             '',              200),
                ("Total Sales",              '',              200),
            ],
            options,
        )

    def test_generate_oss_xml_be(self):
        report = self.env.ref('l10n_eu_oss_reports.oss_sales_report')
        options = self._generate_options(report, fields.Date.from_string('2021-04-01'), fields.Date.from_string('2021-06-30'))

        expected_xml = """
            <ns0:OSSConsignment
              xmlns:ns2="urn:minfin.fgov.be:oss:common"
              xmlns:ns1="http://www.minfin.fgov.be/InputCommon"
              xmlns:ns0="http://www.minfin.fgov.be/OSSDeclaration"
              OSSDeclarationNbr="1">
              <ns0:OSSDeclaration SequenceNumber="1">
                <ns0:Trader_ID>
                  <ns2:VATNumber issuedBy="BE">0477472701</ns2:VATNumber>
                </ns0:Trader_ID>
                <ns0:Period>
                  <ns2:Year>2021</ns2:Year>
                  <ns2:Quarter>2</ns2:Quarter>
                </ns0:Period>
                <ns0:OSSDeclarationInfo SequenceNumber="1">
                  <ns2:MemberStateOfConsumption>FR</ns2:MemberStateOfConsumption>
                  <ns2:OSSDeclarationRows SequenceNumber="1">
                    <ns2:SupplyType>GOODS</ns2:SupplyType>
                    <ns2:VatRateType type="STANDARD">20.00</ns2:VatRateType>
                    <ns2:VatAmount currency="EUR">200.0</ns2:VatAmount>
                    <ns2:TaxableAmount currency="EUR">1000.0</ns2:TaxableAmount>
                  </ns2:OSSDeclarationRows>
                </ns0:OSSDeclarationInfo>
                <ns0:OSSDeclarationInfo SequenceNumber="2">
                  <ns2:MemberStateOfConsumption>EL</ns2:MemberStateOfConsumption>
                  <ns2:CorrectionsInfo>
                    <ns2:Period>
                      <ns2:Year>2021</ns2:Year>
                      <ns2:Quarter>1</ns2:Quarter>
                    </ns2:Period>
                    <ns2:TotalVATAmountCorrection currency="EUR">-240.0</ns2:TotalVATAmountCorrection>
                  </ns2:CorrectionsInfo>
                </ns0:OSSDeclarationInfo>
                <ns0:OSSDeclarationInfo SequenceNumber="3">
                  <ns2:MemberStateOfConsumption>LU</ns2:MemberStateOfConsumption>
                  <ns2:OSSDeclarationRows SequenceNumber="1">
                    <ns2:SupplyType>GOODS</ns2:SupplyType>
                    <ns2:VatRateType type="STANDARD">17.00</ns2:VatRateType>
                    <ns2:VatAmount currency="EUR">170.0</ns2:VatAmount>
                    <ns2:TaxableAmount currency="EUR">1000.0</ns2:TaxableAmount>
                  </ns2:OSSDeclarationRows>
                  <ns2:CorrectionsInfo>
                    <ns2:Period>
                      <ns2:Year>2021</ns2:Year>
                      <ns2:Quarter>2</ns2:Quarter>
                    </ns2:Period>
                    <ns2:TotalVATAmountCorrection currency="EUR">-40.0</ns2:TotalVATAmountCorrection>
                  </ns2:CorrectionsInfo>
                </ns0:OSSDeclarationInfo>
              </ns0:OSSDeclaration>
            </ns0:OSSConsignment>
        """

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].export_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTaxReportOSSNoMapping(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].account_fiscal_country_id = cls.env.ref('base.be')
        cls.company_data['company'].vat = 'BE0477472701'

        cls.tax_report = cls.env['account.report'].create({
            'name': 'Fictive tax report',
            'country_id': cls.company_data['company'].account_fiscal_country_id.id,
            'root_report_id': cls.env.ref("account.generic_tax_report").id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance',})],
        })
        report_line_invoice_base_line = cls._create_tax_report_line('Invoice base', cls.tax_report, sequence=1, tag_name='invoice_base_line')
        report_line_refund_base_line = cls._create_tax_report_line('Refund base', cls.tax_report, sequence=2, tag_name='refund_base_line')

        # Create an OSS tax from scratch
        cls.env['account.tax.group'].create({
            'name': 'tax_group',
            'country_id': cls.company_data['company'].account_fiscal_country_id.id,
            'tax_payable_account_id': cls.company_data['default_tax_account_payable'].id,
            'tax_receivable_account_id': cls.company_data['default_tax_account_receivable'].id,
        })
        oss_tag = cls.env.ref('l10n_eu_oss.tag_oss')
        cls.oss_tax = cls.env['account.tax'].create({
            'name': 'OSS tax for DK',
            'amount': 25,
            'country_id': cls.company_data['company'].account_fiscal_country_id.id,
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(report_line_invoice_base_line.expression_ids._get_matching_tags("+").ids + oss_tag.ids)],
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(oss_tag.ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(report_line_refund_base_line.expression_ids._get_matching_tags("+").ids + oss_tag.ids)],
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(oss_tag.ids)],
                }),
            ],
        })

        cls.env['account.fiscal.position'].create({
            'name': 'OSS B2C Denmark',
            'country_id': cls.env.ref('base.dk').id,
            'company_id': cls.company_data['company'].id,
            'auto_apply': True,
            'tax_ids': [Command.create({'tax_src_id': cls.tax_sale_a.id, 'tax_dest_id': cls.oss_tax.id})],
        })


    def test_oss_tax_report_mixed_tags(self):
        """Checks that the tax report correctly takes into account the amount of the account move lines wearing tax tag
        when it is also wearing an OSS tag.
        """
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.from_string('2022-02-01'),
            amounts=[100.0],
            taxes=[self.oss_tax],
            post=True,
        )
        options = self._generate_options(
            self.tax_report,
            fields.Date.from_string('2022-02-01'),
            fields.Date.from_string('2022-02-28'),
        )
        report_results = self.tax_report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=C0326
            report_results,
            #   Name             Balance
            [   0,                    1],
            [
                ('Invoice base', 100.00),
                ('Refund base',    0.00),
            ],
            options,
        )

    def test_closing_entry(self):
        """Check the closing entry doesn't take the account move line wearing the OSS tag into account"""
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.from_string('2022-02-01'),
            amounts=[100.0],
            taxes=[self.oss_tax],
            post=True,
        )
        options = self._generate_options(
            self.tax_report,
            fields.Date.from_string('2022-02-01'),
            fields.Date.from_string('2022-02-28'),
        )
        tax_closing_entry_lines = self.env['account.generic.tax.report.handler']._generate_tax_closing_entries(self.tax_report, options).line_ids.filtered(lambda l: l.balance != 0.0)

        self.assertEqual(len(tax_closing_entry_lines), 0, "The tax closing entry shouldn't take amls wearing the OSS tag into account")

    def test_tax_report_oss(self):
        """ Test tax report's content for 'domestic' foreign VAT fiscal position option."""
        self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.from_string('2022-02-01'),
            amounts=[100.0],
            taxes=[self.oss_tax],
            post=True,
        )
        report = self.env.ref('l10n_eu_oss_reports.oss_sales_report')
        options = self._generate_options(report, '2022-02-01', '2022-02-28')
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #   Name                          Net               Tax
            [   0,                              1,                2],
            [
                ("Sales",                      '',             25.0),
                ("Denmark",                    '',             25.0),
                ("OSS tax for DK (25.0%)",  100.0,             25.0),
                ("Total Denmark",              '',             25.0),
                ("Total Sales",                '',             25.0),
            ],
            options,
        )
