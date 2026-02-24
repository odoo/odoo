# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api


class SubProject(models.Model):
    _name = 'sub.project'
    _description = 'Sub Project'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    name = fields.Char('Name', required=True)
    project_id = fields.Many2one('project.project', 'Project', required=True)
    budget_applicable = fields.Boolean('Budget Applicable')
    wbs_id = fields.One2many('project.task', 'sub_project')

    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    flag = fields.Boolean('Flag', default=False)  # For Change state button
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], string='Status', readonly=True, copy=False, default='draft')
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)], auto_join=True, readonly=True)
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')

    @api.model_create_multi
    def create(self, vals_list):
        """" Creating Audit Trail """
        for vals in vals_list:
            existing_stage = []
            st_id = self.env['stage.master'].search([('draft', '=', True)])
            msg_ids = {
                'date': datetime.now(),
                'from_stage': None,
                'to_stage': st_id.id,
                'model': 'sub.project'
            }

            if self._context.get('uid'):
                msg_ids.update({'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name, })

            existing_stage.append((0, 0, msg_ids))
            vals.update({'mesge_ids': existing_stage})

        return super(SubProject, self).create(vals_list)

    def change_state(self, context={}):
        if context.get('copy') == True:
            self.flag = True
        else:
            self.flag = False
            view_id = self.env.ref('pragtech_ppc.approval_wizard_form_view').id
            return {
                'type': 'ir.actions.act_window',
                'key2': 'client_action_multi',
                'res_model': 'approval.wizard',
                'multi': 'True',
                'target': 'new',
                'views': [[view_id, 'form']],
            }

