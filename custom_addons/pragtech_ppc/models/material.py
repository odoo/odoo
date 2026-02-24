# -*- coding: utf-8 -*-

from odoo import fields, models, api


class Brand(models.Model):
    _name = 'brand.brand'
    _description = 'Brand'

    name = fields.Char('Name', required=True)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    material_id = fields.Many2one('product.template', 'Material')


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Template'

    material_class = fields.Selection([('A', 'A'), ('B', 'B'), ('C', 'C')], string='Class')
    eoq = fields.Integer('Economic Order Quantity')
    brand_ids = fields.One2many('brand.brand', 'material_id', 'Brand')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    life = fields.Float('Life')
    inspection_required = fields.Boolean('Inspection Required')
    qa_certificate_required = fields.Boolean('QA Certificate Required')
    qa_procedure_id = fields.Many2one('qa.procedure', string='QA Procedure')
    is_hazardous = fields.Boolean('Is Hazardous')
    po_lead_time = fields.Integer('PO Lead Time')
    supplier_lead_time = fields.Integer('Supplier Lead Time')
    total_lead_time = fields.Integer('Total Lead Time')
    tolerance_limit = fields.Float('Tolerance Limit(in %)')
    reorder_quantity = fields.Integer('Re Order Quantity')
    conversion_uom_ids = fields.One2many('conversion.uom', 'prod_uom_id', 'Conversion Factor')


class QaProcedure(models.Model):
    _name = 'qa.procedure'
    _description = 'Qa Procedure'

    name = fields.Char('Name', required=True)
    description = fields.Text('Remark/Description')


class ConversionUom(models.Model):
    _name = 'conversion.uom'
    _description = 'Conversion Uom'

    conversion_factor = fields.Float('Conversion Factor Value')
    from_uom_id = fields.Many2one('uom.uom', 'From Unit of Measures')
    to_uom_id = fields.Many2one('uom.uom', 'To Unit of Measures')
    prod_uom_id = fields.Many2one('product.template', 'Product uom ID')


class TaskMaterialLine(models.Model):
    _name = 'task.material.line'
    _description = 'Task Material Line'

    name = fields.Char('Material Estimation No')
    material_id = fields.Many2one('product.product', 'Material', required=True)
    material_uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    material_uom_qty = fields.Float(string='Quantity', default=1.0)
    material_rate = fields.Float(string='Rate', default=1.0)
    sub_total = fields.Float('Subtotal', compute='_compute_subtotal', store=True)
    material_estimation_total = fields.Float('Total', compute='_compute_total')
    material_line_id = fields.Many2one('project.task', string='Project Task')
    wbs_id = fields.Many2one('project.task', string='WBS')
    group_id = fields.Many2one('project.task', related='material_line_id.parent_task_id', store=True, string='Group')
    material_category = fields.Many2one('product.category', related='material_id.categ_id', store=True, string='Material Category')
    task_category = fields.Many2one('task.category', related='material_line_id.category_id', store=True, string='Task Category')
    planned_start_date = fields.Datetime(string='Planned Start Date', related='material_line_id.planed_start_date', store=True)
    planned_finish_date = fields.Datetime(string='Planned Finish Date', related='material_line_id.planned_finish_date', store=True)
    actual_start_date = fields.Date(string='Actual Finish Date', related='material_line_id.actual_start_date', store=True)
    actual_finish_date = fields.Date(string='Actual Finish Date', related='material_line_id.actual_finish_date', store=True)
    sequence = fields.Char()
    requisition_till_date = fields.Float('Requisition Till Date')
    balanced_requisition = fields.Float('Balanced Requisition', compute='get_balance_requisition', store=True)

    @api.depends('material_uom_qty', 'requisition_till_date')
    def get_balance_requisition(self):
        for rec in self:
            rec.balanced_requisition = rec.material_uom_qty - rec.requisition_till_date

    @api.depends('material_uom_qty', 'material_rate')
    def _compute_subtotal(self):
        sub_total = 0
        for line in self:
            sub_total = line.material_rate * line.material_uom_qty
            line.update({
                'sub_total': sub_total,
            })

    @api.depends('sub_total')
    def _compute_total(self):
        total = 0
        for line in self:
            total = total + line.sub_total
            sub_total = line.material_rate * line.material_uom_qty
            line.update({
                'total': total,
            })

    @api.onchange('material_id')
    def _onchange_material_id(self):
        if self.material_id:
            self.update({
                'material_uom': self.material_id.uom_id,
                'material_rate': self.material_id.standard_price
            })

    def get_wbs_parent(self, task_obj):
        if task_obj.parent_task_id:
            return self.get_wbs_parent(task_obj.parent_id)

        if not task_obj.parent_task_id:
            return task_obj.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            project_task_obj = self.env['project.task'].browse(vals.get('material_line_id'))
            wbs_id = self.get_wbs_parent(project_task_obj)
            vals.update({'wbs_id': wbs_id})
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('task.material.line') or '/'

            return super(TaskMaterialLine, self).create(vals_list)

    def write(self, vals):
        res = super(TaskMaterialLine, self).write(vals)
        self.material_line_id.project_wbs_id = self.wbs_id
        self.group_id.project_wbs_id = self.wbs_id
        return res


class MaterialLibrary(models.Model):
    _name = 'material.library'
    _description = 'Material Library'

    material_line_id = fields.Many2one('project.task', string='Project Task')
    task_library_id = fields.Many2one('project.task.library', string='Project Library Task')
    material_id = fields.Many2one('product.product', string='Material', required=True)
    material_uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    material_uom_qty = fields.Float(string='Quantity', default=1.0)
    material_rate = fields.Float(string='Rate', default=1.0)
    subtotal = fields.Float(string='Subtotal', compute='compute_subtotal', store=True)

    @api.depends('material_uom_qty', 'material_rate')
    def compute_subtotal(self):
        for this in self:
            this.subtotal = this.material_uom_qty * this.material_rate

    @api.onchange('material_id')
    def _onchange_material_id(self):
        if self.material_id:
            self.update({
                'material_uom': self.material_id.uom_id,
                'material_rate': self.material_id.standard_price
            })


class MaterialEstimate(models.Model):
    _name = 'material.estimate'
    _description = 'Material Estimate'

    name = fields.Many2one('product.product', 'Name')
    quantity = fields.Integer('Quantity')
    unit_name = fields.Many2one('uom.uom', 'Unit', required=True)
    rate = fields.Float('Rate')
    project_wbs_id = fields.Many2one('project.task')
    group_name = fields.Char('Group')
    task_id = fields.Many2one('project.task', 'Task')
    group_ids = fields.Many2one('project.task', 'Group')
    project_task_id = fields.Many2one('project.task')

    material_category = fields.Many2one('product.category', related='name.categ_id', store=True)
    task_category = fields.Many2one('task.category', related='task_id.category_id', store=True)
    date_start = fields.Datetime(related='task_id.date_assign', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['sequence'] = self.env['ir.sequence'].next_by_code('material.estimate') or '/'

            return super(MaterialEstimate, self).create(vals_list)

