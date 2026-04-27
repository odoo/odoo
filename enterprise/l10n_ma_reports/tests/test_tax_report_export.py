from odoo import Command
from odoo.addons.account_reports.models.account_report import AccountReportFileDownloadException
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMaExport(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('ma')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'vat': '22233411',
        })

        cls.partner_ma = cls.env['res.partner'].create({
            'name': 'Ma customer',
            'vat': '22233412',
            'country_id': cls.env.ref('base.ma').id,
        })

        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A',
        })

        cls.report = cls.env.ref('l10n_ma.tax_report_vat')

    def test_simple_export_tax_report(self):
        """ This will test a simple export with no moves data. """
        self._report_compare_with_test_file(
            self.report.dispatch_report_action(self._generate_options(self.report, '2019-01-01', '2019-01-31'), 'l10n_ma_reports_export_vat_to_xml'),
            test_xml="""
                <DeclarationReleveDeduction>
                    <idf>22233411</idf>
                    <annee>2019</annee>
                    <periode>1</periode>
                    <regime>1</regime>
                    <releveDeductions>
                    </releveDeductions>
                </DeclarationReleveDeduction>
            """,
        )

        self.env.company.account_tax_periodicity = 'trimester'
        self._report_compare_with_test_file(
            self.report.dispatch_report_action(self._generate_options(self.report, '2019-01-01', '2019-03-31'), 'l10n_ma_reports_export_vat_to_xml'),
             test_xml="""
                <DeclarationReleveDeduction>
                    <idf>22233411</idf>
                    <annee>2019</annee>
                    <periode>1</periode>
                    <regime>2</regime>
                    <releveDeductions>
                    </releveDeductions>
                </DeclarationReleveDeduction>
            """,
        )

    def test_export_tax_report_with_data(self):
        """ This will test a simple export with moves data. """
        self.partner_ma.company_registry = '123456789123456'

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_ma.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
            })],
        })

        bill.action_post()
        self.pay_with_statement_line(bill, self.company_data['default_journal_bank'].id, '2019-01-01', -600)

        self.env.flush_all()

        self._report_compare_with_test_file(
            self.report.dispatch_report_action(self._generate_options(self.report, '2019-01-01', '2019-01-31'), 'l10n_ma_reports_export_vat_to_xml'),
            test_xml="""
                <DeclarationReleveDeduction>
                    <idf>22233411</idf>
                    <annee>2019</annee>
                    <periode>1</periode>
                    <regime>1</regime>
                    <releveDeductions>
                        <rd>
                            <ordre>1</ordre>
                            <num>BILL/2019/01/0001</num>
                            <des>BILL/2019/01/0001</des>
                            <mht>500.0</mht>
                            <tva>100.0</tva>
                            <ttc>600.0</ttc>
                            <refF>
                                <if>22233412</if>
                                <nom>Ma customer</nom>
                                <ice>123456789123456</ice>
                            </refF>
                            <tx>20.0</tx>
                            <mp>
                                <id>7</id>
                            </mp>
                            <dpai>2019-01-01</dpai>
                            <dfac>2019-01-01</dfac>
                        </rd>
                    </releveDeductions>
                </DeclarationReleveDeduction>
            """,
        )

    def test_export_tax_report_local_partner_with_no_ice(self):
        """
            This test will try to export the xml with a partner missing the ice field. We will check the non critical
            error but also the content of the file to see if the move is well skipped
        """
        partner_ma_with_ice = self.env['res.partner'].create({
            'name': 'Ma customer with ice',
            'vat': '22233411',
            'country_id': self.env.ref('base.ma').id,
            'company_registry': '123456789123456',
        })

        bills = self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'date': '2019-01-01',
                'invoice_date': '2019-01-01',
                'partner_id': self.partner_ma.id,
                'currency_id': self.other_currency.id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'date': '2019-01-01',
                'invoice_date': '2019-01-01',
                'partner_id': partner_ma_with_ice.id,
                'currency_id': self.other_currency.id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                })],
            },
        ])

        bills.action_post()
        self.pay_with_statement_line(bills, self.company_data['default_journal_bank'].id, '2019-01-01', -1200)

        self.env.flush_all()

        try:
            self.report.dispatch_report_action(self._generate_options(self.report, '2019-01-01', '2019-01-31'), 'l10n_ma_reports_export_vat_to_xml')
            self.fail("Generating the XML file should have raised, due to the partner without ICE")

        except AccountReportFileDownloadException as download_exception:
            self.assertTrue('partner_vat_ice_missing' in download_exception.errors)
            self._report_compare_with_test_file(
                download_exception.content,
                test_xml="""
                    <DeclarationReleveDeduction>
                        <idf>22233411</idf>
                        <annee>2019</annee>
                        <periode>1</periode>
                        <regime>1</regime>
                        <releveDeductions>
                            <rd>
                                <ordre>1</ordre>
                                <num>BILL/2019/01/0002</num>
                                <des>BILL/2019/01/0002</des>
                                <mht>500.0</mht>
                                <tva>100.0</tva>
                                <ttc>600.0</ttc>
                                <refF>
                                    <if>22233411</if>
                                    <nom>Ma customer with ice</nom>
                                    <ice>123456789123456</ice>
                                </refF>
                                <tx>20.0</tx>
                                <mp>
                                    <id>7</id>
                                </mp>
                                <dpai>2019-01-01</dpai>
                                <dfac>2019-01-01</dfac>
                            </rd>
                        </releveDeductions>
                    </DeclarationReleveDeduction>
                """,
            )

    def test_export_tax_report_critical_error(self):
        """
            This test will check the export when having critical error, there is two potentials critical errors.
            - When the company has no vat
            - When the period selected of the report is not monthly or quarterly
        """
        self.env.company.vat = False
        self.partner_ma.company_registry = '123456789123456'

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_ma.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
            })],
        })

        bill.action_post()
        self.pay_with_statement_line(bill, self.company_data['default_journal_bank'].id, '2019-01-01', -600)

        self.env.flush_all()

        try:
            self.report.dispatch_report_action(self._generate_options(self.report, '2019-01-01', '2019-01-31'), 'l10n_ma_reports_export_vat_to_xml')
            self.fail("Generating the XML file should have raised, due to the company having no VAT")

        except AccountReportFileDownloadException as download_exception:
            self.assertTrue('company_vat_missing' in download_exception.errors)
            self.assertFalse(download_exception.content)

        self.env.company.vat = '22233411'
        self.env.company.account_tax_periodicity = 'semester'

        self.env.flush_all()

        try:
            self.report.dispatch_report_action(self._generate_options(self.report, '2019-01-01', '2019-01-31'), 'l10n_ma_reports_export_vat_to_xml')
            self.fail("Generating the XML file should have raised, due to report periodicity being invalid.")

        except AccountReportFileDownloadException as download_exception:
            self.assertTrue('period_invalid' in download_exception.errors)
            self.assertFalse(download_exception.content)

    def test_export_tax_report_foreign_customer(self):
        # 'vat' value must be random to avoid the partner auto-completion feature that would overwrite the company_registry (ICE)
        foreign_customer = self.env['res.partner'].create({
            'name': 'Foreign customer with no ice',
            'vat': 'US12345',
            'country_id': self.env.ref('base.us').id,
        })

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': foreign_customer.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
            })],
        })

        bill.action_post()
        self.pay_with_statement_line(bill, self.company_data['default_journal_bank'].id, '2019-01-01', -1200)

        self.env.flush_all()

        self._report_compare_with_test_file(
            self.report.dispatch_report_action(self._generate_options(self.report, '2019-01-01', '2019-01-31'), 'l10n_ma_reports_export_vat_to_xml'),
            test_xml="""
                <DeclarationReleveDeduction>
                    <idf>22233411</idf>
                    <annee>2019</annee>
                    <periode>1</periode>
                    <regime>1</regime>
                    <releveDeductions>
                        <rd>
                            <ordre>1</ordre>
                            <num>BILL/2019/01/0001</num>
                            <des>BILL/2019/01/0001</des>
                            <mht>500.0</mht>
                            <tva>100.0</tva>
                            <ttc>600.0</ttc>
                            <refF>
                                <if>20727020</if>
                                <nom>Foreign customer with no ice</nom>
                                <ice>20727020</ice>
                            </refF>
                            <tx>20.0</tx>
                            <mp>
                                <id>7</id>
                            </mp>
                            <dpai>2019-01-01</dpai>
                            <dfac>2019-01-01</dfac>
                        </rd>
                    </releveDeductions>
                </DeclarationReleveDeduction>
            """,
        )
