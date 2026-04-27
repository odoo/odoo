# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class FrenchIntrastatExportWizard(models.TransientModel):
    _name = "l10n_fr_intrastat.export.wizard"
    _description = "Options for the export of Intrastat in France"

    export_type = fields.Selection(
        string='Export type',
        selection=[
            ('statistical_survey', 'Statistical survey (EMEBI)'),
            ('vat_summary_statement', 'VAT summary statement'),
            ('statistical_survey_and_vat_summary_statement', 'Statistical survey (EMEBI) and VAT summary statement'),
        ],
        default='vat_summary_statement',
        required=True,
    )

    emebi_flow = fields.Selection(
        string='Flow Direction',
        selection=[
            ('arrivals', 'Arrivals'),
            ('dispatches', 'Dispatches'),
            ('arrivals_and_dispatches', 'Arrivals and dispatches'),
        ],
        default='arrivals_and_dispatches',
    )

    emebi_flow_visible = fields.Boolean(compute='_compute_export_type')
    warning_incompatible_options = fields.Boolean(compute='_compute_warning_incompatible_options')

    def export_xml_file(self):
        options = self.env.context['l10n_fr_intrastat_export_options']
        options['l10n_fr_intrastat_wizard_id'] = self.id
        report = self.env['account.report'].browse(options['report_id'])
        return report.export_file(options, 'l10n_fr_intrastat_export_to_xml')

    @api.depends('export_type')
    def _compute_export_type(self):
        for wizard in self:
            wizard.emebi_flow_visible = wizard.export_type in ('statistical_survey', 'statistical_survey_and_vat_summary_statement')

    @api.depends('export_type', 'emebi_flow')
    def _compute_warning_incompatible_options(self):
        for wizard in self:
            is_arrival_selected = wizard.export_type in ('statistical_survey', 'statistical_survey_and_vat_summary_statement') \
                              and wizard.emebi_flow in ('arrivals', 'arrivals_and_dispatches')
            is_dispatch_selected = wizard.emebi_flow in ('dispatches', 'arrivals_and_dispatches')

            options = self.env.context['l10n_fr_intrastat_export_options']
            options_include_arrivals = options['intrastat_type'][0]['selected']
            options_include_dispatches = options['intrastat_type'][1]['selected']
            if not options_include_arrivals and not options_include_dispatches:
                options_include_arrivals = options_include_dispatches = True

            wizard.warning_incompatible_options = (not options_include_arrivals and is_arrival_selected) \
                                               or (not options_include_dispatches and is_dispatch_selected)
