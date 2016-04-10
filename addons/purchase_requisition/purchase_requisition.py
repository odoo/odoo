# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
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
        'exclusive': fields.selection([('exclusive', 'Select only one RFQ (exclusive)'), ('multiple', 'Select multiple RFQ')], 'Agreement Selection Type', required=True, help="Select only one RFQ (exclusive):  On the confirmation of a purchase order, it cancels the remaining purchase order.\nSelect multiple RFQ:  It allows to have multiple purchase orders.On confirmation of a purchase order it does not cancel the remaining orders"""),
        'quantity_copy': fields.selection([('copy','Use quantities of agreement'), ('none','Set quantities manually')], 'Quantities', required=True),
        'line_copy': fields.selection([('copy','Use lines of agreement'), ('none', 'Do not create RfQ lines automatically')], 'Lines', required=True)
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

    def _get_po_line(self, cr, uid, ids, field_names, arg=None, context=None):
        result = dict((res_id, []) for res_id in ids)
        for element in self.browse(cr, uid, ids, context=context):
            for po in element.purchase_ids:
                result[element.id] += [po_line.id for po_line in po.order_line]
        return result

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
        obj_data = self.pool.get('ir.model.data')
        return obj_data.get_object_reference(cr, uid, 'stock', 'picking_type_in')[1]

    def _get_type_id(self, cr, uid, context=None):
        types = self.pool.get('purchase.requisition.type').search(cr, uid, [], context=context, limit=1)
        return types and types[0] or False

    _defaults = {
        'state': 'draft',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.requisition', context=c),
        'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id,
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').next_by_code(cr, uid, 'purchase.order.requisition'),
        'type_id': _get_type_id,
        'picking_type_id': _get_picking_in,
    }

    def tender_cancel(self, cr, uid, ids, context=None):
        purchase_order_obj = self.pool.get('purchase.order')
        # try to set all associated quotations to cancel state
        for tender in self.browse(cr, uid, ids, context=context):
            for purchase_order in tender.purchase_ids:
                purchase_order_obj.button_cancel(cr, uid, [purchase_order.id], context=context)
                purchase_order_obj.message_post(cr, uid, [purchase_order.id], body=_('Cancelled by the agreement associated to this quotation.'), context=context)
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def tender_in_progress(self, cr, uid, ids, context=None):
        if not all(obj.line_ids for obj in self.pool['purchase.requisition'].browse(cr, uid, ids, context=context)):
            raise UserError(_('You can not confirm call because there is no product line.'))
        return self.write(cr, uid, ids, {'state': 'in_progress'}, context=context)

    def tender_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def tender_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def action_done(self, cr, uid, ids, context=None):
        """
        Generate all purchase order based on selected lines, should only be called on one agreement at a time
        """
        for tender in self.browse(cr, uid, ids, context=context):
            if tender.state == 'done':
                raise UserError(_('You have already generate the purchase order(s).'))

            #check for complete RFQ
            for quotation in tender.purchase_ids:
                if quotation.state in ('draft', 'sent', 'to approve'):
                    raise UserError(_('You have to cancel or validate all RfQs before closing the purchase requisition.'))

            #set tender to state done
            self.signal_workflow(cr, uid, [tender.id], 'done')
        return True


class purchase_requisition_line(osv.osv):
    _name = "purchase.requisition.line"
    _description = "Purchase Requisition Line"
    _rec_name = 'product_id'

    def _compute_ordered_qty(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict.fromkeys(ids, 0)
        for line in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for order in line.requisition_id.purchase_ids:
                if order.state in ('purchase','done'):
                    for oline in order.order_line:
                        if oline.product_id.id == line.product_id.id:
                            total += oline.product_qty
            result[line.id] = total
        return result

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', domain=[('purchase_ok', '=', True)], required=True),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'price': fields.float('Price', digits_compute=dp.get_precision('Product Price')),
        'product_ordered_qty': fields.function(_compute_ordered_qty, string='Ordered Quantities', type='float'),
        'requisition_id': fields.many2one('purchase.requisition', 'Purchase Agreement', ondelete='cascade'),
        'company_id': fields.related('requisition_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'schedule_date': fields.date('Scheduled Date'),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, product_uom_id, parent_analytic_account, analytic_account, parent_date, date, context=None):
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
    def onchange_tender_id(self, cr, uid, ids, tender_id, partner_id, context=None):
        po_line_obj = self.pool.get('purchase.order.line')
        if not tender_id:
            return {}
        order_lines = []
        tender = self.pool.get('purchase.requisition').browse(cr, uid, tender_id, context=context)
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        fpos = self.pool.get('account.fiscal.position').get_fiscal_position(cr, uid, partner_id or tender.vendor_id.id, context=context)
        for line in tender.line_ids:
            # TODO: compute taxes
            if partner_id or tender.vendor_id:
                product_lang = line.product_id.with_context({
                    'lang': tender.vendor_id.lang,
                    'partner_id': partner_id or tender.vendor_id.id,
                })
            else:
                product_lang = line.product_id
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            taxes = line.product_id.supplier_taxes_id
            if (partner_id or tender.vendor_id) and fpos:
                taxes = fpos.map_tax(taxes)
            taxes.filtered(lambda r: r.company_id.id == company_id.id)

            order_lines.append((0,0,{
                'name': name,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom_id.id,
                'product_qty': (tender.type_id.quantity_copy=='copy') and line.product_qty or 0,
                'price_unit': line.price,
                'taxes': taxes.mapped('id'),
                'date_planned': tender.schedule_date or datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'procurement_ids': tender.procurement_id and [(6,0, [tender.procurement_id.id])] or False,
                'account_analytic_id': line.account_analytic_id and line.account_analytic_id.id or False,
            }))
        value = {
            'partner_id': partner_id or (tender.vendor_id and tender.vendor_id.id) or False,
            'fiscal_position_id': fpos and fpos.id or False,
            'origin': tender.name,
            'notes': tender.description,
            'order_line': (tender.type_id.line_copy=='copy') and order_lines or [],
            'date_order': tender.date_end or fields.datetime.now(),
            'currency_id': company_id and company_id.currency_id.id,
            'picking_type_id': tender.picking_type_id.id,
            'company_id': company_id.id,
        }
        return {'value': value}

    def button_confirm(self, cr, uid, ids, context=None):
        res = super(purchase_order, self).button_confirm(cr, uid, ids, context=context)
        proc_obj = self.pool.get('procurement.order')
        for po in self.browse(cr, uid, ids, context=context):
            if po.requisition_id and (po.requisition_id.type_id.exclusive == 'exclusive'):
                for order in po.requisition_id.purchase_ids:
                    if order.id != po.id:
                        proc_ids = proc_obj.search(cr, uid, [('purchase_id', '=', order.id)])
                        if proc_ids and po.state == 'confirmed':
                            proc_obj.write(cr, uid, proc_ids, {'purchase_id': po.id})
                        order.button_cancel()
                    po.requisition_id.tender_done(context=context)
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
