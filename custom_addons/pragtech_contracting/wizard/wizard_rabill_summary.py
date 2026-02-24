# -*- coding: utf-8 -*-

from odoo import models, fields, api


class WizardRaBillSummary(models.TransientModel):
    _name = 'wizard.rabill.summary'
    _description = 'Ra Bill Summary'

    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    rabill_id = fields.Many2one('ra.bill', 'RA Bill')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    order_line = fields.One2many('wizard.rabill.summary.lines', 'order_id', string='Order Lines', copy=True, ondelete='cascade')
    state = fields.Selection([('draft', 'Draft'), ('paid', 'Paid')])
    stage_id = fields.Many2one('stage.master', 'Stage')
    partner_id = fields.Many2one('res.partner', string='Contractor')

    @api.onchange('project_id')
    def on_change_project(self):
        if self.project_id:
            return {
                'domain': {
                    'sub_project': [('project_id', '=', self.project_id.id)],
                    'project_wbs': [('project_id', '=', self.project_id.id), ('is_wbs', '=', True), ('is_task', '=', False), ('is_group', '=', False)],
                    'rabill_id': [('project_id', '=', self.project_id.id)],
                }
            }

    @api.onchange('sub_project')
    def on_change_subproject(self):
        if self.sub_project:
            return {
                'domain': {
                    'project_wbs': [('sub_project', '=', self.sub_project.id), ('is_wbs', '=', True), ('is_task', '=', False), ('is_group', '=', False)],
                    'rabill_id': [('sub_project', '=', self.sub_project.id)],
                }
            }

    @api.onchange('project_wbs')
    def on_change_projectwbs(self):
        if self.project_wbs:
            return {
                'domain': {
                    'rabill_id': [('project_wbs', '=', self.project_wbs.id)],
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
        if self.rabill_id:
            domain.append(('id', '=', self.rabill_id.id))
        if self.from_date:
            domain.append(('date_order', '>=', self.from_date))
        if self.to_date:
            domain.append(('date_order', '<=', self.to_date))
        if self.stage_id:
            domain.append(('stage_id', '=', self.stage_id.id))
        if self.partner_id:
            domain.append(('contractor_id', '=', self.partner_id.id))

        ra_obj = self.env['ra.bill'].search(domain)
        vals = {}
        for ra in ra_obj:
            vals = {
                'rabill_ids': ra.id,
                'project_id': ra.project_id.id,
                'sub_project': ra.sub_project.id,
                'project_wbs': ra.project_wbs.id,
                'workorder_id': ra.workorder_id.id,
                'stage_id': ra.stage_id.id,
                'contractor_id': ra.contractor_id.id,
                'final_total_payable': ra.final_total_payable,
                'order_id': self.id,
            }
            value = self.order_line.create(vals)

        view_id = self.env.ref('pragtech_contracting.rabill_summary_wizard_form_view1').id
        return {
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'wizard.rabill.summary',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def check_condition(self, val1, val2):
        return val1 == val2


class WizardRaBillSummaryLines(models.TransientModel):
    _name = 'wizard.rabill.summary.lines'
    _description = 'RaBill Summary Lines'

    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    workorder_id = fields.Many2one('work.order', 'WorkOrder')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    order_id = fields.Many2one('wizard.rabill.summary', string='Order Reference', ondelete='cascade')
    final_total_payable = fields.Float('Final Total Payable')
    stage_id = fields.Many2one('stage.master', 'Stage')
    contractor_id = fields.Many2one('res.partner', 'Contractor')
    rabill_ids = fields.Many2one('ra.bill', 'RA Bill')

