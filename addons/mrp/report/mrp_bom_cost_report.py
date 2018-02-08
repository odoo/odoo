# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MrpBomCost(models.AbstractModel):
    _name = 'report.mrp.mrp_bom_cost_report'

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
                product_line = {'bom': bom, 'name': product.name, 'lines': [], 'total': 0.0,
                                'currency': self.env.user.company_id.currency_id,
                                'product_uom_qty': bom.product_qty,
                                'product_uom': bom.product_uom_id,
                                'attributes': attributes}
                total = 0.0
                for bom_line, line_data in result2:
                    price_uom = bom_line.product_id.uom_id._compute_price(bom_line.product_id.standard_price, bom_line.product_uom_id)
                    line = {
                        'product_id': bom_line.product_id,
                        'product_uom_qty': line_data['qty'], #line_data needed for phantom bom explosion
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
    def get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        res = self.get_lines(boms)
        return {'lines': res}
