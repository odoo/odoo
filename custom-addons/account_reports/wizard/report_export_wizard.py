# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.models import check_method_name

import json
import base64
from urllib.parse import urlparse, parse_qs


class ReportExportWizard(models.TransientModel):
    """ Wizard allowing to export an accounting report in several different formats
    at once, saving them as attachments.
    """
    _name = 'account_reports.export.wizard'
    _description = "Export wizard for accounting's reports"

    export_format_ids = fields.Many2many(string="Export to", comodel_name='account_reports.export.wizard.format', relation="dms_acc_rep_export_wizard_format_rel")
    report_id = fields.Many2one(string="Parent Report Id", comodel_name='account.report', required=True)
    doc_name = fields.Char(string="Documents Name", help="Name to give to the generated documents.")

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard.doc_name = wizard.report_id.name

            # We create one export format object per available export type of the report,
            # with the right generation function associated to it.
            # This is done so to allow selecting them as Many2many tags in the wizard.
            for button_dict in self._context.get('account_report_generation_options', {}).get('buttons', []):
                if button_dict.get('file_export_type'):
                    self.env['account_reports.export.wizard.format'].create({
                        'name': button_dict['file_export_type'],
                        'fun_to_call': button_dict['action'],
                        'fun_param': button_dict.get('action_param'),
                        'export_wizard_id': wizard.id,
                    })
        return wizards

    def export_report(self):
        self.ensure_one()
        created_attachments = self.env['ir.attachment']
        for vals in self._get_attachments_to_save():
            created_attachments |= self.env['ir.attachment'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Documents'),
            'view_mode': 'kanban,form',
            'res_model': 'ir.attachment',
            'domain': [('id', 'in', created_attachments.ids)],
        }

    def _get_attachments_to_save(self):
        self.ensure_one()
        to_create_attachments = []
        report_options = self.env.context['account_report_generation_options']
        for format in self.export_format_ids:
            # format.fun_to_call is a button function, so it has to be public
            fun_name = format.fun_to_call
            check_method_name(fun_name)
            if self.report_id.custom_handler_model_id and hasattr(self.env[self.report_id.custom_handler_model_name], fun_name):
                report_function = getattr(self.env[self.report_id.custom_handler_model_name], fun_name)
            else:
                report_function = getattr(self.report_id, fun_name)
            report_function_params = [format.fun_param] if format.fun_param else []
            report_action = report_function(report_options, *report_function_params)

            to_create_attachments.append(format.apply_export(report_action))

        return to_create_attachments


class ReportExportWizardOption(models.TransientModel):
    _name = 'account_reports.export.wizard.format'
    _description = "Export format for accounting's reports"

    name = fields.Char(string="Name", required=True)
    fun_to_call = fields.Char(string="Function to Call", required=True)
    fun_param = fields.Char(string="Function Parameter")
    export_wizard_id = fields.Many2one(string="Parent Wizard", comodel_name='account_reports.export.wizard', required=True, ondelete='cascade')

    def apply_export(self, report_action):
        self.ensure_one()

        if report_action['type'] == 'ir_actions_account_report_download':
            report_options = json.loads(report_action['data']['options'])

            # file_generator functions are always public for ir_actions_account_report_download
            file_generator = report_action['data']['file_generator']
            check_method_name(file_generator)
            report = self.export_wizard_id.report_id
            if report.custom_handler_model_id and hasattr(self.env[report.custom_handler_model_name], file_generator):
                generation_function = getattr(self.env[report.custom_handler_model_name], file_generator)
            else:
                generation_function = getattr(report, file_generator)
            export_result = generation_function(report_options)

            # We use the options from the action, as the action may have added or modified
            # stuff into them (see l10n_es_reports, with BOE wizard)
            file_content = base64.encodebytes(export_result['file_content']) if isinstance(export_result['file_content'], bytes) else export_result['file_content']
            file_name = f"{self.export_wizard_id.doc_name or self.export_wizard_id.report_id.name}.{export_result['file_type']}"
            mimetype = self.export_wizard_id.report_id.get_export_mime_type(export_result['file_type'])

        elif report_action['type'] == 'ir.actions.act_url':
            query_params = parse_qs(urlparse(report_action['url']).query)
            model = query_params['model'][0]
            model_id = int(query_params['id'][0])
            wizard = self.env[model].browse(model_id)
            file_name = wizard[query_params['filename_field'][0]]
            file_content = wizard[query_params['field'][0]]
            mimetype = self.env['account.report'].get_export_mime_type(file_name.split('.')[-1])

        else:
            raise UserError(_("One of the formats chosen can not be exported in the DMS"))

        return self.get_attachment_vals(file_name, file_content, mimetype, report_options)

    def get_attachment_vals(self, file_name, file_content, mimetype, log_options_dict):
        self.ensure_one()
        return {
            'name': file_name,
            'company_id': self.env.company.id,
            'datas': file_content,
            'mimetype': mimetype,
            'description': json.dumps(log_options_dict)
        }
