# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _get_exceptions_domain(self):
        return super(ProcurementGroup, self)._get_exceptions_domain() + [('requistion_line_ids', '=', False)]


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        if product_id.purchase_requisition != 'tenders':
            return super(StockRule, self)._run_buy(product_id, product_qty, product_uom, location_id, name, origin, values)
        values = self.env['purchase.requisition']._prepare_tender_values(product_id, product_qty, product_uom, location_id, name, origin, values)
        values['picking_type_id'] = self.picking_type_id.id
        self.env['purchase.requisition'].create(values)
        return True

    def _prepare_purchase_order(self, product_id, product_qty, product_uom, origin, values, partner):
        res = super(StockRule, self)._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner)
        res['partner_ref'] = values['supplier'].purchase_requisition_id.name
        res['requisition_id'] = values['supplier'].purchase_requisition_id.id
        if values['supplier'].purchase_requisition_id.currency_id:
            res['currency_id'] = values['supplier'].purchase_requisition_id.currency_id.id
        return res

    def _make_po_get_domain(self, values, partner):
        domain = super(StockRule, self)._make_po_get_domain(values, partner)
        if 'supplier' in values and values['supplier'].purchase_requisition_id:
            domain += (
                ('requisition_id', '=', values['supplier'].purchase_requisition_id.id),
            )
        return domain


class StockMove(models.Model):
    _inherit = 'stock.move'

    requisition_line_ids = fields.One2many('purchase.requisition.line', 'move_dest_id')

    def _get_upstream_documents_and_responsibles(self, visited):
        if self.requisition_line_ids:
            return [(requisition_line.requisition_id, requisition_line.requisition_id.user_id, visited) for requisition_line in self.requisition_line_ids if requisition_line.state not in ('done', 'cancel')]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)


class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _quantity_in_progress(self):
        res = super(Orderpoint, self)._quantity_in_progress()
        for op in self:
            for pr in self.env['purchase.requisition'].search([('state','=','draft'),('origin','=',op.name)]):
                for prline in pr.line_ids.filtered(lambda l: l.product_id.id == op.product_id.id):
                    res[op.id] += prline.product_uom_id._compute_quantity(prline.product_qty, op.product_uom, round=False)
        return res
