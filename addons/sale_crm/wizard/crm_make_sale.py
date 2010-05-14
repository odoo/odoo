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
from tools.translate import _
from mx.DateTime import now

class crm_make_sale(osv.osv_memory):
    """ Make sale  order for crm """

    _name = "crm.make.sale"
    _description = "Make sale"
    
    def _selectPartner(self, cr, uid, context=None):
        """
        This function gets default value for partner_id field.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        @return : default value of partner_id field.
        """ 
        if not context:
            context = {}
            
        data = context and context.get('active_ids', []) or []
        case_obj = self.pool.get('crm.lead')
        case = case_obj.read(cr, uid, data, ['partner_id'])
        return  case[0]['partner_id']
    
    def makeOrder(self, cr, uid, ids, context=None):
        """
        This function  create Quotation on given case.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm make sale' ids
        @param context: A standard dictionary for contextual values
        @return : Dictionary value of created sale order.
        """
        if not context:
            context = {}
            
        mod_obj = self.pool.get('ir.model.data')
        result = mod_obj._get_id(cr, uid, 'sale', 'view_sales_order_filter')
        id = mod_obj.read(cr, uid, result, ['res_id'])
        case_obj = self.pool.get('crm.lead')
        sale_obj = self.pool.get('sale.order')
        partner_obj = self.pool.get('res.partner')
        sale_line_obj = self.pool.get('sale.order.line')
        
        data = context and context.get('active_ids', []) or []
             
        for make in self.browse(cr, uid, ids):  
            default_partner_addr = partner_obj.address_get(cr, uid, [make.partner_id.id],
                    ['invoice', 'delivery', 'contact'])
            default_pricelist = partner_obj.browse(cr, uid, make.partner_id.id,
                         context).property_product_pricelist.id
            fpos_data = partner_obj.browse(cr, uid, make.partner_id.id, context).property_account_position
            new_ids = []
    
            for case in case_obj.browse(cr, uid, data):
                if case.partner_id and case.partner_id.id:
                    partner_id = case.partner_id.id
                    fpos = case.partner_id.property_account_position and case.partner_id.property_account_position.id or False
                    partner_addr = partner_obj.address_get(cr, uid, [case.partner_id.id],
                            ['invoice', 'delivery', 'contact'])
                    pricelist = partner_obj.browse(cr, uid, case.partner_id.id,
                            context).property_product_pricelist.id
                else:
                    partner_id = make.partner_id.id
                    fpos = fpos_data and fpos_data.id or False
                    partner_addr = default_partner_addr
                    pricelist = default_pricelist
    
                if False in partner_addr.values():
                    raise osv.except_osv(_('Data Insufficient!'),_('Customer has no addresses defined!'))
    
                vals = {
                    'origin': 'CRM-Opportunity:%s' % str(case.id),
                    'section_id': case.section_id and case.section_id.id or False,
                    'picking_policy': make.picking_policy,
                    'shop_id': make.shop_id.id,
                    'partner_id': partner_id,
                    'pricelist_id': pricelist,
                    'partner_invoice_id': partner_addr['invoice'],
                    'partner_order_id': partner_addr['contact'],
                    'partner_shipping_id': partner_addr['delivery'],
                    'order_policy': 'manual',
                    'date_order': now(),
                    'fiscal_position': fpos,
                }
    
                if partner_id:
                    partner = partner_obj.browse(cr, uid, partner_id, context=context)
                    vals['user_id'] = partner.user_id and partner.user_id.id or uid
    
                if make.analytic_account.id:
                    vals['project_id'] = make.analytic_account.id
                new_id = sale_obj.create(cr, uid, vals)
                for product_id in make.product_ids:
                    value = sale_line_obj.product_id_change(cr, uid, [], pricelist,
                            product_id.id, qty=1, partner_id=partner_id, fiscal_position=fpos)['value']
                    value['product_id'] = product_id.id
                    value['order_id'] = new_id
                    value['tax_id'] = [(6,0,value['tax_id'])]
                    sale_line_obj.create(cr, uid, value)
    
                case_obj.write(cr, uid, [case.id], {'ref': 'sale.order,%s' % new_id})
                new_ids.append(new_id)
    
            if make.close:
                case_obj.case_close(cr, uid, data)
            
            if not new_ids:
                return {}
            if len(new_ids)<=1:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'res_id': new_ids and new_ids[0]
                }
                
            else:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'res_id':new_ids
                    }
            return value

    _columns = {
                'shop_id': fields.many2one('sale.shop', 'Shop', required = True),
                'partner_id': fields.many2one('res.partner', 'Customer',  required = True,  help = 'Use this partner if there is no partner on the case'),
                'picking_policy': fields.selection([('direct','Direct Delivery'),
                                                    ('one','All at once')], 'Picking Policy', required = True),
                'product_ids': fields.many2many('product.product', 'product_sale_rel',\
                                 'sale_id', 'product_id', 'Products'),
                'analytic_account': fields.many2one('account.analytic.account', 'Analytic Account'),   
                'close': fields.boolean('Close Case', help = 'Check this to close the case after having created the sale order.'),              
               }
    _defaults = {
                 'partner_id': _selectPartner,
                 'close': lambda *a: 1
                 }
    
crm_make_sale()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
