# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_subcontracting_line(self, bom, seller, level, bom_quantity):
        ratio_uom_seller = seller.product_uom.ratio / bom.product_uom_id.ratio
        return {
            'name': seller.name.display_name,
            'partner_id': seller.name.id,
            'quantity': bom_quantity,
            'uom': bom.product_uom_id.name,
            'prod_cost': seller.price / ratio_uom_seller * bom_quantity,
            'bom_cost': seller.price / ratio_uom_seller * bom_quantity,
            'level': level or 0
        }

    def _get_price(self, bom, factor, product):
        price = super()._get_price(bom, factor, product)
        if bom and bom.type == 'subcontract':
            bom_quantity = bom.product_qty * factor
            seller = product._select_seller(quantity=bom_quantity, uom_id=bom.product_uom_id, params={'subcontractor_ids': bom.subcontractor_ids})
            if seller:
                price += seller.product_uom._compute_price(seller.price, product.uom_id) * bom_quantity
        return price

    def _get_bom(self, bom_id=False, product_id=False, line_qty=False, line_id=False, level=False):
        res = super(ReportBomStructure, self)._get_bom(bom_id, product_id, line_qty, line_id, level)
        bom = res['bom']
        if bom and bom.type == 'subcontract':
            bom_quantity = line_qty
            if line_id:
                current_line = self.env['mrp.bom.line'].browse(int(line_id))
                bom_quantity = current_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id)

            seller = res['product']._select_seller(quantity=bom_quantity, uom_id=bom.product_uom_id, params={'subcontractor_ids': bom.subcontractor_ids})
            if seller:
                res['subcontracting'] = self._get_subcontracting_line(bom, seller, level, bom_quantity)
                res['total'] += res['subcontracting']['bom_cost']
                res['bom_cost'] += res['subcontracting']['bom_cost']
        return res

    def _get_sub_lines(self, bom, product_id, line_qty, line_id, level, child_bom_ids, unfolded):
        res = super()._get_sub_lines(bom, product_id, line_qty, line_id, level, child_bom_ids, unfolded)
        if bom and bom.type == 'subcontract':
            product = self.env['product.product'].browse(product_id)

            bom_quantity = line_qty
            if line_id:
                current_line = self.env['mrp.bom.line'].browse(int(line_id))
                bom_quantity = current_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id)

            seller = product._select_seller(quantity=bom_quantity, uom_id=bom.product_uom_id, params={'subcontractor_ids': bom.subcontractor_ids})
            if seller:
                values_sub = self._get_subcontracting_line(bom, seller, level, bom_quantity)
                values_sub['type'] = 'bom'
                values_sub['name'] = _("Subcontracting: ") + values_sub['name']
                res.append(values_sub)

        return res
