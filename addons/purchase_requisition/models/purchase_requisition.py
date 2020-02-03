# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


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
    _inherit = ['mail.thread']
    _order = "id desc"

    def _get_picking_in(self):
        pick_in = self.env.ref('stock.picking_type_in', raise_if_not_found=False)
        company = self.env['res.company']._company_default_get('purchase.requisition')
        if not pick_in or pick_in.sudo().warehouse_id.company_id.id != company.id:
            pick_in = self.env['stock.picking.type'].search(
                [('warehouse_id.company_id', '=', company.id), ('code', '=', 'incoming')],
                limit=1,
            )
        return pick_in

    def _get_type_id(self):
        return self.env['purchase.requisition.type'].search([], limit=1)

    name = fields.Char(string='Agreement Reference', required=True, copy=False, default='New', readonly=True)
    origin = fields.Char(string='Source Document')
    order_count = fields.Integer(compute='_compute_orders_number', string='Number of Orders')
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    type_id = fields.Many2one('purchase.requisition.type', string="Agreement Type", required=True, default=_get_type_id)
    ordering_date = fields.Date(string="Ordering Date", track_visibility='onchange')
    date_end = fields.Datetime(string='Agreement Deadline', track_visibility='onchange')
    schedule_date = fields.Date(string='Delivery Date', index=True, help="The expected and scheduled delivery date where all the products are received", track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='Purchase Representative', default= lambda self: self.env.user)
    description = fields.Text()
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('purchase.requisition'))
    purchase_ids = fields.One2many('purchase.order', 'requisition_id', string='Purchase Orders', states={'done': [('readonly', True)]})
    line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string='Products to Purchase', states={'done': [('readonly', True)]}, copy=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    state = fields.Selection(PURCHASE_REQUISITION_STATES,
                              'Status', track_visibility='onchange', required=True,
                              copy=False, default='draft')
    state_blanket_order = fields.Selection(PURCHASE_REQUISITION_STATES, compute='_set_state')
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', required=True, default=_get_picking_in)
    is_quantity_copy = fields.Selection(related='type_id.quantity_copy', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id.id)

    @api.depends('state')
    def _set_state(self):
        self.state_blanket_order = self.state

    @api.onchange('vendor_id')
    def _onchange_vendor(self):
        if not self.vendor_id:
            self.currency_id = self.env.user.company_id.currency_id.id
        else:
            self.currency_id = self.vendor_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id

        requisitions = self.env['purchase.requisition'].search([
            ('vendor_id', '=', self.vendor_id.id),
            ('state', '=', 'ongoing'),
            ('type_id.quantity_copy', '=', 'none'),
        ])
        if any(requisitions):
            title = _("Warning for %s") % self.vendor_id.name
            message = _("There is already an open blanket order for this supplier. We suggest you to use to complete this open blanket order instead of creating a new one.")
            warning = {
                'title': title,
                'message': message
            }
            return {'warning': warning}

    @api.multi
    @api.depends('purchase_ids')
    def _compute_orders_number(self):
        for requisition in self:
            requisition.order_count = len(requisition.purchase_ids)

    @api.multi
    def action_cancel(self):
        # try to set all associated quotations to cancel state
        for requisition in self:
            for requisition_line in requisition.line_ids:
                requisition_line.supplier_info_ids.unlink()
            requisition.purchase_ids.button_cancel()
            for po in requisition.purchase_ids:
                po.message_post(body=_('Cancelled by the agreement associated to this quotation.'))
        self.write({'state': 'cancel'})

    @api.multi
    def action_in_progress(self):
        self.ensure_one()
        if not all(obj.line_ids for obj in self):
            raise UserError(_("You cannot confirm agreement '%s' because there is no product line.") % self.name)
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
            if self.is_quantity_copy != 'none':
                self.name = self.env['ir.sequence'].next_by_code('purchase.requisition.purchase.tender')
            else:
                self.name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order')

    @api.multi
    def action_open(self):
        self.write({'state': 'open'})

    def action_draft(self):
        self.ensure_one()
        self.name = 'New'
        self.write({'state': 'draft'})

    @api.multi
    def action_done(self):
        """
        Generate all purchase order based on selected lines, should only be called on one agreement at a time
        """
        if any(purchase_order.state in ['draft', 'sent', 'to approve'] for purchase_order in self.mapped('purchase_ids')):
            raise UserError(_('You have to cancel or validate every RfQ before closing the purchase requisition.'))
        for requisition in self:
            for requisition_line in requisition.line_ids:
                requisition_line.supplier_info_ids.unlink()
        self.write({'state': 'done'})

    def _prepare_tender_values(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        return{
            'origin': origin,
            'date_end': values['date_planned'],
            'warehouse_id': values.get('warehouse_id') and values['warehouse_id'].id or False,
            'company_id': values['company_id'].id,
            'line_ids': [(0, 0, {
                'product_id': product_id.id,
                'product_uom_id': product_uom.id,
                'product_qty': product_qty,
                'move_dest_id': values.get('move_dest_ids') and values['move_dest_ids'][0].id or False,
            })],
        }

    def unlink(self):
        if any(requisition.state not in ('draft', 'cancel') for requisition in self):
            raise UserError(_('You can only delete draft requisitions.'))
        # Draft requisitions could have some requisition lines.
        self.mapped('line_ids').unlink()
        return super(PurchaseRequisition, self).unlink()

class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"
    _order = 'sequence, purchase_requisition_id desc, min_qty desc, price'

    purchase_requisition_id = fields.Many2one('purchase.requisition', related='purchase_requisition_line_id.requisition_id', string='Blanket order', readonly=False)
    purchase_requisition_line_id = fields.Many2one('purchase.requisition.line')


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _description = "Purchase Requisition Line"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Product Unit of Measure')
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'))
    price_unit = fields.Float(string='Unit Price', digits=dp.get_precision('Product Price'))
    qty_ordered = fields.Float(compute='_compute_ordered_qty', string='Ordered Quantities')
    requisition_id = fields.Many2one('purchase.requisition', required=True, string='Purchase Agreement', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='requisition_id.company_id', string='Company', store=True, readonly=True, default= lambda self: self.env['res.company']._company_default_get('purchase.requisition.line'))
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    schedule_date = fields.Date(string='Scheduled Date')
    move_dest_id = fields.Many2one('stock.move', 'Downstream Move')
    supplier_info_ids = fields.One2many('product.supplierinfo', 'purchase_requisition_line_id')

    @api.model
    def create(self,vals):
        res = super(PurchaseRequisitionLine, self).create(vals)
        if res.requisition_id.state not in ['draft', 'cancel', 'done'] and res.requisition_id.is_quantity_copy == 'none':
            supplier_infos = self.env['product.supplierinfo'].search([
                ('product_id', '=', vals.get('product_id')),
                ('name', '=', res.requisition_id.vendor_id.id),
            ])
            if not any([s.purchase_requisition_id for s in supplier_infos]):
                res.create_supplier_info()
            if vals['price_unit'] <= 0.0:
                raise UserError(_('You cannot confirm the blanket order without price.'))
        return res

    @api.multi
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
            self.env['product.supplierinfo'].create({
                'name': purchase_requisition.vendor_id.id,
                'product_id': self.product_id.id,
                'product_tmpl_id': self.product_id.product_tmpl_id.id,
                'price': self.price_unit,
                'currency_id': self.requisition_id.currency_id.id,
                'purchase_requisition_id': purchase_requisition.id,
                'purchase_requisition_line_id': self.id,
            })

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
            self.product_uom_id = self.product_id.uom_po_id
            self.product_qty = 1.0
        if not self.schedule_date:
            self.schedule_date = self.requisition_id.schedule_date

    @api.multi
    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        self.ensure_one()
        requisition = self.requisition_id
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
            'account_analytic_id': self.account_analytic_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'move_dest_ids': self.move_dest_id and [(4, self.move_dest_id.id)] or []
        }


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    requisition_id = fields.Many2one('purchase.requisition', string='Purchase Agreement', copy=False)
    is_quantity_copy = fields.Selection(related='requisition_id.is_quantity_copy', readonly=False)

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

        FiscalPosition = self.env['account.fiscal.position']
        fpos = FiscalPosition.get_fiscal_position(partner.id)
        fpos = FiscalPosition.browse(fpos)

        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id
        self.company_id = requisition.company_id.id
        self.currency_id = requisition.currency_id.id
        if not self.origin or requisition.name not in self.origin.split(', '):
            if self.origin:
                if requisition.name:
                    self.origin = self.origin + ', ' + requisition.name
            else:
                self.origin = requisition.name
        self.notes = requisition.description
        self.date_order = fields.Datetime.now()
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
                taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id)).ids
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

            # Create PO line
            order_line_values = line._prepare_purchase_order_line(
                name=name, product_qty=product_qty, price_unit=price_unit,
                taxes_ids=taxes_ids)
            order_lines.append((0, 0, order_line_values))
        self.order_line = order_lines

    @api.multi
    def button_approve(self, force=False):
        res = super(PurchaseOrder, self).button_approve(force=force)
        for po in self:
            if not po.requisition_id:
                continue
            if po.requisition_id.type_id.exclusive == 'exclusive':
                others_po = po.requisition_id.mapped('purchase_ids').filtered(lambda r: r.id != po.id)
                others_po.button_cancel()
                po.requisition_id.action_done()
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
            for line in self.order_id.requisition_id.line_ids.filtered(lambda l: l.product_id == self.product_id):
                if line.product_uom_id != self.product_uom:
                    self.price_unit = line.product_uom_id._compute_price(
                        line.price_unit, self.product_uom)
                else:
                    self.price_unit = line.price_unit
                break
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _prepare_sellers(self, params):
        sellers = super(ProductProduct, self)._prepare_sellers(params)
        if params and params.get('order_id'):
            return sellers.filtered(lambda s: not s.purchase_requisition_id or s.purchase_requisition_id == params['order_id'].requisition_id)
        else:
            return sellers


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchase_requisition = fields.Selection(
        [('rfq', 'Create a draft purchase order'),
         ('tenders', 'Propose a call for tenders')],
        string='Procurement', default='rfq',
        help="Create a draft purchase order: Based on your product configuration, the system will create a draft "
             "purchase order.Propose a call for tender : If the 'purchase_requisition' module is installed and this option "
             "is selected, the system will create a draft call for tender.")


class StockMove(models.Model):
    _inherit = "stock.move"

    requistion_line_ids = fields.One2many('purchase.requisition.line', 'move_dest_id')


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _get_exceptions_domain(self):
        return super(ProcurementGroup, self)._get_exceptions_domain() + [('requistion_line_ids', '=', False)]


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        if product_id.purchase_requisition != 'tenders':
            return super(StockRule, self)._run_buy(product_id, product_qty, product_uom, location_id, name, origin, values)
        values = self.env['purchase.requisition']._prepare_tender_values(product_id, product_qty, product_uom, location_id, name, origin, values)
        values['picking_type_id'] = self.picking_type_id.id
        self.env['purchase.requisition'].create(values)
        return True

    def _prepare_purchase_order(self, product_id, product_qty, product_uom, origin, values, partner):
        res = super(StockRule, self)._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner)
        res['partner_ref'] = values['supplier'].purchase_requisition_id.name
        res['requisition_id'] = values['supplier'].purchase_requisition_id.id
        if values['supplier'].purchase_requisition_id.currency_id:
            res['currency_id'] = values['supplier'].purchase_requisition_id.currency_id.id
        return res

    def _make_po_get_domain(self, values, partner):
        domain = super(StockRule, self)._make_po_get_domain(values, partner)
        if 'supplier' in values and values['supplier'].purchase_requisition_id:
            domain += (
                ('requisition_id', '=', values['supplier'].purchase_requisition_id.id),
            )
        return domain


class StockMove(models.Model):
    _inherit = 'stock.move'

    requisition_line_ids = fields.One2many('purchase.requisition.line', 'move_dest_id')

    def _get_upstream_documents_and_responsibles(self, visited):
        if self.requisition_line_ids:
            return [(requisition_line.requisition_id, requisition_line.requisition_id.user_id, visited) for requisition_line in self.requisition_line_ids if requisition_line.requisition_id.state not in ('done', 'cancel')]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)


class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _quantity_in_progress(self):
        res = super(Orderpoint, self)._quantity_in_progress()
        for op in self:
            for pr in self.env['purchase.requisition'].search([('state','=','draft'),('origin','=',op.name)]):
                for prline in pr.line_ids.filtered(lambda l: l.product_id.id == op.product_id.id):
                    res[op.id] += prline.product_uom_id._compute_quantity(prline.product_qty, op.product_uom, round=False)
        return res
