# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo import Command, fields


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEvatXmlReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='no'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        (cls.partner_a + cls.partner_b).write({
            'city': 'Garnich',
            'zip': 'L-8353',
            'country_id': cls.env.ref('base.lu').id,
            'phone': '+352 24 11 11 11',
        })

        cls.company_data['company'].write({
            'city': 'OSLO',
            'zip': 'N-0104',
            'country_id': cls.env.ref('base.no').id,
            'l10n_no_bronnoysund_number': '987654325',
            'vat': 'NO072274687MVA',
        })

        # Create invoices

        invoices = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2020-01-01',
                'date': '2020-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 4.0,
                        'price_unit': 750.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
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
                'invoice_date': '2021-12-01',
                'date': '2021-12-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 6.0,
                        'price_unit': 100.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2021-12-31',
                'date': '2021-12-31',
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
            {
                'move_type': 'in_invoice',
                'invoice_date': '2020-12-31',
                'date': '2020-12-31',
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

    def test_evat_xml_report_dates_year(self):
        report = self.env.ref('l10n_no.tax_report')
        options = self._generate_options(report, fields.Date.to_date('2020-01-01'), fields.Date.to_date('2021-12-31'))

        set_time_interval_function = self.env[report.custom_handler_model_name]._l10n_no_set_time_interval

        # Different years, invalid (error raised)
        with self.assertRaises(UserError):
            set_time_interval_function(options)

        # Correct year, valid (no error raised)
        options['date']['date_from'] = '2021-01-01'
        set_time_interval_function(options)

    def test_evat_xml_report_dates_months(self):
        report = self.env.ref('l10n_no.tax_report')
        options = self._generate_options(report, fields.Date.to_date('2021-01-01'), fields.Date.to_date('2021-11-01'))

        set_time_interval_function = self.env[report.custom_handler_model_name]._l10n_no_set_time_interval

        # 11 months is invalid
        with self.assertRaises(UserError):
            set_time_interval_function(options)

        options['date']['date_from'] = '2021-04-01'
        options['date']['date_to'] = '2021-10-31'

        # 6 months and 30 days (~7 months) is invalid
        with self.assertRaises(UserError):
            set_time_interval_function(options)

        options['date']['date_from'] = '2021-03-01'
        options['date']['date_to'] = '2021-05-31'

        # 2 months is valid, but 5 % 2 != 0 so invalid
        with self.assertRaises(UserError):
            set_time_interval_function(options)

        # Test if a valid interval doesn't raise any Error

        options['date']['date_from'] = '2021-01-01'
        options['date']['date_to'] = '2021-02-28'

        set_time_interval_function(options)

        options['date']['date_to'] = '2021-06-30'

        set_time_interval_function(options)

    def test_evat_xml_report_tax_values(self):
        report = self.env.ref('l10n_no.tax_report')
        options = self._generate_options(report, fields.Date.to_date('2021-01-01'), fields.Date.to_date('2021-01-31'))

        # Single month
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].print_norwegian_report_xml(options)['file_content']),
            self.get_xml_tree_from_string('''
                <mvaMeldingDto xmlns="no:skatteetaten:fastsetting:avgift:mva:skattemeldingformerverdiavgift:v1.0">
                    <innsending>
                        <regnskapssystemsreferanse>1</regnskapssystemsreferanse>
                        <regnskapssystem>
                            <systemnavn>Odoo SA</systemnavn>
                            <systemversjon>___ignore___</systemversjon>
                        </regnskapssystem>
                    </innsending>
                    <skattegrunnlagOgBeregnetSkatt>
                        <skattleggingsperiode>
                            <periode>
                                <skattleggingsperiodeMaaned>januar</skattleggingsperiodeMaaned>
                            </periode>
                            <aar>2021</aar>
                        </skattleggingsperiode>
                        <fastsattMerverdiavgift>1250.0</fastsattMerverdiavgift>
                        <mvaSpesifikasjonslinje>
                            <mvaKode>3</mvaKode>
                            <mvaKodeRegnskapsystem>25%</mvaKodeRegnskapsystem>
                            <grunnlag>5000.0</grunnlag>
                            <sats>25.0</sats>
                            <merverdiavgift>1250.0</merverdiavgift>
                        </mvaSpesifikasjonslinje>
                    </skattegrunnlagOgBeregnetSkatt>
                    <betalingsinformasjon>
                        <kundeIdentifikasjonsnummer>NO072274687MVA</kundeIdentifikasjonsnummer>
                    </betalingsinformasjon>
                    <skattepliktig>
                        <organisasjonsnummer>987654325</organisasjonsnummer>
                    </skattepliktig>
                    <meldingskategori>alminnelig</meldingskategori>
                    <merknad>
                        <beskrivelse>___ignore___</beskrivelse>
                    </merknad>
                </mvaMeldingDto>

            '''),
        )

        # Whole year
        options['date']['date_to'] = '2021-12-31'

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].print_norwegian_report_xml(options)['file_content']),
            self.get_xml_tree_from_string('''
                <mvaMeldingDto xmlns="no:skatteetaten:fastsetting:avgift:mva:skattemeldingformerverdiavgift:v1.0">
                    <innsending>
                        <regnskapssystemsreferanse>1</regnskapssystemsreferanse>
                        <regnskapssystem>
                            <systemnavn>Odoo SA</systemnavn>
                            <systemversjon>___ignore___</systemversjon>
                        </regnskapssystem>
                    </innsending>
                    <skattegrunnlagOgBeregnetSkatt>
                        <skattleggingsperiode>
                            <periode>
                                <skattleggingsperiodeAar>aarlig</skattleggingsperiodeAar>
                            </periode>
                            <aar>2021</aar>
                        </skattleggingsperiode>
                        <fastsattMerverdiavgift>-600.0</fastsattMerverdiavgift>
                        <mvaSpesifikasjonslinje>
                            <mvaKode>1</mvaKode>
                            <mvaKodeRegnskapsystem>25%</mvaKodeRegnskapsystem>
                            <merverdiavgift>-2000.0</merverdiavgift>
                        </mvaSpesifikasjonslinje>
                        <mvaSpesifikasjonslinje>
                            <mvaKode>3</mvaKode>
                            <mvaKodeRegnskapsystem>25%</mvaKodeRegnskapsystem>
                            <grunnlag>5600.0</grunnlag>
                            <sats>25.0</sats>
                            <merverdiavgift>1400.0</merverdiavgift>
                        </mvaSpesifikasjonslinje>
                    </skattegrunnlagOgBeregnetSkatt>
                    <betalingsinformasjon>
                        <kundeIdentifikasjonsnummer>NO072274687MVA</kundeIdentifikasjonsnummer>
                    </betalingsinformasjon>
                    <skattepliktig>
                        <organisasjonsnummer>987654325</organisasjonsnummer>
                    </skattepliktig>
                    <meldingskategori>alminnelig</meldingskategori>
                    <merknad>
                        <beskrivelse>___ignore___</beskrivelse>
                    </merknad>
                </mvaMeldingDto>

            '''),
        )
