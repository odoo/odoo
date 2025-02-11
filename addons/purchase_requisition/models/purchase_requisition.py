# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict


PURCHASE_REQUISITION_STATES = [
    ('draft', 'Draft'),
    ('ongoing', 'Ongoing'),
    ('in_progress', 'Confirmed'),
    ('open', 'Bid Selection'),
    ('done', 'Closed'),
    ('cancel', 'Cancelled')
]


class PurchaseRequisitionType(models.Model):
    _name = "purchase.requisition.type"
    _description = "Purchase Requisition Type"
    _order = "sequence"

    name = fields.Char(string='Agreement Type', required=True, translate=True)
    sequence = fields.Integer(default=1)
    exclusive = fields.Selection([
        ('exclusive', 'Select only one RFQ (exclusive)'), ('multiple', 'Select multiple RFQ (non-exclusive)')],
        string='Agreement Selection Type', required=True, default='multiple',
            help="""Select only one RFQ (exclusive):  when a purchase order is confirmed, cancel the remaining purchase order.\n
                    Select multiple RFQ (non-exclusive): allows multiple purchase orders. On confirmation of a purchase order it does not cancel the remaining orders""")
    quantity_copy = fields.Selection([
        ('copy', 'Use quantities of agreement'), ('none', 'Set quantities manually')],
        string='Quantities', required=True, default='none')
    line_copy = fields.Selection([
        ('copy', 'Use lines of agreement'), ('none', 'Do not create RfQ lines automatically')],
        string='Lines', required=True, default='copy')
    active = fields.Boolean(default=True, help="Set active to false to hide the Purchase Agreement Types without removing it.")


class PurchaseRequisition(models.Model):
    _name = "purchase.requisition"
    _description = "Purchase Requisition"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    def _get_type_id(self):
        return self.env['purchase.requisition.type'].search([], limit=1)

    name = fields.Char(string='Reference', required=True, copy=False, default='New', readonly=True)
    origin = fields.Char(string='Source Document')
    order_count = fields.Integer(compute='_compute_orders_number', string='Number of Orders')
    vendor_id = fields.Many2one('res.partner', string="Vendor", check_company=True)
    type_id = fields.Many2one('purchase.requisition.type', string="Agreement Type", required=True, default=_get_type_id)
    ordering_date = fields.Date(string="Ordering Date", tracking=True)
    date_end = fields.Datetime(string='Agreement Deadline', tracking=True)
    schedule_date = fields.Date(string='Delivery Date', index=True, help="The expected and scheduled delivery date where all the products are received", tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Purchase Representative',
        default=lambda self: self.env.user, check_company=True)
    description = fields.Html()
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    purchase_ids = fields.One2many('purchase.order', 'requisition_id', string='Purchase Orders')
    line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string='Products to Purchase', copy=True)
    product_id = fields.Many2one('product.product', related='line_ids.product_id', string='Product')
    state = fields.Selection(PURCHASE_REQUISITION_STATES,
                              'Status', tracking=True, required=True,
                              copy=False, default='draft')
    state_blanket_order = fields.Selection(PURCHASE_REQUISITION_STATES, compute='_set_state')
    is_quantity_copy = fields.Selection(related='type_id.quantity_copy', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)

    @api.depends('state')
    def _set_state(self):
        for requisition in self:
            requisition.state_blanket_order = requisition.state

    @api.onchange('vendor_id')
    def _onchange_vendor(self):
        self = self.with_company(self.company_id)
        if not self.vendor_id:
            self.currency_id = self.env.company.currency_id.id
        else:
            self.currency_id = self.vendor_id.property_purchase_currency_id.id or self.env.company.currency_id.id

        requisitions = self.env['purchase.requisition'].search([
            ('vendor_id', '=', self.vendor_id.id),
            ('state', '=', 'ongoing'),
            ('type_id.quantity_copy', '=', 'none'),
            ('company_id', '=', self.company_id.id),
        ])
        if any(requisitions):
            title = _("Warning for %s", self.vendor_id.name)
            message = _("There is already an open blanket order for this supplier. We suggest you complete this open blanket order, instead of creating a new one.")
            warning = {
                'title': title,
                'message': message
            }
            return {'warning': warning}

    @api.depends('purchase_ids')
    def _compute_orders_number(self):
        for requisition in self:
            requisition.order_count = len(requisition.purchase_ids)

    def action_cancel(self):
        # try to set all associated quotations to cancel state
        for requisition in self:
            for requisition_line in requisition.line_ids:
                requisition_line.supplier_info_ids.sudo().unlink()
            requisition.purchase_ids.button_cancel()
            for po in requisition.purchase_ids:
                po.message_post(body=_('Cancelled by the agreement associated to this quotation.'))
        self.write({'state': 'cancel'})

    def action_in_progress(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("You cannot confirm agreement '%s' because there is no product line.", self.name))
        if self.type_id.quantity_copy == 'none' and self.vendor_id:
            for requisition_line in self.line_ids:
                if requisition_line.price_unit <= 0.0:
                    raise UserError(_('You cannot confirm the blanket order without price.'))
                if requisition_line.product_qty <= 0.0:
                    raise UserError(_('You cannot confirm the blanket order without quantity.'))
                requisition_line.create_supplier_info()
            self.write({'state': 'ongoing'})
        else:
            self.write({'state': 'in_progress'})
        # Set the sequence number regarding the requisition type
        if self.name == 'New':
            self.name = self.env['ir.sequence'].with_company(self.company_id).next_by_code('purchase.requisition.blanket.order')

    def action_open(self):
        self.write({'state': 'open'})

    def action_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_done(self):
        """
        Generate all purchase order based on selected lines, should only be called on one agreement at a time
        """
        if any(purchase_order.state in ['draft', 'sent', 'to approve'] for purchase_order in self.mapped('purchase_ids')):
            raise UserError(_("To close this purchase requisition, cancel related Requests for Quotation.\n\n"
                "Imagine the mess if someone confirms these duplicates: double the order, double the trouble :)"))
        for requisition in self:
            for requisition_line in requisition.line_ids:
                requisition_line.supplier_info_ids.sudo().unlink()
        self.write({'state': 'done'})

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(requisition.state not in ('draft', 'cancel') for requisition in self):
            raise UserError(_('You can only delete draft or cancelled requisitions.'))

    def unlink(self):
        # Draft requisitions could have some requisition lines.
        self.mapped('line_ids').unlink()
        return super(PurchaseRequisition, self).unlink()


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _inherit = 'analytic.mixin'
    _description = "Purchase Requisition Line"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        compute='_compute_product_uom_id', store=True, readonly=False, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure')
    product_description_variants = fields.Char('Custom Description')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    qty_ordered = fields.Float(compute='_compute_ordered_qty', string='Ordered Quantities')
    requisition_id = fields.Many2one('purchase.requisition', required=True, string='Purchase Agreement', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='requisition_id.company_id', string='Company', store=True, readonly=True)
    schedule_date = fields.Date(string='Scheduled Date')
    supplier_info_ids = fields.One2many('product.supplierinfo', 'purchase_requisition_line_id')

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            if line.requisition_id.state not in ['draft', 'cancel', 'done'] and line.requisition_id.is_quantity_copy == 'none':
                supplier_infos = self.env['product.supplierinfo'].search([
                    ('product_id', '=', vals.get('product_id')),
                    ('partner_id', '=', line.requisition_id.vendor_id.id),
                ])
                if not any(s.purchase_requisition_id for s in supplier_infos):
                    line.create_supplier_info()
                if vals['price_unit'] <= 0.0:
                    raise UserError(_('You cannot confirm the blanket order without price.'))
        return lines

    def write(self, vals):
        res = super(PurchaseRequisitionLine, self).write(vals)
        if 'price_unit' in vals:
            if vals['price_unit'] <= 0.0 and any(
                    requisition.state not in ['draft', 'cancel', 'done'] and
                    requisition.is_quantity_copy == 'none' for requisition in self.mapped('requisition_id')):
                raise UserError(_('You cannot confirm the blanket order without price.'))
            # If the price is updated, we have to update the related SupplierInfo
            self.supplier_info_ids.write({'price': vals['price_unit']})
        return res

    def unlink(self):
        to_unlink = self.filtered(lambda r: r.requisition_id.state not in ['draft', 'cancel', 'done'])
        to_unlink.mapped('supplier_info_ids').unlink()
        return super(PurchaseRequisitionLine, self).unlink()

    def create_supplier_info(self):
        purchase_requisition = self.requisition_id
        if purchase_requisition.type_id.quantity_copy == 'none' and purchase_requisition.vendor_id:
            # create a supplier_info only in case of blanket order
            self.env['product.supplierinfo'].sudo().create({
                'partner_id': purchase_requisition.vendor_id.id,
                'product_id': self.product_id.id,
                'product_tmpl_id': self.product_id.product_tmpl_id.id,
                'price': self.price_unit,
                'currency_id': self.requisition_id.currency_id.id,
                'purchase_requisition_line_id': self.id,
            })

    @api.depends('requisition_id.purchase_ids.state')
    def _compute_ordered_qty(self):
        line_found = defaultdict(set)
        for line in self:
            total = 0.0
            for po in line.requisition_id.purchase_ids.filtered(lambda purchase_order: purchase_order.state in ['purchase', 'done']):
                for po_line in po.order_line.filtered(lambda order_line: order_line.product_id == line.product_id):
                    if po_line.product_uom != line.product_uom_id:
                        total += po_line.product_uom._compute_quantity(po_line.product_qty, line.product_uom_id)
                    else:
                        total += po_line.product_qty
            if line.product_id not in line_found[line.requisition_id]:
                line.qty_ordered = total
                line_found[line.requisition_id].add(line.product_id)
            else:
                line.qty_ordered = 0

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id
            self.product_qty = 1.0
        if not self.schedule_date:
            self.schedule_date = self.requisition_id.schedule_date

    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        self.ensure_one()
        requisition = self.requisition_id
        if self.product_description_variants:
            name += '\n' + self.product_description_variants
        if requisition.schedule_date:
            date_planned = datetime.combine(requisition.schedule_date, time.min)
        else:
            date_planned = datetime.now()
        return {
            'name': name,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_po_id.id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'taxes_id': [(6, 0, taxes_ids)],
            'date_planned': date_planned,
            'analytic_distribution': self.analytic_distribution,
        }
