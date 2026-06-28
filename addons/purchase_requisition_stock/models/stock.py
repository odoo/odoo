# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        res = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)
        values = values[0]
        res['partner_ref'] = values['supplier'].purchase_requisition_id.name
        res['requisition_id'] = values['supplier'].purchase_requisition_id.id
        if values['supplier'].purchase_requisition_id.currency_id:
            res['currency_id'] = values['supplier'].purchase_requisition_id.currency_id.id
        return res

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super(StockRule, self)._make_po_get_domain(company_id, values, partner)
        if 'supplier' in values and values['supplier'].purchase_requisition_id:
            domain += (
                ('requisition_id', '=',
                 values['supplier'].purchase_requisition_id.id),
            )
        return domain


class StockMove(models.Model):
    _inherit = 'stock.move'

    requisition_line_ids = fields.One2many('purchase.requisition.line', 'move_dest_id')

    def _get_upstream_documents_and_responsibles(self, visited):
        # People without purchase rights should be able to do this operation
        requisition_lines_sudo = self.sudo().requisition_line_ids
        if requisition_lines_sudo:
            return [(requisition_line.requisition_id, requisition_line.requisition_id.user_id, visited) for requisition_line in requisition_lines_sudo if requisition_line.requisition_id.state not in ('done', 'cancel')]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)


class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _quantity_in_progress(self):
        res = super()._quantity_in_progress()
        requisitions = self.env['purchase.requisition'].search(
            [('state', '=', 'draft'), ('origin', 'in', self.mapped('name'))])
        if not requisitions:
            return res
        requisitions.read(['origin'])
        map_requisitions = {r.id: r.origin for r in requisitions}
        data_group = self.env['purchase.requisition.line'].sudo().read_group(
            [('requisition_id', 'in', requisitions.ids),
             ('product_id', 'in', self.product_id.ids),
             ('move_dest_id', '=', False)],
            ['product_id', 'product_qty', 'product_uom_id', 'requisition_id'], ['requisition_id', 'product_id', 'product_uom_id'])
        data = defaultdict(float)
        Uom = self.env['uom.uom']
        Product = self.env['product.product']
        for group in data_group:
            key = (
                map_requisitions[group['requisition_id'][0]], group['product_id'][0])
            data[key] += Uom.browse(group['product_qty'])._compute_quantity(
                group['product_qty'], Product.browse(group['product_id'][0]).uom_id, round=False)
        for op in self:
            key = (op.name, op.product_id.id)
            qty = data.get(key, 0)
            if not qty:
                continue
            res[op.id] += op.product_id.uom_id._compute_quantity(
                qty, op.product_uom, round=False)
        return res
