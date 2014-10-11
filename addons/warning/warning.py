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

from openerp.osv import fields,osv
from openerp.tools.translate import _

WARNING_MESSAGE = [
                   ('no-message','No Message'),
                   ('warning','Warning'),
                   ('block','Blocking Message')
                   ]

WARNING_HELP = _('Selecting the "Warning" option will notify user with the message, Selecting "Blocking Message" will throw an exception with the message and block the flow. The Message has to be written in the next field.')

WARNING_FIELDS = {
    'sale.order': ('sale','partner_id','res.partner'),
    'account.invoice': ('invoice','partner_id','res.partner'),
    'purchase.order': ('purchase', 'partner_id', 'res.partner'),
    'stock.picking': ('picking', 'partner_id', 'res.partner'),
    'stock.picking.in': ('picking', 'partner_id', 'res.partner'),
    'stock.picking.out': ('picking', 'partner_id', 'res.partner'),
    'sale.order.line': ('sale_line','product_id','product.product'),
    'purchase.order.line': ('purchase_line', 'product_id', 'product.product'),
}

def warning_block_message(self, cr, uid, ids, model, context=None):
    warn_field = '%s_warn' % (WARNING_FIELDS[model][0])
    warn_msg_field = '%s_warn_msg' % (WARNING_FIELDS[model][0])
    warning = {}
    for record in self.read(cr, uid, ids, ['name', warn_field, warn_msg_field], context=context):
        if record[warn_field] != 'no-message':
            title = _("Warning for %s") % record['name']
            message = record[warn_msg_field]
            warning = {'title': title, 'message': message, 'warn_field': record.get(warn_field)}
            if record[warn_field] == 'block':
                raise osv.except_osv(_('Blocking')+" "+ warning.get('title'), warning.get('message'))            
    return warning

def onchange_warning(self, cr, uid, ids, model, res_id, result={}, context=None):
    warning = {}
    if res_id:
        warning = warning_block_message(self.pool.get(model), cr, uid, [res_id], self._name, context=context)
        title = warning.get('title', False)
        message = warning.get('message', False)
        if result.get('warning',False):
            warning['title'] = title and title +' & '+ result['warning']['title'] or result['warning']['title']
            warning['message'] = message and message + ' ' + result['warning']['message'] or result['warning']['message']
    return {'value': result.get('value',{}), 'warning':warning}

def raise_block_warning(self, cr, uid, vals, context=None):
    rel_field = WARNING_FIELDS[self._name][1]
    rel_model = WARNING_FIELDS[self._name][2]
    rel_id = vals.get(rel_field, False)
    if rel_id:
        warning = warning_block_message(self.pool.get(rel_model), cr, uid, [rel_id], self._name, context=context)
    return True

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'sale_warn' : fields.selection(WARNING_MESSAGE, 'Sales Order', help=WARNING_HELP, required=True),
        'sale_warn_msg' : fields.text('Message for Sales Order'),
        'purchase_warn' : fields.selection(WARNING_MESSAGE, 'Purchase Order', help=WARNING_HELP, required=True),
        'purchase_warn_msg' : fields.text('Message for Purchase Order'),
        'picking_warn' : fields.selection(WARNING_MESSAGE, 'Stock Picking', help=WARNING_HELP, required=True),
        'picking_warn_msg' : fields.text('Message for Stock Picking'),
        'invoice_warn' : fields.selection(WARNING_MESSAGE, 'Invoice', help=WARNING_HELP, required=True),
        'invoice_warn_msg' : fields.text('Message for Invoice'),
    }
    _defaults = {
         'sale_warn' : 'no-message',
         'purchase_warn' : 'no-message',
         'picking_warn' : 'no-message',
         'invoice_warn' : 'no-message',
    }



class sale_order(osv.osv):
    _inherit = 'sale.order'
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result =  super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context=context)
        return onchange_warning(self, cr ,uid, ids, 'res.partner',  part, result=result, context=context)
    
    def create(self, cr, uid, vals, context=None):
        raise_block_warning(self, cr, uid, vals, context=context)
        return super(sale_order, self).create(cr, uid, vals, context=context)
 
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('partner_id'):
            raise_block_warning(self, cr, uid, vals, context)
        return super(sale_order,self).write(cr, uid, ids, vals, context)

class purchase_order(osv.osv):
    _inherit = 'purchase.order'
    def onchange_partner_id(self, cr, uid, ids, part):
        result =  super(purchase_order, self).onchange_partner_id(cr, uid, ids, part)
        return onchange_warning(self, cr, uid, ids, 'res.partner',  part, result=result)

    def create(self, cr, uid, vals, context=None):
        raise_block_warning(self, cr, uid, vals, context=context)
        return super(purchase_order, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('partner_id'):
            raise_block_warning(self, cr, uid, vals, context)
        return super(purchase_order,self).write(cr, uid, ids, vals, context)

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    def onchange_partner_id(self, cr, uid, ids, type, partner_id,
        date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False):
        result =  super(account_invoice, self).onchange_partner_id(cr, uid, ids, type, partner_id,
        date_invoice=date_invoice, payment_term=payment_term, 
        partner_bank_id=partner_bank_id, company_id=company_id)
        return onchange_warning(self, cr, uid, ids, 'res.partner',  partner_id, result=result)

    def create(self, cr, uid, vals, context=None):
        raise_block_warning(self, cr, uid, vals, context=context)
        return super(account_invoice, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('partner_id'):
            raise_block_warning(self, cr, uid, vals, context)
        return super(account_invoice,self).write(cr, uid, ids, vals, context)


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def onchange_partner_in(self, cr, uid, ids, partner_id=None, context=None):
        if not partner_id:
            return {}
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        warning = {}
        title = False
        message = False
        if partner.picking_warn != 'no-message':
            title = _("Warning for %s") % partner.name
            message = partner.picking_warn_msg
            warning = {
                'title': title,
                'message': message
            }
            if partner.picking_warn == 'block':
                return {'value': {'partner_id': False}, 'warning': warning}

        result =  super(stock_picking_in, self).onchange_partner_in(cr, uid, ids, partner_id, context)
        if result.get('warning',False):
            warning['title'] = title and title +' & '+ result['warning']['title'] or result['warning']['title']
            warning['message'] = message and message + ' ' + result['warning']['message'] or result['warning']['message']

        return {'value': result.get('value',{}), 'warning':warning}


class product_product(osv.osv):
    _inherit = 'product.template'
    _columns = {
         'sale_line_warn' : fields.selection(WARNING_MESSAGE,'Sales Order Line', help=WARNING_HELP, required=True),
         'sale_line_warn_msg' : fields.text('Message for Sales Order Line'),
         'purchase_line_warn' : fields.selection(WARNING_MESSAGE,'Purchase Order Line', help=WARNING_HELP, required=True),
         'purchase_line_warn_msg' : fields.text('Message for Purchase Order Line'),
     }

    _defaults = {
         'sale_line_warn' : 'no-message',
         'purchase_line_warn' : 'no-message',
    }


class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position=False, flag=False, warehouse_id=False, context=None):
        result =  super(sale_order_line, self).product_id_change( cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        return onchange_warning(self, cr ,uid, ids, 'product.product',  product, result=result, context=context)

    def create(self, cr, uid, vals, context=None):
        raise_block_warning(self, cr, uid, vals, context=context)
        return super(sale_order_line,self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('product_id'):
            raise_block_warning(self, cr, uid, vals, context)
        return super(sale_order_line,self).write(cr, uid, ids, vals, context)     


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'
    def onchange_product_id(self,cr, uid, ids, pricelist, product, qty, uom,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', notes=False, context=None):
        result =  super(purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist, product, qty, uom,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned, name=name, 
            price_unit=price_unit, context=context)
        return onchange_warning(self, cr, uid, ids, 'product.product',  product, result=result, context=context)

    def create(self, cr, uid, vals, context=None):
        raise_block_warning(self, cr, uid, vals, context=context)
        return super(purchase_order_line,self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('product_id'):
            raise_block_warning(self, cr, uid, vals, context)
        return super(purchase_order_line,self).write(cr, uid, ids, vals, context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
