# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from openerp import netsvc

from openerp.osv import fields,osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class purchase_requisition(osv.osv):
    _name = "purchase.requisition"
    _description="Purchase Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _columns = {
        'name': fields.char('Requisition Reference', size=32,required=True),
        'origin': fields.char('Source Document', size=32),
        'date_start': fields.datetime('Requisition Date'),
        'date_end': fields.datetime('Requisition Deadline'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'exclusive': fields.selection([('exclusive','Purchase Requisition (exclusive)'),('multiple','Multiple Requisitions')],'Requisition Type', required=True, help="Purchase Requisition (exclusive):  On the confirmation of a purchase order, it cancels the remaining purchase order.\nPurchase Requisition(Multiple):  It allows to have multiple purchase orders.On confirmation of a purchase order it does not cancel the remaining orders"""),
        'description': fields.text('Description'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'purchase_ids' : fields.one2many('purchase.order','requisition_id','Purchase Orders',states={'done': [('readonly', True)]}),
        'line_ids' : fields.one2many('purchase.requisition.line','requisition_id','Products to Purchase',states={'done': [('readonly', True)]}),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),        
        'state': fields.selection([('draft','New'),('in_progress','Sent to Suppliers'),('cancel','Cancelled'),('done','Purchase Done')],
            'Status', track_visibility='onchange', required=True)
    }
    _defaults = {
        'date_start': lambda *args: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': 'draft',
        'exclusive': 'multiple',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.requisition', context=c),
        'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id ,
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'purchase.order.requisition'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'state':'draft',
            'purchase_ids':[],
            'name': self.pool.get('ir.sequence').get(cr, uid, 'purchase.order.requisition'),
        })
        return super(purchase_requisition, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context=None):
        """
        Deletes Requisition and related RFQs 
        """
        if context is None: context = {}
        purchase_obj = self.pool.get('purchase.order')
        purchase_ids = self._requisition_procurement_cancel(cr, uid, ids, context=context)
        if purchase_ids:
            purchase_obj.unlink(cr, uid, purchase_ids, context=context)
        return super(purchase_requisition, self).unlink(cr, uid, ids, context=context)

    def _requisition_procurement_cancel(self, cr, uid, ids, context=None):
        """
        Cancels procurement order related to requisition
        @param ids: requisition ids
        @return: Returns purchase orders associated with requisition if any
        """
        if context is None: context = {}
        purchase_ids = []
        procurement_ids = []
        procurement_obj = self.pool.get('procurement.order')
        for requisition in self.browse(cr, uid, ids, context=context):
            purchase_ids.extend(purchase.id for purchase in requisition.purchase_ids)
            if requisition.state == 'cancel':
                continue
            procurement_ids.extend(procurement_obj.search(cr, uid,
                [('requisition_id', '=', requisition.id)], context=context))
        if procurement_ids:
            procurement_obj.action_cancel(cr, uid, procurement_ids)
        return purchase_ids

    def tender_cancel(self, cr, uid, ids, context=None):
        if context is None: context = {}
        purchase_order_obj = self.pool.get('purchase.order')
        purchase_ids = self._requisition_procurement_cancel(cr, uid, ids, context=context)
        if purchase_ids:
            purchase_order_obj.action_cancel(cr, uid, purchase_ids, context=context)
        procurement_ids = self.pool['procurement.order'].search(cr, uid, [('requisition_id', 'in', ids)], context=context)
        self.pool['procurement.order'].action_done(cr, uid, procurement_ids)
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def tender_in_progress(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'in_progress'} ,context=context)

    def tender_reset(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'})

    def tender_done(self, cr, uid, ids, context=None):
        procurement_ids = self.pool['procurement.order'].search(cr, uid, [('requisition_id', 'in', ids)], context=context)
        self.pool['procurement.order'].action_done(cr, uid, procurement_ids)
        return self.write(cr, uid, ids, {'state':'done', 'date_end':time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)

    def _planned_date(self, requisition, delay=0.0):
        company = requisition.company_id
        date_planned = False
        if requisition.date_start:
            date_planned = datetime.strptime(requisition.date_start, '%Y-%m-%d %H:%M:%S') - relativedelta(days=company.po_lead)
        else:
            date_planned = datetime.today() - relativedelta(days=company.po_lead)
        if delay:
            date_planned -= relativedelta(days=delay)
        return date_planned and date_planned.strftime('%Y-%m-%d %H:%M:%S') or False

    def _seller_details(self, cr, uid, requisition_line, supplier, context=None):
        product_uom = self.pool.get('product.uom')
        pricelist = self.pool.get('product.pricelist')
        supplier_info = self.pool.get("product.supplierinfo")
        product = requisition_line.product_id
        default_uom_po_id = product.uom_po_id.id
        qty = product_uom._compute_qty(cr, uid, requisition_line.product_uom_id.id, requisition_line.product_qty, default_uom_po_id)
        seller_delay = 0.0
        seller_price = False
        seller_qty = False
        for product_supplier in product.seller_ids:
            if supplier.id ==  product_supplier.name and qty >= product_supplier.qty:
                seller_delay = product_supplier.delay
                seller_qty = product_supplier.qty
        supplier_pricelist = supplier.property_product_pricelist_purchase or False
        seller_price = pricelist.price_get(cr, uid, [supplier_pricelist.id], product.id, qty, supplier.id, {'uom': default_uom_po_id})[supplier_pricelist.id]
        if seller_qty:
            qty = max(qty,seller_qty)
        date_planned = self._planned_date(requisition_line.requisition_id, seller_delay)
        return seller_price, qty, default_uom_po_id, date_planned

    def make_purchase_order(self, cr, uid, ids, partner_id, context=None):
        """
        Create New RFQ for Supplier
        """
        if context is None:
            context = {}
        assert partner_id, 'Supplier should be specified'
        purchase_order = self.pool.get('purchase.order')
        purchase_order_line = self.pool.get('purchase.order.line')
        res_partner = self.pool.get('res.partner')
        fiscal_position = self.pool.get('account.fiscal.position')
        supplier = res_partner.browse(cr, uid, partner_id, context=context)
        supplier_pricelist = supplier.property_product_pricelist_purchase or False
        res = {}
        for requisition in self.browse(cr, uid, ids, context=context):
            if supplier.id in filter(lambda x: x, [rfq.state <> 'cancel' and rfq.partner_id.id or None for rfq in requisition.purchase_ids]):
                 raise osv.except_osv(_('Warning!'), _('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
            location_id = requisition.warehouse_id.lot_input_id.id
            purchase_id = purchase_order.create(cr, uid, {
                        'origin': requisition.name,
                        'partner_id': supplier.id,
                        'pricelist_id': supplier_pricelist.id,
                        'location_id': location_id,
                        'company_id': requisition.company_id.id,
                        'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
                        'requisition_id':requisition.id,
                        'notes':requisition.description,
                        'warehouse_id':requisition.warehouse_id.id ,
            })
            res[requisition.id] = purchase_id
            for line in requisition.line_ids:
                product = line.product_id
                seller_price, qty, default_uom_po_id, date_planned = self._seller_details(cr, uid, line, supplier, context=context)
                taxes_ids = product.supplier_taxes_id
                taxes = fiscal_position.map_tax(cr, uid, supplier.property_account_position, taxes_ids)
                purchase_order_line.create(cr, uid, {
                    'order_id': purchase_id,
                    'name': product.partner_ref,
                    'product_qty': qty,
                    'product_id': product.id,
                    'product_uom': default_uom_po_id,
                    'price_unit': seller_price,
                    'date_planned': date_planned,
                    'taxes_id': [(6, 0, taxes)],
                }, context=context)
                
        return res


class purchase_requisition_line(osv.osv):

    _name = "purchase.requisition.line"
    _description="Purchase Requisition Line"
    _rec_name = 'product_id'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', domain=[('purchase_ok', '=', True)]),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'requisition_id' : fields.many2one('purchase.requisition','Purchase Requisition', ondelete='cascade'),
        'company_id': fields.related('requisition_id','company_id',type='many2one',relation='res.company',string='Company', store=True, readonly=True),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, product_uom_id, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        value = {'product_uom_id': ''}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            value = {'product_uom_id': prod.uom_id.id,'product_qty':1.0}
        return {'value': value}

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.requisition.line', context=c),
    }
purchase_requisition_line()

class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _columns = {
        'requisition_id' : fields.many2one('purchase.requisition','Purchase Requisition')
    }

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)
        proc_obj = self.pool.get('procurement.order')
        for po in self.browse(cr, uid, ids, context=context):
            if po.requisition_id and (po.requisition_id.exclusive=='exclusive'):
                for order in po.requisition_id.purchase_ids:
                    if order.id != po.id:
                        proc_ids = proc_obj.search(cr, uid, [('purchase_id', '=', order.id)])
                        if proc_ids and po.state=='confirmed':
                            proc_obj.write(cr, uid, proc_ids, {'purchase_id': po.id})
                        wf_service = netsvc.LocalService("workflow")
                        wf_service.trg_validate(uid, 'purchase.order', order.id, 'purchase_cancel', cr)
                    po.requisition_id.tender_done(context=context)
            if po.requisition_id and all(purchase_id.state in ['draft', 'cancel'] for purchase_id in po.requisition_id.purchase_ids if purchase_id.id != po.id):
                procurement_ids = self.pool['procurement.order'].search(cr, uid, [('requisition_id', '=', po.requisition_id.id)], context=context)
                for procurement in proc_obj.browse(cr, uid, procurement_ids, context=context):
                    if procurement.move_id:
                        procurement.move_id.write({'location_id': procurement.move_id.location_dest_id.id})
        return res

purchase_order()

class product_product(osv.osv):
    _inherit = 'product.product'

    _columns = {
        'purchase_requisition': fields.boolean('Purchase Requisition', help="Check this box to generates purchase requisition instead of generating requests for quotation from procurement.")
    }
    _defaults = {
        'purchase_requisition': False
    }

product_product()

class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
        'requisition_id': fields.many2one('purchase.requisition', 'Latest Requisition')
    }

    def _get_warehouse(self, procurement, user_company):
        """
            Return the warehouse containing the procurment stock location (or one of it ancestors)
            If none match, returns then first warehouse of the company
        """
        # NOTE This method is a copy of the one on the procurement.order defined in purchase
        #      module. It's been copied to ensure it been always available, even if module
        #      purchase is not up to date.
        #      Do not forget to update both version in case of modification.
        company_id = (procurement.company_id or user_company).id
        domains = [
            [
                '&', ('company_id', '=', company_id),
                '|', '&', ('lot_stock_id.parent_left', '<', procurement.location_id.parent_left),
                          ('lot_stock_id.parent_right', '>', procurement.location_id.parent_right),
                     ('lot_stock_id', '=', procurement.location_id.id)
            ],
            [('company_id', '=', company_id)]
        ]

        cr, uid = procurement._cr, procurement._uid
        context = procurement._context
        Warehouse = self.pool['stock.warehouse']
        for domain in domains:
            ids = Warehouse.search(cr, uid, domain, context=context)
            if ids:
                return ids[0]
        return False

    def make_po(self, cr, uid, ids, context=None):
        res = {}
        requisition_obj = self.pool.get('purchase.requisition')
        non_requisition = []
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.product_id.purchase_requisition:
                user_company = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id
                req = requisition_obj.create(cr, uid, {
                    'origin': procurement.origin,
                    'date_end': procurement.date_planned,
                    'warehouse_id': self._get_warehouse(procurement, user_company),
                    'company_id': procurement.company_id.id,
                    'line_ids': [(0, 0, {
                        'product_id': procurement.product_id.id,
                        'product_uom_id': procurement.product_uom.id,
                        'product_qty': procurement.product_qty

                    })],
                })
                procurement.write({
                    'state': 'running',
                    'requisition_id': req
                })
                res[procurement.id] = 0
            else:
                non_requisition.append(procurement.id)

        if non_requisition:
            res.update(super(procurement_order, self).make_po(cr, uid, non_requisition, context=context))

        return res

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
