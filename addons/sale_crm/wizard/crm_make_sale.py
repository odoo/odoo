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
import time
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

        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False
        lead_obj = self.pool.get('crm.lead')
        lead = lead_obj.read(cr, uid, active_id, ['partner_id'])
        return  lead['partner_id']

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
                    'origin': 'Opportunity:%s' % str(case.id),
                    'section_id': case.section_id and case.section_id.id or False,
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
                for line in make.sale_order_line:
                    value = sale_line_obj.product_id_change(cr, uid, [], pricelist,
                            line.product_id.id, qty=1, partner_id=partner_id, fiscal_position=fpos)['value']
                    value['product_id'] =line.product_id.id
                    value['order_id'] = new_id
                    value['tax_id'] = [(6,0,line['tax_id'])]
                    value['product_uom_qty']=line.product_uom_qty
                    value['discount']=line.discount
                    value['product_uom']=line.product_uom.id
                    sale_line_obj.create(cr, uid, value)
                case_obj.write(cr, uid, [case.id], {'ref': 'sale.order,%s' % new_id})
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

    _columns = {
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True),
        'partner_id': fields.many2one('res.partner', 'Customer', required=True, help='Use this partner if there is no partner on the Opportunity'),
        'sale_order_line': fields.one2many('sale.order.make.line', 'order_line', 'Product Line', readonly=True, states={'draft': [('readonly', False)]}),
        'analytic_account': fields.many2one('account.analytic.account', 'Analytic Account'),
        'close': fields.boolean('Close Case', help='Check this to close the case after having created the sale order.'),
    }
    _defaults = {
         'partner_id': _selectPartner,
         'close': 1
    }

crm_make_sale()

class sale_order_make_line(osv.osv_memory):


    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        if not  partner_id:
            raise osv.except_osv(_('No Customer Defined !'), _('You have to select a customer in the sale form !\nPlease set one customer before choosing a product.'))
        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        context = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0, 'product_packaging': False,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}

        if not date_order:
            date_order = time.strftime('%Y-%m-%d')

        result = {}
        product_obj = product_obj.browse(cr, uid, product, context=context)
        if not packaging and product_obj.packaging:
            packaging = product_obj.packaging[0].id
            result['product_packaging'] = packaging

        if packaging:
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            pack = self.pool.get('product.packaging').browse(cr, uid, packaging, context=context)
            q = product_uom_obj._compute_qty(cr, uid, uom, pack.qty, default_uom)
#            qty = qty - qty % q + q
            if qty and (q and not (qty % q) == 0):
                ean = pack.ean
                qty_pack = pack.qty
                type_ul = pack.ul
                warn_msg = _("You selected a quantity of %d Units.\nBut it's not compatible with the selected packaging.\nHere is a proposition of quantities according to the packaging: ") % (qty)
                warn_msg = warn_msg + "\n\n" + _("EAN: ") + str(ean) + _(" Quantity: ") + str(qty_pack) + _(" Type of ul: ") + str(type_ul.name)
                warning = {
                    'title': _('Picking Information !'),
                    'message': warn_msg
                    }
            result['product_uom_qty'] = qty

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False

        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False
        if product_obj.description_sale:
            result['notes'] = product_obj.description_sale
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
        if update_tax: #The quantity only have changed
            result['delay'] = (product_obj.sale_delay or 0.0)
            partner = partner_obj.browse(cr, uid, partner_id)
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)
            result.update({'type': product_obj.procure_method})

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context)[0][1]
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}

        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty

        if not uom2:
            uom2 = product_obj.uom_id
        return {'value': result, 'domain': domain, 'warning': warning}

    def product_uom_change(self, cursor, user, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False):
        res = self.product_id_change(cursor, user, ids, pricelist, product,
                qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name,
                partner_id=partner_id, lang=lang, update_tax=update_tax,
                date_order=date_order)
        if 'product_uom' in res['value']:
            del res['value']['product_uom']
        if not uom:
            res['value']['price_unit'] = 0.0
        return res

    _name = 'sale.order.make.line'
    _description = 'Sale Order Line'
    _columns = {
        'order_line': fields.many2one('crm.make.sale', 'Order Reference', required=True, ondelete='cascade', select=True, readonly=True, ),
        'order_id': fields.many2one('sale.order', 'Order Reference', required=True, ondelete='cascade', select=True, readonly=True, ),
        'name': fields.char('Description', size=256, required=True, select=True, readonly=True, ),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of sale order lines."),
        'delay': fields.float('Delivery Lead Time', required=True, help="Number of days between the order confirmation the the shipping of the products to the customer", readonly=True, ),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
        'procurement_id': fields.many2one('procurement.order', 'Procurement'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Sale Price'), readonly=True, ),
        'tax_id': fields.many2many('account.tax', 'sale_order_tax', 'order_line_id', 'tax_id', 'Taxes', readonly=True, states={'draft':[('readonly',False)]}),
        'type': fields.selection([('make_to_stock', 'from stock'), ('make_to_order', 'on order')], 'Procurement Method', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'product_uom_qty': fields.float('Quantity (UoM)', digits=(16, 2), required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'product_uos_qty': fields.float('Quantity (UoS)', readonly=True, states={'draft':[('readonly',False)]}),
        'product_uos': fields.many2one('product.uom', 'Product UoS'),
        'product_packaging': fields.many2one('product.packaging', 'Packaging'),
        'discount': fields.float('Discount (%)', digits=(16, 2), readonly=True, states={'draft':[('readonly',False)]}),
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
