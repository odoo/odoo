# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from osv import fields, osv
from service import web_services
import netsvc
import pooler
import time
from mx import DateTime
from osv.orm import browse_record, browse_null

class purchase_requisition_partner(osv.osv_memory):
    _name = "purchase.requisition.partner"
    _description = "Purchase Requisition"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'pruchase_requisitions': fields.many2one('mrp.procurement', 'Requisitions',required=True, domain=[('state', '=', 'confirmed')]),
    }
    _defaults = {
        'parnter_id': lambda *a: 1,
    }          
        

    def create_order(self, cr, uid, ids, context):
        """ 
             To merge similar type of purchase orders.
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs 
             @param context: A standard dictionary 
             
             @return: purchase order view
            
        """      
        record_id = context and context.get('active_id', False)
        if record_id:
            data =  self.read(cr, uid, ids)
            company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id        
            order_obj = self.pool.get('purchase.order')
            partner_obj = self.pool.get('res.partner')
            procurement_obj = self.pool.get('mrp.procurement')
            purchase_id=[]
            partner_obj = self.pool.get('res.partner')
            uom_obj = self.pool.get('product.uom')
            pricelist_obj = self.pool.get('product.pricelist')
            prod_obj = self.pool.get('product.product')
            acc_pos_obj = self.pool.get('account.fiscal.position')
            record_id = context and context.get('active_id', False)
            procurement_id=data[0]['pruchase_requisitions']
            for procurement in procurement_obj.browse(cr, uid,[procurement_id]):
                #Todo need to check
              #  partner = procurement.product_id.seller_ids[0].name
                partner_id = data[0]['partner_id']
                address_id = partner_obj.address_get(cr, uid, [partner_id], ['delivery'])['delivery']
                
                res_id = procurement.move_id.id
                partner = procurement.product_id.seller_ids[0].name   
                pricelist_id = partner.property_product_pricelist_purchase.id
                uom_id = procurement.product_id.uom_po_id.id            
                
                newdate = DateTime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S')
                newdate = newdate - DateTime.RelativeDateTime(days=company.po_lead)
                newdate = newdate - procurement.product_id.seller_ids[0].delay
    
                
                qty = uom_obj._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, uom_id)
                            
                if procurement.product_id.seller_ids[0].qty:
                        qty = max(qty,procurement.product_id.seller_ids[0].qty)
        
    
                price = pricelist_obj.price_get(cr, uid, [pricelist_id], procurement.product_id.id, qty, False, {'uom': uom_id})[pricelist_id]
                product = prod_obj.browse(cr, uid, procurement.product_id.id, context=context)
    
        
                line = {
                        'name': product.partner_ref,
                        'product_qty': qty,
                        'product_id': procurement.product_id.id,
                        'product_uom': uom_id,
                        'price_unit': price,
                        'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                        'move_dest_id': res_id,
                        'notes': product.description_purchase,
                    }
        
                taxes_ids = procurement.product_id.product_tmpl_id.supplier_taxes_id
                taxes = acc_pos_obj.map_tax(cr, uid, partner.property_account_position, taxes_ids)
                line.update({
                        'taxes_id': [(6,0,taxes)]
                    })        
                purchase_id = order_obj.create(cr, uid, {
                        'origin': procurement.name,
                        'partner_id': partner_id,
                        'partner_address_id': address_id,
                        'location_id': procurement.location_id.id,
                        'pricelist_id': pricelist_id,
                        'order_line': [(0,0,line)],
                        'company_id': procurement.company_id.id,
                       'fiscal_position': partner.property_account_position and partner.property_account_position.id or False,
                       'tender_id':record_id,
                    })
               
                procurement_obj.write(cr, uid, [procurement.id], {'state': 'running', 'purchase_id': purchase_id})    
            
        return {
            'domain': "[('id','in', [" + ','.join(map(str, [purchase_id])) + "])]",
            'name': 'Purchase Orders',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            }
purchase_requisition_partner()

