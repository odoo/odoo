# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ReportExportWizard(models.TransientModel):
    _inherit = 'account_reports.export.wizard'

    l10n_be_reports_periodic_vat_wizard_id = fields.Many2one(string="Periodic VAT Export Wizard", comodel_name="l10n_be_reports.periodic.vat.xml.export")

    def export_report(self):
        self.ensure_one()
        report = self.report_id
        if report == self.env.ref('l10n_be.tax_report_vat') and any(format.name == 'XML' for format in self.export_format_ids) and not self.l10n_be_reports_periodic_vat_wizard_id:
            manual_action = self.env[report.custom_handler_model_name].print_tax_report_to_xml(self.env.context.get('account_report_generation_options'))
            manual_wizard = self.env[manual_action['res_model']].browse(manual_action['res_id'])
            manual_wizard.calling_export_wizard_id = self
            return manual_action

        return super(ReportExportWizard, self).export_report()


class ReportExportWizardOption(models.TransientModel):
    _inherit = 'account_reports.export.wizard.format'

    def apply_export(self, report_action):
        self.ensure_one()

        if report_action['type'] == 'ir.actions.act_window' and report_action['res_model'] == 'l10n_be_reports.periodic.vat.xml.export':
            report_action = self.export_wizard_id.l10n_be_reports_periodic_vat_wizard_id.print_xml()

        return super(ReportExportWizardOption, self).apply_export(report_action)
