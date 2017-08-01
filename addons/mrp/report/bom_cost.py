# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class MrpBomCost(models.AbstractModel):
    _name = 'report.mrp_bom_cost'

    @api.multi
    def get_lines(self, boms):
        product_lines = []
        for bom in boms:
            products = bom.product_id
            if not products:
                products = bom.product_tmpl_id.product_variant_ids
            for product in products:
                attributes = []
                for value in product.attribute_value_ids:
                    attributes += [(value.attribute_id.name, value.name)]
                result, result2 = self.env['mrp.bom']._bom_explode(bom, product, 1)
                product_line = {'name': product.name, 'lines': [], 'total': 0.0,
                                'currency': self.env.user.company_id.currency_id,
                                'product_uom_qty': bom.product_qty,
                                'product_uom': bom.product_uom,
                                'attributes': attributes}
                total = 0.0
                for bom_line in result:
                    line_product = self.env['product.product'].browse(bom_line['product_id'])
                    price_uom = self.env['product.uom']._compute_price(line_product.uom_id.id, line_product.standard_price, bom_line['product_uom'])
                    line = {
                        'product_id': line_product,
                        'product_uom_qty': bom_line['product_qty'],
                        'product_uom': self.env['product.uom'].browse(bom_line['product_uom']),
                        'price_unit': price_uom,
                        'total_price': price_uom * bom_line['product_qty'],
                    }
                    total += line['total_price']
                    product_line['lines'] += [line]
                product_line['total'] = total
                product_lines += [product_line]
        return product_lines

    @api.multi
    def render_html(self, data=None):
        boms = self.env['mrp.bom'].browse(self.ids)
        res = self.get_lines(boms)
        return self.env['report'].render('mrp.mrp_bom_cost', {'lines': res})
