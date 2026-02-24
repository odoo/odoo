# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import odoo.addons.decimal_precision as dp


class WorkOrderTypes(models.Model):
    _name = 'work.order.types'
    _description = 'Work Order Types'

    name = fields.Char('Work Order Type', required=True)
    remark = fields.Text(string='Remark')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')


class WorkOrder(models.Model):
    _name = 'work.order'
    _description = 'Work Order'

    counter = fields.Integer('counter')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('work.order') or '/'
                seq_obj = self.env['ir.sequence'].search([('code', '=', 'work.order.revision')])
                seq_obj.number_next_actual = 1

            existing_stage = []
            st_id = self.env['stage.master'].search([('draft', '=', True)])
            msg_ids = {
                'date': datetime.now(),
                'from_stage': None,
                'to_stage': st_id.id,
                'remark': 'Created by ' + (self.env['res.users'].browse(self._context.get('uid'))).name,
                'model': 'work.order'
            }
            if vals.get('partner_id'):
                partner = vals.get('partner_id')
                p_id = self.env['res.partner'].browse(partner)
                if p_id.contractor_status == 'trial':
                    if p_id.trial_allowed <= p_id.trial_used:
                        raise UserError(_('Contractor Trial period has expired cannot create work orders.'))

            existing_stage.append((0, 0, msg_ids))
            vals.update({'mesge_ids': existing_stage})

            res = super(WorkOrder, self).create(vals_list)
            if self.order_line:
                for line in self.order_line:
                    if line.amount_to_release != 100:
                        raise UserError(_('Cumulative percentage should be 100.'))

                line.task_id.is_billable = 1

            return res

    def write(self, vals):
        if vals.get('partner_id'):
            partner = vals.get('partner_id')
            p_id = self.env['res.partner'].browse(partner)
            if p_id.contractor_status == 'trial':
                if p_id.trial_allowed <= p_id.trial_used:
                    raise UserError(_('Contractor Trial period has expired cannot create work orders.'))

        if vals.get('wo_requisition_line'):
            for i in vals.get('wo_requisition_line'):
                wo_req_obj = self.env['wo.requisition'].browse(i[1])
                work_order_obj = self.env['work.order'].browse(wo_req_obj.order_id.id)
                stage_master_obj = self.env['stage.master'].search([('amend_and_draft', '=', True)], limit=1)
                if work_order_obj.stage_id.approved:
                    vals.update({
                        'stage_id': stage_master_obj.id,
                        'flag': False,
                        'state': 'draft'
                    })

                if type(i[2]) is dict and i[2].get('current_order_qty'):
                    if i[2].get('current_order_qty') > wo_req_obj.requisition_qty:
                        raise UserError(_('Order quantity is greater than requisition quantity.'))

        res = super(WorkOrder, self).write(vals)
        for line in self.order_line:
            total = 0
            if line:
                for payment in line.payment_schedule_line_ids:
                    total = total + payment.amount_to_release

                if total != 100:
                    raise UserError(_('Cumulative percentage should be 100.'))

            line.task_id.is_billable = 1

        return res

    @api.model
    def _default_stage(self):
        st_ids = self.env['stage.master'].search([('draft', '=', True)])
        if st_ids:
            for st_id in st_ids:
                return st_id.id

    def change_state(self, context={}):
        if self.counter == 0:
            self.counter = self.counter + 1
            self.write({'state': 'confirm'})
            if context.get('copy') == True:
                self.write({'state': 'confirm'})
                """ Assigning work order line no while final approval """
                """ Updating ordered quantity in requisitions """
                for line in self.wo_requisition_line:
                    if line.requisition_id.total_ordered_qty + line.current_order_qty <= line.requisition_id.current_req_qty:
                        line.requisition_id.total_ordered_qty = line.requisition_id.total_ordered_qty + line.current_order_qty
                    else:
                        raise UserError(_('Sorry!! You cannot approve this WO.'))

                for line in self.order_line:
                    line.wo_line_no = self.env['ir.sequence'].next_by_code('work.order.line')

            # To check order line is not empty
            if not self.order_line:
                raise UserError(_('You Must select labour first!'))

                # Checks Budget
                budget_obj = self.env['category.budget'].search([('project_id', '=', self.project_id.id), ('sub_project', '=', self.sub_project.id), ('project_wbs', '=', self.project_wbs.id)])
                for budget_line in budget_obj.category_line_ids:
                    if budget_line.stage_id.approved == True:
                        total = 0
                        for po_line in self.order_line:
                            if po_line.category_id.id == budget_line.task_category.id:
                                total = (po_line.rate * po_line.quantity) + total

                        if total > budget_line.labourbudget_remaining:
                            raise UserError(_('Insufficient Budget.'))
                        else:
                            budget_line.labourbudget_used = budget_line.labourbudget_used + total

            flag = 0
            for purchase_line in self.order_line:
                if purchase_line.quantity == 0:
                    flag = 1
                    break
                else:
                    flag = 0

            if flag:
                raise UserError(_("You haven't set processed quantities."))
            else:
                view_id = self.env.ref('pragtech_contracting.approval_wizard_form_view_contracting').id
                return {
                    'type': 'ir.actions.act_window',
                    'key2': 'client_action_multi',
                    'res_model': 'approval.wizard',
                    'multi': 'True',
                    'target': 'new',
                    'views': [[view_id, 'form']],
                }

    def _get_count(self):
        transaction = self.env['transaction.transaction']
        transaction_obj = transaction.search([('work_order_id', '=', self.id), ('flag', '=', True)])
        count = 0
        for line in transaction_obj:
            count = count + 1

        self.transaction_count = count

    name = fields.Char('Order Reference', required=True, index=True, copy=False, default='New')
    project_wbs = fields.Many2one('project.task', 'Project WBS Name', domain=[('is_wbs', '=', True), ('is_task', '=', False)], required=True)
    labour_category = fields.Many2many('labour.category', 'wo_category_rel', 'work_order_id', 'category_id', string='Labour Category')
    labour = fields.Many2one('labour.master', 'Labour')
    from_date = fields.Date('From', default=str(datetime.now() + timedelta(days=-30)).split(' ')[0])
    to_date = fields.Date('To Date', default=str(fields.date.today()).split(' ')[0])
    partner_id = fields.Many2one('res.partner', string='Contractor', required=True, change_default=True)
    partner_ref = fields.Char('Vendor Reference', copy=False, help="Reference of the sales order or bid sent by the vendor. "
                                                                   "It's used to do the matching when you receive the "
                                                                   "products as this reference is usually written on the "
                                                                   "delivery order sent by your vendor.")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)
    date_order = fields.Datetime('Order Date', required=True, index=True, copy=False, default=fields.Datetime.now())
    valid_till = fields.Datetime('Valid Till')
    sub_project = fields.Many2one('sub.project', 'Sub Project', required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, change_default=True)
    sr_no = fields.Integer('Sr.No')
    is_approved = fields.Boolean('Is Approved')
    material_amount = fields.Float('Material Amount')
    commencement_date = fields.Datetime('Commencement Date')
    completion_date = fields.Datetime('Completion Date')
    maximum_advance = fields.Float('Maximum Advance(%)')
    title = fields.Char('Title')
    tds_account = fields.Many2one('account.analytic.account', string='TDS Account')
    wo_type = fields.Many2one('work.order.types', 'Type')
    wct_account = fields.Many2one('account.analytic.account', string='WCT Account')
    wct_percent = fields.Float('WCT(%)')
    order_line = fields.One2many('work.order.line', 'order_id', string='Order Lines', copy=True, ondelete='cascade', domain=[('quantity', '>', 0)])
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, compute='amount_all')
    amount_tax = fields.Monetary(string='Taxes', store=True, compute='amount_all')
    amount_total = fields.Monetary(string='Total', store=True, compute='amount_all')
    billed_amount = fields.Float('Billed Amount')

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], string='Status', copy=False, index=True, track_visibility='onchange', default='draft')
    stage_id = fields.Many2one('stage.master', 'Stage', default=_default_stage, track_visibility='onchange')
    flag = fields.Boolean('Flag', default=False)
    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)])

    wo_requisition_line = fields.One2many('wo.requisition', 'order_id', string='Requisition Lines')
    revision = fields.Integer('Latest Revision', default='0')
    rev_icrease_flag = fields.Boolean(' ')
    retention = fields.Float('Retention')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=1, default=lambda self: self.env.user.company_id)
    advanced_amount = fields.Float('Advanced Amount')
    debited_amount = fields.Float('Debited Amount')

    task_ids = []
    counter = fields.Float()

    transaction_count = fields.Integer(compute='_get_count', string='# of Transaction')

    retention_held_in_any_bill = fields.Boolean('Retention held?')

    """ Reflects the changes of PO requisition on Purchase Order Lines """

    @api.depends('wo_requisition_line', 'wo_requisition_line.specification', 'wo_requisition_line.current_order_qty')
    def create_order_lines(self, work_order_obj, project_wbs, stage_id):
        old_order_lines = [{'labour_id': line.labour_id.id, 'task_id': line.task_id.id} for line in self.order_line]
        my_list = []
        my_dict = {}
        rate = 0
        for line in self.wo_requisition_line:
            my_dict = {
                'labour_id': line.labour_id.id,
                'task_id': line.task_id.id
            }
            if my_dict not in old_order_lines:
                my_list.append(my_dict)

        for line in my_list:
            lbr_obj = self.env['labour.master'].browse(line.get('labour_id'))

            """ Get rate """
            contractor_price = self.env['labour.contractorinfo'].search([('labour_id', '=', lbr_obj.id), ('name', '=', work_order_obj.partner_id.name), ('is_active', '=', True)])
            if contractor_price:
                rate = contractor_price.price
            else:
                lbr_estimate = self.env['task.labour.line'].search([('labour_line_id', '=', line.get('task_id')), ('labour_id', '=', line.get('labour_id'))], limit=1)
                rate = lbr_estimate.labour_rate

            qty = 0
            specification = ''
            for wo_req in work_order_obj.wo_requisition_line:
                if wo_req.labour_id.id == line.get('labour_id') and wo_req.task_id.id == line.get('task_id'):
                    qty = qty + wo_req.current_order_qty
                    if wo_req.specification:
                        specification = str(specification + ' ' + wo_req.specification)

            line.update({
                'quantity': qty,
                'specification': specification,
                'category_id': lbr_obj.category_id.id,
                'project_wbs': work_order_obj.project_wbs.id,
                'order_id': work_order_obj.id,
                'rate': rate
            })
            task_labour = {
                'labour_id': line.get('labour_id'),
                'task_id': line.get('task_id')
            }
            # if task_labour not in old_order_lines:
            # if adding line after approve then line revision will increase by
            # 1 of the latest rev
            rev = work_order_obj.revision
            if work_order_obj.stage_id.approved:
                stage_master_obj = self.env['stage.master'].search([('amend_and_draft', '=', True)], limit=1)
                self.stage_id = stage_master_obj.id
                rev = work_order_obj.revision
                rev = rev + 1
                work_order_obj.revision = rev
            else:
                rev = work_order_obj.revision

            line.update({'revision': rev})
            if line['labour_id'] not in old_order_lines and line['task_id'] not in old_order_lines:
                res = work_order_obj.order_line.create(line)
                self.update_wo_req(res)

            # if current line (task and labour) is already present in order
            # line then that record will write
            if task_labour in old_order_lines and not self.stage_id.approved:
                qty_final = 0
                specification_final = ""
                for wo_req in self.wo_requisition_line:
                    if wo_req.labour_id.id == task_labour.get('labour_id') and wo_req.task_id.id == task_labour.get('task_id'):
                        qty_final = qty_final + wo_req.current_order_qty
                        if wo_req.specification:
                            specification_final = specification_final + wo_req.specification

                        for order_line in work_order_obj.order_line:
                            if order_line.labour_id.id == task_labour.get('labour_id') and order_line.task_id.id == task_labour.get('task_id'):
                                order_line.write({
                                    'specification': specification_final,
                                    'quantity': qty_final
                                })
                                self.update_wo_req(order_line)

        self.onchange_wo_requisition()

    @api.model
    @api.depends('wo_requisition_line', 'order_line')
    def update_wo_req(self, work_order_obj):
        for wo_req in self.wo_requisition_line:
            if wo_req.labour_id == work_order_obj.labour_id and wo_req.task_id == work_order_obj.task_id:
                res = wo_req.write({
                    'work_order_line_id': work_order_obj.id,
                })

    @api.onchange('wo_requisition_line')
    def onchange_wo_requisition(self):
        for line in self.order_line:
            qty = 0
            specification = ""
            for wo_req in self.wo_requisition_line:
                if line.task_id.id == wo_req.task_id.id and line.labour_id.id == wo_req.labour_id.id:
                    if wo_req.current_order_qty:
                        qty = qty + wo_req.current_order_qty

                    if wo_req.specification:
                        specification = specification + ' ' + str(wo_req.specification)

            line.specification = specification
            line.quantity = qty

    @api.onchange('project_id', 'project_wbs')
    def filter_wbs_material(self):

        project_wbs_lst = []
        labour_list = []
        project_ids = self.env['project.task'].search([('project_id', '=', self.project_id.id)])
        for i in project_ids:
            project_wbs_lst.append(i.name)

        if self.project_wbs:
            project_task_obj = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('name', '=', self.project_wbs.name)])
            for line in project_task_obj.labour_estimate_line:
                labour_list.append(line.labour_id.id)

        return {
            'domain': {
                'material': [('id', 'in', labour_list)]
            }
        }

    @api.depends('order_line.price_total')
    def amount_all(self):
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


class WorkOrderLine(models.Model):
    _name = 'work.order.line'
    _description = 'Work Order Line'

    name = fields.Char('SR.No')
    order_id = fields.Many2one('work.order', string='Order Reference', ondelete='cascade')
    labour_id = fields.Many2one('labour.master', 'Labour', required=True)
    quantity = fields.Integer('Quantity')
    rate = fields.Float('Rate')
    specification = fields.Char('Specification')
    brand_id = fields.Many2one('brand.brand', 'Brand')
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    task_id = fields.Many2one('project.task', 'Task')
    retention = fields.Float(string='Retention (%)')
    work_tax = fields.Many2many('account.tax', 'tax_wo_rel', 'tax_id', 'wo_id', string='Taxes')

    revision = fields.Integer('Revision')
    start_date = fields.Datetime('Start Date')
    completion_date = fields.Datetime('Completion Date')
    original_quantity = fields.Integer('Original Quantity')
    vat_per = fields.Float('Vat(%)')
    vat_on_per = fields.Float('Vat on (%)')
    st_per = fields.Float('ST(%)')
    st_on_per = fields.Float('ST on (%)')
    category_id = fields.Many2one('labour.category', 'Category')
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency')
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Tax', store=True)
    taxed_amount = fields.Monetary(string='Taxed Amount', store=True, compute='_compute_amount')
    basic_amount = fields.Monetary(string='Basic Amount', store=True, compute='_compute_amount')
    net_rate = fields.Monetary(string='Net Rate', store=True, compute='_compute_amount')
    requisition_date = fields.Date('Date')
    material_amount = fields.Float('Material Amount')
    requisition_id = fields.Many2one('labour.requisition', 'Requisition')
    wo_requisition_line_ids = fields.One2many('wo.requisition', 'work_order_line_id', ondelete='cascade')
    payment_schedule_line_ids = fields.One2many('payment.schedule', 'workorder_line_id')
    amount_to_release = fields.Integer('AmountTo Release', compute='get_percent_amount', store=True)
    task_category = fields.Many2one('task.category', 'Task Category', related='task_id.category_id')
    wo_line_no = fields.Char('Sr.No')
    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True)
    project_wbs = fields.Many2one('project.task')

    @api.model
    def default_get(self, fields_list):
        return models.Model.default_get(self, fields_list)

    @api.depends('payment_schedule_line_ids', 'payment_schedule_line_ids.task_id')
    @api.onchange('payment_schedule_line_ids', 'payment_schedule_line_ids.task_id')
    def onchnage_1(self):
        res = None
        for payment in self.payment_schedule_line_ids:
            res = payment.get_task_ids(self._context.get('default_project_wbs'))

    @api.depends('payment_schedule_line_ids.amount_to_release')
    def get_percent_amount(self):
        total = 0
        for line in self.payment_schedule_line_ids:
            total = total + line.amount_to_release
        self.amount_to_release = total
        return total

    def cancel_order(self):
        view_id = self.env.ref('pragtech_contracting.work_order_line_form_to_cancel_req').id
        return {
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'work.order.line',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.onchange('category_id')
    def _onchage_order_line(self):
        category_ids = []
        if not self.order_id:
            return

        part = self.order_id.partner_id
        query = "select category_id from partner_labour_category_rel where partner_id={}".format(part.id)
        self.env.cr.execute(query)

        result = self._cr.fetchall()
        for i in result:
            category_ids.append(i[0])

        return {
            'domain': {'category_id': [('id', 'in', category_ids)]}
        }

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

    def write(self, vals):
        total = 0
        if self:
            for payment in self.payment_schedule_line_ids:
                total = total + payment.amount_to_release

        return super(WorkOrderLine, self).write(vals)


class WORequisition(models.Model):
    _name = 'wo.requisition'
    _description = 'WO Requisition'

    qty_to_cancel = fields.Float('Qty To Cancel')
    group_id = fields.Many2one('project.task', 'Task Group')
    task_id = fields.Many2one('project.task', 'Task')
    labour_id = fields.Many2one('labour.master', 'Labour')
    quantity = fields.Integer('Estimated Quantity')
    specification = fields.Char('Specification')
    remark = fields.Char('Remark')
    estimated_qty = fields.Float('Estimated Qty')
    Requisition_as_on_date = fields.Float('Requisition as on date')
    unit = fields.Many2one('uom.uom', 'UOM', required=True)
    rate = fields.Float('Rate')
    warehouse_id = fields.Char('Procurement Type')
    stage_id = fields.Many2one('transaction.stage', domain=[('model', '=', 'requisition.order.line')])
    project_wbs = fields.Many2one('project.task', 'Project Wbs')
    project_id = fields.Many2one('project.project', 'Project')
    labour_category = fields.Many2one('labour.category', related='labour_id.category_id', store=True, string='Labour Category')
    task_category = fields.Many2one('task.category', related='task_id.category_id', store=True, string='Task Category')
    me_sequence = fields.Char(readonly=True)
    requisition_id = fields.Many2one('labour.requisition', 'Requisition')
    order_id = fields.Many2one('work.order', ondelete="cascade")
    total_ordered_qty = fields.Float('Ordered Qty')
    requisition_qty = fields.Float('Requisition Qty')
    current_order_qty = fields.Float('Current Order Qty')
    is_red = fields.Boolean()
    work_order_line_id = fields.Many2one('work.order.line', 'Work order Line')

    def unlink(self):
        order_line_lst = []
        order_line_obj = self.env['work.order.line'].browse(self.work_order_line_id.id)
        if order_line_obj:
            if order_line_obj.quantity - self.current_order_qty == 0:
                order_line_lst.append((2, order_line_obj.id))
                self.order_id.update({'order_line': order_line_lst})
            else:
                order_line_obj.quantity = order_line_obj.quantity - self.current_order_qty

        return models.Model.unlink(self)

    @api.onchange('current_order_qty')
    def onchnge_order_qty(self):
        if (self.current_order_qty > self.requisition_qty - self.total_ordered_qty):
            raise UserError(_('Order quantity must be less than requisition quantity.'))

