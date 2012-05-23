##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag)
        if product:
            price = self.pool.get('product.product').browse(cr, uid, product).standard_price
            partner_pricelist = self.pool.get('res.partner').browse(cr, uid, partner_id).property_product_pricelist

            if partner_pricelist:
                to_cur = partner_pricelist.currency_id.id
                frm_cur = self.pool.get('res.users').browse(cr, uid, uid).company_id.currency_id.id
                price = self.pool.get('res.currency').compute(cr, uid, frm_cur, to_cur, price, round=False)

            res['value'].update({'purchase_price': price})
        return res

    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = 0
            if line.product_id:
                if line.purchase_price:
                    res[line.id] = round((line.price_unit*line.product_uos_qty*(100.0-line.discount)/100.0) -(line.purchase_price*line.product_uos_qty), 2)
                else:
                    res[line.id] = round((line.price_unit*line.product_uos_qty*(100.0-line.discount)/100.0) -(line.product_id.standard_price*line.product_uos_qty), 2)
        return res

    _columns = {
        'margin': fields.function(_product_margin, method=True, string='Margin', store=True),
        'purchase_price': fields.float('Cost Price', digits=(16,2))
    }

sale_order_line()

class sale_order(osv.osv):
    _inherit = "sale.order"

    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        sale_line_obj = self.pool.get('sale.order.line')
        for sale in self.browse(cr, uid, ids, context=context):
            result[sale.id] = 0.0
            for line in sale.order_line:
                sale_line_obj.write(cr, uid, [line.id], {'order_id': sale.id}, context)
                result[sale.id] += line.margin or 0.0
        return result

    _columns = {
        'margin': fields.function(_product_margin, method=True, string='Margin', store=True, help="It gives profitability by calculating the difference between the Unit Price and Cost Price."),
    }

sale_order()

class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    _columns = {
        'invoice_ids': fields.many2many('account.invoice', 'picking_invoice_rel', 'picking_id', 'invoice_id', 'Invoices', domain=[('type', '=', 'out_invoice')]),
    }

    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        # need to carify with new requirement
        invoice_ids = []            
        if context is None:
            context = {}
        picking_obj = self.pool.get('stock.picking')
        res = super(stock_picking, self).action_invoice_create(cr, uid, ids, journal_id=journal_id,group=group, type=type, context=context)        
        invoice_ids = res.values()
        picking_obj.write(cr, uid, ids, {'invoice_ids': [[6, 0, invoice_ids]]})
        return res

stock_picking()

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    _columns = {
        'cost_price': fields.float('Cost Price', digits=(16, 2)),
    }
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('product_id', False):
            res = self.pool.get('product.product').read(cr, uid, [vals['product_id']], ['standard_price'])
            vals['cost_price'] = res[0]['standard_price']
        return super(account_invoice_line, self).write(cr, uid, ids, vals, context)

    def create(self, cr, uid, vals, context=None):
        if vals.get('product_id',False):
            res = self.pool.get('product.product').read(cr, uid, [vals['product_id']], ['standard_price'])
            vals['cost_price'] = res[0]['standard_price']
        return super(account_invoice_line, self).create(cr, uid, vals, context)

account_invoice_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
