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

    def _get_po_line(self, cr, uid, ids, field_names, arg=None, context=None):
        result = {}
        if not ids: return result
        for id in ids:
            result.setdefault(id, [])
        for element in self.browse(cr, uid, ids, context=context):
            for po in element.purchase_ids:
                for po_line in po.order_line:
                    result[po_line.order_id.requisition_id.id].append(po_line.id)
        return result

    _columns = {
        'name': fields.char('Requisition Reference', size=32,required=True),
        'origin': fields.char('Source Document', size=32),
        'date_start': fields.datetime('Date'),
        'date_end': fields.datetime('Bid Submission Deadline'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'exclusive': fields.selection([('exclusive','Purchase Requisition (exclusive)'),('multiple','Multiple Requisitions')],'Requisition Type', required=True, help="Purchase Requisition (exclusive):  On the confirmation of a purchase order, it cancels the remaining purchase order.\nPurchase Requisition(Multiple):  It allows to have multiple purchase orders.On confirmation of a purchase order it does not cancel the remaining orders"""),
        'description': fields.text('Description'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'purchase_ids' : fields.one2many('purchase.order','requisition_id','Purchase Orders',states={'done': [('readonly', True)]}),
        'po_line_ids': fields.function(_get_po_line, method=True, type='one2many', relation='purchase.order.line', string='Products by supplier'),
        'line_ids' : fields.one2many('purchase.requisition.line','requisition_id','Products to Purchase',states={'done': [('readonly', True)]}),
        'move_dest_id': fields.many2one('stock.move', 'Reservation Destination', ondelete='set null'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),        
        'state': fields.selection([('draft','Draft Tender'),('in_progress','Tender Confirmed'),('open','Close Bids'),('done','PO Created'),('cancel','Cancelled')],
            'Status', track_visibility='onchange', required=True),
        'multiple_rfq_per_supplier': fields.boolean('Multiple RFQ per supplier'),
        'account_analytic_id':fields.many2one('account.analytic.account', 'Analytic Account'),
        'schedule_date': fields.date('Scheduled Date', select=True),
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
    
    def tender_cancel(self, cr, uid, ids, context=None):
        purchase_order_obj = self.pool.get('purchase.order')
        #try to set all associated quotations to cancel state
        for purchase in self.browse(cr, uid, ids, context=context):
            for purchase_id in purchase.purchase_ids:
                purchase_order_obj.action_cancel(cr,uid,[purchase_id.id])
                purchase_order_obj.message_post(cr, uid, [purchase_id.id], body=_('Cancelled by the tender associated to this quotation.'), context=context)
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def tender_in_progress(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'in_progress'} ,context=context)

    def tender_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'open'} ,context=context)

    def tender_reset(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'})
        wf_service = netsvc.LocalService("workflow")
        for p_id in ids:
            # Deleting the existing instance of workflow for PO
            wf_service.trg_delete(uid, 'purchase.requisition', p_id, cr)
            wf_service.trg_create(uid, 'purchase.requisition', p_id, cr)
        return True
    def tender_done(self, cr, uid, ids, context=None):
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
        seller_price = pricelist.price_get(cr, uid, [supplier_pricelist.id], product.id, qty, False, {'uom': default_uom_po_id})[supplier_pricelist.id]
        if seller_qty:
            qty = max(qty,seller_qty)
        date_planned = self._planned_date(requisition_line.requisition_id, seller_delay)
        return seller_price, qty, default_uom_po_id, date_planned

    def open_product_line(self, cr, uid, ids, context=None):
        """ This opens product line view to view all lines from the different quotations, groupby default by product and partner to show comparaison
            between supplier price
            @return: the product line tree view
        """
        if context is None:
            context = {}
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'purchase_requisition','purchase_line_tree', context=context)
        res['context'] = context
        po_ids_browse = self.browse(cr, uid, ids, context=context)[0].po_line_ids
        po_ids=[]
        for po in po_ids_browse:
            po_ids.append(po.id)
        res['context'].update({
            'search_default_groupby_product' : True,
            'search_default_hide_cancelled': True,
        })
        res['domain'] = [('id','in', po_ids)]
        return res


    def open_rfq(self, cr, uid, ids, context=None):
        """ This opens rfq view to view all quotations associated to the tender
            @return: the RFQ tree view
        """
        if context is None:
            context = {}
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'purchase','purchase_rfq', context=context)
        res['context'] = context
        po_ids_browse = self.browse(cr, uid, ids, context=context)[0].purchase_ids
        po_ids=[]
        for po in po_ids_browse:
            po_ids.append(po.id)
        res['domain'] = [('id','in', po_ids)]
        return res

    def _prepare_purchase_order(self, cr, uid, requisition, supplier, context=None):
        if not requisition.warehouse_id:
            warehouse_obj = self.pool.get('stock.warehouse')

            warehouse_id = warehouse_obj.search(cr, uid, [('company_id', '=', requisition.company_id.id)], context=context)
            location_id = warehouse_obj.browse(cr, uid, warehouse_id, context=context)[0].lot_input_id.id
        else:
            location_id = requisition.warehouse_id.lot_input_id.id
        supplier_pricelist = supplier.property_product_pricelist_purchase or False
        return {
            'origin': requisition.name,
            'order_date': requisition.date_end or fields.date.context_today,
            'partner_id': supplier.id,
            'pricelist_id': supplier_pricelist.id,
            'location_id': location_id,
            'company_id': requisition.company_id.id,
            'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
            'requisition_id':requisition.id,
            'notes':requisition.description,
            'warehouse_id':requisition.warehouse_id.id if requisition.warehouse_id else False,
        }
    def _prepare_purchase_order_line(self, cr, uid, requisition, requisition_line, purchase_id, supplier, context=None):
        fiscal_position = self.pool.get('account.fiscal.position')
        res_partner = self.pool.get('res.partner')
        product_product = self.pool.get('product.product')
        product = requisition_line.product_id
        seller_price, qty, default_uom_po_id, date_planned = self._seller_details(cr, uid, requisition_line, supplier, context=context)
        taxes_ids = product.supplier_taxes_id
        taxes = fiscal_position.map_tax(cr, uid, supplier.property_account_position, taxes_ids)
        # - determine name and notes based on product in partner lang.
        context_partner = context.copy()

        if supplier:
            lang = res_partner.browse(cr, uid, supplier.id).lang
            context_partner.update( {'lang': lang, 'partner_id': supplier.id} )
        product = product_product.browse(cr, uid, requisition_line.product_id.id, context=context_partner)
        #call name_get() with partner in the context to eventually match name and description in the seller_ids field
        dummy, name = product_product.name_get(cr, uid, product.id, context=context_partner)[0]
        if product.description_purchase:
            name += '\n' + product.description_purchase
        return {
            'order_id': purchase_id,
            'name': name,
            'product_qty': qty,
            'product_id': product.id,
            'product_uom': default_uom_po_id,
            'price_unit': seller_price,
            'date_planned': requisition_line.schedule_date or date_planned,
            'move_dest_id': requisition.move_dest_id.id,
            'taxes_id': [(6, 0, taxes)],
            'account_analytic_id':requisition_line.account_analytic_id.id,
        }
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
        supplier = res_partner.browse(cr, uid, partner_id, context=context)
        res = {}
        for requisition in self.browse(cr, uid, ids, context=context):
            if not requisition.multiple_rfq_per_supplier and supplier.id in filter(lambda x: x, [rfq.state <> 'cancel' and rfq.partner_id.id or None for rfq in requisition.purchase_ids]):
                 raise osv.except_osv(_('Warning!'), _('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
            purchase_id = purchase_order.create(cr, uid, self._prepare_purchase_order(cr, uid, requisition, supplier, context=context), context=context)
            res[requisition.id] = purchase_id
            for line in requisition.line_ids:
                purchase_order_line.create(cr, uid, self._prepare_purchase_order_line(cr, uid, requisition, line, purchase_id, supplier, context=context), context=context)
        return res

    def check_valid_quotation(self, cr, uid, quotation, context=None):
        """
        Check if a quotation has all his order lines bid in order to confirm it if its the case
        return True if all order line have been selected during bidding process, else return False

        args : 'quotation' must be a browse record
        """
        for line in quotation.order_line:
            if line.state != 'confirmed' or line.product_qty != line.quantity_bid:
                return False
        return True

    def generate_po(self, cr, uid, id, context=None):
        """
        Generate all purchase order based on selected lines, should only be called on one tender at a time
        """
        po = self.pool.get('purchase.order')
        poline = self.pool.get('purchase.order.line')
        id_per_supplier = {}
        tender = self.browse(cr, uid, id, context=context)[0]
        if tender.state == 'done':
            raise osv.except_osv(_('Warning!'), _('You have already generate the purchase order(s).'))

        confirm = False
        #check that we have at least confirm one line
        for po_line in tender.po_line_ids:
            if po_line.state == 'confirmed':
                confirm = True
                break
        if not confirm:
            raise osv.except_osv(_('Warning!'), _('You have no line selected for buying.'))

        #check for complete RFQ
        for quotation in tender.purchase_ids:
            if (self.check_valid_quotation(cr, uid, quotation, context=context)):
                #use workflow to set PO state to confirm
                self.trigger_validate_po(cr, uid, quotation.id, context=context)

        #get other confirmed lines per supplier
        for po_line in tender.po_line_ids:
            #only take into account confirmed line that does not belong to already confirmed purchase order
            if po_line.state == 'confirmed' and po_line.order_id.state in ['draft', 'sent', 'bid', 'cancel']:
                partner = po_line.partner_id.id
                if id_per_supplier.get(partner):
                    id_per_supplier[partner].append(po_line)
                else:
                    id_per_supplier[partner] = [po_line]

        #generate po based on supplier and cancel all previous RFQ
        for supplier, product_line in id_per_supplier.items():
            #copy a quotation for this supplier and change order_line then validate it
            quotation_id = po.search(cr, uid, [('requisition_id', '=', tender.id), ('partner_id', '=', supplier)], limit=1)[0]
            new_po = po.copy(cr, uid, quotation_id, default = {'order_line': []}, context=context)
            #put back link to tender on PO
            po.write(cr, uid, new_po, {'requisition_id': tender.id, 'origin': tender.name}, context=context)
            #duplicate po_line and change product_qty if needed and associate them to newly created PO
            for line in product_line:
                poline.copy(cr, uid, line.id, default = {'product_qty': line.quantity_bid, 'order_id': new_po}, context=context)
                #set previous confirmed line to draft
                poline.action_draft(cr, uid, line.id, context=context)
            #use workflow to set new PO state to confirm
            self.trigger_validate_po(cr, uid, new_po, context=context)
            
        #cancel other orders
        self.cancel_quotation(cr, uid, tender, context=context)

        #set tender to state done
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'purchase.requisition', tender.id, 'done', cr)
        #self.tender_done(cr, uid, id, context=context)
        return True

    def trigger_validate_po(self, cr, uid, po_id, context=None):
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'purchase.order', po_id, 'purchase_confirm', cr)

    def cancel_quotation(self, cr, uid, tender, context=None):
        #cancel other orders
        po = self.pool.get('purchase.order')
        wf_service = netsvc.LocalService("workflow")
        for quotation in tender.purchase_ids:
            if quotation.state in ['draft', 'sent', 'bid']:
                wf_service.trg_validate(uid, 'purchase.order', quotation.id, 'purchase_cancel', cr)
                po.message_post(cr, uid, [quotation.id], body=_('Cancelled by the tender associated to this quotation.'), context=context)
        return True
            

class purchase_requisition_line(osv.osv):

    _name = "purchase.requisition.line"
    _description="Purchase Requisition Line"
    _rec_name = 'product_id'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product' ),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'po_line_buy': fields.many2one('purchase.order.line', 'Purchase Order Line'),
        'requisition_id': fields.many2one('purchase.requisition','Call for Bids', ondelete='cascade'),
        'po_line_ids': fields.related('requisition_id', 'po_line_ids', string='PO lines', readonly=True, type="one2many"),
        'company_id': fields.related('requisition_id','company_id',type='many2one',relation='res.company',string='Company', store=True, readonly=True),
        'account_analytic_id':fields.many2one('account.analytic.account', 'Analytic Account',),
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
            value = {'product_uom_id': prod.uom_id.id,'product_qty':1.0}
        if not analytic_account:
            value.update({'account_analytic_id': parent_analytic_account})
        if not date:
            value.update({'schedule_date': parent_date})
        return {'value': value}

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.requisition.line', context=c),
    }
purchase_requisition_line()

class purchase_order(osv.osv):
    _inherit = "purchase.order"

    _columns = {
        'requisition_id' : fields.many2one('purchase.requisition','Call for Bids'),
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
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'requisition_id':False,
        })
        return super(purchase_order, self).copy(cr, uid, id, default, context)

purchase_order()

class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'

    _columns= {
        'quantity_bid': fields.float('Quantity Bid', digits_compute=dp.get_precision('Product Unit of Measure')),
    }

    def action_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def action_confirm(self, cr, uid, ids, context=None):
        super(purchase_order_line, self).action_confirm(cr, uid, ids, context=context)
        for element in self.browse(cr, uid, ids, context=context):
            if not element.quantity_bid:
                self.write(cr, uid, ids, {'quantity_bid': element.product_qty}, context=context)
        return True

    def generate_po(self, cr, uid, active_id, context=None):
        #call generate_po from tender with active_id
        self.pool.get('purchase.requisition').generate_po(cr, uid, [active_id], context=context)
        return True
        

class product_product(osv.osv):
    _inherit = 'product.product'

    _columns = {
        'purchase_requisition': fields.boolean('Call for Bids', help="Check this box to generate Call for Bids instead of generating requests for quotation from procurement.")
    }
    _defaults = {
        'purchase_requisition': False
    }

product_product()

class procurement_order(osv.osv):

    _inherit = 'procurement.order'
    _columns = {
        'requisition_id' : fields.many2one('purchase.requisition','Latest Requisition')
    }
    def make_po(self, cr, uid, ids, context=None):
        res = {}
        requisition_obj = self.pool.get('purchase.requisition')
        warehouse_obj = self.pool.get('stock.warehouse')
        procurement = self.browse(cr, uid, ids, context=context)[0]
        if procurement.product_id.purchase_requisition:
             warehouse_id = warehouse_obj.search(cr, uid, [('company_id', '=', procurement.company_id.id or company.id)], context=context)
             res[procurement.id] = requisition_obj.create(cr, uid, 
                   {
                    'origin': procurement.origin,
                    'date_end': procurement.date_planned,
                    'warehouse_id':warehouse_id and warehouse_id[0] or False,
                    'company_id':procurement.company_id.id,
                    'move_dest_id':procurement.move_id.id,
                    'line_ids': [(0,0,{
                        'product_id': procurement.product_id.id,
                        'product_uom_id': procurement.product_uom.id,
                        'product_qty': procurement.product_qty

                   })],
                })
             self.write(cr,uid,[procurement.id],{'state': 'running','requisition_id': res[procurement.id]},context=context)
        else:
            res = super(procurement_order, self).make_po(cr, uid, ids, context=context)
        return res

    def check_product_requisition(self, cr, uid, ids, context=None):
        procurement = self.browse(cr, uid, ids, context=context)[0]
        if procurement.product_id.purchase_requisition:
            return True
        return False

procurement_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
