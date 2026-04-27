import csv
import io


from odoo import Command, fields, tools
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged, freeze_time
from odoo.tests.common import test_xsd


class TestDKReportCommon(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('dk')
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({
            'city': 'Aalborg',
            'zip': '9430',
            'vat': 'DK12345674',
            'phone': '+45 32 12 34 56',
            'street': 'Paradisæblevej, 10',
        })
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'DK5000400440116243',
            'allow_out_payment': True,
        })
        cls.env['res.partner'].create({
            'name': 'Mr Big CEO',
            'is_company': False,
            'phone': '+45 32 12 34 77',
            'parent_id': cls.company_data['company'].partner_id.id,
        })

        (cls.partner_a + cls.partner_b).write({
            'street': 'Paradisæblevej, 12',
            'city': 'Garnich',
            'zip': 'L-8353',
            'country_id': cls.env.ref('base.lu').id,
            'phone': '+352 24 11 11 11',
        })

        cls.product_a.default_code = 'PA'
        cls.product_b.default_code = 'PB'

        # Create invoices
        invoices = cls.env['account.move'].create([{
                'move_type': 'out_invoice',
                'invoice_date': '2021-01-01',
                'date': '2021-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 5.0,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2021-03-01',
                'date': '2021-03-01',
                'partner_id': cls.company_data['company'].partner_id.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 2.0,
                        'price_unit': 1500.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'out_refund',
                'invoice_date': '2021-03-01',
                'date': '2021-03-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 3.0,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2021-06-30',
                'date': '2021-06-30',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_b.id,
                        'quantity': 10.0,
                        'price_unit': 800.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    })
                ],
            },
        ])
        invoices.action_post()

    def _generate_xml(cls):
        report = cls.env.ref('account_reports.general_ledger_report')
        options = cls._generate_options(report, fields.Date.from_string('2021-01-01'), fields.Date.from_string('2021-12-31'))
        return cls.env[report.custom_handler_model_name].l10n_dk_export_saft_to_xml(options)['file_content']


@freeze_time('2022-01-01')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDKReport(TestDKReportCommon):

    def test_validate_dk_saft_report_values(self):
        payable_account = self.env['account.chart.template'].ref("dk_coa_7440")
        liability_account = self.env['account.chart.template'].ref("dk_coa_7350")
        # Create a move without a partner but with a receivable line
        move = self.env['account.move'].create({
                'move_type': 'entry',
                'invoice_date': '2021-03-01',
                'date': '2021-03-01',
                'partner_id': None,
                'invoice_line_ids': [
                    Command.create({
                        'credit': 67.0,
                        'account_id': payable_account.id,
                    }),
                    Command.create({
                        'debit': 67.0,
                        'account_id': liability_account.id,
                    })
                ],
            })
        move._post()
        self.env.flush_all()

        with tools.file_open("l10n_dk_reports/tests/xml/expected_test_saft_report.xml", "rb") as expected_xml:
            stringified_xml = self._generate_xml()
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(stringified_xml),
                self.get_xml_tree_from_string(expected_xml.read()),
            )

    def test_l10n_dk_saft_ensure_all_account_type_are_handled(self):
        report = self.env.ref('account_reports.general_ledger_report')
        account_selection = [selection[0] for selection in self.env["account.account"]._fields["account_type"].selection]
        for account_type in account_selection:
            self.env[report.custom_handler_model_name]._saft_get_account_type(account_type)

    def test_l10n_dk_general_ledger_csv_export(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options({})
        csv_content = self.env[report.custom_handler_model_name].l10n_dk_export_general_ledger_csv(options)['file_content']
        reader = csv.reader(io.StringIO(csv_content.decode()), delimiter=',')

        expected_values = (
            # _20230131 is not the export date, but rather the date at which the norm of this csv export was enforced
            ('KONTONUMMER_20230131', 'KONTONAVN_20230131', 'VAERDI_20230131'),
            ('619000', 'Trade receivables', '6250'),
            ('694000', 'Retained earnings, cf. distribution of profit', '3000'),
            ('744001', 'Trade payables (short-term) (copy)', '-10000'),
            ('768000', 'Output VAT', '-1250'),
            ('774000', 'Input VAT', '2000'),
        )
        for idx, content in enumerate(reader):
            self.assertSequenceEqual(expected_values[idx], content)


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestDKReportXML(TestDKReportCommon):

    @test_xsd(url='https://erhvervsstyrelsen.dk/sites/default/files/2023-01/Danish_SAF-T_Financial_Schema_v_1_0_0.zip')
    def test_xml_validity(self):
        return self._generate_xml()
