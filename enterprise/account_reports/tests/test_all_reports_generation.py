# -*- coding: utf-8 -*-

import json

from collections import defaultdict
from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAllReportsGeneration(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # do not disable buttons because of multiple companies selected
        cls.env = cls.env(context={'allowed_company_ids': cls.env.company.ids})
        cls.setup_other_currency('EUR')

        cls.reports = cls.env['account.report'].with_context(active_test=False).search([])

        # Make the reports always available, so that they don't clash with the comany's country
        cls.reports.availability_condition = 'always'
        # We keep the country set on each of these reports, so that we can load the proper test data when testing exports

    def test_open_all_reports(self):
        # 'unfold_all' is forced on all reports (even if they don't support it), so that we really open it entirely
        self.reports.filter_unfold_all = True

        for report in self.reports:
            with self.subTest(report=report.name, country=report.country_id.name):
                # 'report_id' key is forced so that we don't open a variant when calling a root report
                options = report.get_options({'selected_variant_id': report.id, 'unfold_all': True})

                if report.use_sections:
                    self.assertNotEqual(options['report_id'], report.id, "Composite reports should always reroute.")
                    self.env['account.report'].browse(options['report_id']).get_report_information(options)
                else:
                    report.get_report_information(options)

    def test_generate_all_export_files(self):
        # Test values for the fields that become mandatory when doing exports on the reports, depending on the country
        l10n_pl_reports_tax_office = self.env.ref('l10n_pl.pl_tax_office_0215', raise_if_not_found=False)
        l10n_bd_corporate_tax_liability = self.env['account.account'].search([('account_type', '=', 'liability_current')], limit=1)
        l10n_ae_liability_account = self.env['account.account'].search([('account_type', '=', 'liability_current')], limit=1)
        l10n_cz_reports_tax_office = self.env.ref('l10n_cz_reports_2025.tax_office_1', raise_if_not_found=False)
        company_test_values = {
            'LU': {'vat': 'LU12345613'},
            'BR': {'vat': '01234567891251'},
            'AR': {'vat': '30714295698'},
            'AU': {'vat': '11225459588', 'street': 'Arrow Street', 'zip': '1348', 'city': 'Starling City', 'state_id': self.env.ref('base.state_au_1').id},
            'DE': {'vat': 'DE123456788', 'l10n_de_stnr': '151/815/08156', 'state_id': self.env.ref('base.state_de_th').id},
            'NO': {'vat': 'NO123456785', 'l10n_no_bronnoysund_number': '987654325'},
            'PL': {'l10n_pl_reports_tax_office_id': l10n_pl_reports_tax_office and l10n_pl_reports_tax_office.id},
            'BD': {'l10n_bd_corporate_tax_liability': l10n_bd_corporate_tax_liability, 'l10n_bd_corporate_tax_expense': l10n_bd_corporate_tax_liability},
            'AE': {'l10n_ae_tax_report_liabilities_account': l10n_ae_liability_account, 'l10n_ae_tax_report_counterpart_account': l10n_ae_liability_account},
            'CZ': {'l10n_cz_tax_office_id': l10n_cz_reports_tax_office and l10n_cz_reports_tax_office.id}
        }

        # ecdf_prefix and matr_number only exist in enterprise
        if self.env['ir.module.module']._get('l10n_lu_reports').state == 'installed':
            company_test_values['LU'].update({
                'ecdf_prefix': '1234AB',
                'matr_number': '1111111111111',
            })

        partner_test_values = {
            'AR': {'l10n_latam_identification_type_id': (self.env.ref('l10n_ar.it_cuit', raise_if_not_found=False) or {'id': None})['id']},
        }

        # Some root reports are made for just one country and require test fields to be set the right way to generate their exports properly.
        # Since they are root reports and are always available, they normally have no country set; we assign one here (only for the ones requiring it)
        reports_forced_countries = [
            ('AU', 'l10n_au_reports.tpar_report'),
        ]
        for country_code, report_ref in reports_forced_countries:
            country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
            report = self.env.ref(report_ref, raise_if_not_found=False)
            if report:
                report.country_id = country

        # Check buttons of every report
        for report in self.reports:
            with self.subTest(report=report.name, country=report.country_id.name):
                # Setup some generic data on the company that could be needed for some file export
                self.env.company.write({
                    'vat': "VAT123456789",
                    'email': "dummy@email.com",
                    'phone': "01234567890",
                    'company_registry': '42',
                    **company_test_values.get(report.country_id.code, {}),
                })

                self.env.company.partner_id.write(partner_test_values.get(report.country_id.code, {}))

                options = report.get_options({'selected_variant_id': report.id, '_running_export_test': True})

                if report.use_sections:
                    self.assertNotEqual(options['report_id'], report.id, "Composite reports should always reroute.")

                for option_button in options['buttons']:
                    if option_button['name'] in ('PDF', 'Download Excel'):  # keep "Copy to Documents" and other actions
                        # TODO remove me
                        # This test seems to have some trouble on runbot. It is running for way longer than
                        # locally. Freeze is coming, explanation are missing... Sorry 😟
                        continue
                    if report.custom_handler_model_name == 'l10n_fr.report.handler' and option_button['name'] == 'EDI VAT':
                        # This button requires a tax closing entry to be called. It doesn't make sense to test this button
                        # without a tax closing entry, so we will exclude it from testing here.
                        continue
                    with self.subTest(button=option_button['name']):
                        with patch.object(type(self.env['ir.actions.report']), '_run_wkhtmltopdf', lambda *args, **kwargs: b"This is a pdf"):
                            if not option_button.get('client_tag'):
                                action_dict = report.dispatch_report_action(
                                    options,
                                    option_button['action'],
                                    action_param=option_button.get('action_param'),
                                    on_sections_source=True,
                                )

                                if action_dict['type'] == 'ir_actions_account_report_download':
                                    file_gen_res = report.dispatch_report_action(
                                        json.loads(action_dict['data']['options']),
                                        action_dict['data']['file_generator'],
                                        on_sections_source=True,
                                    )
                                    self.assertEqual(
                                        set(file_gen_res.keys()), {'file_name', 'file_content', 'file_type'},
                                        "File generator's result should always contain the same 3 keys."
                                    )

            # Unset the test values, in case they are used in conditions to define custom behaviors
            self.env.company.write({
                field_name: None
                for field_name in company_test_values.get(report.country_id.code, {}).keys()
            })

            self.env.company.partner_id.write({
                field_name: None
                for field_name in partner_test_values.get(report.country_id.code, {}).keys()
            })

    def test_custom_engines_related_groupby(self):
        blacklist_xmlids = [
            'account_reports.account_financial_report_executivesummary_avdebt0_ndays',
            'account_reports.account_financial_report_executivesummary_avgcre0_ndays',
            'account_reports.last_statement_balance_amount',
            'account_reports.last_statement_balance_forced_currency_amount',
        ]

        custom_engine_expressions = self.env['account.report.expression'].search([
            ('engine', '=', 'custom'),
            ('id', 'not in', tuple(self.env['ir.model.data']._xmlid_to_res_id(xmlid) for xmlid in blacklist_xmlids)),
        ])

        expressions_per_engine = defaultdict(lambda: self.env['account.report.expression'])
        for expression in custom_engine_expressions:
            expressions_per_engine[(expression.report_line_id.report_id, expression.formula)] += expression

        for (report, _formula), expressions in expressions_per_engine.items():
            with self.subTest(report=report.name):
                options = report.get_options({})

                # Remove aggregations and external value expressions from those report lines, so that we always can set a groupby on the line
                (expressions.report_line_id.expression_ids.filtered(lambda x: x.engine in ('aggregation', 'external'))).unlink()

                expressions.report_line_id.user_groupby = 'account_code' # account_code is a  non-stored related field on aml
                self.env.flush_all()
                report._compute_expression_totals_for_each_column_group(expressions, options, groupby_to_expand='account_code')
                # This computation fill fail if the custom engine forgot to handle such groupby, typically via a call to _field_to_sql
