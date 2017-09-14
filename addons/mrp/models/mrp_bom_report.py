# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MrpBomReport(models.TransientModel):
    _name = 'mrp.bom.report'
    _description = "Mrp Bom Report"

    def _get_price(self, bom, line_qty):
        price = 0
        for line in bom.bom_line_ids:
            if line.child_bom_id:
                sub_price = self._get_price(line.child_bom_id, line.product_qty)
                price += sub_price * line.product_qty
            else:
                prod_qty = (line.product_qty * line_qty) / bom.product_qty
                price += (line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * prod_qty) / line_qty
        return price

    @api.model
    def get_lines(self, bom_id=False, line_qty=False, level=False):
        context = self.env.context or {}
        datas = []
        bom = self.env['mrp.bom'].browse(bom_id or context.get('active_id'))

        if bom:
            products = bom.product_id or bom.product_tmpl_id.product_variant_ids or bom.product_tmpl_id

            for product in products:
                lines = {}
                components = []
                lines.update({
                    'bom': bom,
                    'bom_prod_name': product.display_name,
                    'currency': self.env.user.company_id.currency_id,
                    'product': product,
                    'total': 0.0
                })
                for line in bom.bom_line_ids:
                    if line._skip_bom_line(product):
                        continue
                    if line.child_bom_id:
                        price = self._get_price(line.child_bom_id, line.product_qty)
                    else:
                        price = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id)
                    prod_qty = line_qty * (line.product_qty / bom.product_qty) if line_qty else line.product_qty
                    total = prod_qty * price

                    components.append({
                        'prod_id': line.product_id.id,
                        'prod_name': line.product_id.display_name,
                        'prod_qty': prod_qty,
                        'prod_uom': line.product_uom_id.name,
                        'prod_cost': price,
                        'parent_id': bom_id,
                        'total': total,
                        'child_bom': line.child_bom_id.id,
                        'level': level or 0
                    })
                    lines['total'] += total
                lines['components'] = components
                lines['components'] and datas.append(lines)
        return datas

    @api.model
    def get_html(self, given_context=None, bom_id=False, line_qty=False, level=False):
        rcontext = {}
        rcontext['datas'] = self.with_context(given_context).get_lines(bom_id, line_qty, level)
        if bom_id:
            rcontext['data'] = rcontext['datas'][0]
            return self.env.ref('mrp.report_mrp_bom_line').render(rcontext)
        else:
            return self.env.ref('mrp.report_mrp_bom').render(rcontext)
