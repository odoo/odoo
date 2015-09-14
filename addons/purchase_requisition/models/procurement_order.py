# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    requisition_id = fields.Many2one('purchase.requisition', string='Latest Requisition')

    @api.multi
    def make_po(self):
        ProcOrder = self.env['procurement.order']
        StockWarehouse = self.env['stock.warehouse']
        PurchaseRequisition = self.env['purchase.requisition']
        for procurement in self:
            if procurement.product_id.purchase_requisition == 'tenders':
                warehouse = StockWarehouse.search([('company_id', '=', procurement.company_id.id)], limit=1)
                requisition = PurchaseRequisition.create({
                    'origin': procurement.origin,
                    'date_end': procurement.date_planned,
                    'warehouse_id': warehouse.id,
                    'company_id': procurement.company_id.id,
                    'procurement_id': procurement.id,
                    'picking_type_id': procurement.rule_id.picking_type_id.id,
                    'line_ids': [(0, 0, {
                        'product_id': procurement.product_id.id,
                        'product_uom_id': procurement.product_uom.id,
                        'product_qty': procurement.product_qty
                    })],
                })
                procurement.message_post(body=_("Purchase Requisition created"))
                procurement.requisition_id = requisition
                ProcOrder |= procurement
        set_others = self - ProcOrder
        return super(ProcurementOrder, set_others).make_po()
