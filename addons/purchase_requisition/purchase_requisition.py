# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from openerp import api, models
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError

class purchase_requisition_type(osv.osv):
    _name = "purchase.requisition.type"
    _description = "Purchase Agreement Type"
    _order = "sequence"
    _columns = {
        'name': fields.char('Agreement Type', required=True, translate=True),
        'sequence': fields.integer('Sequence'),
        'exclusive': fields.selection([
            ('exclusive', 'Select only one RFQ (exclusive)'), ('multiple', 'Select multiple RFQ')],\
            'Agreement Selection Type', required=True,\
            help="""Select only one RFQ (exclusive):  when a purchase order is confirmed, cancel the remaining purchase order.\n
                    Select multiple RFQ: allows multiple purchase orders. On confirmation of a purchase order it does not cancel the remaining orders"""),
        'quantity_copy': fields.selection([
            ('copy', 'Use quantities of agreement'), ('none', 'Set quantities manually')],\
            'Quantities', required=True),
        'line_copy': fields.selection([
            ('copy', 'Use lines of agreement'), ('none', 'Do not create RfQ lines automatically')],\
            'Lines', required=True),
    }
    _defaults = {
        'exclusive': 'multiple',
        'quantity_copy': 'none',
        'line_copy': 'copy',
        'sequence': 1
    }

class purchase_requisition(osv.osv):
    _name = "purchase.requisition"
    _description = "Purchase Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = "id desc"

    def _compute_orders_number(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict.fromkeys(ids, 0)
        for order in self.browse(cr, uid, ids, context=context):
            result[order.id] = len(order.purchase_ids)
        return result

    _columns = {
        'name': fields.char('Agreement Reference', required=True, copy=False),
        'origin': fields.char('Source Document'),
        'order_count': fields.function(_compute_orders_number, 'Number of Orders', type='integer'),
        'vendor_id': fields.many2one('res.partner', string="Vendor"),
        'type_id': fields.many2one('purchase.requisition.type', string="Agreement Type", required=True),
        'ordering_date': fields.date('Ordering Date'),
        'date_end': fields.datetime('Agreement Deadline'),
        'schedule_date': fields.date('Delivery Date', select=True, help="The expected and scheduled delivery date where all the products are received"),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'description': fields.text('Description'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'purchase_ids': fields.one2many('purchase.order', 'requisition_id', 'Purchase Orders', states={'done': [('readonly', True)]}),
        'line_ids': fields.one2many('purchase.requisition.line', 'requisition_id', 'Products to Purchase', states={'done': [('readonly', True)]}, copy=True),
        'procurement_id': fields.many2one('procurement.order', 'Procurement', ondelete='set null', copy=False),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'state': fields.selection([('draft', 'Draft'), ('in_progress', 'Confirmed'),
                                   ('open', 'Bid Selection'), ('done', 'Done'),
                                   ('cancel', 'Cancelled')],
                                  'Status', track_visibility='onchange', required=True,
                                  copy=False),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', required=True),

    }

    def _get_picking_in(self, cr, uid, context=None):
        picking_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'stock.picking_type_in', raise_if_not_found=False)
        if not picking_id:
            company_id = self.pool['res.company']._company_default_get(cr, uid, 'purchase.requisition', context=context)
            picking_id = self.pool['stock.picking.type'].search(
                cr, uid, [('warehouse_id.company_id', '=', company_id), ('code', '=', 'incoming')],
                limit=1, context=context)
            picking_id = picking_id[0] if picking_id else False
        return picking_id

    def _get_type_id(self, cr, uid, context=None):
        types = self.pool.get('purchase.requisition.type').search(cr, uid, [], context=context, limit=1)
        return types[0] if types else False

    _defaults = {
        'state': 'draft',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.requisition', context=c),
        'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id,
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').next_by_code(cr, uid, 'purchase.order.requisition'),
        'type_id': _get_type_id,
        'picking_type_id': _get_picking_in,
    }

    def action_cancel(self, cr, uid, ids, context=None):
        purchase_order_obj = self.pool.get('purchase.order')
        # try to set all associated quotations to cancel state
        for requisition in self.browse(cr, uid, ids, context=context):
            for po in requisition.purchase_ids:
                purchase_order_obj.button_cancel(cr, uid, [po.id], context=context)
                purchase_order_obj.message_post(cr, uid, [po.id], body=_('Cancelled by the agreement associated to this quotation.'), context=context)
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def action_in_progress(self, cr, uid, ids, context=None):
        if not all(obj.line_ids for obj in self.pool['purchase.requisition'].browse(cr, uid, ids, context=context)):
            raise UserError(_('You cannot confirm call because there is no product line.'))
        return self.write(cr, uid, ids, {'state': 'in_progress'}, context=context)

    def action_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def action_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def action_done(self, cr, uid, ids, context=None):
        """
        Generate all purchase order based on selected lines, should only be called on one agreement at a time
        """
        requisitions = self.browse(cr, uid, ids, context=context)
        if requisitions.mapped('purchase_ids') and any(r.state in ['draft', 'sent', 'to approve'] for r in requisitions.mapped('purchase_ids')):
            raise UserError(_('You have to cancel or validate every RfQ before closing the purchase requisition.'))
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)


class purchase_requisition_line(osv.osv):
    _name = "purchase.requisition.line"
    _description = "Purchase Requisition Line"
    _rec_name = 'product_id'

    def _compute_ordered_qty(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict.fromkeys(ids, 0)
        for line in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for po in line.requisition_id.purchase_ids.filtered(lambda r: r.state in ['purchase', 'done']):
                for po_line in po.order_line.filtered(lambda r: r.product_id == line.product_id):
                    if po_line.product_uom != line.product_uom_id:
                        total += self.pool.get('product.uom')._compute_qty_obj(
                            cr, uid, po_line.product_uom, po_line.product_qty, line.product_uom_id, context=context)
                    else:
                        total += po_line.product_qty
            result[line.id] = total
        return result

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', domain=[('purchase_ok', '=', True)], required=True),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'price_unit': fields.float('Unit Price', digits_compute=dp.get_precision('Product Price')),
        'qty_ordered': fields.function(_compute_ordered_qty, string='Ordered Quantities', type='float'),
        'requisition_id': fields.many2one('purchase.requisition', 'Purchase Agreement', ondelete='cascade'),
        'company_id': fields.related('requisition_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'schedule_date': fields.date('Scheduled Date'),
    }

    def _onchange_product_id(self, cr, uid, ids, product_id, product_uom_id, parent_analytic_account, analytic_account, parent_date, date, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        value = {'product_uom_id': ''}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            value = {'product_uom_id': prod.uom_id.id, 'product_qty': 1.0}
        if not analytic_account:
            value.update({'account_analytic_id': parent_analytic_account})
        if not date:
            value.update({'schedule_date': parent_date})
        return {'value': value}

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.requisition.line', context=c),
    }


class purchase_order(osv.osv):
    _inherit = "purchase.order"

    _columns = {
        'requisition_id': fields.many2one('purchase.requisition', 'Purchase Agreement', copy=False),
    }

    def _onchange_requisition_id(self, cr, uid, ids, requisition_id, partner_id, context=None):
        if not requisition_id:
            return {}

        requisition = self.pool.get('purchase.requisition').browse(cr, uid, [requisition_id], context=context)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, [partner_id], context=context)
        else:
            partner = requisition.vendor_id
        payment_term = partner.property_supplier_payment_term_id
        currency = partner.property_purchase_currency_id or requisition.company_id.currency_id

        fpos_obj = self.pool.get('account.fiscal.position')
        fpos = fpos_obj.get_fiscal_position(cr, uid, partner.id, context=context)
        fpos = fpos_obj.browse(cr, uid, [fpos], context=context)

        value = {
            'partner_id': partner.id,
            'fiscal_position_id': fpos.id,
            'payment_term_id': payment_term.id,
            'company_id': requisition.company_id.id,
            'currency_id': currency.id,
            'origin': requisition.name,
            'partner_ref': requisition.name, # to control vendor bill based on agreement reference
            'notes': requisition.description,
            'date_order': requisition.date_end or fields.datetime.now(),
            'picking_type_id': requisition.picking_type_id.id,
        }

        if requisition.type_id.line_copy != 'copy':
            return {'value': value}

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
                taxes_ids = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos,\
                    line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id == requisition.company_id), context=context)
            else:
                taxes_ids = line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id == requisition.company_id).ids

            # Compute quantity and price_unit
            if line.product_uom_id != line.product_id.uom_po_id:
                product_uom_obj = self.pool.get('product.uom')
                product_qty = product_uom_obj._compute_qty_obj(
                    cr, uid, line.product_uom_id, line.product_qty, line.product_id.uom_po_id, context=context)
                price_unit = product_uom_obj._compute_price(
                    cr, uid, line.product_uom_id.id, line.price_unit, to_uom_id=line.product_id.uom_po_id.id)
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
                'date_planned': requisition.schedule_date or datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'procurement_ids': [(6, 0, [requisition.procurement_id.id])] if requisition.procurement_id else False,
                'account_analytic_id': line.account_analytic_id and line.account_analytic_id.id or False,
            }))
        value['order_line'] = order_lines

        return {'value': value}

    def button_confirm(self, cr, uid, ids, context=None):
        res = super(purchase_order, self).button_confirm(cr, uid, ids, context=context)
        stock_move_obj = self.pool.get('stock.move')
        for po in self.browse(cr, uid, ids, context=context):
            if po.requisition_id and (po.requisition_id.type_id.exclusive == 'exclusive'):
                others_po = po.requisition_id.mapped('purchase_ids').filtered(lambda r: r.id != po.id)
                others_po.button_cancel()
                po.requisition_id.action_done(context=context)

            for element in po.order_line:
                if element.product_id == po.requisition_id.procurement_id.product_id:
                    stock_move_obj.write(cr, uid, element.move_ids.ids, {
                        'procurement_id': po.requisition_id.procurement_id.id,
                        'move_dest_id': po.requisition_id.procurement_id.move_dest_id.id,
                    }, context=context)
        return res


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


class product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'purchase_requisition': fields.selection(
            [('rfq', 'Create a draft purchase order'),
             ('tenders', 'Propose a call for tenders')],
            string='Procurement'),
    }
    _defaults = {
        'purchase_requisition': 'rfq',
    }


class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
        'requisition_id': fields.many2one('purchase.requisition', 'Latest Requisition')
    }

    def make_po(self, cr, uid, ids, context=None):
        requisition_obj = self.pool.get('purchase.requisition')
        warehouse_obj = self.pool.get('stock.warehouse')
        req_ids = []
        res = []
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.product_id.purchase_requisition == 'tenders':
                warehouse_id = warehouse_obj.search(cr, uid, [('company_id', '=', procurement.company_id.id)], context=context)
                requisition_id = requisition_obj.create(cr, uid, {
                    'origin': procurement.origin,
                    'date_end': procurement.date_planned,
                    'warehouse_id': warehouse_id and warehouse_id[0] or False,
                    'company_id': procurement.company_id.id,
                    'procurement_id': procurement.id,
                    'picking_type_id': procurement.rule_id.picking_type_id.id,
                    'line_ids': [(0, 0, {
                        'product_id': procurement.product_id.id,
                        'product_uom_id': procurement.product_uom.id,
                        'product_qty': procurement.product_qty
                    })],
                })
                self.message_post(cr, uid, [procurement.id], body=_("Purchase Requisition created"), context=context)
                procurement.write({'requisition_id': requisition_id})
                req_ids += [procurement.id]
                res += [procurement.id]
        set_others = set(ids) - set(req_ids)
        if set_others:
            res += super(procurement_order, self).make_po(cr, uid, list(set_others), context=context)
        return res
