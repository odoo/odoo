# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class LabourRequisition(models.TransientModel):
    _name = 'labour.requisition.wizard'
    _description = "Labour Requisition Wizard"

    name = fields.Many2one('project.task', 'Project WBS Name', domain=[('is_wbs', '=', True), ('is_task', '=', False)], required=True)
    project_id = fields.Many2one('project.project', 'Project', required=True)
    sub_project = fields.Many2one('sub.project', 'Sub Project')

    task_category = fields.Many2many('task.category', 'labour_req_task_categ_rel', 'requisition_id', 'task_category_id', string="Task Category")
    labour_category = fields.Many2many('labour.category', 'labour_req_labour_categ_rel', 'requisition_id', 'labour_category_id', string='Labour Category')
    labour_id = fields.Many2one('labour.master', 'Labour')
    group_id = fields.Many2one('project.task', 'Group')
    task_id = fields.Many2one('project.task', 'Task')
    requisition_line_ids = fields.One2many('labour.requisition.wizard.line', 'requisition_id', string='Requisition Order')
    from_date = fields.Date('From Date', default=str(datetime.now() + timedelta(days=-30)).split(' ')[0], required=True)
    to_date = fields.Date('To Date', default=lambda self: fields.Date.context_today(self) + timedelta(days=1), required=True)
    material = fields.Many2one('product.product')
    is_use = fields.Boolean(' ')

    task_date_type = fields.Selection([('planned', 'Planned'), ('actual', 'Actual')], string='Task Date Type', default='planned')  # ,'Search Task having'
    date_type = fields.Selection([('start_date', 'Start Date'), ('finish_date', 'Finish Date')], string='Date Type')
    note = fields.Char(default='You can only add Requisition for approved labour for current contractor')

    @api.depends('group_id')
    @api.onchange('group_id')
    def group_id_onchange(self):
        task_list = []
        if self.project_id:
            wbs = self.env['project.task'].browse(self.name.id)
            for line in wbs.labour_estimate_line:
                task_list.append(line.labour_line_id.category_id.id)

        return {
            'domain': {
                'task_id': [('parent_id', '=', self.group_id.id), ('is_task', '=', True), ('project_wbs_id', '=', self.name.id)]
            }
        }

    @api.depends('category_id')
    @api.onchange('category_id')
    def task_category_onchange(self):
        return {
            'domain': {
                'task_id': [('category_id', '=', self.task_category.id), ('is_task', '=', True), ('project_wbs_id', '=', self.name.id)]
            }
        }

    @api.model
    def default_get(self, fields):
        res = super(LabourRequisition, self).default_get(fields)
        res.update({
            'project_id': self._context.get('project_id'),
            'name': self._context.get('project_wbs'),
            'sub_project': self._context.get('sub_project'),
        })

        return res

    """ Return True if labour rate is approved """

    def get_is_red(self, labour_id, partner_id):
        price_info = self.env['labour.contractorinfo'].search([('labour_id', '=', labour_id), ('name', '=', partner_id), ('is_active', '=', True)])

        return price_info

    """ search requisitions on work order """

    @api.depends('project_id', 'sub_project', 'name', 'labour_category', 'labour_id', 'to_date', 'from_date')
    def get_requisitions_lines_wo(self):
        self.requisition_line_ids.unlink()
        # Search from different fields and add requisition depending on search
        # result
        work_order_obj = self.env['work.order'].browse(self._context.get('active_id'))
        sub_project_id = self.env['work.order'].browse(self._context.get('sub_project'))
        requisition_list = []
        domain = []
        labour_category = []
        # Get Approved stage from stage.master table
        stage_master_obj = self.env['stage.master'].search([('approved', '=', True)])
        domain.append(('project_id', '=', self.project_id.id))
        domain.append(('sub_project', '=', sub_project_id.id))
        domain.append(('project_wbs', '=', self.name.id))
        domain.append(('requisition_date', '>=', self.from_date))
        domain.append(('requisition_date', '<=', self.to_date))

        if self.labour_id:
            domain.append(('labour_id', '=', self.labour_id.id))

        if self.labour_category:
            for i in self.labour_category:
                labour_category.append(i.id)

            domain.append(('labour_category', 'in', labour_category))

        labour_requisition_obj = self.env['labour.requisition'].search(domain)
        cum_orderd_quantity = 0
        for line in labour_requisition_obj:
            cum_orderd_quantity = cum_orderd_quantity + line.current_req_qty
            if line.balance_qty > 0:
                price_info = self.get_is_red(line.labour_id.id, work_order_obj.partner_id.id)
                vals = {
                    'project_id': self.project_id.id,
                    'project_wbs': self.name.id,
                    'sub_project': sub_project_id.id,
                    'requisition_name': line.id,
                    'labour_id': line.labour_id.id,
                    'quantity': line.quantity,
                    'unit': line.unit.id,
                    'task_id': line.task_id.id,
                    'group_id': line.group_id.id,
                    'me_sequence': line.me_sequence,
                    'requisition_qty': line.current_req_qty,
                    'total_ordered_qty': line.total_ordered_qty,
                    'current_order_qty': line.current_req_qty - line.total_ordered_qty,
                    'current_req_qty': line.current_req_qty,
                    'specification': line.specification,
                }

                if price_info:
                    vals.update({'rate': price_info.price, 'is_red': False})
                else:
                    vals.update({'rate': line.rate, 'is_red': True})

                requisition_list.append((0, 0, vals))

        self.update({'requisition_line_ids': requisition_list})
        view_id = self.env.ref('pragtech_contracting.requisition_wizard_for_work_order').id
        return {
            'name': 'Add requisitions on Work Order',
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'labour.requisition.wizard',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    """ Add Requisitions on WO Requisition (Above Work Order Lines) """

    def add_labour_requisition(self):
        stage_id = self._context.get('stage_id')
        Work_order_obj = self.env['work.order'].browse(self._context.get('active_id'))
        wo_requisition_line_obj = self.env['wo.requisition'].search([('order_id', '=', self._context.get('active_id'))])
        old_wo_requisition_lines = [line.requisition_id for line in wo_requisition_line_obj]
        vals = {}

        for line in self.requisition_line_ids:
            if (line.current_order_qty > (line.requisition_qty - line.total_ordered_qty) or line.current_order_qty == 0) and line.is_use == True:
                raise UserError(_('Invalid Order Quantity.'))

            if line.is_use == True and line.current_order_qty > 0 and line.requisition_name not in old_wo_requisition_lines:
                vals = {
                    'project_wbs': self.name.id,
                    'labour_id': line.labour_id.id,
                    'labour_category': line.labour_id.category_id.id,
                    'quantity': line.quantity,
                    'unit': line.unit.id,
                    'rate': line.rate,
                    'task_id': line.task_id.id,
                    'group_id': line.group_id.id,
                    'Requisition_as_on_date': line.Requisition_as_on_date,
                    'total_ordered_qty': line.total_ordered_qty,
                    'current_order_qty': line.current_order_qty,
                    'me_sequence': line.me_sequence,
                    'order_id': self._context.get('active_id'),
                    'requisition_id': line.requisition_name.id,
                    'specification': line.specification,
                    'requisition_qty': line.requisition_qty,
                }

                if Work_order_obj.stage_id.approved == True:
                    Work_order_obj.flag = False
                    Work_order_obj.state = 'draft'

                self.env['wo.requisition'].create(vals)

        Work_order_obj.create_order_lines(Work_order_obj, self.name, stage_id)

    @api.depends('project_id', 'name', 'group_id', 'task_category', 'task_id', 'material_category', 'material')
    def compute_labour_requisitions(self):
        # Search from different fields and add requisition depending on search
        # result
        self.requisition_line_ids.unlink()
        vals = {}
        project_task_obj = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('name', '=', self.name.name), ('sub_project', '=', self.sub_project.id)])
        domain = []
        task_category_lst = []
        labour_category_lst = []
        domain.append(('wbs_id', '=', project_task_obj.id))

        if self.from_date > self.to_date:
            raise UserError("From Date should be lesser than To Date.")

        if self.task_date_type == 'planned' and self.date_type == 'start_date':
            domain.append(('planned_start_date', '>=', self.from_date))
            domain.append(('planned_start_date', '<=', self.to_date))
        if self.task_date_type == 'actual' and self.date_type == 'start_date':
            domain.append(('actual_start_date', '>=', self.from_date))
            domain.append(('actual_start_date', '<=', self.to_date))
        if self.task_date_type == 'planned' and self.date_type == 'finish_date':
            domain.append(('planned_finish_date', '>=', self.from_date))
            domain.append(('planned_finish_date', '<=', self.to_date))
        if self.task_date_type == 'actual' and self.date_type == 'finish_date':
            domain.append(('planned_finish_date', '>=', self.from_date))
            domain.append(('planned_finish_date', '<=', self.to_date))
        if self.group_id:
            domain.append(('group_id', '=', self.group_id.id))
        if self.task_id:
            domain.append(('labour_line_id', '=', self.task_id.id))
        if self.labour_id:
            domain.append(('labour_id', '=', self.labour_id.id))
        if self.task_category:
            for i in self.task_category:
                task_category_lst.append(i.id)
            domain.append(('task_category', 'in', task_category_lst))
        if self.labour_category:
            for i in self.labour_category:
                labour_category_lst.append(i.id)

            domain.append(('labour_category', 'in', labour_category_lst))

        labour_esimate_obj = project_task_obj.labour_estimate_line.search(domain)
        for line in labour_esimate_obj:
            if not line.labour_line_id.actual_finish_date and line.balanced_requisition > 0:
                vals = {
                    'labour_id': line.labour_id.id,
                    'quantity': line.labour_uom_qty,
                    'rate': line.labour_rate,
                    'task_id': line.labour_line_id.id,
                    'group_id': line.group_id.id,
                    'requisition_date': datetime.now(),
                    'task_category': line.labour_line_id.category_id,
                    'unit': line.labour_uom.id,
                    'me_sequence': line.sequence,
                    'Requisition_as_on_date': line.requisition_till_date,
                    'current_req_qty': line.labour_uom_qty - line.requisition_till_date,
                    'requisition_id': self.id,
                    'estimation_id': line.id,
                }
                self.requisition_line_ids.create(vals)

        view_id = self.env.ref('pragtech_contracting.labour_requisition_wizard_form_view').id
        return {
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'labour.requisition.wizard',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.onchange('is_use')
    def is_use_onchange(self):
        for line in self.requisition_line_ids:
            line.update({'is_use': self.is_use})

    def create_labour_requisition(self):
        action = self.env.ref('pragtech_contracting.action_labour_requisition')
        vals = {}
        req_ids = []
        stage = self.env['stage.master'].search([('draft', '=', True)])

        for line in self.requisition_line_ids:
            total_qty = 0
            domain = []
            task_category = []
            material_category = []
            domain.append(('project_wbs', '=', line.project_wbs.id))
            domain.append(('project_id', '=', line.project_id.id))
            domain.append(('sub_project', '=', line.sub_project.id))

            if line.group_id:
                domain.append(('group_id', '=', line.group_id.id))

            if line.task_id:
                domain.append(('task_id', '=', line.task_id.id))

            if line.labour_id:
                domain.append(('labour_id', '=', line.labour_id.id))

            requisition_obj = self.env['labour.requisition'].search(domain)
            for requisition_obj in requisition_obj:
                total_qty = total_qty + requisition_obj.quantity

            if line.is_use == True:
                vals = {
                    'project_id': self.project_id.id,
                    'sub_project': self.sub_project.id,
                    'project_wbs': self.name.id,
                    'labour_id': line.labour_id.id,
                    'quantity': line.quantity,
                    'unit': line.unit.id,
                    'rate': line.rate,
                    'task_id': line.task_id.id,
                    'group_id': line.group_id.id,
                    'me_sequence': line.me_sequence,
                    'requisition_date': datetime.now(),
                    'current_req_qty': line.current_req_qty,
                    'Requisition_as_on_date': line.Requisition_as_on_date,
                    'specification': line.specification,
                    'stage_id': stage.id,
                    'estimation_id': line.estimation_id.id,
                }

                action = self.env.ref('pragtech_contracting.action_labour_requisition')
                res = self.env['labour.requisition'].create(vals)
                vals = {
                    'date': datetime.now(),
                    'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                    'model': 'labour.requisition',
                    'res_id': res.id,
                    'author_id': self._context.get('uid'),
                    'to_stage': stage.id
                }
                re = self.env['mail.messages'].create(vals)
                req_ids.append(res.id)

                if line.current_req_qty > (line.quantity - line.Requisition_as_on_date):
                    raise UserError(_('Please enter valid Requisition Quantity.'))

        view_id = self.env.ref('pragtech_contracting.labour_requisition_tree').id
        context = self._context.copy()
        return {
            'name': 'Labour Requisitions',
            'view_mode': action.view_mode,
            'views': [(view_id, 'tree')],
            'res_model': 'labour.requisition',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'domain': [('id', 'in', req_ids)],
            'context': context,
        }


class LabourRequisitionWizardLine(models.TransientModel):
    _name = 'labour.requisition.wizard.line'
    _description = "Labour Requisition wizard Line"

    name = fields.Char('Requisition No')
    group_id = fields.Many2one('project.task', 'Group')
    task_id = fields.Many2one('project.task', 'Task')
    flag = fields.Boolean('Flag', default=False)
    partner_id = fields.Many2one('res.partner', string='Contractor', change_default=True)
    requisition_date = fields.Date('Date', default=fields.date.today(), required=True)
    requirement_date = fields.Date('Requirement Date')
    procurement_date = fields.Date('Procurement Date')
    quantity = fields.Float('Quantity')
    specification = fields.Char('Specification')
    remark = fields.Char('Remark')
    total_approved_qty = fields.Float('Approved Qty')
    total_ordered_qty = fields.Float('Ordered Qty')
    balance_qty = fields.Float('Balance Qty')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    priority = fields.Selection([('high', 'High'), ('low', 'Low')], 'Priority')
    brand_id = fields.Many2one('brand.brand', 'Brand')
    requisition_type = fields.Selection([('estimated', 'Estimated'), ('non_estimated', 'Non Estimated')], 'Type')
    requisition_id = fields.Many2one('labour.requisition.wizard', 'Labour Requisition')
    unit = fields.Many2one('uom.uom', 'UOM')
    rate = fields.Float('Rate')
    procurement_type = fields.Selection([('New Purchase from Supplier', 'New Purchase from Supplier'),
                                         ('Cash Purchase ', 'Cash Purchase '), ('IST from other sites', 'IST from other sites'), ], "Procurement Type")
    warehouse_id = fields.Char('Procurement Type')
    requisition_fulfill = fields.Boolean('Req fulfill')
    stage_id = fields.Many2one('transaction.stage', string='Transaction Stage', domain=[('model', '=', 'labour.requisition.wizard.line')])
    work_class = fields.Many2one('labour.work.classification', 'Work Class')
    labour_id = fields.Many2one('labour.master', 'Labour')
    is_use = fields.Boolean(' ')
    task_category = fields.Many2many('task.category', 'labour_req_line_task_categ_rel', 'requisition_line_id', 'task_category_id', string="Task Category")
    labour_category = fields.Many2many('labour.category', 'labour_req_line_labour_categ_rel', 'requisition_line_id', 'labour_category_id', string='Labour Category')
    project_id = fields.Many2one('project.project', related='requisition_id.project_id', store=True, string='Project')
    sub_project = fields.Many2one('sub.project', related='requisition_id.sub_project', string='Sub Project', required=True)
    project_wbs = fields.Many2one('project.task', related='requisition_id.name', store=True, string='Project Wbs')

    me_sequence = fields.Char(readonly=True)
    estimation_id = fields.Many2one('task.labour.line', 'Estimate No.')
    estimated_qty = fields.Float('Estimated Qty')
    Requisition_as_on_date = fields.Float('Requisition as on date')
    requisition_qty = fields.Float('Requisition Qty')
    current_req_qty = fields.Float('Current requisition Qty', readonly=False)
    requisition_name = fields.Many2one('labour.requisition', 'Requisition')
    current_order_qty = fields.Float('Current Order Qty')
    is_red = fields.Boolean()  # line will read if labour rate is not approved

    def change_state(self):
        view_id = self.env.ref('pragtech_contracting.approval_wizard_form_view_contracting').id
        return {
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'res_model': "approval.wizard",
            'multi': "True",
            'target': 'new',
            'views': [[view_id, 'form']],
        }

    @api.onchange('current_req_qty')
    def onchnge_Requisition_qty(self):
        if self.current_req_qty > (self.quantity - self.Requisition_as_on_date):
            raise UserError(_('Please enter valid Requisition Quantity.'))

    @api.onchange('stage_id')
    @api.depends('stage_id.approved')
    def onchange_stage(self):
        if self.stage_id.approved:
            self.flag = True

