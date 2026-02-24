# -*- coding: utf-8 -*-

import json
from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class Task(models.Model):
    _inherit = 'project.task'
    _description = 'Task'
    
    
    depend_id = fields.Char('depend_id Name')
    day_count = fields.Char('day_count Name')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        return models.Model.fields_get(self, allfields=allfields, attributes=attributes)

    @api.model
    def fields_get_keys(self):
        return models.Model.fields_get_keys(self)

    # Gantt View Function
    @api.model
    def get_data(self):
        task_list = []
        projects = self.env['project.project'].search([])
        for line in projects:
            vals = {
                "name": line.name,
                "level": 0,
                'depends': "",
                "progress": '0',
                "progressByWorklog": False,
                "relevance": '0',
                "type": "",
                "typeId": "",
                "description": "",
                "code": "",
                "status": "STATUS_ACTIVE",
                "canWrite": True,
                "start": 1396994400000,
                "duration": 2,
                "end": 1398203999999,
                "startIsMilestone": True,
                "endIsMilestone": False,
                "collapsed": False,
                "assigs": [],
                "hasChild": True,
                "dbid": (line.id),
                'is_project': True,
            }
            task_list.append(vals)

        sub_projects = self.env['sub.project'].search([])

        for line in sub_projects:
            project_id = str(line.project_id.id)
            vals = {
                'is_subproject': True,
                "id": -(line.id),
                "name": line.name,
                "level": 1,
                "progress": '0',
                "progressByWorklog": False,
                "relevance": '0',
                "type": "",
                "typeId": "",
                "description": "",
                "code": "",
                "status": "STATUS_ACTIVE",
                "canWrite": True,
                "start": 1396994400000,
                "duration": 2,
                "end": 1398203999999,
                "startIsMilestone": False,
                "endIsMilestone": False,
                "collapsed": False,
                "depends": "",
                "assigs": [],
                "hasChild": True
            }
            task_list.append(vals)

        data = self.search([('id', '>', 12)])

        for line in data:
            if not line.is_task and not line.is_wbs:  # group
                parent = str(line.parent_id.id)
                vals = {
                    'is_group': True,
                    "id": -(line.id),
                    "name": line.name,
                    "level": 3,
                    "progress": '0',
                    "progressByWorklog": False,
                    "relevance": '0',
                    "type": "",
                    "typeId": "",
                    "description": "",
                    "code": "",
                    "status": "STATUS_ACTIVE",
                    "canWrite": True,
                    "start": 1396994400000,
                    "duration": 2,
                    "end": 1398203999999,
                    "startIsMilestone": False,
                    "endIsMilestone": False,
                    "collapsed": False,
                    "depends": parent,
                    "assigs": [],
                    "hasChild": True
                }
                task_list.append(vals)
            elif line.is_task and not line.is_wbs:  # task
                group_id = str(line.parent_id)
                vals = {
                    'is_task': True,
                    "id": -(line.id),
                    "name": line.name,
                    "level": 4,
                    'depends': "",
                    "progress": '0',
                    "progressByWorklog": False,
                    "relevance": '0',
                    "type": "",
                    "typeId": "",
                    "description": "",
                    "code": "",
                    "status": "STATUS_ACTIVE",
                    "canWrite": True,
                    "start": 1396994400000,
                    "duration": 2,
                    "end": 1398203999999,
                    "startIsMilestone": False,
                    "endIsMilestone": False,
                    "collapsed": False,
                    "assigs": [],
                    "hasChild": True
                }
                task_list.append(vals)
            elif not line.is_task and line.is_wbs:  # wbs
                subproject_id = str(line.sub_project.id)
                vals = {
                    'is_wbs': True,
                    "id": -(line.id),
                    "name": line.name,
                    "level": 2,
                    "progress": '0',
                    "progressByWorklog": False,
                    "relevance": '0',
                    "type": "",
                    "typeId": "",
                    "description": "",
                    "code": "",
                    "status": "STATUS_ACTIVE",
                    "start": 1396994400000,
                    "duration": 2,
                    "end": 1398203999999,
                    "startIsMilestone": False,
                    "endIsMilestone": False,
                    "canWrite": True,
                    "collapsed": False,
                    "depends": "",
                    "assigs": [],
                    "hasChild": True
                }
                task_list.append(vals)

        return json.dumps(task_list)

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    name = fields.Char('WBS Name', required=True)
    wbs_name = fields.Char('WBS Name')  # Added For Domain Purpose
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    is_task = fields.Boolean('Task')
    category_id = fields.Many2one('task.category', 'Category')
    sub_category_id = fields.Many2one('task.sub.category', 'Sub Category')
    material_cost = fields.Float(compute='calculate_material_cost', string='Material Cost', method=True)
    min_qty = fields.Integer('Minimum Qty')
    labour_cost = fields.Float(compute='calculate_labour_cost', string='Labour Cost', method=True)
    parent_task_id = fields.Many2one('project.task', 'Parent Group', store=True)
    parent_group_id = fields.Many2one('project.task', 'Parent Group')
    task_ids = fields.One2many('project.task', 'parent_task_id')
    group_ids = fields.One2many('project.task', 'parent_group_id', domain=[('is_task', '=', False)])
    wbs_task_ids = fields.One2many("project.task", 'parent_id', string="Group")
    child_ids2 = fields.One2many('project.task', 'parent_id', compute="compute_child", store=True)
    task_material_line = fields.One2many('task.material.line', 'material_line_id', string='Task Material Lines')
    task_labour_line = fields.One2many('task.labour.line', 'labour_line_id', string='Task labour Lines')
    is_wbs = fields.Boolean('WBS', domain=[('is_task', '=', False), ('is_task', '=', True)])
    actual_cost = fields.Float('Actual Cost', compute='get_actual_cost', readonly=True)
    is_completed = fields.Boolean('Is Completed')
    completion_date = fields.Date('Actual Start Date')
    planed_start_date = fields.Datetime('Planed Start Date')
    planned_finish_date = fields.Datetime('Planned Finish Date')
    is_started = fields.Boolean('Is Started')
    actual_start_date = fields.Date('Actual Start Date')
    actual_finish_date = fields.Date('Actual Finish Date')
    percentage = fields.Float('Percentage')

    wbs_start_date = fields.Datetime(string='Start Date')
    wbs_end_date = fields.Datetime(string='End Date')

    project_task_library_ids = fields.Many2many('project.task.library', 'task_library_rel', 'task_id', 'task_library_id', string="Tasks", domain="[('is_library_task','=',True)]")
    project_child_task_library_ids = fields.Many2many('project.task.library', 'child_task_library_rel', 'task_id', 'task_library_id', domain="[('is_library_task','=',True)]", store=True)
    is_group = fields.Boolean('Is_Group')
    unit = fields.Many2one('uom.uom', 'Unit')
    labour_estimate_line = fields.One2many('task.labour.line', 'wbs_id', 'Estimated Labour')
    material_estimate_line = fields.One2many('task.material.line', 'wbs_id', 'Estimated Material')
    is_billable = fields.Boolean('Billable')

    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)], auto_join=True, readonly=True)
    flag = fields.Boolean(' ')
    stage_master_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    project_wbs_id = fields.Many2one('project.task', 'WBS')
    budgeted_category_ids = fields.Char('Budgeted Category Ids')
    library_task_id = fields.Many2one('project.task.library', 'Library Task')
    status = fields.Selection([('unplanned', 'Unplanned'), ('non_started', 'Non Started'), ('started', 'Started'), ('in_complete', 'In Complete'), ('completed', 'Completed')], string='Status')
    tasks_having = fields.Selection([('planned', 'Planned'), ('actual', 'Actual')], string='Tasks Having')
    parent_id = fields.Many2one('project.task', string="Parent", help="Set field for task hierarchy.", store=True)
    """ fields required in report """

    category_list = []
    task_obj_list = []
    category_domain_many2many = []
    budgeted_category_ids = []

    def get_actual_cost(self):
        """ Method to calculate the actual_cost of wbs. """
        for task in self:
            total_amount = 0.0
            ra_total_amount = 0.0
            account_move_rec = self.env['account.move'].search([('project_wbs_id', '=', task.id), ('state', '=', 'posted')])
            for move in account_move_rec:
                total_amount += move.amount_total
                
            ra_move_rec = self.env['ra.bill'].search([('project_wbs', '=', task.id), ('state', '=', 'paid')])
            for ra_bil in ra_move_rec:
                ra_total_amount += ra_bil.final_total_payable

            task.update({
                'actual_cost': total_amount + ra_total_amount
            })

    def change_state(self, context={}):
        if context.get('copy') == True:
            self.flag = True
        else:
            flag = 0
            view_id = self.env.ref('pragtech_ppc.approval_wizard_form_view').id
            return {
                'type': 'ir.actions.act_window',
                'key2': 'client_action_multi',
                'res_model': 'approval.wizard',
                'multi': 'True',
                'target': 'new',
                'views': [[view_id, 'form']],
            }

    @api.depends('material_estimate_line.sub_total')
    def _compute_material_total(self):
        total = 0
        for line in self.material_estimate_line:
            total = total + line.sub_total

        self.material_estimation_total = total

    @api.depends('labour_estimate_line.sub_total')
    def _compute_labour_total(self):
        total = 0
        for line in self.labour_estimate_line:
            total = total + line.sub_total

        self.labour_estimation_total = total

    @api.constrains('parent_id')
    def _check_subtask_project(self):
        for task in self:
            if task.parent_id.project_id and task.project_id != task.parent_id.project_id.subproject_ids:
                pass

    @api.depends('quantity', 'discount', 'rate', 'work_tax')
    def _compute_amount(self):
        """
            Compute the amounts of the VQ line.
        """
        for line in self:
            tax_amount = 0
            price = line.rate * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.work_tax.compute_all(price, line.order_id.currency_id, line.quantity, product=line.labour_id, partner=line.order_id.partner_id)
            for tax in taxes['taxes']:
                tax_amount = tax_amount + tax['amount']

            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'taxed_amount': tax_amount,
                'basic_amount': (line.rate * line.quantity),
                'net_rate': taxes['total_excluded'] + tax_amount,
            })

    @api.depends('project_task_library_ids', 'sub_project', 'project_id')
    @api.onchange('project_child_task_library_ids')
    def onchange_project_child_task_library_ids(self):
        stage_id = self.env['stage.master'].search([('approved', '=', True)])
        wbs = (self.search([('name', '=', self.wbs_name)])).id
        if self.sub_project.budget_applicable:
            category_list = []
            budget_id = self.env['category.budget'].search([('project_id', '=', self.project_id.id), ('project_wbs', '=', wbs), ('sub_project', '=', self.sub_project.id)])
            for line in budget_id.category_line_ids:
                if line.stage_id == stage_id:
                    category_list.append(line.task_category.id)

            return {
                'domain': {
                    'project_child_task_library_ids': [('category_id', 'in', category_list)]
                }
            }

    # Percentage validated between 0 to 100 on create.....
    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_lists):
        for vals_list in vals_lists:
            if vals_list.get('percentage'):
                if vals_list.get('percentage') < 0 or vals_list.get('percentage') > 100:
                    raise UserError(_('Please Enter Valid Percentage.'))

            """" Creating Audit Trail """
            if vals_list.get('project_id') and vals_list.get('sub_project'):
                existing_stage = []
                st_id = self.env['stage.master'].search([('draft', '=', True)])
                msg_ids = {
                    'date': datetime.now(),
                    'from_stage': None,
                    'to_stage': st_id.id,
                    'model': 'project.project'
                }

                if self._context.get('uid'):
                    msg_ids.update({
                        'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                    })

                existing_stage.append((0, 0, msg_ids))
                vals_list.update({'mesge_ids': existing_stage})

            res = super(Task, self).create(vals_lists)

            if 'wbs_task_ids' in vals_list:
                task_ids = []
                wbs_task_ids = vals_list['wbs_task_ids']
                for child_task in wbs_task_ids:
                    if child_task and type(child_task[2]) is dict:
                        if child_task[2]['task_ids']:
                            break

                            for o in child_task[2]['task_ids']:
                                prj_task = self.browse(o[1])
                                self._cr.execute("select id, name from project_task where name='%s' order by id asc" % prj_task.name)
                                data = self._cr.fetchall()
                                self._cr.execute("update project_task set parent_id=%s where id=%s" % (res.id, data[0][0]))
                                task_ids.append(data[0][0])

                for i in self.env['project.task'].search([('id', 'in', task_ids)]):
                    for j in i.task_ids:
                        for k in j.task_material_line:
                            k.wbs_id = res.id
                        for k in j.task_labour_line:
                            k.wbs_id = res.id

            for rec in res:
                if rec:
                    for i in rec.wbs_task_ids:
                        for j in i.task_ids:
                            for k in j.task_material_line:
                                k.wbs_id = rec.id
                            for k in j.task_labour_line:
                                k.wbs_id = rec.id

            return res

    # Percentage validated between 0 and 100 on write
    def write(self, vals):
        if vals.get('percentage'):
            if vals.get('percentage') < 0 or vals.get('percentage') > 100:
                raise UserError(_('Please Enter Valid Percentage.'))

        res = super(Task, self).write(vals)

        for rec in self:
            if rec:
                for i in rec.wbs_task_ids:
                    for j in i.task_ids:
                        for k in j.task_material_line:
                            k.wbs_id = rec.id
                        for k in j.task_labour_line:
                            k.wbs_id = rec.id

        return res

    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.name:
            self.sub_project = False
            sub_project_ids = []
            sub_project_obj = self.env['sub.project'].search([('project_id', '=', self.project_id.id)])
            for line in sub_project_obj:
                sub_project_ids.append(line.id)

            return {
                'domain': {'sub_project': [('id', 'in', sub_project_ids)]}
            }

    # Percentage validated between 0 to 100
    @api.onchange('percentage')
    def onchange_percentage(self):
        if self.percentage < 0 or self.percentage > 100:
            raise UserError(_('Please Enter Valid Percentage.'))

    @api.onchange('category_id')
    def onchange_category_id(self):
        return {
            'domain': {
                'sub_category_id': [('category_id', '=', self.category_id.id)]
            }
        }

    @api.depends('task_material_line')
    def calculate_material_cost(self):
        for line in self:
            total_material_cost = 0.0
            if line.task_material_line:
                for lines in line.task_material_line:
                    total_material_cost += lines.material_uom_qty * lines.material_rate

                line.material_cost = total_material_cost
            else:
                line.material_cost = total_material_cost

    @api.depends('task_labour_line')
    def calculate_labour_cost(self):
        for line in self:
            total_labour_cost = 0.0
            if line.task_labour_line:
                for lines in line.task_labour_line:
                    total_labour_cost += lines.labour_uom_qty * lines.labour_rate

                line.labour_cost = total_labour_cost

    """ Start report functions"""

    def get_category(self, obj):
        task_obj = self.env['project.task'].search([('parent_id', '=', obj.id)])
        for i in task_obj:
            self.get_category(i)
            if i.is_task == True:
                self.task_obj_list.append(i)
                self.category_list.append(i.category_id.name)

        self.category_list = list(set(self.category_list))

    def get_material_estimated_budget(self, category):
        budget = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        for i in self.task_obj_list:
            if i.category_id.id == cat_obj.id:
                budget = budget + i.material_cost

        return budget

    def get_labour_estimated_budget(self, category):
        budget = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        for i in self.task_obj_list:
            if i.category_id.id == cat_obj.id:
                budget = budget + i.labour_cost

        return budget

    def get_material_budgeted(self, task_obj, category):
        wbs_id = self.get_wbs_id(task_obj)
        cat_obj = self.env['task.category'].search([('name', '=', category)])
        budget = 0
        budget_obj = self.env['category.budget'].search([('project_wbs', '=', wbs_id)], limit=1)
        for line in budget_obj.category_line_ids:
            if line.task_category.id == cat_obj.id:
                budget = budget + ((line.material_percent / 100) * line.amount)

        return budget

    def get_labour_budgeted(self, task_obj, category):
        wbs_id = self.get_wbs_id(task_obj)
        cat_obj = self.env['task.category'].search([('name', '=', category)])
        budget = 0
        budget_obj = self.env['category.budget'].search([('project_wbs', '=', wbs_id)], limit=1)
        for line in budget_obj.category_line_ids:
            if line.task_category.id == cat_obj.id:
                budget = budget + ((line.labour_percent / 100) * line.amount)

        return budget

    def get_completed_work_material_estimate(self, category):
        budget = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        for i in self.task_obj_list:
            if i.category_id.id == cat_obj.id and i.actual_finish_date:
                budget = budget + i.material_cost

        return budget

    def get_completed_work_labour_estimate(self, category):
        budget = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        for i in self.task_obj_list:
            if i.category_id.id == cat_obj.id and i.actual_finish_date:
                budget = budget + i.labour_cost

        return budget

    def get_inprogress_work_material_estimate(self, category):
        budget = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        for i in self.task_obj_list:
            if i.category_id.id == cat_obj.id and not i.actual_finish_date and i.actual_start_date:
                budget = budget + i.material_cost

        return budget

    def get_inprogress_work_labour_estimate(self, category):
        budget = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        for i in self.task_obj_list:
            if i.category_id.id == cat_obj.id and not i.actual_finish_date and i.actual_start_date:
                budget = budget + i.labour_cost

        return budget

    def get_material_actual_cost_of_completed(self, category):
        """to do- add project and wbs in condition"""
        budget = 0
        price = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        move_obj = self.env['stock.move'].search([('task_category', '=', cat_obj.id)])
        qty = 0
        for move in move_obj:
            if move.task_id.actual_finish_date:
                qty = qty + move.product_uom_qty
                supplierinfo = self.env['product.supplierinfo'].search([('product_id', '=', move.product_id.id)], limit=1)
                price = supplierinfo.price

        return qty * price

    def get_labour_actual_cost_of_completed(self, category):
        """to do- add project and wbs in condition"""
        budget = 0
        price = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        move_obj = self.env['stock.move'].search([('task_category', '=', cat_obj.id)])
        qty = 0
        for move in move_obj:
            if move.task_id.actual_finish_date:
                qty = qty + move.product_uom_qty
                supplierinfo = self.env['product.supplierinfo'].search([('product_id', '=', move.product_id.id)], limit=1)
                price = supplierinfo.price

        return qty * price

    def get_material_actual_cost_of_inprogress(self, category):
        """ to do- add project and wbs in condition """
        budget = 0
        price = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        move_obj = self.env['stock.move'].search([('task_category', '=', cat_obj.id)])
        qty = 0
        for move in move_obj:
            if not move.task_id.actual_finish_date and move.task_id.actual_start_date:
                qty = qty + move.product_uom_qty
                supplierinfo = self.env['product.supplierinfo'].search([('product_id', '=', move.product_id.id)], limit=1)
                price = supplierinfo.price

        return qty * price

    def get_labour_actual_cost_of_inprogress(self, category):
        """ to do- add project and wbs in condition """
        budget = 0
        price = 0
        cat_obj = self.env['task.category'].search([('name', '=', category)], limit=1)
        move_obj = self.env['stock.move'].search([('task_category', '=', cat_obj.id)])
        qty = 0
        for move in move_obj:
            if not move.task_id.actual_finish_date and move.task_id.actual_start_date:
                qty = qty + move.product_uom_qty
                supplierinfo = self.env['product.supplierinfo'].search([('product_id', '=', move.product_id.id)], limit=1)
                price = supplierinfo.price

        return qty * price

    def get_balance_budet(self, category):
        return self.get_material_actual_cost_of_completed(category) - self.get_material_actual_cost_of_inprogress(category)

    def get_material_balance_estimate(self, category):
        return (self.get_material_estimated_budget(category) - (self.get_material_actual_cost_of_completed(category) + self.get_material_actual_cost_of_inprogress(category)))

    def get_labour_balance_estimate(self, category):
        return (self.get_labour_estimated_budget(category) - (self.get_labour_actual_cost_of_completed(category) + self.get_labour_actual_cost_of_inprogress(category)))

    def material_cost_variance(self, category):
        return self.get_completed_work_material_estimate(category) - self.get_material_actual_cost_of_completed(category)

    def labour_cost_variance(self, category):
        return self.get_completed_work_labour_estimate(category) - self.get_labour_actual_cost_of_completed(category)

    # creates estimated material and labour of manually added groups in 'Wbs Task Group' page of project wbs.
    def create_wbs_task(self):
        task_list = []
        group_obj = []
        for project_task_library_id in self.project_child_task_library_ids:
            group_obj = self.env['project.task.library'].browse(project_task_library_id.id)
            self.create_task_wbs(group_obj)
            task_list.append((3, project_task_library_id.id, False))

        self.project_child_task_library_ids = task_list

    # Called in create_task_wbs to Get Wbs id i.e.Parent.
    def get_wbs_id(self, task_obj):
        if task_obj.parent_id:
            return self.get_wbs_id(task_obj.parent_id)
        if not task_obj.parent_id:
            return task_obj.id

    def create_task_wbs(self, group_obj, parent_id=None, parent=None, parent_task=None, parent_group=None):
        task_list = []
        count = 0
        for obj in group_obj:
            count = count + 1
            data = {
                'name': obj.name,
                'category_id': obj.category_id.id,
                'sub_category_id': obj.sub_category_id.id,
                'is_task': obj.is_library_task,
                'is_wbs': False,
                'parent_task_id': self.id,
                'planed_start_date': self.planed_start_date,
                'planned_finish_date': self.planned_finish_date,
                'library_task_id': obj.id,
            }
            task_list.append((0, 0, data))

        task_obj = self.env['project.task'].create(data)
        wbs = self.get_wbs_id(task_obj)
        material_lst = []

        for material in obj.task_material_line:
            material_data = {
                'material_id': material.material_id.id,
                'material_uom': material.material_uom.id,
                'material_uom_qty': material.material_uom_qty,
                'material_rate': material.material_rate,
                'material_line_id': task_obj.id,
                'group_id': task_obj.parent_id.id,
                'task_category': obj.category_id.id,
                'wbs_id': wbs,
            }
            self.env['task.material.line'].create(material_data)
            material_lst.append((0, 0, material_data))

        for labour in obj.task_labour_line:
            labour_data = {
                'labour_id': labour.labour_id.id,
                'labour_uom': labour.labour_uom.id,
                'labour_uom_qty': labour.labour_uom_qty,
                'labour_rate': labour.labour_rate,
                'labour_line_id': task_obj.id,
                'group_id': task_obj.parent_id.id,
                'task_category': obj.category_id.id,
                'wbs_id': wbs,
            }
            labour = self.env['task.labour.line'].create(labour_data)
            labour.labour_line_id.project_wbs_id = wbs
            labour.group_id.project_wbs_id = wbs

        # Recursively create subgroup and sub-task
        for sub_group_obj in obj.group_ids:
            self.create_task_wbs(sub_group_obj, task_obj.id, parent=True, parent_group=True)

        for sub_task_obj in obj.task_ids:
            self.create_task_wbs(sub_task_obj, task_obj.id, parent=True, parent_task=True)
            

    def action_apply(self):
        material_lst = []
        labour_lst = []
        for obj in self.project_child_task_library_ids:
            for material in obj.task_material_line:
                material_data = {
                    'material_id': material.material_id.id,
                    'material_uom': material.material_uom.id,
                    'material_uom_qty': material.material_uom_qty,
                    'material_rate': material.material_rate,
                    'material_line_id': self.id,
                    'group_id': self.id,
                    'task_category': obj.category_id.id,
                    'wbs_id': self.id,
                }
                material_lst.append((0, 0, material_data))

            for labour in obj.task_labour_line:
                labour_data = {
                    'labour_id': labour.labour_id.id,
                    'labour_uom': labour.labour_uom.id,
                    'labour_uom_qty': labour.labour_uom_qty,
                    'labour_rate': labour.labour_rate,
                    'labour_line_id': self.id,
                    'group_id': self.id,
                    'task_category': obj.category_id.id,
                    'wbs_id': self.id,
                }
                labour_lst.append((0, 0, labour_data))
        
        # Remove existing records in one2many field
        self.material_estimate_line.unlink()
        self.labour_estimate_line.unlink()

        # Add new records to one2many field
        self.material_estimate_line = material_lst
        self.labour_estimate_line = labour_lst
        

    @api.onchange('min_qty')
    def onchange_min_qty(self):
        for line in self:
            if line.is_task:
                lib_material_qty = [task_mat_line.material_uom_qty for task_mat_line in line.library_task_id.task_material_line]
                cntr = 0
                for material_line in line.task_material_line:
                    try:
                        if line.min_qty > 0 or line.library_task_id.min_qty > 0.0:
                            material_line.material_uom_qty = (line.min_qty * lib_material_qty[cntr]) / line.library_task_id.min_qty
                            cntr = cntr + 1
                    except:
                        pass

                #   Labour Qty Calculation
                lib_material_qty = [task_lbr_line.labour_uom_qty for task_lbr_line in line.library_task_id.task_labour_line]
                cntr = 0
                for labour_line in line.task_labour_line:
                    try:
                        if line.min_qty > 0 or line.library_task_id.min_qty > 0.0:
                            labour_line.labour_uom_qty = (line.min_qty * lib_material_qty[cntr]) / line.library_task_id.min_qty
                            cntr = cntr + 1
                    except:
                        pass

    def create_wbs_task_group(self):
        task_list = []
        for project_task_library_id in self.project_task_library_ids:
            group_obj = self.env['project.task.library'].browse(project_task_library_id.id)
            self.create_group_wbs(group_obj)
            task_list.append((3, project_task_library_id.id, False))

        self.project_task_library_ids = task_list

    def create_group_wbs(self, group_obj, parent_id=None, parent=None, parent_task=None, parent_group=None):
        for obj in group_obj:
            data = {
                'name': obj.name,
                'category_id': obj.category_id.id,
                'sub_category_id': obj.sub_category_id.id,
                'is_task': obj.is_library_task,
                'parent_id': self.id,
                'is_wbs': False,
            }

            if parent and parent_id and parent_group:
                data.update({
                    'parent_group_id': parent_id,
                    'parent_id': parent_id
                })

            if parent and parent_id and parent_task:
                data.update({
                    'parent_task_id': parent_id,
                    'parent_id': parent_id
                })

        task_obj = self.env['project.task'].create(data)

        for material in obj.task_material_line:
            material_data = {
                'material_id': material.material_id.id,
                'material_uom': material.material_uom.id,
                'material_uom_qty': material.material_uom_qty,
                'material_rate': material.material_rate,
                'material_line_id': task_obj.id,
                'group_id': parent_id,
                'task_category': obj.category_id.id,
                'wbs_id': self.id,
            }
            self.env['task.material.line'].create(material_data)

        for labour in obj.task_labour_line:
            labour_data = {
                'labour_id': labour.labour_id.id,
                'labour_uom': labour.labour_uom.id,
                'labour_uom_qty': labour.labour_uom_qty,
                'labour_rate': labour.labour_rate,
                'labour_line_id': task_obj.id,
                'parent_id': self.id,
                'group_id': parent_id,
                'task_category': obj.category_id.id,
                'wbs_id': self.id,
            }
            self.env['task.labour.line'].create(labour_data)

        # Recursively create subgroup and sub-task
        for sub_group_obj in obj.group_ids:
            self.create_group_wbs(sub_group_obj, task_obj.id, parent=True, parent_group=True)

        for sub_task_obj in obj.task_ids:
            self.create_group_wbs(sub_task_obj, task_obj.id, parent=True, parent_task=True)

    @api.model
    def default_get(self, fields_list):
        category_list = []
        stage_id = self.env['stage.master'].search([('approved', '=', True)])
        budget_obj = self.env['category.budget'].search([('project_id', '=', self._context.get('default_project_id')),
                                                         ('sub_project', '=', self._context.get('default_sub_project')), ('project_wbs', '=', self._context.get('wbs'))])

        for line in budget_obj.category_line_ids:
            if line.stage_id == stage_id:
                category_list.append(line.task_category.id)

        return super(Task, self).default_get(fields_list)

    @api.depends('task_ids', 'group_ids')
    def compute_child(self):
        for task in self:
            child_ids = []
            for child_task in task.task_ids:
                child_ids.append((4, child_task.id))
            for child_task in task.group_ids:
                child_ids.append((4, child_task.id))
            for wbs in task.wbs_task_ids:
                child_ids.append((4, wbs.id))

            if child_ids:
                task.child_ids2 = child_ids

    def print_cost_var_report(self):
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'project.task',
            'form': data
        }
        values = self.env.ref('pragtech_ppc.groupwise_cost_variance_report_id').report_action(self, data=datas)

        return values


class TaskEstimate(models.Model):
    _name = 'task.estimate'
    _description = 'Task Estimate'

    task_no = fields.Many2one('project.task.library', 'Task')
    task_type = fields.Selection([('group', 'Task Group'), ('task', 'Task')], 'Task Type')
    task_status = fields.Selection([('unstarted', 'Unstarted'), ('started', 'Started'), ('completed', 'Completed')], 'Task Status')
    unit_no = fields.Many2one('uom.uom', 'Unit')
    days_required = fields.Integer('Days Required', default=1)
    days_worked = fields.Integer('Days Worked', default=1)
    quantity = fields.Integer('Quantity')
    completed_qty = fields.Integer('Completed Quantity')
    category_id = fields.Many2one('task.category', 'Category')
    sub_category_id = fields.Many2one('task.sub.category', 'Sub Category')

    @api.onchange('category_id')
    def onchange_category_id(self):
        return {'domain': {'sub_category_id': [('category_id', '=', self.category_id.id)]}}


class WBSTaskGroup(models.Model):
    _name = 'wbs.task.group'
    _description = 'WBS Task Group'

    name = fields.Char('Group Title', track_visibility='onchange', size=128, required=True, select=True)
    date_start = fields.Datetime('Starting Date', select=True, copy=False, store=True, compute='_get_start_date')
    date_end = fields.Datetime('Ending Date', select=True, copy=False, store=True, compute='_get_end_date')
    project_wbs_id = fields.Many2one('project.wbs', string='Project')
    task_id = fields.Many2many('project.task', 'task_project_rel1', 'task_wbs_id', 'project_wbs_id')

    @api.depends('task_id', 'task_id.date_assign')
    def _get_start_date(self):
        # Set Minimum date_start
        if self.task_id:
            vals = [task.date_assign for task in self.task_id]
            self.date_start = min(vals) if vals else None

    @api.depends('task_id', 'task_id.date_end')
    def _get_end_date(self):
        # Set Maximum date_end
        if self.task_id:
            vals = [task.date_end for task in self.task_id]
            self.date_end = max(vals) if vals else None
