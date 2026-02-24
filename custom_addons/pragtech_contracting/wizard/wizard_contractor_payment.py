# -*- coding: utf-8 -*-

from odoo import models, fields, api


class WizardContractorPayment(models.TransientModel):
    _name = 'wizard.contractor.payment'
    _description = 'Contractor Payment'

    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    workorder_id = fields.Many2one('work.order', 'WorkOrder')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    order_line = fields.One2many('wizard.contractor.payment.line', 'order_id', string='Order Lines', copy=True, ondelete='cascade')

    partner_id = fields.Many2one('res.partner', string='Contractor')

    @api.onchange('project_id')
    def on_change_project(self):
        if self.project_id:
            return {
                'domain': {
                    'sub_project': [('project_id', '=', self.project_id.id)],
                    'project_wbs': [('project_id', '=', self.project_id.id), ('is_wbs', '=', True), ('is_task', '=', False), ('is_group', '=', False)],
                    'workorder_id': [('project_id', '=', self.project_id.id)],
                }
            }

    @api.onchange('sub_project')
    def on_change_subproject(self):
        if self.sub_project:
            return {
                'domain': {
                    'project_wbs': [('sub_project', '=', self.sub_project.id), ('is_wbs', '=', True), ('is_task', '=', False), ('is_group', '=', False)],
                    'workorder_id': [('sub_project', '=', self.sub_project.id)],
                }
            }

    @api.onchange('project_wbs')
    def on_change_projectwbs(self):
        if self.project_wbs:
            return {
                'domain': {
                    'workorder_id': [('project_wbs', '=', self.project_wbs.id)],
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
        if self.from_date:
            domain.append(('date_order', '>=', self.from_date))
        if self.to_date:
            domain.append(('date_order', '<=', self.to_date))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        domain.append(('state', '=', 'confirm'))
        vals = {}
        wo_obj = self.env['work.order'].search(domain)
        for wo in wo_obj:
            ra_obj = self.env['ra.bill'].search([('workorder_id', '=', wo.id)])
            if ra_obj:
                total = 0.0
                paid = 0.0
                for ra in ra_obj:
                    total = total + ra.final_total_payable
                    if ra.state == 'paid':
                        paid = paid + ra.final_total_payable

                vals = {
                    'workorder_id': wo.id,
                    'bill_created': total,
                    'bill_paid': paid,
                    'bill_balance': total - paid,
                    'order_id': self.id,
                    'partner_id': wo.partner_id.id,
                    'project_id': wo.project_id.id,
                    'sub_project': wo.sub_project.id,
                    'project_wbs': wo.project_wbs.id,
                }
                value = self.order_line.create(vals)

        view_id = self.env.ref('pragtech_contracting.contractor_payment_form_view').id
        return {
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'wizard.contractor.payment',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def check_condition(self, val1, val2):
        return val1 == val2


class WizardContractorPaymentLine(models.TransientModel):
    _name = 'wizard.contractor.payment.line'
    _description = 'Contractor Payment line'

    workorder_id = fields.Many2one('work.order', 'WorkOrder')
    order_id = fields.Many2one('wizard.contractor.payment', string='Order Reference', ondelete='cascade')
    bill_created = fields.Float('Bill Created')
    bill_paid = fields.Float('Bill Paid')
    bill_balance = fields.Float('Balance Remaining')
    partner_id = fields.Many2one('res.partner', string='Contractor')

    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])

