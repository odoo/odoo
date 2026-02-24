# -*- coding: utf-8 -*-

from odoo import models, fields, api


class WizardIncompleteWO(models.TransientModel):
    _name = 'wizard.incomplete.wo'
    _description = 'Incomplete WorkOrder'

    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    workorder_id = fields.Many2one('work.order', 'WorkOrder')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    order_line = fields.One2many('wizard.incomplete.wo.line', 'order_id', string='Order Lines', copy=True, ondelete='cascade')

    partner_id = fields.Many2one('res.partner', string='Contractor')
    labour_id = fields.Many2one('labour.master', string='labour')

    @api.onchange('project_id')
    def on_change_project(self):
        if self.project_id:
            return {
                'domain': {
                    'sub_project': [('project_id', '=', self.project_id.id)],
                    'project_wbs': [('project_id', '=', self.project_id.id), ('is_wbs', '=', True), ('is_task', '=', False), ('is_group', '=', False)],
                    'workorder_id': [('project_id', '=', self.project_id.id), ('state', '=', 'confirm')],
                }
            }

    @api.onchange('sub_project')
    def on_change_subproject(self):
        if self.sub_project:
            return {
                'domain': {
                    'project_wbs': [('sub_project', '=', self.sub_project.id), ('is_wbs', '=', True), ('is_task', '=', False), ('is_group', '=', False)],
                    'workorder_id': [('sub_project', '=', self.sub_project.id), ('state', '=', 'confirm')],
                }
            }

    @api.onchange('project_wbs')
    def on_change_projectwbs(self):
        if self.project_wbs:
            return {
                'domain': {
                    'workorder_id': [('project_wbs', '=', self.project_wbs.id), ('state', '=', 'confirm')],
                }
            }

    def compute_workorders(self):
        self.order_line.unlink()
        domain = []

        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        if self.sub_project:
            domain.append(('sub_project', '=', self.sub_project.id))
        if self.project_wbs:
            domain.append(('project_wbs', '=', self.project_wbs.id))
        if self.workorder_id:
            domain.append(('id', '=', self.workorder_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        domain.append(('state', '=', 'confirm'))
        wo_obj = self.env['work.order'].search(domain)

        vals = {}
        for wo in wo_obj:
            for order in wo.order_line:
                domain_completion = []
                domain_completion.append(('workorder_id', '=', wo.id))
                domain_completion.append(('labour_id', '=', order.labour_id.id))
                recs = self.env['work.completion'].search(domain_completion)
                for rec in recs:
                    value = self.check_completion(wo, rec)
                    if not value:
                        vals = {
                            'name': wo.id,
                            'date_order': wo.date_order,
                            'partner_id': wo.partner_id.id,
                            'project_id': wo.project_id.id,
                            'sub_project': wo.sub_project.id,
                            'project_wbs': wo.project_wbs.id,
                            'completion_id': rec.id,
                            'order_id': self.id,
                        }
                        value = self.order_line.create(vals)

        view_id = self.env.ref('pragtech_contracting.incomplete_workorder_summary_wizard_form_view').id
        return {
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'wizard.incomplete.wo',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def check_condition(self, val1, val2):
        return val1 == val2

    def check_completion(self, wo, rec):
        if not rec:
            return False
        if rec.total_percent != 100:
            return False
        return True


class WizardIncompleteWOLine(models.TransientModel):
    _name = 'wizard.incomplete.wo.line'
    _description = 'Incomplete WorkOrder line'

    name = fields.Many2one('work.order', 'WorkOrder')
    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    order_id = fields.Many2one('wizard.incomplete.wo', string='Order Reference', ondelete='cascade')
    date_order = fields.Datetime('Order Date')
    partner_id = fields.Many2one('res.partner', string='Contractor')
    completion_id = fields.Many2one('work.completion', 'Completion Reference')

