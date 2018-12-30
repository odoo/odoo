# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def _compute_margin(self, order_id, product_id, product_uom_id):
        frm_cur = self.env.user.company_id.currency_id
        to_cur = order_id.pricelist_id.currency_id
        purchase_price = product_id.standard_price
        if product_uom_id != product_id.uom_id:
            purchase_price = self.env['product.uom']._compute_price(product_id.uom_id.id, purchase_price, to_uom_id=product_uom_id.id)
        ctx = self.env.context.copy()
        ctx['date'] = order_id.date_order
        price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
        return price

    @api.model
    def _get_purchase_price(self, pricelist, product, product_uom, date):
        frm_cur = self.env.user.company_id.currency_id
        to_cur = pricelist.currency_id
        purchase_price = product.standard_price
        if product_uom != product.uom_id:
            purchase_price = self.env['product.uom']._compute_price(product.uom_id.id, purchase_price, to_uom_id=product_uom.id)
        ctx = self.env.context.copy()
        ctx['date'] = date
        price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
        return {'purchase_price': price}


    @api.onchange('product_id', 'product_uom')
    def product_id_change_margin(self):
        if not self.order_id.pricelist_id or not self.product_id or not self.product_uom:
            return
        self.purchase_price = self._compute_margin(self.order_id, self.product_id, self.product_uom)

    @api.model
    def create(self, vals):
        # Calculation of the margin for programmatic creation of a SO line. It is therefore not
        # necessary to call product_id_change_margin manually
        if 'purchase_price' not in vals:
            order_id = self.env['sale.order'].browse(vals['order_id'])
            product_id = self.env['product.product'].browse(vals['product_id'])
            product_uom_id = self.env['product.uom'].browse(vals['product_uom'])

            vals['purchase_price'] = self._compute_margin(order_id, product_id, product_uom_id)

        return super(sale_order_line, self).create(vals)

    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = 0
            if line.product_id:
                price = line.purchase_price

                if not price:
                    from_cur = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id
                    cost = line.product_id.standard_price
                    ctx = context.copy()
                    ctx['date'] = line.order_id.date_order
                    price = self.pool['res.currency'].compute(cr, uid, from_cur.id, cur.id, cost, round=False, context=ctx)

                tmp_margin = line.price_subtotal - (price * line.product_uom_qty)
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
                'sale.order.line': (_get_order, ['margin', 'purchase_price', 'order_id'], 20),
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 20),
                }, digits_compute= dp.get_precision('Product Price')),
    }
