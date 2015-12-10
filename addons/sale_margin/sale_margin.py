# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    @api.multi
    @api.onchange('product_id', 'product_uom')
    def product_id_change_margin(self):
        for line in self:
            if line.order_id.pricelist_id:
                frm_cur = self.env.user.company_id.currency_id
                to_cur = line.order_id.pricelist_id.currency_id
                purchase_price = line.product_id.standard_price
                if line.product_uom != line.product_id.uom_id:
                    purchase_price = self.env['product.uom']._compute_price(line.product_id.uom_id.id, purchase_price, to_uom_id=line.product_uom.id)
                ctx = self.env.context.copy()
                ctx['date'] = line.order_id.date_order
                price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
                line.purchase_price = price

    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = 0
            if line.product_id:
                tmp_margin = line.price_subtotal - ((line.purchase_price or line.product_id.standard_price) * line.product_uom_qty)
                res[line.id] = cur_obj.round(cr, uid, cur, tmp_margin)
        return res

    _columns = {
        'margin': fields.function(_product_margin, string='Margin', digits_compute= dp.get_precision('Product Price'),
              store = True),
        'purchase_price': fields.float('Cost', digits_compute= dp.get_precision('Product Price'))
    }


class sale_order(osv.osv):
    _inherit = "sale.order"

    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for sale in self.browse(cr, uid, ids, context=context):
            result[sale.id] = 0.0
            for line in sale.order_line:
                if line.state == 'cancel':
                    continue
                result[sale.id] += line.margin or 0.0
        return result

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'margin': fields.function(_product_margin, string='Margin', help="It gives profitability by calculating the difference between the Unit Price and the cost.", store={
                'sale.order.line': (_get_order, ['margin', 'purchase_price'], 20),
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 20),
                }, digits_compute= dp.get_precision('Product Price')),
    }
