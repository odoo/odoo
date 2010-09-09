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
import decimal_precision as dp

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
        lead_obj = self.pool.get('crm.lead')
        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False
        lead = lead_obj.read(cr, uid, active_id, ['partner_id'])
        return lead['partner_id']

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        if context.get('active_ids', False) and context['active_ids']:
            oppr = self.pool.get('crm.lead').browse(cr, uid, context['active_ids'])
            for line in oppr:
                if not line.section_id:
                    raise osv.except_osv(_('Warning !'), _(' Sales Team is not specified.'))
        return super(crm_make_sale, self).view_init(cr, uid, fields_list, context=context)



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
        case_obj = self.pool.get('crm.lead')
        sale_obj = self.pool.get('sale.order')
        partner_obj = self.pool.get('res.partner')
        sale_line_obj = self.pool.get('sale.order.line')

        result = mod_obj._get_id(cr, uid, 'sale', 'view_sales_order_filter')
        id = mod_obj.read(cr, uid, result, ['res_id'])

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
                    'origin': 'Opportunity: %s' % str(case.id),
                    'section_id': case.section_id and case.section_id.id or False,
                    'shop_id': make.shop_id.id,
                    'partner_id': partner_id,
                    'pricelist_id': pricelist,
                    'partner_invoice_id': partner_addr['invoice'],
                    'partner_order_id': partner_addr['contact'],
                    'partner_shipping_id': partner_addr['delivery'],
                    'date_order': time.strftime('%Y-%m-%d'),
                    'fiscal_position': fpos,
                }

                if partner_id:
                    partner = partner_obj.browse(cr, uid, partner_id, context=context)
                    vals['user_id'] = partner.user_id and partner.user_id.id or uid

                if make.analytic_account.id:
                    vals['project_id'] = make.analytic_account.id
                new_id = sale_obj.create(cr, uid, vals)
                for line in make.sale_order_line:
                    value = {}
                    value['order_id'] = new_id
                    value['name'] = line.name
                    value['delay'] = line.delay
                    value['product_id'] =line.product_id and line.product_id.id or False
                    value['price_unit'] = line.price_unit
                    value['tax_id'] = line.tax_id and [(6,0,map(lambda x: x.id,line.tax_id))] or False
                    value['type'] = line.type
                    value['product_uom_qty']=line.product_uom_qty
                    value['product_uom']=line.product_uom.id
                    value['product_uos_qty']=line.product_uos_qty
                    value['product_uos']=line.product_uos and line.product_uos.id or False
                    value['product_packaging'] = line.product_packaging and line.product_packaging.id or False
                    value['discount']=line.discount
                    value['notes']=line.notes
                    sale_line_obj.create(cr, uid, value)
                stage_data = mod_obj._get_id(cr, uid, 'crm', 'stage_lead3')
                stage_data = mod_obj.read(cr, uid, stage_data, ['res_id'])
                case_obj.write(cr, uid, [case.id], {'ref': 'sale.order,%s' % new_id, 'stage_id': stage_data['res_id']})
                new_ids.append(new_id)
                message = _('Opportunity ') + " '" + case.name + "' "+ _("is converted to Sales Quotation.")
                self.log(cr, uid, case.id, message)

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
                    'res_id': new_ids
                }
            return value

    def _get_shop_id(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        cmpny_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        shop = self.pool.get('sale.shop').search(cr, uid, [('company_id', '=', cmpny_id)])
        return shop and shop[0] or False

    _columns = {
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True),
        'partner_id': fields.many2one('res.partner', 'Customer', required=True),
        'sale_order_line': fields.one2many('sale.order.make.line', 'opportunity_order_id', 'Product Line'),
        'analytic_account': fields.many2one('account.analytic.account', 'Analytic Account'),
        'close': fields.boolean('Close Case', help='Check this to close the case after having created the sale order.'),
    }
    _defaults = {
         'shop_id': _get_shop_id,
         'partner_id': _selectPartner,
         'close': 1
    }

crm_make_sale()

class sale_order_make_line(osv.osv_memory):

    def product_id_change(self, cr, uid, ids, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, packaging=False, flag=False):
        if not  partner_id:
            raise osv.except_osv(_('No Customer Defined !'), _('You have to select a customer in the sale form !\nPlease set one customer before choosing a product.'))
        date_order = time.strftime('%Y-%m-%d')
        part = self.pool.get('res.partner').browse(cr, uid, partner_id)
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        return self.pool.get('sale.order.line').product_id_change(cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag)

    _name = 'sale.order.make.line'
    _description = 'Opportunity Sale Order Line'
    _columns = {
        'opportunity_order_id': fields.many2one('crm.make.sale', 'Order Reference', required=True, ondelete='cascade', select=True, readonly=True, ),
        'name': fields.char('Description', size=256, required=True, select=True, ),
        'delay': fields.float('Delivery Lead Time', required=True, help="Number of days between the order confirmation the the shipping of the products to the customer"),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Sale Price')),
        'tax_id': fields.many2many('account.tax', 'sale_order_tax', 'order_line_id', 'tax_id', 'Taxes'),
        'type': fields.selection([('make_to_stock', 'from stock'), ('make_to_order', 'on order')], 'Procurement Method', required=True),
        'product_uom_qty': fields.float('Quantity (UoM)', digits=(16, 2), required=True, ),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, ),
        'product_uos_qty': fields.float('Quantity (UoS)'),
        'product_uos': fields.many2one('product.uom', 'Product UoS'),
        'product_packaging': fields.many2one('product.packaging', 'Packaging'),
        'discount': fields.float('Discount (%)', digits=(16, 2)),
        'notes': fields.text('Notes'),
    }
    _order = 'sequence, id'
    _defaults = {
        'discount': 0.0,
        'delay': 0.0,
        'product_uom_qty': 1,
        'product_uos_qty': 1,
        'type': 'make_to_stock',
        'product_packaging': False
    }

sale_order_make_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
