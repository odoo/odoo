# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import api, models, fields

class L10nLuGenerateAccountsReport(models.TransientModel):
    """
    This wizard is used to generate an xml yearly accounts report for Luxembourg
    according to the xml 2.0 standard.
    """
    _inherit = 'l10n_lu.generate.xml'
    _name = 'l10n_lu.generate.accounts.report'
    _description = 'Generate Accounts Report'

    avg_nb_employees = fields.Float(string="Average number of employees for the fiscal year", required=True, default=1)
    size = fields.Selection([('large', "Large-Sized Undertaking"),
                             ('medium', "Medium-Sized Undertaking"),
                             ('small', "Small-Sized Undertaking")], required=True, default='large')
    pl = fields.Selection([('abr', 'Abridged'), ('full', 'Full')], required=True, default='full')
    bs = fields.Selection([('abr', 'Abridged'), ('full', 'Full')], required=True, default='full')
    coa_only = fields.Boolean(default=False)
    optional_remarks = fields.Char(default='')
    import_notes_as_references = fields.Boolean(default=False)

    @api.onchange("size")
    def _onchange_size(self):
        if self.size == 'large' or self.size == 'medium':
            self.bs = 'full'
            if self.size == 'large':
                self.pl = 'full'

    def _get_report_options(self, report):
        return report.get_options({})

    def _lu_get_declarations(self, declaration_template_values):
        # Basic (required) declaration group
        declaration = {'declaration_groups': [], 'declaration_singles': {'forms': []}}
        declaration.update(declaration_template_values)
        report_options = self.env.context['report_generation_options']

        # Balance Sheet Report
        if not self.coa_only:
            if self.bs == 'abr':
                bs_report = self.env.ref('l10n_lu_reports.account_financial_report_l10n_lu_bs_abr')
            else:
                bs_report = self.env.ref('l10n_lu_reports.account_financial_report_l10n_lu_bs')
            bs_report_options = self._get_report_options(bs_report)
            bs_report_options['date'].update(report_options.get('date', {}))
            bs_model = self.env[bs_report.custom_handler_model_name].with_context(skip_options_recompute=True)
            bs_declaration = bs_model.get_xml_2_0_report_values(bs_report_options, self.import_notes_as_references)[0]

        # Profit&Loss Report
        if not self.coa_only:
            if self.pl == 'abr':
                pl_report = self.env.ref('l10n_lu_reports.account_financial_report_l10n_lu_pl_abr')
            else:
                pl_report = self.env.ref('l10n_lu_reports.account_financial_report_l10n_lu_pl')
            pl_report_options = self._get_report_options(pl_report)
            pl_report_options['date'].update(report_options.get('date', {}))
            pl_model = self.env[pl_report.custom_handler_model_name].with_context(skip_options_recompute=True)
            pl_declaration = pl_model.get_xml_2_0_report_values(pl_report_options, self.import_notes_as_references)[0]

        # Chart of Accounts Report
        options = {
            'journals': report_options['journals'],
            'all_entries': report_options['all_entries'],
            'date': report_options['date'],
        }
        coa_report = self.env.ref('account_reports.trial_balance_report')
        options = coa_report.get_options(options)
        options['date'].update(report_options.get('date', {}))
        coa_declaration = coa_report.l10n_lu_get_xml_2_0_report_coa_values(
            options, self.avg_nb_employees, self.size, self.pl, self.bs, self.coa_only, self.optional_remarks)

        forms = [pl_declaration, bs_declaration] if not self.coa_only else []
        forms.append(coa_declaration)
        if datetime.strptime(report_options['date']['date_from'], '%Y-%m-%d').year != 2019 and not self.coa_only:
            declaration['declaration_groups'].append({'forms': forms})
        else:
            declaration['declaration_singles']['forms'].extend(forms)

        return {
            'declarations': [declaration],
            'year': fields.Datetime.from_string(report_options['date']['date_from']).year,
            'period': '1',
        }
