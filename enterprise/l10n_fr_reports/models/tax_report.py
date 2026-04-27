# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class FrenchReportCustomHandler(models.AbstractModel):
    _name = 'l10n_fr.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'French Report Custom Handler'

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # OVERRIDE
        """ Apply the rounding from the French tax report by adding a line to the end of the query results
            representing the sum of the roundings on each line of the tax report.
        """
        rounding_accounts = {
            'profit': company.l10n_fr_rounding_difference_profit_account_id,
            'loss': company.l10n_fr_rounding_difference_loss_account_id,
        }

        vat_results_summary = [
            ('due', self.env.ref('l10n_fr_account.tax_report_32').id, 'balance'),
            ('due', self.env.ref('l10n_fr_account.tax_report_22').id, 'balance'),
            ('deductible', self.env.ref('l10n_fr_account.tax_report_27').id, 'balance'),
        ]
        return self._vat_closing_entry_results_rounding(company, options, results, rounding_accounts, vat_results_summary)

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options['buttons'].append({
            'name': _('EDI VAT'),
            'sequence': 30,
            'action': 'send_vat_report',
        })

    def send_vat_report(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        view_id = self.env.ref('l10n_fr_reports.view_l10n_fr_reports_report_form').id
        date_from, date_to = self.env.company._get_tax_closing_period_boundaries(fields.Date.to_date(options['date']['date_from']), report)

        closing_moves = self._get_tax_closing_entries_for_closed_period(report, options, self.env.company)
        if not closing_moves:
            raise UserError(_("You need to complete the tax closing process for this period before submitting the report to the French administration."))

        l10n_fr_vat_report = self.env['l10n_fr_reports.send.vat.report'].create({
            'report_id': report.id,
            'date_from': date_from,
            'date_to': date_to,
        })
        return {
            'name': _('EDI VAT'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_fr_reports.send.vat.report',
            'res_id': l10n_fr_vat_report.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_audit_cell(self, options, params):
        # OVERRIDES 'account_reports'

        # Each line of the French VAT report is rounded to the unit.
        # In addition, the tax amounts are computed using the rounded base amounts.
        # The computation of the tax lines is done using the 'aggregation' engine,
        # so the tax tags are no longer used in the report.

        # That means the 'expression_label' needs to be adjusted when auditing tax lines,
        # in order to target the expression that uses the 'tax_tags' engine,
        # if we want to display the expected journal items.

        report_line = self.env['account.report.line'].browse(params['report_line_id'])

        if set(report_line.expression_ids.mapped('label')) == {'balance', 'balance_from_tags'}:
            params['expression_label'] = 'balance_from_tags'

        return report_line.report_id.action_audit_cell(options, params)

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        def _evaluate_check(check_func):
            return all(
                check_func(expression_totals)
                for expression_totals in all_column_groups_expression_totals.values()
            )

        def _compare_expression_totals(expression_totals):
            return float_compare(sum(
                expression_totals[balance_line_expression_per_line_code[code]]['value']
                for code in ['box_A1', 'box_A2', 'box_A3', 'box_B2', 'box_B3', 'box_B4']
            ), sum(
                expression_totals[balance_line_expression_per_line_code[code]]['value']
                for code in [
                    'box_08_base', 'box_09_base', 'box_9B_base', 'box_10_base',
                    'box_11_base', 'box_T1_base', 'box_T2_base', 'box_T3_base',
                    'box_T4_base', 'box_T5_base', 'box_T6_base', 'box_T7_base',
                ]
            ), 2) == 0

        super()._customize_warnings(report, options, all_column_groups_expression_totals, warnings)
        balance_line_expression_per_line_code = {
            line.code: line.expression_ids.filtered(lambda x: x.label == 'balance')
            for line in report.line_ids
            if line.code
        }

        checks = [
            (
                _('Sum of field 08+09+9B+10+11+T1->T7 is not equal to sum of field A1+A2+A3+B2+B3+B4'),
                _compare_expression_totals,
            )
        ]

        failed_controls = [
            check_name
            for check_name, check_func in checks
            if not _evaluate_check(check_func)
        ]

        if failed_controls:
            warnings['l10n_fr_reports.tax_report_warning_checks'] = {'failed_controls': failed_controls, 'alert_type': 'danger'}
