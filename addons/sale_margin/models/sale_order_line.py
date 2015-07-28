# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position_id=False, flag=False, context=None):
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position_id=fiscal_position_id, flag=flag, context=context)
        if not pricelist:
            return res
        if context is None:
            context = {}
        frm_cur = self.pool.get('res.users').browse(cr, uid, uid).company_id.currency_id.id
        to_cur = self.pool.get('product.pricelist').browse(cr, uid, [pricelist])[0].currency_id.id
        if product:
            product = self.pool['product.product'].browse(cr, uid, product, context=context)
            purchase_price = product.standard_price
            to_uom = res.get('product_uom', uom)
            if to_uom != product.uom_id.id:
                purchase_price = self.pool['product.uom']._compute_price(cr, uid, product.uom_id.id, purchase_price, to_uom)
            ctx = context.copy()
            ctx['date'] = date_order
            price = self.pool.get('res.currency').compute(cr, uid, frm_cur, to_cur, purchase_price, round=False, context=ctx)
            res['value'].update({'purchase_price': price})
        return res

    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = 0
            if line.product_id:
                tmp_margin = line.price_subtotal - ((line.purchase_price or line.product_id.standard_price) * line.product_uos_qty)
                res[line.id] = cur_obj.round(cr, uid, cur, tmp_margin)
        return res

    _columns = {
        'margin': fields.function(_product_margin, string='Margin', digits_compute= dp.get_precision('Product Price'),
              store = True),
        'purchase_price': fields.float('Cost Price', digits_compute= dp.get_precision('Product Price'))
    }
