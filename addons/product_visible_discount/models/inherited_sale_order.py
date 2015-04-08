# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def get_real_price_currency(self, product, res_dict, qty, uom, pricelist):
        """Retrieve the price before applying the pricelist"""
        PriceItem = self.env['product.pricelist.item']
        PriceType = self.env['product.price.type']
        field_name = 'list_price'
        rule_id = res_dict.get(pricelist) and res_dict[pricelist][1] or False
        if rule_id:
            item_base = PriceItem.browse(rule_id).base
            if item_base > 0:
                price_type = PriceType.browse(item_base)
                field_name = price_type.field
                currency_id = price_type.currency_id

        if not currency_id:
            currency_id = product.company_id.currency_id.id
        factor = 1.0
        if uom and uom != product.uom_id.id:
            # the unit price is in a different uom
            factor = self.env['product.uom']._compute_qty(uom, 1.0, product.uom_id.id)
        return getattr(product, field_name) * factor, currency_id

    @api.multi
    def product_id_change(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position_id=False, flag=False):

        Product = self.env['product.product']
        res = super(SaleOrderLine, self).product_id_change(pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id,
            lang, update_tax, date_order, packaging=packaging, fiscal_position_id=fiscal_position_id, flag=flag)

        price_unit = res['value'].get('price_unit', False)
        if not (price_unit and product and pricelist and self.env['res.users'].has_group('sale.group_discount_per_so_line')):
            return res

        uom = res['value'].get('product_uom', uom)
        product = Product.browse(product)
        context = dict(self.env.context, lang=lang, partner_id=partner_id)
        pricelist_context = dict(context, uom=uom, date=date_order)
        product_price = self.env['product.pricelist'].browse(pricelist)
        list_price = product_price.with_context(pricelist_context).price_rule_get(
                product.id, qty or 1.0, partner_id)

        new_list_price, currency_id = self.get_real_price_currency(product, list_price, qty, uom, pricelist)
        if product_price.visible_discount and list_price[pricelist][0] != 0 and new_list_price != 0:
            if product.company_id and product_price.currency_id != product.company_id.currency_id:
                # new_list_price is in company's currency while price in pricelist currency
                ctx = dict(context, date=date_order)
                new_list_price = product.company_id.currency_id.with_context(ctx).compute(
                    new_list_price, product_price.currency_id)

            discount = (new_list_price - price_unit) / new_list_price * 100
            if discount > 0:
                res['value']['price_unit'] = new_list_price
                res['value']['discount'] = discount
            else:
                res['value']['discount'] = 0.0
        else:
            res['value']['discount'] = 0.0
        return res
