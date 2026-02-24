# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import UserError


class WizardGrnReport(models.TransientModel):
    _name = 'wizard.grn.report'
    _description = 'Grn Report'

    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    workorder_id = fields.Many2one('work.order', 'WorkOrder')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    partner_id = fields.Many2one('res.partner', string='Contractor')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    order_line = fields.One2many('wizard.grn.report.line', 'order_id', string='Order Lines', copy=True, ondelete='cascade')

    def compute_workorders(self):
        self.order_line.unlink()
        domain = []
        if self.from_date > self.to_date:
            raise UserError("From Date should be lesser than To Date.")

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
        wo_obj = self.env['work.order'].search(domain)
        vals = {}
        for wo in wo_obj:
            # print wo
            for order in wo.order_line:
                domain_completion = []
                domain_completion.append(('workorder_id', '=', wo.id))
                domain_completion.append(('labour_id', '=', order.labour_id.id))
                recs = self.env['work.completion'].search(domain_completion)
                if recs:
                    for rec in recs:
                        completion_qty = (rec.total_percent * rec.estimated_qty) / 100
                        vals = {
                            'order_id': self.id,
                            'workorder_id': wo.id,
                            'partner_id': wo.partner_id.id,
                            'project_id': wo.project_id.id,
                            'sub_project': wo.sub_project.id,
                            'project_wbs': wo.project_wbs.id,
                            'labour_id': order.labour_id.id,
                            'wo_qty': order.quantity,
                            'wo_completed': completion_qty,
                            'wo_balance': order.quantity - completion_qty,
                            'rate': order.rate,
                            'bal_amount': order.rate * (order.quantity - completion_qty),
                        }
                        value = self.order_line.create(vals)
                else:
                    vals = {
                        'order_id': self.id,
                        'workorder_id': wo.id,
                        'partner_id': wo.partner_id.id,
                        'project_id': wo.project_id.id,
                        'sub_project': wo.sub_project.id,
                        'project_wbs': wo.project_wbs.id,
                        'labour_id': order.labour_id.id,
                        'wo_qty': order.quantity,
                        'wo_completed': 0,
                        'wo_balance': order.quantity,
                        'rate': order.rate,
                        'bal_amount': order.rate * (order.quantity),
                    }
                    value = self.order_line.create(vals)

        view_id = self.env.ref('pragtech_contracting.grn_report_form_view').id
        return {
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'wizard.grn.report',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class WizardGrnReportLine(models.TransientModel):
    _name = 'wizard.grn.report.line'
    _description = 'Grn Report Line'

    order_id = fields.Many2one('wizard.grn.report', string='Order Reference', ondelete='cascade')
    workorder_id = fields.Many2one('work.order', 'WorkOrder')
    partner_id = fields.Many2one('res.partner', string='Contractor')
    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    labour_id = fields.Many2one('labour.master', 'Labour')

    wo_qty = fields.Float('WO Qty.')
    wo_completed = fields.Float('Completed Qty.')
    wo_balance = fields.Float('Balance Qty.')
    rate = fields.Float('Rate')
    bal_amount = fields.Float('Balance Amount')

