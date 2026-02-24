# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class CategoryBudget(models.Model):
    _name = 'category.budget'
    _description = 'Category Budget'
    _rec_name = 'sub_project'

    project_id = fields.Many2one('project.project', 'Project Name', required=True)
    builtup_area = fields.Float('Builtup Area')
    project_wbs = fields.Many2one('project.task', 'Project WBS', domain=[('is_wbs', '=', True), ('is_task', '=', False)], required=True)
    category_line_ids = fields.One2many('category.budget.line', 'category_id', string='Category Budget Line')
    sub_project = fields.Many2one('sub.project', 'Sub Project', required=True)

    @api.model
    def change_stage(self):
        return True

    @api.onchange('project_id')
    def onchange_project(self):
        if self.project_id:
            self.builtup_area = self.project_id.builtup_area

        if not self.project_id:
            self.project_wbs = None

        self.sub_project = False
        sub_project_ids = []
        sub_project_obj = self.env['sub.project'].search([('project_id', '=', self.project_id.id)])
        for line in sub_project_obj:
            sub_project_ids.append(line.id)

        return {
            'domain': {'sub_project': [('id', 'in', sub_project_ids)]}
        }

    """ Used in report to get Expended Material. """

    def get_expended_material(self):
        issued_qty = 0
        for line in self.category_line_ids:
            move = self.env['stock.move'].search([('task_category', '=', line.task_category.id)])
            for move_line in move:
                issued_qty = move_line.product_uom_qty + issued_qty

        return issued_qty

    def get_expended_labour(self):
        issued_qty = 0
        return issued_qty

    def get_expended_total(self):
        material = (self.get_expended_material())
        labour = (self.get_expended_labour())
        return float(material[0] + labour[0])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            obj = self.search([('project_id', '=', vals.get('project_id')), ('sub_project', '=', vals.get('sub_project')), ('project_wbs', '=', vals.get('project_wbs'))])
            if obj:
                raise UserError(_('Budget is already created for current Project.'))

            task_obj = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('id', '=', self.project_wbs.id)])
            task_obj.project_task_library_ids

            return super(CategoryBudget, self).create(vals_list)

    def unlink(self):
        for i in self.category_line_ids:
            if i.stage_id.approved == True:
                raise UserError(_('You cannot delete this record as Budget for some categories is Approved.'))

        return super(CategoryBudget, self).unlink()


class CategoryBudgetLine(models.Model):
    _name = 'category.budget.line'
    rec_name = 'project_id'
    _description = 'Category Budget Line'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    date = fields.Date('Date', default=fields.date.today(), required=True)
    task_category = fields.Many2one('task.category', 'Task Category', required=True)
    quantity = fields.Integer('Budgeted Qty')
    rate = fields.Float('Budget Rate')
    amount = fields.Float('Budget Amount', compute='compute_amount', store=True)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    material_percent = fields.Float('Material %')
    labour_percent = fields.Float('Labour %')
    labour_cost = fields.Float('Labour Cost', compute='compute_labour_material_cost', store=True)
    material_cost = fields.Float('Material Cost', compute='compute_labour_material_cost', store=True)
    category_id = fields.Many2one('category.budget', 'Category Budget', ondelete='cascade')
    date = fields.Date('Date', default=fields.date.today(), required=True)

    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    flag = fields.Boolean('')
    remark = fields.Char('Remark')

    labourbudget_used = fields.Float('Labour Budget Used')
    materialbudget_used = fields.Float('Material Budget Used')
    labourbudget_remaining = fields.Float('Labour Budget Remaining', compute='_get_budget')
    materialbudget_remaining = fields.Float('Material Budget Remaining', compute='_get_budget')

    @api.depends('labourbudget_used', 'materialbudget_used')
    def _get_budget(self):
        for line in self:
            labour_budget = (line.amount * line.labour_percent) / 100
            material_budget = (line.amount * line.material_percent) / 100
            line.labourbudget_remaining = labour_budget - line.labourbudget_used
            line.materialbudget_remaining = material_budget - line.materialbudget_used

    def change_state(self, context={}):
        view_id = self.env.ref('pragtech_ppc.approval_wizard_form_view').id
        if context.get('copy') == True:
            self.flag = 1

        return {
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'res_model': "approval.wizard",
            'multi': "True",
            'target': 'new',
            'views': [[view_id, 'form']],
        }

    @api.depends('task_category')
    def compute_labour_material_cost(self):
        labour_total = 0.0
        material_total = 0.0
        for line in self:
            wbs_obj = self.env['project.task'].search([('id', '=', line.category_id.project_wbs.id)])
            labour_obj = self.env['task.labour.line'].search([('task_category', '=', line.task_category.id), ('wbs_id', '=', wbs_obj.id)])
            for labour in labour_obj:
                labour_total += labour.labour_rate
                line.labour_cost = labour_total
            material_obj = self.env['task.material.line'].search([('task_category', '=', line.task_category.id), ('wbs_id', '=', wbs_obj.id)])
            for material in material_obj:
                material_total += material.material_rate
                line.material_cost = material_total

    @api.depends('quantity', 'rate')
    def compute_amount(self):
        for obj in self:
            obj.amount = obj.quantity * obj.rate

    @api.onchange('labour_percent')
    def onchange_labour_percent(self):
        if self.labour_percent:
            self.material_percent = 100 - self.labour_percent

    @api.onchange('material_percent')
    def onchange_material_percent(self):
        if self.material_percent:
            self.labour_percent = 100 - self.material_percent

    """" Used in report to get budget vs actual """

    def get_budget_variance(self):
        a = self.category_id.get_expended_total()
        return self.amount - a

    """" Used in report to get budget vs actual """

    def get_estimation_variance(self):
        a = self.category_id.get_expended_total()
        return ((self.material_cost + self.labour_cost) - a)


class WbsBudget(models.Model):
    _name = 'wbs.budget'
    _description = 'WBS Budget'

    project_id = fields.Many2one('project.project', "Project Name", required=True)
    project_wbs = fields.Many2one('project.task', 'Sub Project', domain=[('is_wbs', '=', True), ('is_task', '=', False)], required=True)
    wbs_budget_line_ids = fields.One2many('wbs.budget.line', 'wbs_budget_id', string='WBS Budget Line')

    @api.onchange('project_id')
    def onchange_material(self):
        if not self.project_id:
            self.project_wbs = None


class WbsBudgetLine(models.Model):
    _name = 'wbs.budget.line'
    _description = 'Wbs Budget Line'

    date = fields.Date('Date', default=fields.date.today(), required=True)
    quantity = fields.Integer('Budgeted Quantity')
    rate = fields.Float('Budget Rate')
    amount = fields.Float('Budget Amount', compute='compute_amount', store=True)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    material_percent = fields.Float('Material %', default=0.00)
    labour_percent = fields.Float('Labour %', default=0.00)
    wbs_budget_id = fields.Many2one('wbs.budget', 'WBS Budget')

    @api.depends('quantity', 'rate')
    def compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.rate

    @api.onchange('material_percent', 'labour_percent')
    def onchange_material(self):
        for line in self:
            line.labour_percent = 100 - line.material_percent
            line.material_percent = 100 - line.labour_percent

