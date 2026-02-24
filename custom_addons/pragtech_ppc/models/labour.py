# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import models, fields, api
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class LabourMaster(models.Model):
    _name = 'labour.master'
    _description = 'Labour Master'

    name = fields.Char('Name', required=True)
    account_tag_ids = fields.Many2many(string="Account Tags", comodel_name='account.account.tag', help="Tags to be set on the base and tax journal items created for this product.")
    category_id = fields.Many2one('labour.category', 'Labour Category', required=True)
    sub_category_id = fields.Many2one('labour.sub.category', 'Labour Sub Category')
    work_class_id = fields.Many2one('labour.work.classification', 'Labour Work Class')
    type = fields.Selection([('labour', 'Labour'), ('group', 'Labour Group')], 'Type')
    rate = fields.Float('Rate', required=True)
    unit_no = fields.Many2one('uom.uom', 'Unit', required=True)
    is_labour = fields.Boolean('Labour', defualt=True)
    parent_labour_id = fields.Many2one('labour.master', 'Labour')
    parent_group_id = fields.Many2one('labour.master', 'Labour Group')
    parent_id = fields.Many2one('labour.master', 'Parent')
    labour_ids = fields.One2many('labour.master', 'parent_labour_id')
    labour_group_ids = fields.One2many('labour.master', 'parent_group_id', domain=[('is_labour', '=', False)])
    child_ids2 = fields.One2many('labour.master', 'parent_id')

    Requisition_as_on_date = fields.Float('Requisition as on date')
    current_req_qty = fields.Float('Current Requisition Qty')
    contractor_ids = fields.One2many('labour.contractorinfo', 'labour_id')

    @api.onchange('category_id')
    def onchange_category_id(self):
        return {
            'domain': {'sub_category_id': [('category_id', '=', self.category_id.id)]}
        }

    @api.depends('labour_ids', 'labour_group_ids')
    def compute_child(self):
        for labour in self:
            if 'odoo.api.' not in str(type(labour)):
                child_ids = []
                for child_task in labour.labour_ids:
                    child_ids.append((4, child_task.id))
                for child_task in labour.labour_group_ids:
                    child_ids.append((4, child_task.id))
                if child_ids:
                    labour.child_ids2 = child_ids

    def compute_labour(self):
        return True

    def some_action(self):
        for line in self:
            if self.labour_ids:
                rate = 0.0
                for lines in line.labour_ids:
                    rate += lines.rate

                line.write({
                    'rate': rate,
                    'type_no': 0.0
                })


class LabourWorkClassification(models.Model):
    _name = 'labour.work.classification'
    description = 'Labour Work Classification'

    name = fields.Char('Name', required=True)


class LabourRateMaster(models.Model):
    _name = 'labour.rate.master'
    _description = 'Labour Rate Master'

    name = fields.Char('Name', required=True)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    date = fields.Date('Creation Date', default=fields.date.today())
    user = fields.Many2one('res.users', 'Created By User', default=lambda self: self.env.user)


class TaskLabourLine(models.Model):
    _name = 'task.labour.line'
    _description = 'Task Labour Line'

    name = fields.Char('Labour Estimation No')
    labour_id = fields.Many2one('labour.master', string='Labour', required=True)
    labour_uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    labour_uom_qty = fields.Float(string='Quantity', default=1.0)
    labour_rate = fields.Float(string='Rate', default=1.0)
    sub_total = fields.Float('Subtotal', compute='_compute_subtotal', store=True)
    labour_estimation_total = fields.Float('Total', compute='_compute_total')

    labour_line_id = fields.Many2one('project.task', string='Project Task')
    wbs_id = fields.Many2one('project.task', string='WBS')
    sub_project = fields.Many2one('sub.project', 'Sub Project')
    sequence = fields.Char()
    sub_total = fields.Float('Subtotal', compute='_compute_subtotal', store=True)
    # Temporary Added
    group_id = fields.Many2one('project.task', related='labour_line_id.parent_task_id', store=True, string='Group')
    labour_category = fields.Many2one('labour.category', related='labour_id.category_id', store=True, string='Labour Category')
    task_category = fields.Many2one('task.category', related='labour_line_id.category_id', store=True, string='Task Category')
    date_start = fields.Datetime(string='Start Date', related='labour_line_id.date_assign', store=True)

    planned_start_date = fields.Datetime(string='Planned Start Date', related='labour_line_id.planed_start_date', store=True)
    planned_finish_date = fields.Datetime(string='Planned Finish Date', related='labour_line_id.planned_finish_date', store=True)
    actual_start_date = fields.Date(string='Actual Finish Date', related='labour_line_id.actual_start_date', store=True)
    actual_finish_date = fields.Date(string='Actual Finish Date', related='labour_line_id.actual_finish_date', store=True)

    requisition_till_date = fields.Float('Requisition Till Date')
    balanced_requisition = fields.Float('Balanced Requisition', compute='get_balance_requisition', store=True)

    @api.depends('labour_uom_qty', 'requisition_till_date')
    def get_balance_requisition(self):
        for record in self:
            record.balanced_requisition = record.labour_uom_qty - record.requisition_till_date

    @api.depends('labour_uom_qty', 'labour_rate')
    def _compute_subtotal(self):
        sub_total = 0
        for line in self:
            sub_total = line.labour_rate * line.labour_uom_qty
            line.update({
                'sub_total': sub_total,
            })
            line.sub_total = sub_total

    @api.onchange('labour_id')
    def _onchange_labour_id(self):
        if self.labour_id:
            self.update({
                'labour_uom': self.labour_id.unit_no.id,
                'labour_rate': self.labour_id.rate
            })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('task.labour.line') or '/'

            res = super(TaskLabourLine, self).create(vals_list)

            return res

    def write(self, vals):
        res = super(TaskLabourLine, self).write(vals)
        self.labour_line_id.project_wbs_id = self.wbs_id
        self.group_id.project_wbs_id = self.wbs_id

        return res


class LabourLibrary(models.Model):
    _name = 'labour.library'
    _description = 'Labour Library'

    task_library_id = fields.Many2one('project.task.library', string='Project Library Task')
    labour_id = fields.Many2one('labour.master', string='Labour', required=True)
    labour_uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    labour_uom_qty = fields.Float(string='Quantity', default=1.0)
    labour_rate = fields.Float(string='Rate', default=1.0)
    subtotal = fields.Float(string='Subtotal', compute='compute_subtotal', store=True)

    @api.depends('labour_uom_qty', 'labour_rate')
    def compute_subtotal(self):
        for this in self:
            this.subtotal = this.labour_uom_qty * this.labour_rate

    @api.onchange('labour_id')
    def _onchange_labour_id(self):
        if self.labour_id:
            self.update({
                'labour_uom': self.labour_id.unit_no.id,
                'labour_rate': self.labour_id.rate
            })


class LabourEstimate(models.Model):
    _name = 'labour.estimate'
    _description = 'Labour Estimate'

    labour_id = fields.Many2one('labour.master', 'Name')
    quantity = fields.Integer('Quantity')
    product_uom = fields.Many2one('uom.uom', string='Unit')
    rate = fields.Float('Rate')
    project_wbs_id = fields.Many2one('project.task', string='Project')
    task_id = fields.Many2one('project.task', 'Task')
    group_id = fields.Many2one('project.task', 'Group')
    group_name = fields.Char('Group')
    labour_category = fields.Many2one('labour.category', related='labour_id.category_id', store=True)
    task_category = fields.Many2one('task.category', related='task_id.category_id', store=True)
    date_start = fields.Datetime(related='task_id.date_assign', store=True)


class LabourRequisition(models.Model):
    _name = 'labour.requisition'
    _inherit = ['mail.thread']
    _description = 'Labour Requisition'

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    name = fields.Char('Name')
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
    total_approved_qty = fields.Float('Approved Qty', readonly=True)
    total_ordered_qty = fields.Float('Ordered Qty', readonly=True)
    balance_qty = fields.Float('Balance Qty', compute='get_balanced_quantity', help="Current requisition qty-Total ordered qty")
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    priority = fields.Selection([('high', 'High'), ('low', 'Low')], 'Priority')
    brand_id = fields.Many2one('brand.brand', 'Brand')
    requisition_type = fields.Selection([('estimated', 'Estimated'), ('non_estimated', 'Non Estimated')], 'Type')
    unit = fields.Many2one('uom.uom', 'UOM')
    rate = fields.Float('Rate')
    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage)
    procurement_type = fields.Selection([('New Purchase from Supplier', 'New Purchase from Supplier'),
                                         ('Cash Purchase ', 'Cash Purchase '), ('IST from other sites', 'IST from other sites'), ], "Procurement Type")
    warehouse_id = fields.Char('Procurement Type', readonly=True)
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

    counter = 0
    flag = fields.Boolean('')

    @api.depends('current_req_qty', 'total_ordered_qty')
    def get_balanced_quantity(self):
        for this in self:
            this.balance_qty = this.current_req_qty - this.total_ordered_qty

    def change_state(self, fields={}):
        if self.counter == 0:
            self.counter = self.counter + 1

            """ Updating Requisition till date in estimation table """
            if fields.get('copy') == True:
                requisition_till_date = self.estimation_id.requisition_till_date + self.current_req_qty
                if requisition_till_date <= self.estimation_id.labour_uom_qty:
                    self.estimation_id.requisition_till_date = self.estimation_id.requisition_till_date + self.current_req_qty
                    self.name = self.env['ir.sequence'].next_by_code('labour.requisition') or '/'
                    self.flag = 1
                else:
                    self.flag = 0
                    raise UserError(_('Sorry you cannot approve requisition greater then available quantity!'))

            view_id = self.env.ref('pragtech_ppc.approval_wizard_form_view').id

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


class LabourRequisitionLine(models.Model):
    _name = 'labour.requisition.line'
    _inherit = ['mail.thread']
    _description = 'Labour Requisition Line'

    name = fields.Char('Requisition No')
    group_id = fields.Many2one('project.task', 'Group')
    task_id = fields.Many2one('project.task', 'Task')
    flag = fields.Boolean('Flag', default=False)
    partner_id = fields.Many2one('res.partner', string='Contractor', required=True, change_default=True, track_visibility='always')
    requisition_date = fields.Date('Date', default=fields.date.today(), required=True)
    requirement_date = fields.Date('Requirement Date')
    procurement_date = fields.Date('Procurement Date')
    quantity = fields.Integer('Quantity')
    specification = fields.Char('Specification')
    remark = fields.Char('Remark')
    total_approved_qty = fields.Float('Approved Qty', readonly=True)
    total_ordered_qty = fields.Float('Ordered Qty', readonly=True)
    balance_qty = fields.Float('Balance Qty')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    priority = fields.Selection([('high', 'High'), ('low', 'Low')], 'Priority')
    brand_id = fields.Many2one('brand.brand', 'Brand')
    requisition_type = fields.Selection([('estimated', 'Estimated'), ('non_estimated', 'Non Estimated')], 'Type')
    order_id = fields.Many2one('labour.requisition', 'Labour Requisition')
    unit = fields.Many2one('uom.uom', 'UOM')
    rate = fields.Float('Rate')
    procurement_type = fields.Selection([('New Purchase from Supplier', 'New Purchase from Supplier'),
                                         ('Cash Purchase ', 'Cash Purchase '), ('IST from other sites', 'IST from other sites'), ], 'Procurement Type')
    warehouse_id = fields.Char('Procurement Type', readonly=True)
    requisition_fulfill = fields.Boolean('Req fulfill')
    stage_id = fields.Many2one('transaction.stage', string='Transaction Stage', domain=[('model', '=', 'labour.requisition.line')], readonly=True)
    work_class = fields.Many2one('labour.work.classification', 'Work Class')
    labour_id = fields.Many2one('labour.master', 'Labour')

    def change_state(self):
        view_id = self.env.ref('pragtech_ppc.approval_wizard_form_view').id
        return {
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'res_model': 'approval.wizard',
            'multi': 'True',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

    @api.onchange('stage_id')
    @api.depends('stage_id.approved')
    def onchange_stage(self):
        if self.stage_id.approved:
            self.flag = True


class LabourQuotation(models.Model):
    _name = 'labour.quotation'
    _description = 'Labour Quotation'

    @api.model
    def _default_stage(self):
        st_id = self.env['stage.master'].search([('draft', '=', True)])
        if st_id:
            return st_id.id

    def change_state(self, context={}):
        if context.get('copy') == True:
            self.write({'state': 'confirm'})
        else:
            view_id = self.env.ref('pragtech_ppc.approval_wizard_form_view').id
            return {
                'type': 'ir.actions.act_window',
                'key2': 'client_action_multi',
                'res_model': 'approval.wizard',
                'multi': 'True',
                'target': 'new',
                'views': [[view_id, 'form']],
            }

    name = fields.Char('Order Reference', required=True, select=True, copy=False, default='New')
    origin = fields.Char('Source Document', copy=False,
                         help='Reference of the document that generated this purchase order request (e.g. a sale order or an internal procurement request)')

    date_order = fields.Datetime('Quotation Date', required=True, select=True, copy=False, default=fields.Datetime.now(),
                                 help='Depicts the date where the Quotation should be validated and converted into a purchase order.')
    partner_id = fields.Many2one('res.partner', string='Contractor', required=True, change_default=True, track_visibility='always')
    partner_ref = fields.Char('Vendor Reference', copy=False, help="Reference of the sales order or bid sent by the vendor."
                                                                   "It's used to do the matching when you receive the"
                                                                   "products as this reference is usually written on the"
                                                                   "delivery order sent by your vendor.")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')],
                             string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    order_line = fields.One2many('labour.quotation.line', 'order_id', string='Order Lines', copy=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    valid_till = fields.Datetime('Valid Till')
    transport_amount = fields.Float('Transport Amount')
    loading_charges = fields.Float('Loading Charges')
    unloading_charges = fields.Float('Unloading Charges')
    other_charges = fields.Float('Other Charges')
    company_id = fields.Many2one('res.company', 'Company', readonly=True, index=1, default=lambda self: self.env.user.company_id.id)
    use_in_quotation = fields.Boolean('Use In Quotation')
    delivery_schedule = fields.Datetime(string='Delivery Schedule')
    host_name = fields.Char(string='Host Name')
    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage, readonly=True, track_visibility='onchange')
    flag = fields.Boolean('Flag', default=False)
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('labour.quotation') or '/'

            existing_stage = []
            st_id = self.env['stage.master'].search([('draft', '=', True)])
            msg_ids = {
                'date': datetime.now(),
                'from_stage': None,
                'to_stage': st_id.id,
                'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                'model': 'labour.quotation'
            }
            existing_stage.append((0, 0, msg_ids))
            vals.update({'mesge_ids': existing_stage})

            return super(LabourQuotation, self).create(vals_list)

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax

            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    def _taxed_amount(self):
        return 1


class LabourQuotationLine(models.Model):
    _name = 'labour.quotation.line'
    _description = 'Labour Quotation Line'

    name = fields.Text(string='Description')
    labour_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1)
    date_planned = fields.Datetime(string='Scheduled Date', select=True)
    taxes_id = fields.Many2many('account.tax', 'labour_quot_line_tax_rel', 'labour_quot_line_id', 'tax_id', string='Taxes')
    labour_uom = fields.Many2one('uom.uom', string='Units', required=True)
    labour_id = fields.Many2one('labour.master', string='Labour', required=True)
    labour_category = fields.Many2one('labour.category', string='Labour Category', required=True)
    price_unit = fields.Float(string='Rate', required=True, digits=dp.get_precision('Product Price'))
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Discounted Rate', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Tax', store=True)

    work_class = fields.Many2one('labour.work.classification', 'Work Class')
    order_id = fields.Many2one('labour.quotation', string='Order Reference', select=True, required=True, ondelete='cascade')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', domain=[('account_type', '=', 'normal')])
    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True, readonly=True)
    state = fields.Selection(related='order_id.state', stored=True, string='State')
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Partner', readonly=True, store=True)
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
    currency_rate = fields.Float('Currency Rate')
    date_order = fields.Datetime(related='order_id.date_order', string='Order Date', readonly=True)
    brand_id = fields.Many2one('brand.brand', 'Brand')
    negotiated_rate = fields.Float('Negotiated Rate')
    credit_period = fields.Integer('Credit Period')
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    vat_per = fields.Float('Vat(%)')
    vat_on_per = fields.Float('Vat on (%)')
    st_per = fields.Float('ST(%)')
    st_on_per = fields.Float('ST on (%)')
    retention = fields.Float('Retention(%)')
    payment_schedule = fields.Many2one('payment.schedule.template', 'Payment Schedule')

    taxed_amount = fields.Monetary(string='Taxed Amount', store=True, readonly=True, compute='_compute_amount')
    basic_amount = fields.Monetary(string='Basic Amount', store=True, readonly=True, compute='_compute_amount')
    net_rate = fields.Monetary(string='Net Rate', store=True, compute='_compute_amount')

    @api.onchange('labour_category')
    def onchange_labour_category(self):
        return {
            'domain': {'labour_id': [('category_id', '=', self.labour_category.id)]}
        }

    @api.onchange('labour_id')
    def onchange_labour_id(self):
        result = {}
        if not self.labour_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.labour_id.rate
        self.labour_uom = self.labour_id.unit_no
        self.work_class = self.labour_id.work_class_id.id

    @api.depends('labour_qty', 'discount', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        # Compute the amounts of the VQ line.
        for line in self:
            tax_amount = 0
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.labour_qty, product=line.labour_id, partner=line.order_id.partner_id)
            for tax in taxes['taxes']:
                tax_amount = tax_amount + tax['amount']

            basic_amount = line.price_unit * line.labour_qty
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'taxed_amount': tax_amount,
                'basic_amount': basic_amount,
                'net_rate': taxes['total_excluded'] + tax_amount,
            })


class LabourSupplierInfo(models.Model):
    _name = 'labour.contractorinfo'
    _description = 'Labour Contractor Info'

    name = fields.Many2one('res.partner', 'Contractor', required=True, ondelete='cascade', help="contractor of this product")
    product_name = fields.Char('Contractor Product Name')
    date = fields.Datetime('Date', default=datetime.now())
    delay = fields.Integer('Delivery Lead Time')

    min_qty = fields.Float('Minimal Quantity', required=True,
                           help="The minimal quantity to purchase from this Contractor, expressed in the Contractor  Unit of Measure if not any, in the default unit of measure otherwise.")
    price = fields.Float('Price', required=True)
    is_active = fields.Boolean('Active')
    unit = fields.Many2one('uom.uom', 'UOM')
    labour_id = fields.Many2one('labour.master', 'Labour')
    labour_category = fields.Many2one('labour.category', related='labour_id.category_id', store=True, string='Labour Category')

