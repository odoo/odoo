# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

import openerp.addons.decimal_precision as dp

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin = fields.Float(compute='_product_margin', digits=dp.get_precision('Product Price'), store=True)
    purchase_price = fields.Float(string='Cost Price', digits=dp.get_precision('Product Price'))

    @api.multi
    def product_id_change(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position_id=False, flag=False):
        result = super(SaleOrderLine, self).product_id_change(pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position_id=fiscal_position_id, flag=flag)
        frm_cur = self.env.user.company_id.currency_id
        to_cur = self.env['product.pricelist'].browse([pricelist]).currency_id
        if product:
            product = self.env['product.product'].browse(product)
            purchase_price = product.standard_price
            to_uom = result.get('product_uom', uom)
            if to_uom != product.uom_id.id:
                purchase_price = self.env['product.uom']._compute_price(
                    product.uom_id.id, purchase_price, to_uom)
            ctx = dict(self._context)
            ctx['date'] = date_order
            price = frm_cur.compute(purchase_price, to_cur, round=False)
            result['value']['purchase_price'] = price
        return result

    @api.one
    @api.depends('purchase_price', 'product_uos_qty', 'price_unit')
    def _product_margin(self):
        cur = self.order_id.pricelist_id.currency_id
        self.margin = cur.round(self.price_subtotal - ((self.purchase_price or self.product_id.standard_price) * self.product_uos_qty))

class SaleOrder(models.Model):
    _inherit = "sale.order"

    margin = fields.Monetary(compute='_product_margin', help="It gives profitability by calculating the difference between the Unit Price and the cost price.", currency_field='currency_id', digits=dp.get_precision('Product Price'),store=True)

    @api.one
    @api.depends('order_line.margin')
    def _product_margin(self):
        self.margin = sum(line.margin for line in self.order_line if line.state != 'cancel') or 0.0
