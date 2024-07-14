# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

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
            ('due', self.env.ref('l10n_fr.tax_report_32').id, 'balance'),
            ('due', self.env.ref('l10n_fr.tax_report_22').id, 'balance'),
            ('deductible', self.env.ref('l10n_fr.tax_report_27').id, 'balance'),
        ]

        return self._vat_closing_entry_results_rounding(company, options, results, rounding_accounts, vat_results_summary)

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        report._custom_options_add_integer_rounding(options, 'HALF-UP', previous_options=previous_options)

        options['buttons'].append({
            'name': _('EDI VAT'),
            'sequence': 30,
            'action': 'send_vat_report',
        })

    def send_vat_report(self, options):
        view_id = self.env.ref('l10n_fr_reports.view_l10n_fr_reports_report_form').id
        return {
            'name': _('EDI VAT'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_fr_reports.send.vat.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {**self.env.context, 'l10n_fr_generation_options': options},
        }
