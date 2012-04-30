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

import time
from osv import fields, osv
from tools.translate import _

class event_event(osv.osv):
    _inherit = 'event.event'

    def make_quotation(self, cr, uid, ids, partner_id, context=None):
        event_pool = self.pool.get('event.event')
        register_pool = self.pool.get('event.registration')
        sale_order_line_pool = self.pool.get('sale.order.line')
        sale_order = self.pool.get('sale.order')
        res_partner_obj = self.pool.get('res.partner')
        prod_pricelist_obj = self.pool.get('product.pricelist')
        res_users_obj = self.pool.get('res.users')
        customer = res_partner_obj.browse(cr, uid, partner_id, context=context)
        
        partner_id = res_users_obj.browse(cr, uid, uid, context=context).partner_id.id
        if not partner_id:
              raise osv.except_osv(_('Error !'),
                                    _('There is no Partner defined ' \
                                            'for this event:'))
        
        user_name = res_users_obj.browse(cr, uid, uid, context=context).name
        price_list = prod_pricelist_obj.search(cr,uid,[],context=context)[0]
        for event_id in self.browse(cr, uid, ids, context=context):
            sale_order_lines = []
            price_list = prod_pricelist_obj.search(cr,uid,[],context=context)[0]
            new_sale_id = sale_order.create(cr, uid, {
                            'partner_id': partner_id,
                            'pricelist_id': price_list,
                            'partner_invoice_id': partner_id,
                            'partner_shipping_id': partner_id,
                            'date_order': event_id.date_begin
                })            
            if event_id.event_item_ids:
                for items in event_id.event_item_ids:
                    product = items.product_id.id
                    sale_order_line = sale_order_line_pool.create(cr, uid, {
                        'order_id': new_sale_id,                                
                        'name': items.product_id.name,
                        'product_uom_qty': items.qty,
                        'product_id': items.product_id.id,
                        'product_uom': items.uom_id.id,
                        'price_unit': items.price,
                        'date_planned': items.sales_end_date,
                    }, context=context)
        return True
