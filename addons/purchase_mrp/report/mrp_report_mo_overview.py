# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ReportMoOverview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_extra_replenishments(self, product):
        res = super()._get_extra_replenishments(product)
        domain = [('state', 'in', ['draft', 'sent', 'to approve']), ('product_id', '=', product.id)]
        warehouse_id = self.env['stock.warehouse']._get_warehouse_id_from_context()
        if warehouse_id:
            domain += [('order_id.picking_type_id.warehouse_id', '=', warehouse_id)]
        po_lines = self.env['purchase.order.line'].search(domain, order='date_planned, id')

        for po_line in po_lines:
            line_qty = po_line.product_qty
            # Need to fetch every move connected to a manufacturing order from this PO line. This can happen when:
            # - Multiple MOs are linked to a single PO line (e.g. Same MTO component for multiple MO).
            # - A MO has a backorder / is splitted.
            dest_moves = self.env['stock.move'].browse(po_line.move_dest_ids._rollup_move_dests())
            for move in dest_moves:
                if not move.raw_material_production_id:
                    continue
                prod_qty = min(line_qty, move.product_uom._compute_quantity(move.product_uom_qty, po_line.product_uom))
                res.append(self._format_extra_replenishment(po_line, prod_qty, move.raw_material_production_id.id))
                line_qty -= prod_qty
            if line_qty:
                res.append(self._format_extra_replenishment(po_line, line_qty))

        return res

    def _format_extra_replenishment(self, po_line, quantity, production_id=False):
        po = po_line.order_id
        price = po_line.taxes_id.with_context(round=False).compute_all(
            po_line.price_unit, currency=po.currency_id, quantity=quantity, product=po_line.product_id, partner=po.partner_id
        )['total_void']
        return {
            '_name': 'purchase.order',
            'id': po.id,
            'cost': price,
            'quantity': quantity,
            'uom': po_line.product_uom,
            'production_id': production_id
        }

    def _get_replenishment_receipt(self, doc_in, components):
        res = super()._get_replenishment_receipt(doc_in, components)
        if doc_in._name == 'purchase.order':
            if doc_in.state != 'purchase':
                return self._format_receipt_date('estimated', doc_in.date_planned)
            in_pickings = doc_in.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            planned_date = max(in_pickings.mapped('scheduled_date')) if in_pickings else doc_in.date_planned
            return self._format_receipt_date('expected', planned_date)
        return res

    def _get_resupply_data(self, rules, rules_delay, quantity, uom_id, product, production):
        res = super()._get_resupply_data(rules, rules_delay, quantity, uom_id, product, production)
        if any(rule for rule in rules if rule.action == 'buy' and product.seller_ids):
            supplier = product._select_seller(quantity=quantity, uom_id=product.uom_id)
            if supplier:
                return {
                    'delay': supplier.delay + rules_delay,
                    'cost': supplier.price * uom_id._compute_quantity(quantity, supplier.product_uom),
                    'currency': supplier.currency_id,
                }
        return res

    def _is_doc_in_done(self, doc_in):
        if doc_in._name == 'purchase.order':
            return doc_in.state == 'purchase' and all(move.state in ('done', 'cancel') for move in doc_in.order_line.move_ids)
        return super()._is_doc_in_done(doc_in)

    def _get_origin(self, move):
        if move.purchase_line_id:
            return move.purchase_line_id.order_id
        return super()._get_origin(move)

    def _get_replenishment_mo_cost(self, product, quantity, uom_id, currency, move_in=False):
        if move_in and move_in.purchase_line_id:
            po_line = move_in.purchase_line_id
            po = po_line.order_id
            price = po_line.taxes_id.with_context(round=False).compute_all(
                po_line.price_unit, currency=po.currency_id, quantity=uom_id._compute_quantity(quantity, move_in.purchase_line_id.product_uom),
                product=po_line.product_id, partner=po.partner_id
            )['total_void']
            price = po_line.currency_id._convert(price, currency, (move_in.company_id or self.env.company), fields.Date.today())
            return currency.round(price)
        return super()._get_replenishment_mo_cost(product, quantity, uom_id, currency, move_in)
