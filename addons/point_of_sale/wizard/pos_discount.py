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

import netsvc
from osv import osv,fields
from tools.translate import _

class pos_discount(osv.osv_memory):
    _name = 'pos.discount'
    _description = 'Add Discount'

    _columns = {
                'discount': fields.float('Discount ', required=True),
                'discount_notes': fields.char('Discount Notes',size= 128, required=True),
    }
    _defaults = {
                    'discount': lambda *a: 5,
                }
    
    def apply_discount(self, cr, uid, ids, context):
        """ 
             To give the discount of  product and check the  .            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary 
             @return : nothing
        """        
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('record_id',False)
        if isinstance(record_id, (int, long)):
            record_id=[record_id]
        
        order_ref = self.pool.get('pos.order')
        order_line_ref =self.pool.get('pos.order.line')
        
        for order in order_ref.browse(cr, uid, record_id, context=context):
            for line in order.lines :
                company_discount = order.company_id.company_discount
                applied_discount =this.discount
               
                if applied_discount == 0.00:
                    notice = 'No Discount'
                elif company_discount >=  applied_discount:
                    notice = 'Minimum Discount'
                else:
                    notice = this.discount_notes
                    
                if self.check_discount(cr, uid, record_id,this.discount,context) == 'apply_discount':
                    order_line_ref.write(cr, uid, [line.id],
                            {'discount': this.discount,
                            'price_ded':line.price_unit*line.qty*(this.discount or 0)*0.01 or 0.0,
                            'notice':notice
                            },
                            context=context,)
                else :
                    order_line_ref.write(cr, uid, [line.id],
                            {'discount': this.discount,
                            'notice': notice,
                            'price_ded':line.price_unit*line.qty*(this.discount or 0)*0.01 or 0.0 
                            },
                            context=context,)
        return {}
    
    def check_discount(self, cr, uid, record_id,discount, context):
        """ 
             Check the discount of define by company  .            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param record_id:Current Order id
             @param discount:Select Discount
             @param context: A standard dictionary 
             @return : retrun  to apply and used the company discount base on condition
        """                
        order_ref = self.pool.get('pos.order')
        for order in order_ref.browse(cr, uid, record_id, context=context):
            company_disc = order.company_id.company_discount
            for line in order.lines :
                prod_disc = discount
                if prod_disc <= company_disc :
                   return 'apply_discount'
                else :
                    return 'disc_discount'    
pos_discount()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
