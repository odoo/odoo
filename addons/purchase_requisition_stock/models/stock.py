# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        res = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)
        values = values[0]
        requisition = self._get_supplier_requisition(values)
        res['partner_ref'] = requisition.name
        res['requisition_ids'] = [Command.set(requisition.ids)]
        if requisition.currency_id:
            res['currency_id'] = requisition.currency_id.id
        return res

    def _get_supplier_requisition(self, values):
        # the seller information only holds a pricelist when it does not come from the purchase history
        seller_info = values.get('supplier') or {}
        return seller_info.get('supplierinfo', self.env['product.supplierinfo']).purchase_requisition_id

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        if not self._get_supplier_requisition(values):
            product_id = product_id.with_context(exclude_blanket_orders=True)
        return super()._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)


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
