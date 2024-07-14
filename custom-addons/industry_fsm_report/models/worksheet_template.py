# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, models, _
from odoo.exceptions import UserError


class WorksheetTemplate(models.Model):
    _inherit = 'worksheet.template'

    def action_analysis_report(self):
        res = super().action_analysis_report()
        res['context'] = dict(literal_eval(res.get('context', '{}')), fsm_mode=True)
        return res

    @api.model
    def _get_models_to_check_dict(self):
        res = super()._get_models_to_check_dict()
        res['project.task'] = [('project.task', 'Task'), ('project.project', 'Project')]
        return res

    @api.model
    def _get_project_task_user_group(self):
        return self.env.ref('project.group_project_user')

    @api.model
    def _get_project_task_manager_group(self):
        return self.env.ref('project.group_project_manager')

    @api.model
    def _get_project_task_access_all_groups(self):
        return self.env.ref('project.group_project_manager') | self.env.ref('industry_fsm.group_fsm_user')

    @api.model
    def _get_project_task_module_name(self):
        return 'industry_fsm_report'

    @api.model
    def _create_demo_data_fsm(self):
        # create demo data in batch for performance reasons (avoid multiple calls to setup_models)
        model_id = self.env.ref('industry_fsm_report.fsm_worksheet_template2').model_id.id
        self.env['ir.model.fields'].create([{
            'name': 'x_intervention_type',
            'ttype': 'selection',
            'field_description': 'Intervention Type',
            'selection': "[('first_installation','First installation'),('technical_maintenance','Technical maintenance')]",
            'model_id': model_id,
        }, {
            'name': 'x_description',
            'ttype': 'text',
            'field_description': 'Description of the Intervention',
            'model_id': model_id,
        }, {
            'name': 'x_manufacturer',
            'ttype': 'many2one',
            'relation': 'res.partner',
            'field_description': 'Manufacturer',
            'model_id': model_id,
        }, {
            'name': 'x_checkbox',
            'ttype': 'boolean',
            'field_description': 'I hereby certify that this device meets the requirements of an acceptable device at the time of testing.',
            'model_id': model_id,
        }, {
            'name': 'x_serial_number',
            'ttype': 'char',
            'field_description': 'Serial Number',
            'model_id': model_id,
        }, {
            'name': 'x_date',
            'ttype': 'date',
            'field_description': 'Date',
            'model_id': model_id,
        }, {
            'name': 'x_worker_signature',
            'ttype': 'binary',
            'field_description': 'Worker Signature',
            'model_id': model_id,
        }])
