# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class PurchaseRequisitionType(models.Model):
    _name = "purchase.requisition.type"
    _description = "Purchase Agreement Type"
    _order = "sequence"

    name = fields.Char(string='Agreement Type', required=True, translate=True)
    sequence = fields.Integer(default=1)
    exclusive = fields.Selection([
        ('exclusive', 'Select only one RFQ (exclusive)'), ('multiple', 'Select multiple RFQ')],
        string='Agreement Selection Type', required=True, default='multiple',
            help="""Select only one RFQ (exclusive):  when a purchase order is confirmed, cancel the remaining purchase order.\n
                    Select multiple RFQ: allows multiple purchase orders. On confirmation of a purchase order it does not cancel the remaining orders""")
    quantity_copy = fields.Selection([
        ('copy', 'Use quantities of agreement'), ('none', 'Set quantities manually')],
        string='Quantities', required=True, default='none')
    line_copy = fields.Selection([
        ('copy', 'Use lines of agreement'), ('none', 'Do not create RfQ lines automatically')],
        string='Lines', required=True, default='copy')


class PurchaseRequisition(models.Model):
    _name = "purchase.requisition"
    _description = "Purchase Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = "id desc"

    def _get_picking_in(self):
        return self.env.ref('stock.picking_type_in')

    def _get_type_id(self):
        return self.env['purchase.requisition.type'].search([], limit=1)

    name = fields.Char(string='Agreement Reference', required=True, copy=False, default= lambda self: self.env['ir.sequence'].next_by_code('purchase.order.requisition'))
    origin = fields.Char(string='Source Document')
    order_count = fields.Integer(compute='_compute_orders_number', string='Number of Orders')
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    type_id = fields.Many2one('purchase.requisition.type', string="Agreement Type", required=True, default=_get_type_id)
    ordering_date = fields.Date(string="Ordering Date")
    date_end = fields.Datetime(string='Agreement Deadline')
    schedule_date = fields.Date(string='Delivery Date', index=True, help="The expected and scheduled delivery date where all the products are received")
    user_id = fields.Many2one('res.users', string='Responsible', default= lambda self: self.env.user)
    description = fields.Text()
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('purchase.requisition'))
    purchase_ids = fields.One2many('purchase.order', 'requisition_id', string='Purchase Orders', states={'done': [('readonly', True)]})
    line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string='Products to Purchase', states={'done': [('readonly', True)]}, copy=True)
    procurement_id = fields.Many2one('procurement.order', string='Procurement', ondelete='set null', copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'Confirmed'),
                               ('open', 'Bid Selection'), ('done', 'Done'),
                               ('cancel', 'Cancelled')],
                              'Status', track_visibility='onchange', required=True,
                              copy=False, default='draft')
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', required=True, default=_get_picking_in)

    @api.multi
    @api.depends('purchase_ids')
    def _compute_orders_number(self):
        for requisition in self:
            requisition.order_count = len(requisition.purchase_ids)

    @api.multi
    def action_cancel(self):
        # try to set all associated quotations to cancel state
        for requisition in self:
            requisition.purchase_ids.button_cancel()
            for po in requisition.purchase_ids:
                po.message_post(body=_('Cancelled by the agreement associated to this quotation.'))
        self.write({'state': 'cancel'})

    @api.multi
    def action_in_progress(self):
        if not all(obj.line_ids for obj in self):
            raise UserError(_('You cannot confirm call because there is no product line.'))
        self.write({'state': 'in_progress'})

    @api.multi
    def action_open(self):
        self.write({'state': 'open'})

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})

    @api.multi
    def action_done(self):
        """
        Generate all purchase order based on selected lines, should only be called on one agreement at a time
        """
        if any(purchase_order.state in ['draft', 'sent', 'to approve'] for purchase_order in self.mapped('purchase_ids')):
            raise UserError(_('You have to cancel or validate every RfQ before closing the purchase requisition.'))
        self.write({'state': 'done'})


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _description = "Purchase Requisition Line"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], required=True)
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure')
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'))
    price_unit = fields.Float(string='Unit Price', digits=dp.get_precision('Product Price'))
    qty_ordered = fields.Float(compute='_compute_ordered_qty', string='Ordered Quantities')
    requisition_id = fields.Many2one('purchase.requisition', string='Purchase Agreement', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='requisition_id.company_id', string='Company', store=True, readonly=True, default= lambda self: self.env['res.company']._company_default_get('purchase.requisition.line'))
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    schedule_date = fields.Date(string='Scheduled Date')

    @api.multi
    @api.depends('requisition_id.purchase_ids.state')
    def _compute_ordered_qty(self):
        for line in self:
            total = 0.0
            for po in line.requisition_id.purchase_ids.filtered(lambda purchase_order: purchase_order.state in ['purchase', 'done']):
                for po_line in po.order_line.filtered(lambda order_line: order_line.product_id == line.product_id):
                    if po_line.product_uom != line.product_uom_id:
                        total += po_line.product_uom._compute_quantity(po_line.product_qty, line.product_uom_id)
                    else:
                        total += po_line.product_qty
            line.qty_ordered = total

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            self.product_qty = 1.0
        if not self.account_analytic_id:
            self.account_analytic_id = self.requisition_id.account_analytic_id
        if not self.schedule_date:
            self.schedule_date = self.requisition_id.schedule_date


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    requisition_id = fields.Many2one('purchase.requisition', string='Purchase Agreement', copy=False)

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        if not self.requisition_id:
            return

        requisition = self.requisition_id
        if self.partner_id:
            partner = self.partner_id
        else:
            partner = requisition.vendor_id
        payment_term = partner.property_supplier_payment_term_id
        currency = partner.property_purchase_currency_id or requisition.company_id.currency_id

        FiscalPosition = self.env['account.fiscal.position']
        fpos = FiscalPosition.get_fiscal_position(partner.id)
        fpos = FiscalPosition.browse(fpos)

        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id,
        self.company_id = requisition.company_id.id
        self.currency_id = currency.id
        self.origin = requisition.name
        self.partner_ref = requisition.name # to control vendor bill based on agreement reference
        self.notes = requisition.description
        self.date_order = requisition.date_end or fields.Datetime.now()
        self.picking_type_id = requisition.picking_type_id.id

        if requisition.type_id.line_copy != 'copy':
            return

        # Create PO lines if necessary
        order_lines = []
        for line in requisition.line_ids:
            # Compute name
            product_lang = line.product_id.with_context({
                'lang': partner.lang,
                'partner_id': partner.id,
            })
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            # Compute taxes
            if fpos:
                taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id))
            else:
                taxes_ids = line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id).ids

            # Compute quantity and price_unit
            if line.product_uom_id != line.product_id.uom_po_id:
                product_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_po_id)
                price_unit = line.product_uom_id._compute_price(line.price_unit, line.product_id.uom_po_id)
            else:
                product_qty = line.product_qty
                price_unit = line.price_unit

            if requisition.type_id.quantity_copy != 'copy':
                product_qty = 0

            # Compute price_unit in appropriate currency
            if requisition.company_id.currency_id != currency:
                price_unit = requisition.company_id.currency_id.compute(price_unit, currency)

            # Create PO line
            order_lines.append((0, 0, {
                'name': name,
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_po_id.id,
                'product_qty': product_qty,
                'price_unit': price_unit,
                'taxes_id': [(6, 0, taxes_ids)],
                'date_planned': requisition.schedule_date or fields.Date.today(),
                'procurement_ids': [(6, 0, [requisition.procurement_id.id])] if requisition.procurement_id else False,
                'account_analytic_id': line.account_analytic_id.id,
            }))
        self.order_line = order_lines

    @api.multi
    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for po in self:
            if po.requisition_id.type_id.exclusive == 'exclusive':
                others_po = po.requisition_id.mapped('purchase_ids').filtered(lambda r: r.id != po.id)
                others_po.button_cancel()
                po.requisition_id.action_done()

            for element in po.order_line:
                if element.product_id == po.requisition_id.procurement_id.product_id:
                    element.move_ids.write({
                        'procurement_id': po.requisition_id.procurement_id.id,
                        'move_dest_id': po.requisition_id.procurement_id.move_dest_id.id,
                    })
        return res

    @api.model
    def create(self, vals):
        purchase = super(PurchaseOrder, self).create(vals)
        if purchase.requisition_id:
            purchase.message_post_with_view('mail.message_origin_link',
                    values={'self': purchase, 'origin': purchase.requisition_id},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'))
        return purchase

    @api.multi
    def write(self, vals):
        result = super(PurchaseOrder, self).write(vals)
        if vals.get('requisition_id'):
            self.message_post_with_view('mail.message_origin_link',
                    values={'self': self, 'origin': self.requisition_id, 'edit': True},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'))
        return result


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        res = super(PurchaseOrderLine, self)._onchange_quantity()
        if self.order_id.requisition_id:
            for line in self.order_id.requisition_id.line_ids:
                if line.product_id == self.product_id:
                    if line.product_uom_id != self.product_uom:
                        self.price_unit = self.env['product.uom']._compute_price(
                            line.product_uom_id.id, line.price_unit, to_uom_id=self.product_uom.id)
                    else:
                        self.price_unit = line.price_unit
                    break
        return res


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchase_requisition = fields.Selection(
        [('rfq', 'Create a draft purchase order'),
         ('tenders', 'Propose a call for tenders')],
        string='Procurement', default='rfq')


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    requisition_id = fields.Many2one('purchase.requisition', string='Latest Requisition')

    @api.multi
    def make_po(self):
        Requisition = self.env['purchase.requisition']
        procurements = self.env['procurement.order']
        Warehouse = self.env['stock.warehouse']
        res = []
        for procurement in self:
            if procurement.product_id.purchase_requisition == 'tenders':
                warehouse_id = Warehouse.search([('company_id', '=', procurement.company_id.id)], limit=1).id
                requisition_id = Requisition.create({
                    'origin': procurement.origin,
                    'date_end': procurement.date_planned,
                    'warehouse_id': warehouse_id,
                    'company_id': procurement.company_id.id,
                    'procurement_id': procurement.id,
                    'picking_type_id': procurement.rule_id.picking_type_id.id,
                    'line_ids': [(0, 0, {
                        'product_id': procurement.product_id.id,
                        'product_uom_id': procurement.product_uom.id,
                        'product_qty': procurement.product_qty
                    })],
                })
                procurement.message_post(body=_("Purchase Requisition created"))
                requisition_id.message_post_with_view('mail.message_origin_link',
                    values={'self': requisition_id, 'origin': procurement},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'))
                procurement.requisition_id = requisition_id
                procurements += procurement
                res += [procurement.id]
        set_others = self - procurements
        if set_others:
            res += super(ProcurementOrder, set_others).make_po()
        return res
