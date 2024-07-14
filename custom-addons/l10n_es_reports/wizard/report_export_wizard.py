# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _

import re

class ReportExportWizard(models.TransientModel):
    _inherit = 'account_reports.export.wizard'

    # id of the related BOE generation wizard when exporting a Spanish report
    l10n_es_reports_boe_wizard_id = fields.Integer()
    # model of the related BOE generation wizard when exporting a Spanish report
    l10n_es_reports_boe_wizard_model = fields.Char()

    def export_report(self):
        self.ensure_one()

        if not self.l10n_es_reports_boe_wizard_model:
            boe_format = self.export_format_ids.filtered(lambda x: x.name == 'BOE')

            if boe_format:
                report = self.report_id
                boe_action = self.env[report.custom_handler_model_name].open_boe_wizard(self.env.context.get('account_report_generation_options'), boe_format.fun_param)

                # BOE generation may require the use of a wizard (hence returning act_window)
                # to prompt for some manual data. If so, we display this wizard, and
                # its validation will then set the l10n_es_reports_boe_wizard_id and l10n_es_reports_boe_wizard_model
                # fields, before recalling export_report, so that the manual values are used in the export.
                if boe_action['type'] == 'ir.actions.act_window':
                    boe_wizard = self.env[boe_action['res_model']].create({'report_id': report.id})
                    boe_wizard.calling_export_wizard_id = self
                    boe_action['res_id'] = boe_wizard.id
                    return boe_action

        return super(ReportExportWizard, self).export_report()


class ReportExportWizardOption(models.TransientModel):
    _inherit = 'account_reports.export.wizard.format'

    def apply_export(self, report_action):
        self.ensure_one()
        if report_action['type'] == 'ir.actions.act_window' and re.match(r'l10n_es_reports\.aeat\.boe\.mod[0-9]{3}\.export\.wizard', report_action['res_model']):
            # If we need to export to BOE and the report has a BOE wizard (for manual value),
            # we call that wizard and return the resulting action.
            # The wizard itself will always have been created if needed before arriving in
            # this function by report export wizard's export_report function.
            if self.export_wizard_id.l10n_es_reports_boe_wizard_id and self.export_wizard_id.l10n_es_reports_boe_wizard_model:
                boe_wizard = self.env[self.export_wizard_id.l10n_es_reports_boe_wizard_model].browse(self.export_wizard_id.l10n_es_reports_boe_wizard_id)
                report_action = boe_wizard.download_boe_action()
            # BOE reports without BOE export wizard behave normally

        return super(ReportExportWizardOption, self).apply_export(report_action)
