# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_real_price_currency(self, product, pricelist_dict, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param dict pricelist_dict: dict contain pricelist id and rule id
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sale order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = None
        rule_id = pricelist_dict[pricelist_id][1] if pricelist_dict.get(pricelist_id) else False
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
            if pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        product_currency = product_currency or (product.company_id and product.company_id.currency_id) or self.env.user.company_id.currency_id
        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id)

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(uom.id, 1.0, product.uom_id.id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id.id

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id')
    def _onchange_discount(self):
        self.discount = 0.0
        if not (self.product_id and self.product_uom
                and self.order_id.partner_id and self.order_id.pricelist_id
                and self.order_id.pricelist_id.discount_policy == 'without_discount'
                and self.env.user.has_group('sale.group_discount_per_so_line')):
            return

        context_partner = dict(self.env.context, partner_id=self.order_id.partner_id.id)
        pricelist_context = dict(context_partner, uom=self.product_uom.id, date=self.order_id.date_order)

        list_price = self.order_id.pricelist_id.with_context(pricelist_context).price_rule_get(self.product_id.id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        new_list_price, currency_id = self.with_context(context_partner)._get_real_price_currency(self.product_id, list_price, self.product_uom_qty, self.product_uom, self.order_id.pricelist_id.id)
        new_list_price = self.env['account.tax']._fix_tax_included_price(new_list_price, self.product_id.taxes_id, self.tax_id)
        list_price = list_price[self.order_id.pricelist_id.id][0]

        if list_price != 0 and new_list_price != 0:
            if self.product_id.company_id and self.order_id.pricelist_id.currency_id != self.product_id.company_id.currency_id:
                # new_list_price is in company's currency while price in pricelist currency
                ctx = dict(context_partner, date=self.order_id.date_order)
                new_list_price = self.env['res.currency'].browse(currency_id).with_context(ctx).compute(new_list_price, self.order_id.pricelist_id.currency_id)
            discount = (new_list_price - list_price) / new_list_price * 100
            if discount > 0:
                self.discount = discount

    @api.multi
    def _get_display_price(self, product):
        if self.order_id.pricelist_id.discount_policy == 'without_discount':
            return self.order_id.company_id.currency_id.compute(
                product.lst_price, self.order_id.pricelist_id.currency_id)
        return super(SaleOrderLine, self)._get_display_price(product)
