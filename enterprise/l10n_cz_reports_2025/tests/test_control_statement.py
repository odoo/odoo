from freezegun import freeze_time

from odoo import Command, release
from odoo.tests import tagged
from odoo.addons.l10n_cz_reports_2025.tests.test_l10n_cz_reports_2025_common import CzechReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class CzechControlStatementTest(CzechReportsCommon):
    @freeze_time('2024-02-01')
    def test_generate_xml_control_statement(self):
        """
            This test verifies that the Control Statement is generated with all the necessary fields for
            all sections of the Control Statement, including different l10n_cz_supplies_code within the
            same move. The taxes used define in which section the move value should appear.
        """
        # Code A1 and A5
        self.env['account.move'].create({
            'invoice_date': '2024-01-04',
            'taxable_supply_date': '2024-01-04',
            'move_type': 'out_invoice',
            'partner_id': self.partner_cz_1.id,
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 500, 'tax_ids': self.l10n_cz_tax_reverse_charge_mode.ids, 'l10n_cz_supplies_code': '1'},
                {'price_unit': 300, 'tax_ids': self.l10n_cz_tax_reverse_charge_mode.ids, 'l10n_cz_supplies_code': '17'},
                {'price_unit': 1000, 'tax_ids': self.l10n_cz_21_domestic_supplies.ids, 'l10n_cz_supplies_code': '3'},
                {'price_unit': 1000, 'tax_ids': self.l10n_cz_12_domestic_supplies.ids},
            ]],
        }).action_post()
        # Code A4
        self.env['account.move'].create({
            'invoice_date': '2024-01-06',
            'taxable_supply_date': '2024-01-06',
            'move_type': 'out_invoice',
            'partner_id': self.partner_cz_2.id,
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 9500, 'tax_ids': self.l10n_cz_21_domestic_supplies.ids},
                {'price_unit': 900, 'tax_ids': self.l10n_cz_12_domestic_supplies.ids},
            ]],
        }).action_post()
        # Code A3
        self.env['account.move'].create({
            'invoice_date': '2024-01-07',
            'taxable_supply_date': '2024-01-07',
            'move_type': 'out_invoice',
            'partner_id': self.partner_cz_2.id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 1000, 'tax_ids': self.l10n_cz_investment_gold.ids})],
        }).action_post()
        # Code A2
        self.env['account.move'].create({
            'invoice_date': '2024-01-09',
            'taxable_supply_date': '2024-01-09',
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'ref': 'ABC',
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 500, 'tax_ids': self.l10n_cz_21_acquisition_goods_eu.ids},
                {'price_unit': 800, 'tax_ids': self.l10n_cz_12_purchase_goods_eu.ids},
                {'price_unit': 700, 'tax_ids': self.l10n_cz_21_receipt_service_person_eu.ids},
                {'price_unit': 1200, 'tax_ids': self.l10n_cz_12_receipt_service_person_eu.ids},
            ]],
        }).action_post()
        self.env['account.move'].create({
            'invoice_date': '2024-01-10',
            'taxable_supply_date': '2024-01-10',
            'move_type': 'in_invoice',
            'partner_id': self.partner_b.id,
            'ref': 'DEF',
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 20000, 'tax_ids': self.l10n_cz_acquisition_transport.ids})],
        }).action_post()
        self.env['account.move'].create({
            'invoice_date': '2024-01-11',
            'taxable_supply_date': '2024-01-11',
            'move_type': 'in_invoice',
            'ref': 'XYZ',
            'partner_id': self.partner_non_eu.id,
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 500, 'tax_ids': self.l10n_cz_21_receipt_service_person_non_eu.ids},
                {'price_unit': 800, 'tax_ids': self.l10n_cz_12_receipt_service_person_non_eu.ids},
            ]],
        }).action_post()
        # Codes B1 and B3
        self.env['account.move'].create({
            'invoice_date': '2024-01-13',
            'taxable_supply_date': '2024-01-13',
            'move_type': 'in_invoice',
            'partner_id': self.partner_cz_1.id,
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 500, 'tax_ids': self.l10n_cz_21_tax_reverse_charge_scheme.ids, 'l10n_cz_supplies_code': '12'},
                {'price_unit': 900, 'tax_ids': self.l10n_cz_21_tax_reverse_charge_scheme.ids, 'l10n_cz_supplies_code': '13'},
                {'price_unit': 700, 'tax_ids': self.l10n_cz_12_tax_reverse_charge_scheme.ids, 'l10n_cz_supplies_code': '12'},
                {'price_unit': 2000, 'tax_ids': self.l10n_cz_21_receipt_domestic_supplies.ids},
                {'price_unit': 1000, 'tax_ids': self.l10n_cz_12_receipt_domestic_supplies.ids},
            ]],
        }).action_post()
        # Code B2
        self.env['account.move'].create({
            'invoice_date': '2024-01-15',
            'taxable_supply_date': '2024-01-15',
            'move_type': 'in_invoice',
            'partner_id': self.partner_cz_1.id,
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 20459.23, 'tax_ids': self.l10n_cz_21_receipt_domestic_supplies.ids},
                {'price_unit': 500, 'tax_ids': self.l10n_cz_12_receipt_domestic_supplies.ids},
            ]],
        }).action_post()
        self.env['account.move'].create({
            'invoice_date': '2024-01-15',
            'taxable_supply_date': '2024-01-15',
            'move_type': 'in_invoice',
            'partner_id': self.partner_cz_1.id,
            'ref': 'XXX',
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 10000, 'tax_ids': self.l10n_cz_21_receipt_domestic_supplies.ids},
            ]],
        }).action_post()
        # code A5 for l10n_cz_scheme_code != "0 - Standard VAT regime"
        self.env['account.move'].create({
            'invoice_date': '2024-01-04',
            'taxable_supply_date': '2024-01-04',
            'move_type': 'out_invoice',
            'l10n_cz_scheme_code': '1',
            'partner_id': self.partner_cz_1.id,
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 11000, 'tax_ids': self.l10n_cz_21_domestic_supplies.ids},
            ]],
        }).action_post()
        # code A5 for partner without a vat number
        self.partner_eu_1.vat = '/'
        self.env['account.move'].create({
            'invoice_date': '2024-01-04',
            'taxable_supply_date': '2024-01-04',
            'move_type': 'out_invoice',
            'partner_id': self.partner_eu_1.id,
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 11000, 'tax_ids': self.l10n_cz_21_domestic_supplies.ids},
            ]],
        }).action_post()
        # code A4 for invoice in foreign currency with converted amount > 10000 CZK
        foreign_currency = self.setup_other_currency("EUR", rates=[('2024-01-04', 0.01)])
        self.env['account.move'].create({
            'invoice_date': '2024-01-04',
            'taxable_supply_date': '2024-01-04',
            'move_type': 'out_invoice',
            'currency_id': foreign_currency.id,
            'partner_id': self.partner_cz_1.id,
            'invoice_line_ids': [Command.create({'quantity': 1, **line_data}) for line_data in [
                {'price_unit': 1000, 'tax_ids': self.l10n_cz_21_domestic_supplies.ids},
            ]],
        }).action_post()

        report = self.env.ref('l10n_cz_reports_2025.control_statement_report')
        options = report.get_options({})

        self.assertLinesValues(
            report._get_lines(options),
            #    Name                                                                             Country   VAT              Document Number        Date            Tax base 1   Tax amount 1   Tax base 2   Tax amount 2   Supply code
            [0,                                                                               1,        2,               3,                     4,              5,           6,             7,           8,             9],
            [
                ('A. Transactions in the domestic reverse charge regime',                         '',       '',              '',                    '',             '',          '',            '',          '',            ''),
                ('A.1. Realized taxable supplies in the domestic reverse charge regime',          '',       '',              '',                    '',             800,         '',            '',          '',            ''),
                ('INV/2024/00001',                                                                '',       '00000001',      'INV/2024/00001',      '04.01.2024',   800,         '',            '',          '',            ''),
                ('A.2. Received taxable supplies',                                                '',       '',              '',                    '',             21700,       4557,          2800,        336,           ''),
                ('BILL/2024/01/0003 (XYZ)',                                                       '',       '',              'XYZ',                 '11.01.2024',   500,         105,           800,         96,            ''),
                ('BILL/2024/01/0002 (DEF)',                                                       'BE',     '0477472701',    'DEF',                 '10.01.2024',   20000,       4200,          0,           0,             ''),
                ('BILL/2024/01/0001 (ABC)',                                                       'FR',     '23334175221',   'ABC',                 '09.01.2024',   1200,        252,           2000,        240,           ''),
                ('A.3. Realized supplies in the special regime of investment gold',               '',       '',              '',                    '',             1000,        '',            '',          '',            ''),
                ('INV/2024/00003',                                                                'CZ',     '11111119',      'INV/2024/00003',      '07.01.2024',   1000,        '',            '',          '',            ''),
                ('A.4. Realized taxable supplies and received payments above CZK 10,000',         '',       '',              '',                    '',             109500,      22995,         900,         108,           ''),
                ('INV/2024/00002',                                                                '',       '11111119',      'INV/2024/00002',      '06.01.2024',   9500,        1995,          900,         108,           '0'),
                ('INV/2024/00006',                                                                '',       '00000001',      'INV/2024/00006',      '04.01.2024',   100000,      21000,         0,           0,             '0'),
                ('A.5. Other realized taxable supplies and received payments up to CZK 10,000',   '',       '',              '',                    '',             23000,       4830,          1000,        120,           ''),
                ('B. Received taxable supplies with the place of supply in the country',          '',       '',              '',                    '',             '',          '',            '',          '',            ''),
                ('B.1. Received taxable supplies in the domestic reverse charge regime',          '',       '',              '',                    '',             1400,        294,           700,         84,            ''),
                ('BILL/2024/01/0004',                                                             '',       '00000001',      '',                    '13.01.2024',   1400,        294,           700,         84,            ''),
                ('B.2. Received taxable supplies and provided payments above CZK 10,000',         '',       '',              '',                    '',             30459.23,    6396.44,       500,         60,            ''),
                ('BILL/2024/01/0006 (XXX)',                                                       '',       '00000001',      'XXX',                 '15.01.2024',   10000,       2100,          0,           0,             ''),
                ('BILL/2024/01/0005',                                                             '',       '00000001',      'BILL/2024/01/0005',   '15.01.2024',   20459.23,    4296.44,       500,         60,            ''),
                ('B.3. Received taxable supplies and provided payments up to CZK 10,000',         '',       '',              '',                    '',             2000,        420,           1000,        120,           ''),
                ('C. Control lines towards VAT return',                                           '',       '',              '',                    '',             '',          '',            '',          '',            ''),
                ('A.4. + A.5. Total tax bases at the basic VAT rate',                             '',       '',              '',                    '',             132500,      '',            '',          '',            ''),
                ('A.4. + A.5. Total tax bases at the reduced VAT rate',                           '',       '',              '',                    '',             1900,        '',            '',          '',            ''),
                ('B.2. + B.3. Total tax bases at the basic VAT rate',                             '',       '',              '',                    '',             32459.23,    '',            '',          '',            ''),
                ('B.2. + B.3. Total tax bases at the reduced VAT rate',                           '',       '',              '',                    '',             1500,        '',            '',          '',            ''),
                ('A.1 Total tax base',                                                            '',       '',              '',                    '',             800,         '',            '',          '',            ''),
                ('B.1. Total tax bases at the basic VAT rate',                                    '',       '',              '',                    '',             1400,        '',            '',          '',            ''),
                ('B.1. Total tax bases at the reduced VAT rate',                                  '',       '',              '',                    '',             700,         '',            '',          '',            ''),
                ('A.2. Total tax bases',                                                          '',       '',              '',                    '',             24500,       '',            '',          '',            ''),
            ],
            options,
            currency_map={
                5: {'currency': self.env.company.currency_id},
                6: {'currency': self.env.company.currency_id},
                7: {'currency': self.env.company.currency_id},
                8: {'currency': self.env.company.currency_id},
            },
        )

        expected_xml = f"""
            <Pisemnost nazevSW="Odoo SA" verzeSW="{release.version}">
                <DPHKH1 verzePis="03.01.10">
                <VetaD dokument="KH1" k_uladis="DPH" khdph_forma="B" mesic="1" rok="2024"/>
                <VetaP typ_ds="P" zkrobchjm="company_1_data" c_pracufo="2001" c_ufo="451" dic="12345679" email="info@company.czexample.com"/>
                <VetaA1 dic_odb="00000001" c_evid_dd="INV/2024/00001" duzp="04.01.2024" zakl_dane1="500.00" kod_pred_pl="1"/>
                <VetaA1 dic_odb="00000001" c_evid_dd="INV/2024/00001" duzp="04.01.2024" zakl_dane1="300.00" kod_pred_pl="17"/>
                <VetaA2 k_stat="" vatid_dod="" c_evid_dd="XYZ" dppd="11.01.2024" zakl_dane1="500.00" dan1="105.00" zakl_dane2="800.00" dan2="96.00"/>
                <VetaA2 k_stat="BE" vatid_dod="0477472701" c_evid_dd="DEF" dppd="10.01.2024" zakl_dane1="20000.00" dan1="4200.00"/>
                <VetaA2 k_stat="FR" vatid_dod="23334175221" c_evid_dd="ABC" dppd="09.01.2024" zakl_dane1="1200.00" dan1="252.00" zakl_dane2="2000.00" dan2="240.00"/>
                <VetaA3 k_stat="CZ" vatid_odb="11111119" c_evid_dd="INV/2024/00003" dup="07.01.2024" osv_filling="1000.00"/>
                <VetaA4 zdph_44="N" dic_odb="11111119" c_evid_dd="INV/2024/00002" dppd="06.01.2024" zakl_dane1="9500.00" dan1="1995.00" zakl_dane2="900.00" dan2="108.00" kod_rezim_pl="0"/>
                <VetaA4 zakl_dane1= "100000.00" c_evid_dd= "INV/2024/00006" dppd= "04.01.2024" dic_odb= "00000001" dan1= "21000.00" kod_rezim_pl= "0" zdph_44= "N"/>
                <VetaA5 zakl_dane1="23000.00" dan1="4830.00" zakl_dane2="1000.00" dan2="120.00"/>
                <VetaB1 dic_dod="00000001" duzp="13.01.2024" zakl_dane1="500.00" dan1="105.00" zakl_dane2="700.00" dan2="84.00" kod_pred_pl="12"/>
                <VetaB1 dic_dod="00000001" duzp="13.01.2024" zakl_dane1="900.00" dan1="189.00" kod_pred_pl="13"/>
                <VetaB2 pomer="N" zdph_44="N" dic_dod="00000001" c_evid_dd="XXX" dppd="15.01.2024" zakl_dane1="10000.00" dan1="2100.00"/>
                <VetaB2 pomer="N" zdph_44="N" dic_dod="00000001" c_evid_dd="BILL/2024/01/0005" dppd="15.01.2024" zakl_dane1="20459.23" dan1="4296.44" zakl_dane2="500.00" dan2="60.00"/>
                <VetaB3 zakl_dane1="2000.00" dan1="420.00" zakl_dane2="1000.00" dan2="120.00"/>
                <VetaC celk_zd_a2="24500.00" obrat23="132500.00" obrat5="1900.00" pln23="32459.23" pln5="1500.00" pln_rez_pren="800.00" rez_pren23="1400.00" rez_pren5="700.00"/>
            </DPHKH1>
        </Pisemnost>
        """

        actual_xml = self.env[report.custom_handler_model_name].l10n_cz_export_vat_control_report_to_xml(options)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )
