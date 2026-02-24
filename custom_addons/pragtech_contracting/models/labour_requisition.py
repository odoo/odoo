# -*- coding: utf-8 -*-

import logging
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LabourRequisition(models.Model):
    _name = 'labour.requisition'
    _description = 'Labour Requisition'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    name = fields.Char('Requisition No.')
    group_id = fields.Many2one('project.task', 'Group')
    task_id = fields.Many2one('project.task', 'Task')
    flag = fields.Boolean('Flag', default=False)
    partner_id = fields.Many2one('res.partner', string='Contractor', change_default=True, track_visibility='always')
    requisition_date = fields.Date('Date', default=fields.date.today(), required=True)
    requirement_date = fields.Date('Requirement Date')
    procurement_date = fields.Date('Procurement Date')
    quantity = fields.Integer('Quantity')
    specification = fields.Char('Specification')
    remark = fields.Char('Remark')
    total_approved_qty = fields.Float('Approved Qty')
    total_ordered_qty = fields.Float('Ordered Qty')
    balance_qty = fields.Float('Balance Qty', compute='get_balanced_quantity', help="Current requisition qty-Total ordered qty")
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    priority = fields.Selection([('high', 'High'), ('low', 'Low')], 'Priority')
    brand_id = fields.Many2one('brand.brand', 'Brand')
    requisition_type = fields.Selection([('estimated', 'Estimated'), ('non_estimated', 'Non Estimated')], 'Type')
    unit = fields.Many2one('uom.uom', 'UOM')
    rate = fields.Float('Rate')
    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    procurement_type = fields.Selection([('New Purchase from Supplier', 'New Purchase from Supplier'),
                                         ('Cash Purchase ', 'Cash Purchase '), ('IST from other sites', 'IST from other sites')], "Procurement Type")
    warehouse_id = fields.Char('Procurement Type')
    requisition_fulfill = fields.Boolean('Req fulfill')

    work_class = fields.Many2one('labour.work.classification', 'Work Class')
    labour_id = fields.Many2one('labour.master', 'Labour')
    is_use = fields.Boolean('Is Use')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)])
    project_id = fields.Many2one('project.project', 'Project')
    sub_project = fields.Many2one('sub.project', 'Sub Project')

    labour_category = fields.Many2one('labour.category', related='labour_id.category_id', store=True, string='Labour Category')
    task_category = fields.Many2one('task.category', related='task_id.category_id', store=True, string='Task Category')
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)], auto_join=True, readonly=True)
    me_sequence = fields.Char(readonly=True)
    estimation_id = fields.Many2one('task.labour.line', 'Estimate No.')

    estimated_qty = fields.Float('Estimated Qty')
    Requisition_as_on_date = fields.Float('Requisition as on date')
    current_req_qty = fields.Float('Current Requisition Qty')
    flag = fields.Boolean('')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')],
                             string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    counter = fields.Integer('counter')

    @api.depends('current_req_qty', 'total_ordered_qty')
    def get_balanced_quantity(self):
        for this in self:
            this.balance_qty = this.current_req_qty - this.total_ordered_qty

    def change_state(self, fields={}):
        if self.counter == 0:
            """ Updating Requisition till date in estimation table """
            if fields.get('copy') == True:
                requisition_till_date = self.estimation_id.requisition_till_date + self.current_req_qty
                if requisition_till_date <= self.estimation_id.labour_uom_qty:
                    self.estimation_id.requisition_till_date = self.estimation_id.requisition_till_date + self.current_req_qty
                    self.name = self.env['ir.sequence'].next_by_code('labour.requisition') or '/'
                    self.flag = 1
                    self.write({'state': 'confirm'})
                else:
                    self.flag = 0
                    raise UserError(_('Sorry you cannot approve requisition greater then available quantity!'))

            view_id = self.env.ref('pragtech_contracting.approval_wizard_form_view_contracting').id
            return {
                'type': 'ir.actions.act_window',
                'key2': 'client_action_multi',
                'res_model': "approval.wizard",
                'multi': "True",
                'target': 'new',
                'views': [[view_id, 'form']],
            }

    def write(self, vals):
        res = models.Model.write(self, vals)
        if (self.quantity - self.current_req_qty) < self.Requisition_as_on_date:
            raise UserError(_('Current requisition quantity must be less than requisitions till date.'))

        return res

