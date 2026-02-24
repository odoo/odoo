# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProjectTaskLibrary(models.Model):
    _name = 'project.task.library'
    _description = 'Project Task Library'

    name = fields.Char('Task Title', required=True)
    user_id = fields.Many2one('res.users', 'Assigned to')
    is_library_task = fields.Boolean('Library Task')
    category_id = fields.Many2one('task.category', 'Category')
    sub_category_id = fields.Many2one('task.sub.category', 'Sub Category')
    material_cost = fields.Float(compute='_calculate_material_cost', default='0.0', string='Material Cost', method=True)
    min_qty = fields.Integer('Minimum Qty', required=True)
    labour_cost = fields.Float(compute="calculate_labour_cost", string="Labour Cost", method=True)
    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')
    parent_task_id = fields.Many2one('project.task.library', 'Parent Group')
    parent_group_id = fields.Many2one('project.task.library', 'Parent Group')
    parent_id = fields.Many2one('project.task.library', string="Parent", help="Hierarchy Purpose.")
    task_ids = fields.One2many('project.task.library', 'parent_task_id', 'Tasks')
    group_ids = fields.One2many('project.task.library', 'parent_group_id', 'Group')
    child_ids2 = fields.One2many('project.task.library', 'parent_id', compute='compute_child', store=True)
    task_material_line = fields.One2many('material.library', 'task_library_id', string='Task Material Lines')
    task_labour_line = fields.One2many('labour.library', 'task_library_id', string='Task labour Lines')
    uom_id = fields.Many2one('uom.uom', 'Unit', required=True)
    total_cost = fields.Float(compute='_get_total_cost', string='Total Cost', help='Sum of material cost and labour cost', method=True)

    def _get_total_cost(self):
        for this in self:
            this.total_cost = sum([line.subtotal for line in this.task_material_line]) + sum([line.subtotal for line in this.task_labour_line])

    @api.onchange('category_id')
    def onchange_category_id(self):
        return {
            'domain': {
                'sub_category_id': [('category_id', '=', self.category_id.id)]
            }
        }

    def _calculate_material_cost(self):
        for line in self:
            total_material_cost = 0.0
            if line.task_material_line:
                for lines in line.task_material_line:
                    total_material_cost += lines.material_uom_qty * lines.material_rate

                line.material_cost = total_material_cost
            else:
                self.material_cost = total_material_cost

    def calculate_labour_cost(self):
        for line in self:
            total_labour_cost = 0.0
            if line.task_labour_line:
                for lines in line.task_labour_line:
                    total_labour_cost += lines.labour_uom_qty * lines.labour_rate

                line.labour_cost = total_labour_cost
            else:
                self.labour_cost = total_labour_cost

    @api.depends('task_ids', 'group_ids')
    def compute_child(self):
        for task in self:
            child_ids = []
            for child_task in task.task_ids:
                child_ids.append((4, child_task.id))

            for child_task in task.group_ids:
                child_ids.append((4, child_task.id))

            if child_ids:
                task.child_ids2 = child_ids

