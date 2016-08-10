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
                result, result2 = bom.explode(product, 1)
                product_line = {'name': product.name, 'lines': [], 'total': 0.0,
                                'currency': self.env.user.company_id.currency_id,
                                'product_uom_qty': bom.product_qty,
                                'product_uom': bom.product_uom_id,
                                'attributes': attributes}
                total = 0.0
                for bom_line, line_data in result2:
                    line_product = line_data['product']
                    price_uom = self.env['product.uom']._compute_qty(line_product.uom_id.id, line_product.standard_price, bom_line.product_uom_id.id)
                    line = {
                        'product_id': line_product,
                        'product_uom_qty': line_data['qty'],
                        'product_uom': bom_line.product_uom_id,
                        'price_unit': price_uom,
                        'total_price': price_uom * line_data['qty'],
                    }
                    total += line['total_price']
                    product_line['lines'] += [line]
                product_line['total'] = total
                product_lines += [product_line]
        return product_lines

    @api.model
    def render_html(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        res = self.get_lines(boms)
        return self.env['report'].render('mrp.mrp_bom_cost', {'lines': res})
