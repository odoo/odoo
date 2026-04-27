# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command, release
from odoo.tests import tagged
from odoo.addons.l10n_cz_reports_2025.tests.test_l10n_cz_reports_2025_common import CzechReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class CzechTaxReportTest(CzechReportsCommon):
    @freeze_time('2019-12-31')
    def setUp(self):
        super().setUp()
        company = self.env.company
        first_tax = self.env.ref(f'account.{company.id}_l10n_cz_21_domestic_supplies')
        second_tax = self.env.ref(f'account.{company.id}_l10n_cz_import_goods_tax_authority')
        invoice_date = '2019-11-12'

        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'partner_id': self.partner_a.id,
            'invoice_date': invoice_date,
            'date': invoice_date,
            'taxable_supply_date': invoice_date,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'name': 'product test 1',
                    'price_unit': 100,
                    'tax_ids': first_tax.ids,
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 1.0,
                    'name': 'product test 2',
                    'price_unit': 50,
                    'tax_ids': second_tax.ids,
                }),
            ]
        }).action_post()
        self._fill_tax_report_line_external_value('l10n_cz.l10n_cz_vat_declaration_line_54_coefficient', 35, invoice_date)
        self._fill_tax_report_line_external_value('l10n_cz.l10n_cz_vat_declaration_line_55_value', 83, invoice_date)

    @freeze_time('2019-12-31')
    def test_generate_xml_default_options(self):
        report = self.env.ref('l10n_cz.l10n_cz_vat_declaration')
        options = report.get_options({})

        generated_xml = self.env['l10n_cz.tax.report.handler'].export_to_xml(options)['file_content']
        expected_xml = f"""
            <Pisemnost nazevSW="Odoo SA" verzeSW="{release.version}">
            <DPHDP3 verzePis="02.01">
                <VetaD dapdph_forma="B" dokument="DP3" k_uladis="DPH" typ_platce="P" mesic="11" rok="2019"/>
                <VetaP zkrobchjm="company_1_data" c_pracufo="2001" c_ufo="451" dic="12345679" typ_ds="P" email="info@company.czexample.com"/>
                <Veta1 dan23="21.0" obrat23="100.0"/>
                <Veta2/>
                <Veta3/>
                <Veta4 dov_cu="50.0" odp_cu_nar="50.0" odp_sum_nar="50.0"/>
                <Veta5 koef_p20_nov="35.0" odp_uprav_kf="83.0"/>
                <Veta6 dan_zocelk="21.0" dano_no="112.0" odp_zocelk="133.0"/>
            </DPHDP3>
            </Pisemnost>
        """
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    @freeze_time('2019-12-31')
    def test_generate_xml_custom_options(self):
        report = self.env.ref('l10n_cz.l10n_cz_vat_declaration')
        options = self._generate_options(report, date_from='2017-04-01', date_to='2017-06-30')
        self.env.company.partner_id.company_type = 'person'

        generated_xml = self.env['l10n_cz.tax.report.handler'].export_to_xml(options)['file_content']
        expected_xml = f"""
            <Pisemnost nazevSW="Odoo SA" verzeSW="{release.version}">
            <DPHDP3 verzePis="02.01">
                <VetaD dapdph_forma="B" dokument="DP3" k_uladis="DPH" typ_platce="P" ctvrt="2" rok="2017"/>
                <VetaP zkrobchjm="company_1_data" c_pracufo="2001" c_ufo="451" dic="12345679" typ_ds="F" email="info@company.czexample.com"/>
                <Veta1/>
                <Veta2/>
                <Veta3/>
                <Veta4/>
                <Veta5/>
                <Veta6/>
            </DPHDP3>
            </Pisemnost>
        """
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml),
            self.get_xml_tree_from_string(expected_xml),
        )
