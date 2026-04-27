from freezegun import freeze_time

from odoo import Command, release
from odoo.tests import tagged
from odoo.addons.l10n_cz_reports_2025.tests.test_l10n_cz_reports_2025_common import CzechReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class CzechVIESReportTest(CzechReportsCommon):
    @freeze_time('2019-12-31')
    def setUp(self):
        super().setUp()
        self.env['account.move'].create({
            'invoice_date': '2019-11-12',
            'taxable_supply_date': '2019-11-12',
            'move_type': 'in_invoice',
            'partner_id': self.partner_eu_1.id,
            'invoice_line_ids': [Command.create(line_data) for line_data in [
                {'quantity': 1, 'price_unit': 100, 'l10n_cz_transaction_code': '0'},
                {'quantity': 3, 'price_unit': 10, 'l10n_cz_transaction_code': '0'},
                {'quantity': 2, 'price_unit': 30, 'l10n_cz_transaction_code': '1'},
            ]],
        }).action_post()
        self.env['account.move'].create({
            'invoice_date': '2019-11-12',
            'taxable_supply_date': '2019-11-12',
            'move_type': 'in_invoice',
            'partner_id': self.partner_eu_1.id,
            'invoice_line_ids': [Command.create(line_data) for line_data in [
                {'quantity': 2, 'price_unit': 90, 'l10n_cz_transaction_code': '1'},
                {'quantity': 3, 'price_unit': 20, 'l10n_cz_transaction_code': '2'},
                {'quantity': 1, 'price_unit': 80, 'l10n_cz_transaction_code': '3'},
            ]],
        }).action_post()
        self.env['account.move'].create({
            'invoice_date': '2019-11-12',
            'taxable_supply_date': '2019-11-12',
            'move_type': 'in_invoice',
            'partner_id': self.partner_eu_2.id,
            'invoice_line_ids': [Command.create(line_data) for line_data in [
                {'quantity': 3, 'price_unit': 20, 'l10n_cz_transaction_code': '1'},
                {'quantity': 2, 'price_unit': 90, 'l10n_cz_transaction_code': '1'},
                {'quantity': 1, 'price_unit': 80, 'l10n_cz_transaction_code': '3'},
            ]],
        }).action_post()
        self.env['account.move'].create({
            'invoice_date': '2019-11-12',
            'taxable_supply_date': '2019-11-12',
            'move_type': 'in_invoice',
            'partner_id': self.partner_eu_3.id,
            'invoice_line_ids': [Command.create({'quantity': 3, 'price_unit': 20, 'l10n_cz_transaction_code': '2'})],
        }).action_post()
        self.env['account.move'].create({
            'invoice_date': '2019-11-12',
            'taxable_supply_date': '2019-11-12',
            'move_type': 'in_invoice',
            'partner_id': self.partner_non_eu.id,
            'invoice_line_ids': [Command.create(line_data) for line_data in [
                {'quantity': 3, 'price_unit': 20, 'l10n_cz_transaction_code': '0'},
                {'quantity': 2, 'price_unit': 90, 'l10n_cz_transaction_code': '1'},
                {'quantity': 1, 'price_unit': 80, 'l10n_cz_transaction_code': '2'},
                {'quantity': 4, 'price_unit': 50, 'l10n_cz_transaction_code': '3'},
            ]],
        }).action_post()
        self.env.flush_all()

    @freeze_time('2019-12-31')
    def test_cz_vies_report(self):
        report = self.env.ref('l10n_cz_reports_2025.vies_summary_report')
        options = report.get_options({})

        # Excluding journal items lines from the test
        lines = [line for line in report._get_lines({**options, 'unfold_all': True}) if line['level'] != 6]

        self.assertLinesValues(
            lines,
            # Name                   county code        vat number          transaction code         supplies number                total
            [0,                          1,                 2,                      3,                     4,                        5],
            [
                ('B. SECTION',          '',                '',                      '',                    8,                        890),
                ('Partner EU 1',        'FR',              'FR23334175221',         '',                    5,                        510),
                ('0 Goods',             'FR',              'FR23334175221',         '0',                   1,                        130),
                ('1 Business asset',    'FR',              'FR23334175221',         '1',                   2,                        240),
                ('2 Triangular',        'FR',              'FR23334175221',         '2',                   1,                        60),
                ('3 Service',           'FR',              'FR23334175221',         '3',                   1,                        80),
                ('Partner EU 2',        'DE',              'DE123456788',           '',                    2,                        320),
                ('1 Business asset',    'DE',              'DE123456788',           '1',                   1,                        240),
                ('3 Service',           'DE',              'DE123456788',           '3',                   1,                        80),
                ('Partner EU 3',        'BE',              'BE0477472701',          '',                    1,                        60),
                ('2 Triangular',        'BE',              'BE0477472701',          '2',                   1,                        60),
            ],
            options,
        )

    @freeze_time('2019-12-31')
    def test_cz_vies_report_default_options_export(self):
        self.env['account.move'].create({
            'invoice_date': '2019-11-12',
            'taxable_supply_date': '2019-11-12',
            'move_type': 'in_invoice',
            'partner_id': self.partner_eu_1.id,
            'invoice_line_ids': [Command.create(line_data) for line_data in [
                {'quantity': 1, 'price_unit': 100, 'l10n_cz_transaction_code': '0'},
                {'quantity': 3, 'price_unit': 10, 'l10n_cz_transaction_code': '0'},
                {'quantity': 2, 'price_unit': 30, 'l10n_cz_transaction_code': '1'},
            ]],
        }).action_post()
        report = self.env.ref('l10n_cz_reports_2025.vies_summary_report')
        options = report.get_options({})

        generated_xml = self.env['l10n_cz.vies.summary.report.handler'].export_to_xml(options)['file_content']
        expected_xml = f"""
            <Pisemnost nazevSW="Odoo SA" verzeSW="{release.version}">
            <DPHSHV verzePis="02.01">
                <VetaD shvies_forma="N" dokument="SHV" k_uladis="DPH" mesic="11" rok="2019"/>
                <VetaP typ_ds="P" zkrobchjm="company_1_data" c_pracufo="2001" c_ufo="451" dic="12345679" email="info@company.czexample.com"/>
                <VetaR k_stat="FR" c_vat="FR23334175221" k_pln_eu="0" pln_pocet="2" pln_hodnota="260"/>
                <VetaR k_stat="FR" c_vat="FR23334175221" k_pln_eu="1" pln_pocet="3" pln_hodnota="300"/>
                <VetaR k_stat="FR" c_vat="FR23334175221" k_pln_eu="2" pln_pocet="1" pln_hodnota="60"/>
                <VetaR k_stat="FR" c_vat="FR23334175221" k_pln_eu="3" pln_pocet="1" pln_hodnota="80"/>
                <VetaR k_stat="DE" c_vat="DE123456788"   k_pln_eu="1" pln_pocet="1" pln_hodnota="240"/>
                <VetaR k_stat="DE" c_vat="DE123456788"   k_pln_eu="3" pln_pocet="1" pln_hodnota="80"/>
                <VetaR k_stat="BE" c_vat="BE0477472701"  k_pln_eu="2" pln_pocet="1" pln_hodnota="60"/>
            </DPHSHV>
            </Pisemnost>
        """
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    @freeze_time('2019-12-31')
    def test_cz_vies_report_custom_options_export(self):
        report = self.env.ref('l10n_cz_reports_2025.vies_summary_report')
        options = self._generate_options(report, date_from='2018-07-01', date_to='2018-09-30')
        self.env.company.partner_id.company_type = 'person'

        generated_xml = self.env['l10n_cz.vies.summary.report.handler'].export_to_xml(options)['file_content']
        expected_xml = f"""
            <Pisemnost nazevSW="Odoo SA" verzeSW="{release.version}">
            <DPHSHV verzePis="02.01">
                <VetaD shvies_forma="N" dokument="SHV" k_uladis="DPH" ctvrt="3" rok="2018"/>
                <VetaP typ_ds="F" zkrobchjm="company_1_data" c_pracufo="2001" c_ufo="451" dic="12345679" email="info@company.czexample.com"/>
            </DPHSHV>
            </Pisemnost>
        """
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    def test_cz_vies_report_with_miscellaneous_entry(self):
        self.env['account.move'].create({
            'invoice_date': '2025-01-01',
            'taxable_supply_date': '2025-01-01',
            'move_type': 'in_invoice',
            'partner_id': self.partner_eu_1.id,
            'invoice_line_ids': [Command.create(line_data) for line_data in [
                {
                    'price_unit': 20,
                    'deferred_start_date': '2025-01-01',
                    # Create deferred entries --> not an invoice/refund (with a transaction code set)
                    'deferred_end_date': '2025-12-31',
                    'l10n_cz_transaction_code': '0',
                },
            ]],
        }).action_post()
        report = self.env.ref('l10n_cz_reports_2025.vies_summary_report')
        options = self._generate_options(report, date_from='2025-01-01', date_to='2025-12-31')

        self.assertLinesValues(
            report._get_lines({**options, 'unfold_all': True}), [0, 5],
            #        name              total
            [
                ('B. SECTION',          20),
                ('Partner EU 1',        20),
                ('0 Goods',             20),
                ('BILL/2025/01/0001',   20),
            ],
            options,
        )

    def test_cz_vies_report_with_integer_rounding(self):
        self.env['account.move'].create({
            'invoice_date': '2025-01-01',
            'taxable_supply_date': '2025-01-01',
            'move_type': 'in_invoice',
            'partner_id': self.partner_eu_1.id,
            'invoice_line_ids': [Command.create({'price_unit': 20.3, 'l10n_cz_transaction_code': '0'})],
        }).action_post()
        report = self.env.ref('l10n_cz_reports_2025.vies_summary_report')
        report.integer_rounding = 'HALF-UP'
        options = self._generate_options(report, date_from='2025-01-01', date_to='2025-12-31')

        self.assertLinesValues(
            report._get_lines({**options, 'unfold_all': True}), [0, 5],
            #        name              total
            [
                ('B. SECTION',          21),
                ('Partner EU 1',        21),
                ('0 Goods',             21),
                ('BILL/2025/01/0001',   21),
            ],
            options,
        )

    @freeze_time('2020-12-31')
    def test_cz_vies_report_foreign_exchange_mismatch(self):
        """
            Test to verify that invoice amounts in currencies different from
              the company's are correctly converted in the VIES summary report.
        """
        first_tax = self.env.ref(f'account.{self.env.company.id}_l10n_cz_21_domestic_supplies')

        self.env['res.currency.rate'].create({
            'name': '2020-11-12',
            'currency_id': self.env.ref('base.USD').id,
            'rate': 0.1,
            'company_id': self.env.user.company_id.id,
        })

        partner = self.env['res.partner'].create({
            'name': 'Test EU Partner',
            'country_id': self.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })

        self.env['account.move'].create({
            'currency_id': self.env.ref('base.USD').id,
            'invoice_date': '2020-11-12',
            'taxable_supply_date': '2020-11-12',
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [Command.create({
                'name': 'Test Line',
                'quantity': 1,
                'price_unit': 100,
                'l10n_cz_transaction_code': '0',
                'tax_ids': first_tax.ids,
            })],
        }).action_post()

        report = self.env.ref('l10n_cz_reports_2025.vies_summary_report')
        options = self.env['account.report'].browse(report.id).get_options({})
        options['date'] = {
            'string': '11/11/2020 - 13/11/2020',
            'mode': 'range',
            'date_from': '2020-11-11',
            'date_to': '2020-11-13',
            'filter': 'custom',
            'period_type': 'range',
        }

        xml_content = self.env['l10n_cz.vies.summary.report.handler'].export_to_xml(options)['file_content']
        tree = self.get_xml_tree_from_string(xml_content)
        veta_r = tree.find('.//VetaR')

        self.assertEqual(veta_r.attrib.get('pln_hodnota'), '1000')

    @freeze_time('2021-12-31')
    def test_cz_vies_report_foreign_exchange_mismatch_refund(self):
        """
            Test to verify that invoice amounts in currencies different from
              the company's are correctly converted in the VIES summary report when the move type is 'out_refund'.
        """
        first_tax = self.env.ref(f'account.{self.env.company.id}_l10n_cz_21_domestic_supplies')

        self.env['res.currency.rate'].create({
            'name': '2020-11-12',
            'currency_id': self.env.ref('base.USD').id,
            'rate': 0.1,
            'company_id': self.env.user.company_id.id,
        })

        partner = self.env['res.partner'].create({
            'name': 'Test EU Partner',
            'country_id': self.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })

        self.env['account.move'].create({
            'currency_id': self.env.ref('base.USD').id,
            'invoice_date': '2021-11-12',
            'taxable_supply_date': '2021-11-12',
            'move_type': 'out_refund',
            'partner_id': partner.id,
            'invoice_line_ids': [Command.create({
                'name': 'Refund Line',
                'quantity': 1,
                'price_unit': 100,
                'l10n_cz_transaction_code': '0',
                'tax_ids': first_tax.ids,
            })],
        }).action_post()

        refund_report = self.env.ref('l10n_cz_reports_2025.vies_summary_report')
        refund_options = self.env['account.report'].browse(refund_report.id).get_options({})
        refund_options['date'] = {
            'string': '11/11/2021 - 13/11/2021',
            'mode': 'range',
            'date_from': '2021-11-11',
            'date_to': '2021-11-13',
            'filter': 'custom',
            'period_type': 'range',
        }

        refund_xml_content = self.env['l10n_cz.vies.summary.report.handler'].export_to_xml(refund_options)['file_content']
        refudn_tree = self.get_xml_tree_from_string(refund_xml_content)
        refudn_veta_r = refudn_tree.find('.//VetaR')

        self.assertEqual(refudn_veta_r.attrib.get('pln_hodnota'), '-1000')
