# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class EstonianTaxReportTest(AccountSalesReportCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ee'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_ee_1 = cls.env['res.partner'].create({
            'name': 'Partner EE 1',
            'country_id': cls.env.ref('base.ee').id,
            'company_registry': '98765432',
            'is_company': True,
        })

        cls.partner_ee_2 = cls.env['res.partner'].create({
            'name': 'Partner EE 2',
            'country_id': cls.env.ref('base.ee').id,
            'is_company': True,
        })

        cls.taxes = {
            # Purchase Taxes
            'vat_in_22_g': cls.env['account.tax'].search([
                    ('name', '=', '22% G'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_22_partial': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '22% S'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_9_g': cls.env['account.tax'].search([
                    ('name', '=', '9% G'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_5_g': cls.env['account.tax'].search([
                    ('name', '=', '5% G'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_0_g': cls.env['account.tax'].search([
                    ('name', '=', '0% G'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_0_eu_g': cls.env['account.tax'].search([
                    ('name', '=', '0% EU G 22%'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_0_eu_s': cls.env['account.tax'].search([
                    ('name', '=', '0% EU S 22%'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_22_car': cls.env['account.tax'].search([
                    ('name', '=', '22% Car'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_22_car_part': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '22% Car 50%'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_22_assets': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '22% Fixed Assets'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_imp_cus': cls.env['account.tax'].search([
                    ('name', '=', 'EX VAT Customs'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_22_imp_kms_38': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '22% EX KMS §38'),
                    ('type_tax_use', '=', 'purchase'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_in_0_kms_41_1': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '22% KMS §41¹'),
                    ('type_tax_use', '=', 'purchase'),
                    ('amount', '=', 22),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            # Sales Taxes
            'vat_out_22_g': cls.env['account.tax'].search([
                    ('name', '=', '22% G'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_9_g': cls.env['account.tax'].search([
                    ('name', '=', '9% G'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_5_g': cls.env['account.tax'].search([
                    ('name', '=', '5% G'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_0_g': cls.env['account.tax'].search([
                    ('name', '=', '0% G'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_0_eu_g': cls.env['account.tax'].search([
                    ('name', '=', '0% EU G'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_0_eu_s': cls.env['account.tax'].search([
                    ('name', '=', '0% EU S'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_0_exp_g': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '0% EX G'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_0_pas': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '0% Passengers'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_0_exp_s': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '0% EX S'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_exempt': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '0% Exempt'),
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
            'vat_out_0_kms_41_1': cls.env['account.tax'].with_context(active_test=False).search([
                    ('name', '=', '22% KMS §41¹'),
                    ('type_tax_use', '=', 'sale'),
                    ('amount', '=', 22),
                    ('company_id', '=', cls.company_data['company'].id)
                ], limit=1),
        }
        cls.taxes['vat_in_22_partial'].l10n_ee_kmd_inf_code = '11'

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.ee').id,
            'vat': 'EE123456780',
            'company_registry': '12345678',
        })
        return res

    @freeze_time('2023-02-01')
    def test_generate_xml_purchase(self):
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_ee_1.id,
            'invoice_date': '2023-01-11',
            'date': '2023-01-11',
            'ref': 'INV001',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_in_22_g'].ids,
                }),
            ],
        })
        move.action_post()

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_ee_2.id,
            'invoice_date': '2023-01-13',
            'date': '2023-01-13',
            'ref': 'INV002',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_in_22_partial'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT2',
                    'price_unit': 300,
                    'tax_ids': self.taxes['vat_in_9_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT3',
                    'price_unit': 200,
                    'tax_ids': self.taxes['vat_in_5_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT4',
                    'price_unit': 150,
                    'tax_ids': self.taxes['vat_in_0_g'].ids,
                }),
            ],
        })
        move.action_post()

        report = self.env.ref('l10n_ee.tax_report_vat')
        options = report.get_options()

        expected_xml = """
            <vatDeclaration>
                <taxPayerRegCode>12345678</taxPayerRegCode>
                <year>2023</year>
                <month>1</month>
                <declarationType>1</declarationType>
                <version>KMD4</version>
                <declarationBody>
                    <noSales>true</noSales>
                    <noPurchases>false</noPurchases>
                    <sumPerPartnerSales>false</sumPerPartnerSales>
                    <sumPerPartnerPurchases>false</sumPerPartnerPurchases>
                    <inputVatTotal>257.00</inputVatTotal>
                </declarationBody>
                <purchasesAnnex>
                    <purchaseLine>
                        <sellerName>Partner EE 2</sellerName>
                        <invoiceNumber>INV002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSumVat>1297.00</invoiceSumVat>
                        <vatInPeriod>147.00</vatInPeriod>
                        <comments>11</comments>
                    </purchaseLine>
                    <purchaseLine>
                        <sellerRegCode>98765432</sellerRegCode>
                        <sellerName>Partner EE 1</sellerName>
                        <invoiceNumber>INV001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSumVat>610.00</invoiceSumVat>
                        <vatInPeriod>110.00</vatInPeriod>
                    </purchaseLine>
                </purchasesAnnex>
            </vatDeclaration>
        """

        actual_xml = self.env[report.custom_handler_model_name].export_to_xml(options)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2023-02-01')
    def test_generate_xml_sale(self):
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'partner_id': self.partner_ee_1.id,
            'invoice_date': '2023-01-11',
            'date': '2023-01-11',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_out_22_g'].ids,
                }),
            ],
        }).action_post()

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'partner_id': self.partner_ee_2.id,
            'invoice_date': '2023-01-13',
            'date': '2023-01-13',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_out_22_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT2',
                    'price_unit': 300,
                    'tax_ids': self.taxes['vat_out_9_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT3',
                    'price_unit': 200,
                    'tax_ids': self.taxes['vat_out_5_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT4',
                    'price_unit': 150,
                    'tax_ids': self.taxes['vat_out_0_g'].ids,
                }),
            ],
        }).action_post()

        report = self.env.ref('l10n_ee.tax_report_vat')
        options = report.get_options()

        expected_xml = """
            <vatDeclaration>
                <taxPayerRegCode>12345678</taxPayerRegCode>
                <year>2023</year>
                <month>1</month>
                <declarationType>1</declarationType>
                <version>KMD4</version>
                <declarationBody>
                    <noSales>false</noSales>
                    <noPurchases>true</noPurchases>
                    <sumPerPartnerSales>false</sumPerPartnerSales>
                    <sumPerPartnerPurchases>false</sumPerPartnerPurchases>
                    <transactions22>1000.00</transactions22>
                    <transactions9>300.00</transactions9>
                    <transactions5>200.00</transactions5>
                    <transactionsZeroVat>150.00</transactionsZeroVat>
                </declarationBody>
                <salesAnnex>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <sumForRateInPeriod>500.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>9</taxRate>
                        <sumForRateInPeriod>300.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>5</taxRate>
                        <sumForRateInPeriod>200.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerRegCode>98765432</buyerRegCode>
                        <buyerName>Partner EE 1</buyerName>
                        <invoiceNumber>INV/2023/00001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSum>500.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <sumForRateInPeriod>500.00</sumForRateInPeriod>
                    </saleLine>
                </salesAnnex>
            </vatDeclaration>
        """

        actual_xml = self.env[report.custom_handler_model_name].export_to_xml(options)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2023-02-01')
    def test_generate_xml_mixed_all(self):
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_ee_1.id,
            'invoice_date': '2023-01-11',
            'date': '2023-01-11',
            'ref': 'INV001',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_in_22_g'].ids,
                }),
            ],
        })
        move.action_post()

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_ee_2.id,
            'invoice_date': '2023-01-13',
            'date': '2023-01-13',
            'ref': 'INV002',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_in_22_partial'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT2',
                    'price_unit': 300,
                    'tax_ids': self.taxes['vat_in_9_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT3',
                    'price_unit': 200,
                    'tax_ids': self.taxes['vat_in_5_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT4',
                    'price_unit': 150,
                    'tax_ids': self.taxes['vat_in_0_g'].ids,
                }),
            ],
        })
        move.action_post()

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-20',
            'date': '2023-01-20',
            'ref': 'INV003',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 800,
                    'tax_ids': self.taxes['vat_in_0_eu_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT2',
                    'price_unit': 700,
                    'tax_ids': self.taxes['vat_in_0_eu_s'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT3',
                    'price_unit': 600,
                    'tax_ids': self.taxes['vat_in_22_car'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT4',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_in_22_car_part'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT5',
                    'price_unit': 400,
                    'tax_ids': self.taxes['vat_in_22_assets'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT6',
                    'price_unit': 300,
                    'tax_ids': self.taxes['vat_in_imp_cus'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT7',
                    'price_unit': 200,
                    'tax_ids': self.taxes['vat_in_22_imp_kms_38'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT8',
                    'price_unit': 100,
                    'tax_ids': self.taxes['vat_in_0_kms_41_1'].ids,
                }),
            ],
        })
        move.action_post()

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'partner_id': self.partner_ee_1.id,
            'invoice_date': '2023-01-11',
            'date': '2023-01-11',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_out_22_g'].ids,
                }),
            ],
        })
        move.action_post()

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'partner_id': self.partner_ee_2.id,
            'invoice_date': '2023-01-13',
            'date': '2023-01-13',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_out_22_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT2',
                    'price_unit': 300,
                    'tax_ids': self.taxes['vat_out_9_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT3',
                    'price_unit': 200,
                    'tax_ids': self.taxes['vat_out_5_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT4',
                    'price_unit': 150,
                    'tax_ids': self.taxes['vat_out_0_g'].ids,
                }),
            ],
        }).action_post()

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-01-25',
            'date': '2023-01-25',
            'invoice_line_ids': [
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT1',
                    'price_unit': 800,
                    'tax_ids': self.taxes['vat_out_0_eu_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT2',
                    'price_unit': 700,
                    'tax_ids': self.taxes['vat_out_0_eu_s'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT3',
                    'price_unit': 600,
                    'tax_ids': self.taxes['vat_out_0_exp_g'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT4',
                    'price_unit': 500,
                    'tax_ids': self.taxes['vat_out_0_pas'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT5',
                    'price_unit': 400,
                    'tax_ids': self.taxes['vat_out_0_exp_s'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT6',
                    'price_unit': 300,
                    'tax_ids': self.taxes['vat_out_exempt'].ids,
                }),
                (0, 0, {
                    'quantity': 1.0,
                    'name': 'PT7',
                    'price_unit': 200,
                    'tax_ids': self.taxes['vat_out_0_kms_41_1'].ids,
                }),
            ],
        })
        move.action_post()

        report = self.env.ref('l10n_ee.tax_report_vat')
        options = report.get_options()

        expected_xml = """
            <vatDeclaration>
                <taxPayerRegCode>12345678</taxPayerRegCode>
                <year>2023</year>
                <month>1</month>
                <declarationType>1</declarationType>
                <version>KMD4</version>
                <declarationBody>
                    <noSales>false</noSales>
                    <noPurchases>false</noPurchases>
                    <sumPerPartnerSales>false</sumPerPartnerSales>
                    <sumPerPartnerPurchases>false</sumPerPartnerPurchases>
                    <transactions22>2600.00</transactions22>
                    <transactions9>300.00</transactions9>
                    <transactions5>200.00</transactions5>
                    <transactionsZeroVat>3150.00</transactionsZeroVat>
                    <euSupplyInclGoodsAndServicesZeroVat>1500.00</euSupplyInclGoodsAndServicesZeroVat>
                    <euSupplyGoodsZeroVat>800.00</euSupplyGoodsZeroVat>
                    <exportZeroVat>1100.00</exportZeroVat>
                    <salePassengersWithReturnVat>500.00</salePassengersWithReturnVat>
                    <inputVatTotal>1228.00</inputVatTotal>
                    <importVat>344.00</importVat>
                    <fixedAssetsVat>88.00</fixedAssetsVat>
                    <carsVat>132.00</carsVat>
                    <carsPartialVat>55.00</carsPartialVat>
                    <euAcquisitionsGoodsAndServicesTotal>1500.00</euAcquisitionsGoodsAndServicesTotal>
                    <euAcquisitionsGoods>800.00</euAcquisitionsGoods>
                    <acquisitionOtherGoodsAndServicesTotal>100.00</acquisitionOtherGoodsAndServicesTotal>
                    <acquisitionImmovablesAndScrapMetalAndGold>100.00</acquisitionImmovablesAndScrapMetalAndGold>
                    <supplyExemptFromTax>300.00</supplyExemptFromTax>
                    <supplySpecialArrangements>200.00</supplySpecialArrangements>
                </declarationBody>
                <salesAnnex>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <sumForRateInPeriod>500.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>9</taxRate>
                        <sumForRateInPeriod>300.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>5</taxRate>
                        <sumForRateInPeriod>200.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerRegCode>98765432</buyerRegCode>
                        <buyerName>Partner EE 1</buyerName>
                        <invoiceNumber>INV/2023/00001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSum>500.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <sumForRateInPeriod>500.00</sumForRateInPeriod>
                    </saleLine>
                </salesAnnex>
                <purchasesAnnex>
                    <purchaseLine>
                        <sellerName>Partner EE 2</sellerName>
                        <invoiceNumber>INV002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSumVat>1297.00</invoiceSumVat>
                        <vatInPeriod>147.00</vatInPeriod>
                        <comments>11</comments>
                    </purchaseLine>
                    <purchaseLine>
                        <sellerRegCode>98765432</sellerRegCode>
                        <sellerName>Partner EE 1</sellerName>
                        <invoiceNumber>INV001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSumVat>610.00</invoiceSumVat>
                        <vatInPeriod>110.00</vatInPeriod>
                    </purchaseLine>
                </purchasesAnnex>
            </vatDeclaration>
        """

        actual_xml = self.env[report.custom_handler_model_name].export_to_xml(options)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2023-02-01')
    def test_special_code_single_tax(self):
        """ Special code column (comments) should not appear when
        there are only invoices with invoice lines with a single
        tax
        """
        moves = self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'journal_id': self.company_data['default_journal_sale'].id,
                'partner_id': self.partner_ee_1.id,
                'invoice_date': '2023-01-11',
                'date': '2023-01-11',
                'invoice_line_ids': [
                    (0, 0, {
                        'quantity': 1.0,
                        'name': 'PT1',
                        'price_unit': 500,
                        'tax_ids': self.taxes['vat_out_22_g'].ids,
                    }),
                ],
            },
            {
                'move_type': 'out_invoice',
                'journal_id': self.company_data['default_journal_sale'].id,
                'partner_id': self.partner_ee_1.id,
                'invoice_date': '2023-01-11',
                'date': '2023-01-11',
                'invoice_line_ids': [
                    (0, 0, {
                        'quantity': 1.0,
                        'name': 'PT1',
                        'price_unit': 500,
                        'tax_ids': self.taxes['vat_out_9_g'].ids,
                    }),
                ],
            },
        ])

        moves.action_post()

        report = self.env.ref('l10n_ee.tax_report_vat')
        options = report.get_options()
        expected_xml = """
            <vatDeclaration>
            <taxPayerRegCode>12345678</taxPayerRegCode>
            <year>2023</year>
            <month>1</month>
            <declarationType>1</declarationType>
            <version>KMD4</version>
            <declarationBody>
                <noSales>false</noSales>
                <noPurchases>true</noPurchases>
                <sumPerPartnerSales>false</sumPerPartnerSales>
                <sumPerPartnerPurchases>false</sumPerPartnerPurchases>
                <transactions22>500.00</transactions22>
                <transactions9>500.00</transactions9>
            </declarationBody>
            <salesAnnex>
                <saleLine>
                <buyerRegCode>98765432</buyerRegCode>
                <buyerName>Partner EE 1</buyerName>
                <invoiceNumber>INV/2023/00002</invoiceNumber>
                <invoiceDate>2023-01-11</invoiceDate>
                <invoiceSum>500.00</invoiceSum>
                <taxRate>9</taxRate>
                <sumForRateInPeriod>500.00</sumForRateInPeriod>
                </saleLine>
                <saleLine>
                <buyerRegCode>98765432</buyerRegCode>
                <buyerName>Partner EE 1</buyerName>
                <invoiceNumber>INV/2023/00001</invoiceNumber>
                <invoiceDate>2023-01-11</invoiceDate>
                <invoiceSum>500.00</invoiceSum>
                <taxRate>22</taxRate>
                <sumForRateInPeriod>500.00</sumForRateInPeriod>
                </saleLine>
            </salesAnnex>
            </vatDeclaration>
        """

        actual_xml = self.env[report.custom_handler_model_name].export_to_xml(options)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )
